import json
import logging
import math
from collections import defaultdict
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from color.models import PhysicalColor
from color.service import lab_distance
from core.exceptions import BadRequestError, NotFoundError
from palette.models import MappedByEnum, PaletteColorMapping
from production.models import ProductionJob

logger = logging.getLogger(__name__)


async def list_copy_candidates(db: AsyncSession, job_id: UUID) -> list[dict]:
    """列出可作為「從其他 job 複製對應」來源的 job：
    - 同 batch_id 或同 image_id（admin_color.md §2.2）
    - 已有完整 palette_color_mappings（每筆色號都對到 physical_color）
    - 排除自己

    回傳依 created_at desc 排序的 list[dict]，每筆已含 filled signed URL。
    """
    from sqlalchemy import and_, func, or_

    from production.service import _make_signed_url

    target = await _get_job_or_404(db, job_id)

    if target.batch_id is None and target.image_id is None:
        return []

    # 撈同批次或同原圖的其他 job
    conditions = []
    if target.batch_id is not None:
        conditions.append(ProductionJob.batch_id == target.batch_id)
    if target.image_id is not None:
        conditions.append(ProductionJob.image_id == target.image_id)
    related = (
        await db.execute(
            select(ProductionJob).where(
                and_(
                    or_(*conditions),
                    ProductionJob.id != target.id,
                    ProductionJob.status == "completed",
                )
            ).order_by(ProductionJob.created_at.desc())
        )
    ).scalars().all()

    # 過濾出有完整 mapping 的 job（mapping 數 >= palette_json 長度）
    items = []
    for j in related:
        if not j.palette_json:
            continue
        cnt = (
            await db.execute(
                select(func.count(PaletteColorMapping.id)).where(
                    PaletteColorMapping.production_job_id == j.id
                )
            )
        ).scalar()
        if cnt < len(j.palette_json):
            continue
        relation = (
            "same_batch"
            if j.batch_id is not None and j.batch_id == target.batch_id
            else "same_image"
        )
        items.append({
            "job_id": j.id,
            "detail": str(j.detail),
            "difficulty": str(j.difficulty),
            "canvas_w_cm": float(j.canvas_w_cm),
            "canvas_h_cm": float(j.canvas_h_cm),
            "num_colors_used": j.num_colors_used,
            "filled_template_url": (
                _make_signed_url(j.filled_template_url) if j.filled_template_url else None
            ),
            "relation": relation,
            "created_at": j.created_at,
        })
    return items


async def get_mappings(db: AsyncSession, job_id: UUID) -> list[dict]:
    job = await _get_job_or_404(db, job_id)

    result = await db.execute(
        select(PaletteColorMapping).where(
            PaletteColorMapping.production_job_id == job_id
        )
    )
    mappings = list(result.scalars().all())

    if not mappings:
        if not job.palette_json:
            return []
        mappings = await _auto_map(db, job)

    return await _enrich_mappings(db, mappings)


