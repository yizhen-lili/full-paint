"""顏料準備清單 service —

給定 production_job_id + 製作件數 quantity，回傳該任務需要的物理顏料清單
（按 output_label / 用量加總、含庫存對照）。

支援三類來源：商品 variant / 客製訂單 / 試驗（standalone）任務。三類都歸結到
production_job_id 查詢，user 在 picker UI 選哪邊由 sources endpoint 列出。

資料來源：palette_color_mappings JOIN physical_colors（finalize 時已寫入
required_ml 與 output_label），SQL 層 group_by physical_color_id 即可聚合。
"""
from uuid import UUID

from sqlalchemy import and_, exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from auth.models import User
from color.models import PhysicalColor
from core.exceptions import BadRequestError, NotFoundError
from custom.models import CustomRequest
from palette.models import PaletteColorMapping
from product.models import Product, ProductVariant
from production.models import ProductionJob


def _rgb_to_hex(rgb_value: list | tuple | None) -> str:
    """PhysicalColor.rgb 是 JSONB list（如 [255, 0, 0]）→ "#FF0000"。

    None / 異常 → 灰色保底，避免前端 NaN。
    """
    if not rgb_value or not isinstance(rgb_value, (list, tuple)) or len(rgb_value) < 3:
        return "#CCCCCC"
    try:
        r, g, b = int(rgb_value[0]), int(rgb_value[1]), int(rgb_value[2])
    except (TypeError, ValueError):
        return "#CCCCCC"
    r = max(0, min(255, r))
    g = max(0, min(255, g))
    b = max(0, min(255, b))
    return f"#{r:02X}{g:02X}{b:02X}"


async def calculate_for_job(
    db: AsyncSession, job_id: UUID, quantity: int,
) -> dict:
    """指定 job + 製作件數 → 物理顏料聚合需求 + 庫存對照。

    錯誤：
    - 404 job 不存在
    - 400 JOB_NOT_FINALIZED：job.finalized_at 為 null（尚未完成顏色對應）
    """
    job = await db.get(ProductionJob, job_id)
    if job is None:
        raise NotFoundError("製作任務不存在")

    if job.finalized_at is None:
        raise BadRequestError(
            detail="該任務尚未完成顏色對應，無法查詢顏料需求",
            code="JOB_NOT_FINALIZED",
            extra={"production_job_id": str(job_id)},
        )

    # SQL 層聚合：同 physical_color_id 的 mapping rows sum(required_ml)
    # output_label 在同色 mapping 內一致，min() 是純取唯一值的安全手法
    rows = (await db.execute(
        select(
            PhysicalColor.id,
            PhysicalColor.code,
            PhysicalColor.name,
            PhysicalColor.rgb,
            PhysicalColor.stock_ml,
            func.min(PaletteColorMapping.output_label).label("output_label"),
            func.sum(PaletteColorMapping.required_ml).label("required_per_unit_ml"),
        )
        .join(
            PaletteColorMapping,
            PaletteColorMapping.physical_color_id == PhysicalColor.id,
        )
        .where(PaletteColorMapping.production_job_id == job.id)
        .group_by(PhysicalColor.id)
        .order_by(func.min(PaletteColorMapping.output_label).asc())
    )).all()

    items = []
    for r in rows:
        per_unit = float(r.required_per_unit_ml or 0)
        total_ml = round(per_unit * quantity, 2)
        stock_ml = float(r.stock_ml or 0)
        shortage_ml = round(max(0.0, total_ml - stock_ml), 2)
        items.append({
            "physical_color_id": str(r.id),
            "output_label": r.output_label,
            "code": r.code,
            "name": r.name,
            "hex": _rgb_to_hex(r.rgb),
            "required_per_unit_ml": round(per_unit, 2),
            "total_required_ml": total_ml,
            "stock_ml": stock_ml,
            "shortage_ml": shortage_ml,
            "is_short": shortage_ml > 0,
        })

    return {
        "production_job_id": str(job.id),
        "quantity": quantity,
        "canvas_w_cm": float(job.canvas_w_cm),
        "canvas_h_cm": float(job.canvas_h_cm),
        "items": items,
        "summary": {
            "total_colors": len(items),
            "short_count": sum(1 for i in items if i["is_short"]),
            "total_required_ml": round(
                sum(i["total_required_ml"] for i in items), 2,
            ),
        },
    }


