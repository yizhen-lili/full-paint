"""Production Celery tasks — 真實 PBN 引擎整合（Phase 2）。

run_production_job：DB 取 job → 下載原圖 → 跑引擎 → 上傳 Firebase → 寫回 DB。
失敗回滾：刪除已上傳的 Firebase 物件、status=failed、notes 寫錯誤摘要。
"""
from __future__ import annotations

import asyncio
import logging
import os
import shutil
import tempfile
import traceback
import uuid
from typing import Any

from core.celery_app import celery_app
from production.engine import generate_standard, resolve_engine_params

logger = logging.getLogger(__name__)


# ── helpers (Celery worker 是同步 process，async 用 asyncio.run 包住) ───────────


def _run_async(coro):
    """同步 worker 中跑 async 程式碼。"""
    import sys
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    return asyncio.run(coro)


async def _load_job(session, job_id: str):
    from sqlalchemy import select  # noqa: PLC0415

    from production.models import ProductionJob  # noqa: PLC0415

    result = await session.execute(
        select(ProductionJob).where(ProductionJob.id == job_id)
    )
    return result.scalar_one_or_none()


async def _load_image(session, image_id):
    from sqlalchemy import select  # noqa: PLC0415

    from production.models import Image  # noqa: PLC0415

    result = await session.execute(
        select(Image).where(Image.id == image_id)
    )
    return result.scalar_one_or_none()


def _download_image_to_path(image_url: str, dest_path: str) -> None:
    """從 Firebase Storage 下載原圖。

    image_url 可能是 gs://bucket/path 或 https://storage.googleapis.com/... 格式。
    """
    from core.firebase import get_bucket  # noqa: PLC0415

    bucket = get_bucket()
    blob_path = _parse_blob_path(image_url, bucket.name)
    blob = bucket.blob(blob_path)
    blob.download_to_filename(dest_path)


def _parse_blob_path(url: str, bucket_name: str) -> str:
    """從 gs:// 或 https:// URL 中萃取 blob 路徑。"""
    if url.startswith("gs://"):
        prefix = f"gs://{bucket_name}/"
        if not url.startswith(prefix):
            raise ValueError(f"URL bucket 不符：{url}")
        return url[len(prefix):]
    if "/" + bucket_name + "/" in url:
        # https://storage.googleapis.com/<bucket>/<path>?<query>
        path = url.split("/" + bucket_name + "/", 1)[1]
        return path.split("?", 1)[0]
    raise ValueError(f"無法從 URL 解出 blob 路徑：{url}")


def _upload_file(local_path: str, blob_path: str, content_type: str) -> str:
    """上傳本地檔到 Firebase 並回傳 gs:// 路徑。

    公開讀取一律走 signed URL（與 upload/service.py、production.create_image 模式一致）。
    Bucket 啟用 uniform bucket-level access 時 make_public() 會 raise 400 — 不採用。
    """
    from core.firebase import get_bucket  # noqa: PLC0415

    bucket = get_bucket()
    blob = bucket.blob(blob_path)
    blob.upload_from_filename(local_path, content_type=content_type)
    return f"gs://{bucket.name}/{blob_path}"


def _delete_blob(blob_path: str) -> None:
    """刪除 Firebase 物件（回滾用）— 失敗只記 log，不再 raise。"""
    try:
        from core.firebase import get_bucket  # noqa: PLC0415

        bucket = get_bucket()
        bucket.blob(blob_path).delete()
    except Exception as e:  # noqa: BLE001
        logger.warning("Firebase delete failed (orphan may remain): %s — %s", blob_path, e)


# ── Main task ─────────────────────────────────────────────────────────────────


@celery_app.task(bind=True, name="production.run_job", max_retries=0)
def run_production_job(self, job_id: str) -> None:
    """跑單筆 production_job：引擎產出 → Firebase 上傳 → DB 回寫。

    僅支援 mode=standard。sam_refine / sam_weighted 留 Phase 2-B。
    """
    _run_async(_run_production_job_async(job_id))


def _get_db_url() -> str:
    """允許測試 monkey-patch 這個函式來指向 test DB。"""
    from core.config import settings  # noqa: PLC0415

    return settings.database_url


async def _mark_job_failed(job_id: str, notes: str) -> None:
    """用獨立 engine 標 job=failed + notes。專供主 session 連線壞掉的回滾路徑使用。

    任何步驟失敗都吞例外只 log — 因為這已是「最後一道保險」，再 raise 會讓 Celery
    把整個 task 標 failed 反而看不到我們已寫好的 notes。
    """
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine  # noqa: PLC0415
    from sqlalchemy.pool import NullPool  # noqa: PLC0415

    from production.models import JobStatusEnum  # noqa: PLC0415

    fallback_engine = create_async_engine(_get_db_url(), poolclass=NullPool)
    try:
        async with AsyncSession(fallback_engine, expire_on_commit=False) as session:
            job = await _load_job(session, job_id)
            if job is None:
                logger.warning("_mark_job_failed: job %s not found in fallback session", job_id)
                return
            job.status = JobStatusEnum.failed
            job.notes = notes[:500]
            await session.commit()
    except Exception as e:  # noqa: BLE001
        logger.exception("_mark_job_failed itself failed for %s: %s", job_id, e)
    finally:
        try:
            await fallback_engine.dispose()
        except Exception as e:  # noqa: BLE001
            logger.warning("fallback engine dispose failed: %s", e)