async def update_mapping(
    db: AsyncSession, job_id: UUID, template_id: int, physical_color_id: UUID
) -> dict:
    job = await _get_job_or_404(db, job_id)

    color = await db.execute(
        select(PhysicalColor).where(
            PhysicalColor.id == physical_color_id,
            PhysicalColor.is_active == True,  # noqa: E712
        )
    )
    if not color.scalar_one_or_none():
        raise NotFoundError("實體色不存在或已停用")

    result = await db.execute(
        select(PaletteColorMapping).where(
            PaletteColorMapping.production_job_id == job_id,
            PaletteColorMapping.template_id == template_id,
        )
    )
    mapping = result.scalar_one_or_none()
    if not mapping:
        raise NotFoundError("調色板對應不存在")

    old_pid = mapping.physical_color_id
    is_color_change = old_pid != physical_color_id

    mapping.physical_color_id = physical_color_id
    mapping.mapped_by = MappedByEnum.manual
    mapping.required_ml = None

    # 換色 → 清掉這格的 output_label（它是舊實體色的編號，已過期）。下次 finalize
    # 才能正確判斷「此格的新實體色」是既有色（沿用號）還是新色（補號），避免舊號污染。
    if is_color_change:
        mapping.output_label = None

    # 物理色實際變動 + job 已 finalize → 清 finalized_at（保留 template_final_url
    # 讓前端能區分「曾 finalize 過 stale」vs「從未 finalize」兩種狀態）
    # 同色 no-op 不觸發失效，避免 admin 誤點不變色就被迫重產
    if is_color_change and job.finalized_at is not None:
        job.finalized_at = None
        # 換色 → 既有「合併建議」跟「合併版 preview」都失效（基於舊 mapping 算的、
        # polygon_id 雖在 SVG 仍存在，但「合進哪個 target」的色彩判斷已過期）。
        # 一起清掉避免 admin 在 stale UI 上做 confirm 決定（reviewer 必修項）。
        if job.pending_auto_merges or job.template_final_merged_preview_url:
            _delete_merged_preview_blob(job_id)
            job.pending_auto_merges = None
            job.template_final_merged_preview_url = None
        logger.info(
            "update_mapping: job %s finalized_at + 合併建議已清空（template_id=%s 換色）",
            job_id, template_id,
        )

    await db.commit()
    await db.refresh(mapping)

    enriched = await _enrich_mappings(db, [mapping])
    return enriched[0]


async def copy_from_job(
    db: AsyncSession, job_id: UUID, source_job_id: UUID
) -> list[dict]:
    if job_id == source_job_id:
        raise BadRequestError("不能從自身複製調色板對應")
    await _get_job_or_404(db, job_id)
    await _get_job_or_404(db, source_job_id)

    source_result = await db.execute(
        select(PaletteColorMapping).where(
            PaletteColorMapping.production_job_id == source_job_id
        )
    )
    source_mappings = list(source_result.scalars().all())
    if not source_mappings:
        raise BadRequestError("來源 job 沒有調色板對應資料")

    source_by_template = {m.template_id: m for m in source_mappings}

    source_color_ids = list({m.physical_color_id for m in source_mappings})
    active_result = await db.execute(
        select(PhysicalColor).where(
            PhysicalColor.id.in_(source_color_ids),
            PhysicalColor.is_active == True,  # noqa: E712
        )
    )
    active_color_ids = {c.id for c in active_result.scalars().all()}
    missing = [
        tid for tid, m in source_by_template.items()
        if m.physical_color_id not in active_color_ids
    ]
    if missing:
        raise BadRequestError(
            f"來源 job 部分對應色彩已停用或不存在，無法複製（template_id: {missing}）"
        )

    existing_result = await db.execute(
        select(PaletteColorMapping).where(
            PaletteColorMapping.production_job_id == job_id
        )
    )
    existing = {m.template_id: m for m in existing_result.scalars().all()}

    for template_id, src in source_by_template.items():
        if template_id in existing:
            ex = existing[template_id]
            # 換色 → 清掉舊號（與 update_mapping 一致）。否則 finalize 補號時這個殘存
            # 舊號會跟別的實體色撞號（兩個不同實體色拿到同一 output_label）。
            if ex.physical_color_id != src.physical_color_id:
                ex.output_label = None
            ex.physical_color_id = src.physical_color_id
            ex.mapped_by = MappedByEnum.manual
            ex.required_ml = None
        else:
            new_mapping = PaletteColorMapping(
                production_job_id=job_id,
                template_id=template_id,
                algorithm_rgb=src.algorithm_rgb,
                physical_color_id=src.physical_color_id,
                mapped_by=MappedByEnum.manual,
                required_ml=None,
            )
            db.add(new_mapping)

    await db.commit()

    result = await db.execute(
        select(PaletteColorMapping).where(
            PaletteColorMapping.production_job_id == job_id
        )
    )
    mappings = list(result.scalars().all())
    return await _enrich_mappings(db, mappings)


