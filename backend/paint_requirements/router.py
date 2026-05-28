from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from dependencies.auth import require_admin
from paint_requirements import service
from paint_requirements.schemas import (
    PaintRequirementSourcesResponse,
    PaintRequirementsResponse,
)

router = APIRouter(tags=["Admin - Paint Requirements"])


@router.get(
    "/admin/paint-requirements/sources",
    response_model=PaintRequirementSourcesResponse,
)
async def get_paint_requirement_sources(
    _=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """列出可查詢的三類來源：商品（含 variants）/ 客製訂單 / 試驗任務。

    每項都帶 `is_finalized` 旗標；admin 在 picker 可看到「未對應」的項目並知道
    去 mapping 頁完成對應後才能查。
    """
    return await service.list_sources(db)


@router.get(
    "/admin/paint-requirements",
    response_model=PaintRequirementsResponse,
)
async def get_paint_requirements(
    production_job_id: UUID = Query(..., description="製作任務 id"),
    quantity: int = Query(default=1, ge=1, le=1000, description="製作件數"),
    _=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """製作任務 + 製作件數 → 物理顏料用量清單（含庫存對照）。

    錯誤情況：
    - 404：job 不存在
    - 400 JOB_NOT_FINALIZED：job 尚未完成顏色對應（finalized_at 為 null）
    """
    return await service.calculate_for_job(db, production_job_id, quantity)