async def _run_production_job_async(job_id: str) -> None:
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine  # noqa: PLC0415
    from sqlalchemy.pool import NullPool  # noqa: PLC0415

    from production.models import JobStatusEnum  # noqa: PLC0415

    engine_db = create_async_engine(_get_db_url(), poolclass=NullPool)
    uploaded_blob_paths: list[str] = []

    try:
        async with AsyncSession(engine_db, expire_on_commit=False) as session:
            job = await _load_job(session, job_id)
            if not job:
                logger.warning("run_production_job: job %s not found", job_id)
                return

            if job.mode != "standard":
                # sam_refine / sam_weighted 留 Phase 2-B
                job.status = JobStatusEnum.failed
                job.notes = f"目前僅支援 standard 模式，收到 mode={job.mode}（Phase 2-B 將補上）"
                await session.commit()
                return

            if job.image_id is None:
                job.status = JobStatusEnum.failed
                job.notes = "缺少 image_id（custom_request 路徑請先指派 image）"
                await session.commit()
                return

            image = await _load_image(session, job.image_id)
            if image is None:
                job.status = JobStatusEnum.failed
                job.notes = f"找不到 image_id={job.image_id}"
                await session.commit()
                return

            # status pending → processing
            job.status = JobStatusEnum.processing
            await session.commit()

            # 跑引擎（在 temp dir 內）+ 上傳
            try:
                result = await asyncio.to_thread(
                    _run_engine_and_upload, str(job.id), image.original_url, _resolve_params(job),
                    uploaded_blob_paths,
                )
            except Exception as e:  # noqa: BLE001
                logger.exception("run_production_job: engine/upload failed for %s", job_id)
                # 回滾：刪已上傳
                for p in uploaded_blob_paths:
                    _delete_blob(p)
                job.status = JobStatusEnum.failed
                job.notes = f"引擎或上傳失敗：{type(e).__name__}: {e}"[:500]
                await session.commit()
                return

            # 寫回 DB（commit 失敗 → blob 已上傳但無法落地，必須回滾刪 blob 並標 failed）
            job.svg_url = result["svg_url"]
            job.filled_template_url = result["filled_template_url"]
            job.snapped_rgb_url = result["snapped_rgb_url"]
            job.palette_json = result["palette_data"]
            job.num_colors_used = result["num_colors_used"]
            job.status = JobStatusEnum.completed
            try:
                await session.commit()
            except Exception as e:  # noqa: BLE001
                logger.exception(
                    "run_production_job: final commit failed for %s — rolling back blobs",
                    job_id,
                )
                # rollback 也可能失敗（連線斷）— 不能擋下標 failed 的關鍵動作
                try:
                    await session.rollback()
                except Exception as rb:  # noqa: BLE001
                    logger.warning("session rollback also failed: %s", rb)
                for p in uploaded_blob_paths:
                    _delete_blob(p)
                # 用獨立 engine + session 標 failed（避免共用同一個壞掉的連線
                # 而導致 job 永遠卡 processing）
                await _mark_job_failed(
                    job_id,
                    f"DB 寫回失敗（已清 Firebase orphan）：{type(e).__name__}: {e}",
                )
                return
            logger.info(
                "run_production_job: %s completed (%d colors)",
                job_id, result["num_colors_used"],
            )
    finally:
        await engine_db.dispose()


def _resolve_params(job) -> dict[str, Any]:
    return resolve_engine_params(job)