async def complete_mappings(db: AsyncSession, job_id: UUID) -> dict:
    job = await _get_job_or_404(db, job_id)

    result = await db.execute(
        select(PaletteColorMapping).where(
            PaletteColorMapping.production_job_id == job_id
        )
    )
    mappings = list(result.scalars().all())

    if not mappings:
        raise BadRequestError("尚無調色板對應資料")

    if job.palette_json:
        palette_ids = {entry["template_id"] for entry in job.palette_json}
        mapped_ids = {m.template_id for m in mappings}
        if palette_ids - mapped_ids:
            raise BadRequestError("尚有未對應的色號，無法完成")

    settings = await _get_settings(db)
    paint_ml_per_cm2 = float(settings.get("paint_ml_per_cm2", "0.05"))
    paint_min_ml = float(settings.get("paint_min_ml", "3.0"))
    paint_buffer_ratio = float(settings.get("paint_buffer_ratio", "1.3"))

    area = float(job.canvas_w_cm) * float(job.canvas_h_cm)

    palette_by_id: dict[int, dict] = {}
    if job.palette_json:
        for entry in job.palette_json:
            palette_by_id[entry["template_id"]] = entry

    color_ids = [m.physical_color_id for m in mappings]
    colors_result = await db.execute(
        select(PhysicalColor).where(PhysicalColor.id.in_(color_ids))
    )
    colors_by_id = {c.id: c for c in colors_result.scalars().all()}

    shortage_colors = []
    for mapping in mappings:
        entry = palette_by_id.get(mapping.template_id, {})
        # pbn_gen 在 production/engine.py 寫 percent 是 0~100 形式（百分比，
        # e.g. 47.5 表示 47.5%）— 用前要除 100 轉成 0~1 ratio，否則 required_ml
        # 會大 100 倍（曾發生 30×40 cm 一張畫單色需 2933 ml 的 bug）。
        percent_pct = float(entry.get("percent", 0.0))
        percent_ratio = percent_pct / 100.0
        required = max(
            area * percent_ratio * paint_ml_per_cm2 * paint_buffer_ratio,
            paint_min_ml,
        )
        required = math.ceil(required * 100) / 100
        mapping.required_ml = required

        color = colors_by_id.get(mapping.physical_color_id)
        if color and float(color.stock_ml) < required:
            shortage_colors.append({
                "template_id": mapping.template_id,
                "physical_color_id": mapping.physical_color_id,
                "code": color.code,
                "name": color.name,
            })

    await db.commit()

    # 對應完成後產出「實體色版最終模板」（重編號 + template_final.svg + palette_final.json）。
    # 密集模板 finalize 是重活、可能數十秒，放在這個 HTTP 請求裡同步跑會閘道逾時 502，
    # 所以丟給 Celery worker 非同步跑；這裡立刻返回（shortage_colors 不依賴 finalize）。
    # 模板稍後產好，前端輪詢 job.finalized_at / template_final_url 取得。
    try:
        from core.celery_app import celery_app  # noqa: PLC0415
        # retry=False：broker 短暫不可用時 send_task 立即失敗、不阻塞 HTTP 請求
        # （絕不 fallback 同步跑 finalize —— 那又會把這個請求拖到逾時 502）。
        celery_app.send_task(
            "production.finalize_template", args=[str(job_id)], retry=False
        )
    except Exception as e:  # noqa: BLE001
        # 入列失敗只 log：模板未產出（best-effort），admin 重按完成對應或後製會補產。
        logger.warning(
            "enqueue finalize_template failed for %s: %s（模板未產，可重按完成對應補產）",
            job_id, e,
        )

    return {
        "all_stocked": len(shortage_colors) == 0,
        "shortage_colors": shortage_colors,
    }


