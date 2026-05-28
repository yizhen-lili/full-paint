from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from dependencies.auth import require_admin
from print_batch import service
from print_batch.schemas.request import (
    BatchDeleteBatchesRequest,
    CreateBatchRequest,
    PreviewRequest,
)
from print_batch.schemas.response import (
    BatchDeleteBatchesResponse,
    CandidateListResponse,
    PreviewResponse,
    PrintBatchDetailResponse,
    PrintBatchListResponse,
)

router = APIRouter(tags=["Admin - Print Batch"])


@router.post(
    "/admin/print-batches/preview", response_model=PreviewResponse
)
async def preview_batch(
    body: PreviewRequest,
    _=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await service.preview(
        db,
        [s.model_dump() for s in body.required],
        [s.model_dump() for s in (body.candidates or [])],
    )


@router.get(
    "/admin/print-batches/candidates", response_model=CandidateListResponse
)
async def list_candidates(
    _=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await service.list_candidates(db)


@router.post(
    "/admin/print-batches",
    status_code=201,
    response_model=PrintBatchDetailResponse,
)
async def create_batch(
    body: CreateBatchRequest,
    operator=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    batch = await service.create_batch(
        db,
        [s.model_dump() for s in body.required],
        [s.model_dump() for s in (body.candidates or [])],
        body.admin_notes,
        operator.id,
    )
    return await service.get_batch(db, batch.id)


@router.post(
    "/admin/print-batches/{batch_id}/finalize",
    response_model=PrintBatchDetailResponse,
)
async def finalize_batch(
    batch_id: UUID,
    _=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    batch = await service.finalize(db, batch_id)
    return await service.get_batch(db, batch.id)


@router.get(
    "/admin/print-batches", response_model=PrintBatchListResponse
)
async def list_batches(
    _=Depends(require_admin),
    status: Literal["draft", "finalized"] | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    return await service.list_batches(db, status, page, page_size)


@router.get(
    "/admin/print-batches/{batch_id}", response_model=PrintBatchDetailResponse
)
async def get_batch(
    batch_id: UUID,
    _=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await service.get_batch(db, batch_id)


@router.post(
    "/admin/print-batches/batch-delete",
    response_model=BatchDeleteBatchesResponse,
)
async def batch_delete_batches(
    body: BatchDeleteBatchesRequest,
    _=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """批次硬刪除列印批次（一次最多 50 筆）— 失敗筆獨立、不影響成功筆。

    每筆都會走單筆 delete 的所有檢查：
    - 被 order_item 引用 → 拒絕（金流稽核紅線）
    - FK ON DELETE CASCADE 自動清光 items
    - Firebase PDF best-effort 刪
    """
    results = await service.batch_delete_print_batches(db, body.batch_ids)
    success = sum(1 for r in results if r["ok"])
    return BatchDeleteBatchesResponse(
        total=len(results),
        success=success,
        failed=len(results) - success,
        results=results,
    )


@router.delete(
    "/admin/print-batches/{batch_id}",
    status_code=204,
    response_class=Response,
)
async def delete_batch(
    batch_id: UUID,
    _=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """硬刪除單筆 print_batch — 連帶刪 items + Firebase PDF。

    安全規則：批次內任何 item 是 order_item 來源 → 400（code=BATCH_BLOCKED_BY_ORDER）。
    draft / finalized 都可刪。
    """
    await service.delete_print_batch(db, batch_id)
    return Response(status_code=204)