# ── Sources endpoint：列出可查詢的三類來源（picker 用）─────────────────


async def list_sources(db: AsyncSession) -> dict:
    """列出顏料查詢可選的三類來源。

    所有 source 都需 status=completed 才有意義（mapping 才可能存在）；
    finalized 與否各自帶 flag，admin 可看到「未對應」項目並知道要先去 mapping 頁。

    回傳結構：
    {
      products: [{id, title, status, variants: [{...}]}],
      custom_requests: [{custom_request_id, job_id, label, status, canvas, is_finalized}],
      standalone_jobs: [{job_id, label, canvas, is_finalized, created_at}],
    }
    """
    # ── 商品（含 variants）──────────────────────────────────────────────
    # 把每個 product 帶它的 variants（不論 product 狀態都列：on_sale / draft / off_sale）
    products_rows = (await db.execute(
        select(Product).order_by(Product.title.asc())
    )).scalars().all()

    products_list = []
    for prod in products_rows:
        variant_rows = (await db.execute(
            select(ProductVariant, ProductionJob)
            .join(ProductionJob, ProductVariant.production_job_id == ProductionJob.id)
            .where(ProductVariant.product_id == prod.id)
            .where(ProductionJob.status == "completed")
            .order_by(ProductVariant.created_at.asc())
        )).all()
        if not variant_rows:
            continue
        products_list.append({
            "id": str(prod.id),
            "title": prod.title,
            "status": prod.status.value if hasattr(prod.status, "value") else str(prod.status),
            "variants": [
                {
                    "variant_id": str(v.id),
                    "production_job_id": str(j.id),
                    "canvas_w_cm": float(j.canvas_w_cm),
                    "canvas_h_cm": float(j.canvas_h_cm),
                    "price": float(v.price),
                    "is_finalized": j.finalized_at is not None,
                }
                for v, j in variant_rows
            ],
        })

    # ── 客製訂單 ────────────────────────────────────────────────────────
    # 有綁 production_job 的 custom_requests（即 quote 已確認 job 已建）
    custom_rows = (await db.execute(
        select(CustomRequest, User, ProductionJob)
        .join(User, CustomRequest.user_id == User.id)
        .join(
            ProductionJob,
            ProductionJob.custom_request_id == CustomRequest.id,
        )
        .where(ProductionJob.status == "completed")
        .order_by(CustomRequest.created_at.desc())
    )).all()

    custom_list = [
        {
            "custom_request_id": str(cr.id),
            "production_job_id": str(j.id),
            "label": f"客製 - {u.name}",
            "status": cr.status.value if hasattr(cr.status, "value") else str(cr.status),
            "canvas_w_cm": float(j.canvas_w_cm),
            "canvas_h_cm": float(j.canvas_h_cm),
            "is_finalized": j.finalized_at is not None,
        }
        for cr, u, j in custom_rows
    ]

    # ── 試驗任務（standalone）─────────────────────────────────────────
    # 沒綁 variant + 沒綁 custom_request_id 的 completed job
    variant_alias = aliased(ProductVariant)
    standalone_rows = (await db.execute(
        select(ProductionJob)
        .where(ProductionJob.status == "completed")
        .where(ProductionJob.custom_request_id.is_(None))
        .where(
            ~exists().where(
                and_(
                    variant_alias.production_job_id == ProductionJob.id,
                )
            )
        )
        .order_by(ProductionJob.created_at.desc())
    )).scalars().all()

    standalone_list = [
        {
            "production_job_id": str(j.id),
            "label": f"試驗任務 #{str(j.id)[:8]}",
            "canvas_w_cm": float(j.canvas_w_cm),
            "canvas_h_cm": float(j.canvas_h_cm),
            "detail": j.detail.value if hasattr(j.detail, "value") else str(j.detail),
            "difficulty": j.difficulty.value if hasattr(j.difficulty, "value") else str(j.difficulty),
            "created_at": j.created_at,
            "is_finalized": j.finalized_at is not None,
        }
        for j in standalone_rows
    ]

    return {
        "products": products_list,
        "custom_requests": custom_list,
        "standalone_jobs": standalone_list,
    }