def _run_engine_and_upload(
    job_id: str,
    image_url: str,
    params: dict[str, Any],
    uploaded_blob_paths_out: list[str],
) -> dict[str, Any]:
    """同步部分：下載 → 引擎 → 上傳。在 thread 中跑（避免 block event loop）。

    uploaded_blob_paths_out 是個 list，會 in-place append 已上傳的 blob path，
    讓外層在後續失敗時可以反向刪除。
    """
    tmp_dir = tempfile.mkdtemp(prefix=f"prod_{job_id}_")
    try:
        # 1. 下載原圖
        ext = os.path.splitext(image_url.split("?", 1)[0])[1] or ".jpg"
        src_path = os.path.join(tmp_dir, f"src{ext}")
        _download_image_to_path(image_url, src_path)

        # 2. 跑引擎
        out_dir = os.path.join(tmp_dir, "out")
        engine_result = generate_standard(src_path, out_dir, **params)

        # 3. 上傳 3 個檔（svg / snapped 私有；filled 公開讀，admin UI 直接 <img>）
        token = uuid.uuid4().hex[:8]
        svg_blob = f"production_jobs/{job_id}/template_{token}.svg"
        filled_blob = f"production_jobs/{job_id}/filled_{token}.png"
        snapped_blob = f"production_jobs/{job_id}/snapped_{token}.png"

        svg_url = _upload_file(engine_result["svg_path"], svg_blob, "image/svg+xml")
        uploaded_blob_paths_out.append(svg_blob)
        filled_url = _upload_file(engine_result["filled_path"], filled_blob, "image/png")
        uploaded_blob_paths_out.append(filled_blob)
        snapped_url = _upload_file(engine_result["snapped_rgb_path"], snapped_blob, "image/png")
        uploaded_blob_paths_out.append(snapped_blob)

        return {
            "svg_url": svg_url,
            "filled_template_url": filled_url,
            "snapped_rgb_url": snapped_url,
            "palette_data": engine_result["palette_data"],
            "num_colors_used": engine_result["num_colors_used"],
        }
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


# ── Post-process task（沿用 stub 結構，實際後處理 Phase 2-B 補）─────────────────


@celery_app.task(bind=True, name="production.run_post_process", max_retries=0)
def run_post_process_job(self, job_id: str, params: dict) -> None:
    """後處理：合併色塊 / 消邊界 / 平滑輪廓。沿用 snapped_rgb 不重跑 KMeans。

    Phase 2-A 暫時 fallback 到 stub（status flip）— 實際操作邏輯需要對 PbnGen 加入
    可重新從 snapped_rgb 進入 output_to_svg 的能力。Phase 2-B 補完。
    """
    _run_async(_run_post_process_async(job_id, params))


_POST_PROCESS_PHASE2B_NOTE = (
    "[Phase 2-B] post-process 尚未實作，本次操作未變更檔案；svg/filled/snapped 維持原狀"
)


async def _run_post_process_async(job_id: str, params: dict) -> None:
    """Phase 2-A 保留 stub：status flip + notes 明示「未實作」，避免 admin 誤以為已生效。

    真實後處理需擴展 PbnGen 介面（從 snapped_rgb 重啟）— 違反 CLAUDE.md「不修改
    paint-by-number/src/」原則，留 Phase 2-B 處理。
    """
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine  # noqa: PLC0415
    from sqlalchemy.pool import NullPool  # noqa: PLC0415

    from production.models import JobStatusEnum  # noqa: PLC0415

    engine_db = create_async_engine(_get_db_url(), poolclass=NullPool)
    try:
        async with AsyncSession(engine_db, expire_on_commit=False) as session:
            job = await _load_job(session, job_id)
            if not job:
                logger.warning("run_post_process_job: job %s not found", job_id)
                return
            logger.info(
                "run_post_process_job(stub Phase 2-B): %s params=%s",
                job_id, params,
            )
            # 寫明確的 Phase 2-B 標記到 notes，admin UI 看 detail 時能識別
            existing_notes = (job.notes or "").strip()
            if _POST_PROCESS_PHASE2B_NOTE not in existing_notes:
                job.notes = (
                    _POST_PROCESS_PHASE2B_NOTE
                    if not existing_notes
                    else f"{existing_notes}\n{_POST_PROCESS_PHASE2B_NOTE}"
                )
            job.status = JobStatusEnum.completed
            await session.commit()
    finally:
        await engine_db.dispose()


# ── Cancel batch（既有，不動）──────────────────────────────────────────────────


@celery_app.task(bind=True, name="production.cancel_batch")
def cancel_batch_remaining(self, batch_id: str) -> None:
    """Cancel all pending jobs in a batch after a failure."""
    _run_async(_cancel_batch_async(batch_id))


async def _cancel_batch_async(batch_id: str) -> None:
    from sqlalchemy import update  # noqa: PLC0415
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine  # noqa: PLC0415
    from sqlalchemy.pool import NullPool  # noqa: PLC0415

    from production.models import JobStatusEnum, ProductionJob  # noqa: PLC0415

    engine_db = create_async_engine(_get_db_url(), poolclass=NullPool)
    try:
        async with AsyncSession(engine_db, expire_on_commit=False) as session:
            await session.execute(
                update(ProductionJob)
                .where(
                    ProductionJob.batch_id == batch_id,
                    ProductionJob.status == JobStatusEnum.pending,
                )
                .values(status=JobStatusEnum.cancelled)
            )
            await session.commit()
    finally:
        await engine_db.dispose()


# silence unused-import linting in some envs
_ = traceback