async def confirm_pending_merges(db: AsyncSession, job_id: UUID) -> dict:
    """把 pending_auto_merges 轉成 per-polygon post_process merge_color 批次。

    **重要設計** — 不直接改 palette_color_mappings（per template_id），改走既有
    post_process pipeline 的 merge_color op（per polygon_id）。
    這樣 template #7 內 5 個 tiny polygon 各自合進 target、95 個大塊保留 #7 不變色。

    流程：
    1. 取 job.pending_auto_merges（無 → 400）
    2. 把每筆建議轉成 {op: "merge_color", polygon_id, target_template_id}
    3. 清空 pending_auto_merges（避免重複）
    4. 呼叫 production.service.post_process → Celery 在 SVG 層級改 polygon 歸屬
       + 重產 template.svg / palette_json / template_final / filled_template_final
    """
    job = await _get_job_or_404(db, job_id)
    pending = job.pending_auto_merges or []
    if not pending:
        raise BadRequestError("沒有待確認的自動合併建議")

    # 轉成 per-polygon merge_color operations
    operations: list[dict] = []
    seen_polygon_ids: set[str] = set()  # 防 same polygon_id 在 list 內重複 → Celery 拒
    for rec in pending:
        polygon_id = rec.get("polygon_id")
        target_tid = rec.get("target_template_id")
        if not polygon_id or target_tid is None:
            continue
        if polygon_id in seen_polygon_ids:
            continue
        seen_polygon_ids.add(polygon_id)
        operations.append({
            "op": "merge_color",
            "polygon_id": str(polygon_id),
            "target_template_id": int(target_tid),
        })

    if not operations:
        raise BadRequestError(
            "pending 內無有效 polygon_id（可能是舊版資料）— 請重按「完成對應」重新偵測",
        )

    pending_count = len(pending)
    # 清掉 pending（避免下次 finalize 又把舊的回寫）
    # preview URL 跟 pending 同生命週期 — 一起清掉避免 UI 殘留指向舊 SVG
    # GCS blob 也一併刪掉避免 Firebase orphan（reviewer 必修項）
    _delete_merged_preview_blob(job_id)
    job.pending_auto_merges = None
    job.template_final_merged_preview_url = None
    await db.commit()

    logger.info(
        "confirm_pending_merges: job=%s dispatching %d merge_color ops (from %d pending)",
        job_id, len(operations), pending_count,
    )

    # 走既有 post_process pipeline（Celery）— per-polygon 精準改色 + 重 finalize
    from production.service import post_process  # noqa: PLC0415
    updated_job = await post_process(db, job_id, {"operations": operations})
    return {
        "operations_dispatched": len(operations),
        "pending_count": pending_count,
        "job_status": (
            updated_job.status.value
            if hasattr(updated_job.status, "value")
            else str(updated_job.status)
        ),
    }


async def reject_pending_merges(db: AsyncSession, job_id: UUID) -> dict:
    """拒絕自動合併建議：清空 pending_auto_merges、不動 mapping、不重 finalize。

    admin 不喜歡這次的合併建議 → 回頭手動調 mapping 或直接維持現狀。
    """
    job = await _get_job_or_404(db, job_id)
    pending_count = len(job.pending_auto_merges or [])
    job.pending_auto_merges = None
    # preview URL 跟 pending 同生命週期 — reject 後也一起清，避免 UI 殘留對比
    # GCS blob 也一併刪掉避免 Firebase orphan（reviewer 必修項）
    _delete_merged_preview_blob(job_id)
    job.template_final_merged_preview_url = None
    await db.commit()
    logger.info(
        "reject_pending_merges: job=%s rejected=%d pending",
        job_id, pending_count,
    )
    return {"rejected_count": pending_count}


