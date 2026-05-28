"""顏料準備清單 service —

給定 ProductVariant id + 製作件數 quantity，回傳該規格需要的物理顏料清單
（按 output_label / 用量加總、含庫存對照）。

資料來源：palette_color_mappings JOIN physical_colors（finalize 時已寫入 required_ml
與 output_label），SQL 層 group_by physical_color_id 即可聚合。
"""
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from color.models import PhysicalColor
from core.exceptions import BadRequestError, NotFoundError
from palette.models import PaletteColorMapping
from product.models import ProductVariant
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


async def calculate_for_variant(
    db: AsyncSession, variant_id: UUID, quantity: int,
) -> dict:
    """單一 variant + quantity 的顏料需求聚合。

    - 不存在 → NotFoundError 404
    - job 尚未 finalize → BadRequestError(code=VARIANT_NOT_FINALIZED) 400
    - 已 finalize → 回每個物理色一筆（含庫存與缺料）
    """
    variant = await db.get(ProductVariant, variant_id)
    if variant is None:
        raise NotFoundError("規格不存在")

    job = await db.get(ProductionJob, variant.production_job_id)
    if job is None:
        # ProductVariant.production_job_id NOT NULL + FK，但 job 被 raw SQL 刪可能孤兒
        raise NotFoundError("規格綁定的製作任務不存在")

    if job.finalized_at is None:
        raise BadRequestError(
            detail="該規格尚未完成顏色對應，無法查詢顏料需求",
            code="VARIANT_NOT_FINALIZED",
            extra={
                "variant_id": str(variant_id),
                "production_job_id": str(job.id),
            },
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
        # round() 對 .5 用銀行進位、不適合用量場景 — 寧多估也不少；用 ceil 到 0.01
        # 但既有 complete_mappings 已 ceil 進 0.01，這裡 ×qty 後也保 2 位
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
        "variant_id": str(variant_id),
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