async def finalize_template(db: AsyncSession, job_id: UUID) -> dict:
    """產出「實體色版最終模板」：

    1. 依 palette_json.pixels 統計每個 template_id 的塗色面積
    2. 按 physical_color_id groupby，組內總 pixels 加總當排序鍵
    3. 由大到小派 output_label = 1..N，回寫每個 mapping 的 output_label
    4. 從 Firebase 拉 template.svg → renumber_svg_labels → 上傳 template_final.svg
    5. 組 palette_final.json（legend 資料源）→ 上傳
    6. 更新 job.template_final_url / palette_final_url / finalized_at

    呼叫端：complete_mappings 完成 required_ml 計算後自動觸發。冪等。

    回傳：{"output_labels_count": N, "template_final_url": ..., "palette_final_url": ...}
    """
    from core.firebase import get_bucket  # noqa: PLC0415
    from palette.svg_consolidate import regenerate_merged_svg  # noqa: PLC0415

    job = await _get_job_or_404(db, job_id)

    if not job.svg_url:
        raise BadRequestError("job 尚無 template.svg URL，無法 finalize")
    if not job.palette_json:
        raise BadRequestError("job 尚無 palette_json，無法統計面積")

    # ── 「原始版」保留 ─────────────────────────────────────────────────────
    # 第二次以上 finalize 時把當前 latest 搬到 archive/ 路徑，給 admin 比對用
    # 條件：曾經 finalize 過（template_final_url 已存在）+ 尚未 archive 過
    if job.template_final_url and not job.original_template_final_url:
        try:
            archive_bucket = get_bucket()
            _copy_to_archive(archive_bucket, job_id, "template_final.svg")
            _copy_to_archive(archive_bucket, job_id, "palette_final.json")
            _copy_to_archive(archive_bucket, job_id, "filled_template_final.png")
            job.original_template_final_url = (
                f"gs://{archive_bucket.name}/production_jobs/{job_id}/"
                f"archive/template_final_v0.svg"
            )
            job.original_palette_final_url = (
                f"gs://{archive_bucket.name}/production_jobs/{job_id}/"
                f"archive/palette_final_v0.json"
            )
            job.original_filled_template_final_url = (
                f"gs://{archive_bucket.name}/production_jobs/{job_id}/"
                f"archive/filled_template_final_v0.png"
            )
            job.original_finalized_at = job.finalized_at
            await db.flush()
            logger.info("finalize: archived original version for job %s", job_id)
        except Exception as e:  # noqa: BLE001
            # best-effort：archive 失敗不阻擋當次 finalize 流程
            logger.warning("finalize: archive original failed for %s: %s", job_id, e)

    mapping_rows = list(
        (
            await db.execute(
                select(PaletteColorMapping).where(
                    PaletteColorMapping.production_job_id == job_id
                )
            )
        ).scalars().all()
    )
    if not mapping_rows:
        raise BadRequestError("尚無調色板對應資料，無法 finalize")

    # 1. template_id → pixels (來自 pbn_gen 的 palette_json，必有 pixels 欄位)
    pixels_by_template: dict[int, int] = {}
    for entry in job.palette_json:
        pixels_by_template[int(entry["template_id"])] = int(entry.get("pixels", 0))

    # 2. groupby physical_color_id，組內 pixels 加總
    groups: dict[UUID, list[PaletteColorMapping]] = defaultdict(list)
    for m in mapping_rows:
        groups[m.physical_color_id].append(m)

    def group_area(pc_id: UUID) -> int:
        return sum(pixels_by_template.get(m.template_id, 0) for m in groups[pc_id])

    # 3. 派 label — 保留既有編號：已對應過的實體色沿用原號（避免改一格就全部跳號），
    #    只有「沒有號的新實體色」才補號，取最小未使用整數（填補空號再往後接）。
    #    新色的補號順序沿用面積由大到小，讓新出現的大色塊拿較小號；同面積用 pc_id 破 tie。
    #    註：換色時 update_mapping 會把該格 output_label 清成 None，故同組殘存的號都是
    #    「此實體色上次 finalize 的號」，min() 取其一即可（同組應一致）。
    label_of_pc: dict[UUID, int] = {}
    used_labels: set[int] = set()
    new_pool: list[UUID] = []
    # 既有色沿用原號；先搶先得（號小者優先）。萬一兩色撞同號（理論上不該發生，
    # 因換色都會 reset output_label；此為防呆）→ 撞號者丟回新色池重新補號。
    prev_pairs = []
    for pc_id, members in groups.items():
        prev = [m.output_label for m in members if m.output_label is not None]
        if prev:
            prev_pairs.append((pc_id, min(prev)))
        else:
            new_pool.append(pc_id)
    for pc_id, lbl in sorted(prev_pairs, key=lambda x: x[1]):
        if lbl in used_labels:
            new_pool.append(pc_id)  # 撞號 → 當新色補號
        else:
            label_of_pc[pc_id] = lbl
            used_labels.add(lbl)

    new_pc_ids = sorted(
        new_pool,
        key=lambda pc_id: (-group_area(pc_id), str(pc_id)),
    )
    next_label = 1
    for pc_id in new_pc_ids:
        while next_label in used_labels:
            next_label += 1
        label_of_pc[pc_id] = next_label
        used_labels.add(next_label)

    label_map: dict[int, int] = {}   # template_id → output_label
    for pc_id, members in groups.items():
        lbl = label_of_pc[pc_id]
        for m in members:
            m.output_label = lbl
            label_map[m.template_id] = lbl

    # 4. 先建 palette_final（後面 SVG 合併要用它取得實體色 RGB 算新 tint）
    colors_by_id = {
        c.id: c
        for c in (
            await db.execute(
                select(PhysicalColor).where(
                    PhysicalColor.id.in_(list(groups.keys()))
                )
            )
        ).scalars().all()
    }

    # 依最終 output_label 排序輸出，確保 legend 與模板號碼一致
    palette_final = []
    for pc_id in sorted(groups.keys(), key=lambda p: label_of_pc[p]):
        members = groups[pc_id]
        color = colors_by_id.get(pc_id)
        total_pixels = sum(pixels_by_template.get(m.template_id, 0) for m in members)
        total_ml = sum(float(m.required_ml or 0) for m in members)
        rgb = list(color.rgb) if color else [0, 0, 0]
        palette_final.append({
            "output_label": label_of_pc[pc_id],
            "physical_color_id": str(pc_id),
            "code": color.code if color else "?",
            "name": color.name if color else "?",
            "rgb": rgb,
            "hex": "#{:02X}{:02X}{:02X}".format(*rgb),
            "total_pixels": total_pixels,
            "total_ml": round(total_ml, 2),
            "member_template_ids": sorted(m.template_id for m in members),
        })

    # 5. SVG 合併 — 拉 template.svg → 同 output_label 的多邊形 Shapely union
    #    → 渲染為新 SVG（消除同色相鄰假邊界）→ 上傳 final
    #
    # 跑兩次：主版本 (未套 tiny merge，user 要的細緻版) + preview (套 tiny merge，
    # 給 admin 對比看「按確認合併會變什麼樣」)。 merge_records 從合併版取得。
    bucket = get_bucket()
    svg_path = _gs_path(job.svg_url, bucket.name)
    svg_blob = bucket.blob(svg_path)
    svg_bytes = svg_blob.download_as_bytes()

    # 主版本：未合併（細緻）
    final_svg_bytes, _ = regenerate_merged_svg(
        svg_bytes, label_map, job.palette_json, palette_final,
        enable_tiny_merge=False,
    )
    final_svg_path = f"production_jobs/{job_id}/template_final.svg"
    bucket.blob(final_svg_path).upload_from_string(
        final_svg_bytes, content_type="image/svg+xml",
    )
    template_final_url = f"gs://{bucket.name}/{final_svg_path}"

    # preview：合併版 + 拿 merge_records 給 pending_auto_merges
    merged_preview_svg_bytes, auto_merge_records = regenerate_merged_svg(
        svg_bytes, label_map, job.palette_json, palette_final,
        enable_tiny_merge=True,
    )
    template_final_merged_preview_url: str | None = None
    if auto_merge_records:
        # 只在有 tiny merge 建議時才上傳 preview，避免空建議時浪費 storage
        preview_svg_path = (
            f"production_jobs/{job_id}/template_final_merged_preview.svg"
        )
        bucket.blob(preview_svg_path).upload_from_string(
            merged_preview_svg_bytes, content_type="image/svg+xml",
        )
        template_final_merged_preview_url = (
            f"gs://{bucket.name}/{preview_svg_path}"
        )

    # 6. 上傳 palette_final.json（legend 用）
    palette_final_path = f"production_jobs/{job_id}/palette_final.json"
    bucket.blob(palette_final_path).upload_from_string(
        json.dumps(palette_final, ensure_ascii=False, indent=2),
        content_type="application/json",
    )
    palette_final_url = f"gs://{bucket.name}/{palette_final_path}"

    # 7. 生成「實體色版」filled preview —— 直接把 template_final.svg 的多邊形用實體色
    # 原色 rasterize（與線稿**同一份幾何 + 同一套 per-part z-order**）。保證
    # 「填色預覽 = 照線稿塗完的真實樣子」，不再用 snapped_rgb 點陣（那會比線稿細、
    # 區塊位置對不上 → 預覽過度承諾）。best-effort：失敗只 log。
    filled_template_final_url: str | None = None
    try:
        from palette.svg_consolidate import render_filled_png  # noqa: PLC0415
        filled_bytes = render_filled_png(final_svg_bytes, palette_final)
        filled_path = f"production_jobs/{job_id}/filled_template_final.png"
        bucket.blob(filled_path).upload_from_string(
            filled_bytes, content_type="image/png",
        )
        filled_template_final_url = f"gs://{bucket.name}/{filled_path}"
    except Exception as e:  # noqa: BLE001
        logger.warning(
            "filled_template_final generation failed for %s: %s", job_id, e,
        )

    # 8. 更新 job 欄位 + commit
    job.template_final_url = template_final_url
    job.palette_final_url = palette_final_url
    if filled_template_final_url:
        job.filled_template_final_url = filled_template_final_url
    # preview URL 跟 pending_auto_merges 同生命週期：有建議 → 兩者皆有；
    # 空建議 → 兩者皆 None。confirm/reject 後也應該被一起清掉（既有 endpoints 已處理）。
    job.template_final_merged_preview_url = template_final_merged_preview_url
    job.finalized_at = datetime.now(UTC)
    # 自動合併建議：svg_consolidate 偵測到的微小色塊建議清單，待 admin 確認後寫 DB
    # 空清單 → 設 None（NULL）讓前端用 ?.length 判斷無 pending
    job.pending_auto_merges = auto_merge_records if auto_merge_records else None
    await db.commit()

    logger.info(
        "finalize_template: job=%s mappings=%d unique_colors=%d",
        job_id, len(mapping_rows), len(groups),
    )
    return {
        "output_labels_count": len(groups),
        "template_final_url": template_final_url,
        "palette_final_url": palette_final_url,
    }


def _gs_path(url: str, bucket_name: str) -> str:
    """從 gs://bucket/path 萃出 path（不含 bucket）；非 gs:// 直接回 url。"""
    prefix = f"gs://{bucket_name}/"
    if url.startswith(prefix):
        return url[len(prefix):]
    if url.startswith("gs://"):
        # 萬一 bucket name 不同（測試環境），仍盡力解析
        return url.split("/", 3)[-1]
    return url


# ── helpers ──────────────────────────────────────────────────────────────────

def _delete_merged_preview_blob(job_id: UUID) -> None:
    """刪 GCS 上「合併建議套用後」preview SVG，避免 confirm/reject/換色清掉 DB
    URL 之後 Firebase 物件殘留（reviewer 必修項：Firebase orphan）。

    Best-effort：bucket 取得失敗、blob 不存在、刪除失敗都只 log 不 raise。
    """
    try:
        from core.firebase import get_bucket  # noqa: PLC0415

        bucket = get_bucket()
        path = f"production_jobs/{job_id}/template_final_merged_preview.svg"
        blob = bucket.blob(path)
        if blob.exists():
            blob.delete()
            logger.info(
                "_delete_merged_preview_blob: deleted %s for job %s", path, job_id,
            )
    except Exception as e:  # noqa: BLE001
        logger.warning(
            "_delete_merged_preview_blob: failed for job %s — %s: %s",
            job_id, type(e).__name__, e,
        )


def _copy_to_archive(bucket, job_id: UUID, filename: str) -> None:
    """把當前 finalize 檔（latest）server-side rewrite 到 archive/ 路徑當原始版。

    filename 例如 "template_final.svg" → "archive/template_final_v0.svg"。
    用 GCS rewrite 不下載原檔，效率最高。原始檔不存在（finalize 失敗過？）就 skip。
    """
    base, ext = filename.rsplit(".", 1)
    src_path = f"production_jobs/{job_id}/{filename}"
    dst_path = f"production_jobs/{job_id}/archive/{base}_v0.{ext}"
    src_blob = bucket.blob(src_path)
    if not src_blob.exists():
        return
    dst_blob = bucket.blob(dst_path)
    dst_blob.rewrite(src_blob)


async def _get_job_or_404(db: AsyncSession, job_id: UUID) -> ProductionJob:
    result = await db.execute(
        select(ProductionJob).where(ProductionJob.id == job_id)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise NotFoundError("生產工作不存在")
    return job


async def _auto_map(
    db: AsyncSession, job: ProductionJob
) -> list[PaletteColorMapping]:
    # 先抓主鍵：並發競態下 except 分支會 db.rollback()，rollback 使 job 物件過期，
    # 之後再讀 job.id 會觸發同步 lazy-load → async 下 MissingGreenlet → 500。
    jid = job.id
    colors_result = await db.execute(
        select(PhysicalColor).where(PhysicalColor.is_active == True)  # noqa: E712
    )
    active_colors = list(colors_result.scalars().all())

    in_stock = [c for c in active_colors if float(c.stock_ml) > 0]
    # Global preference: use in-stock pool for all templates if any exist;
    # fall back to full active pool only when nothing is in stock.
    candidates = in_stock if in_stock else active_colors

    if not candidates:
        raise BadRequestError("尚無可用的實體色，無法自動對應")

    new_mappings = []
    for entry in job.palette_json:
        template_id = entry["template_id"]
        rgb = entry["rgb"]
        # palette_json.rgb 為 list[int] 三元組 [r, g, b]（schema.md 規範）
        # 兼容極舊資料格式 {"r":..., "g":..., "b":...}（早期版本，正常情況不會出現）
        if isinstance(rgb, dict):
            alg_rgb = [int(rgb["r"]), int(rgb["g"]), int(rgb["b"])]
        else:
            alg_rgb = [int(c) for c in rgb]

        best = min(
            candidates,
            key=lambda c, _rgb=alg_rgb: (
                lab_distance(_rgb, c.rgb),
                str(c.id),
            ),
        )

        mapping = PaletteColorMapping(
            production_job_id=jid,
            template_id=template_id,
            algorithm_rgb=alg_rgb,
            physical_color_id=best.id,
            mapped_by=MappedByEnum.system,
        )
        db.add(mapping)
        new_mappings.append(mapping)

    try:
        await db.commit()
    except IntegrityError:
        # Concurrent request already created mappings for this job; use those.
        await db.rollback()
        result = await db.execute(
            select(PaletteColorMapping).where(
                PaletteColorMapping.production_job_id == jid
            )
        )
        return list(result.scalars().all())

    for m in new_mappings:
        await db.refresh(m)
    return new_mappings


async def _enrich_mappings(
    db: AsyncSession, mappings: list[PaletteColorMapping]
) -> list[dict]:
    color_ids = [m.physical_color_id for m in mappings]
    colors_result = await db.execute(
        select(PhysicalColor).where(PhysicalColor.id.in_(color_ids))
    )
    colors_by_id = {c.id: c for c in colors_result.scalars().all()}

    enriched = []
    for m in mappings:
        color = colors_by_id.get(m.physical_color_id)
        enriched.append({
            "template_id": m.template_id,
            "algorithm_rgb": list(m.algorithm_rgb),
            "physical_color": {
                "id": color.id,
                "code": color.code,
                "name": color.name,
                "rgb": color.rgb,
                "stock_ml": float(color.stock_ml),
            } if color else None,
            "required_ml": float(m.required_ml) if m.required_ml is not None else None,
            "mapped_by": m.mapped_by,
            "output_label": m.output_label,
        })
    return enriched


async def _get_settings(db: AsyncSession) -> dict[str, str]:
    from color.models import SystemSetting
    result = await db.execute(select(SystemSetting))
    return {s.key: s.value for s in result.scalars().all()}
