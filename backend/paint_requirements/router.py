from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from dependencies.auth import require_admin
from paint_requirements import service
from paint_requirements.schemas import PaintRequirementsResponse

router = APIRouter(tags=["Admin - Paint Requirements"])


@router.get(
    "/admin/paint-requirements",
    response_model=PaintRequirementsResponse,
)
async def get_paint_requirements(
    variant_id: UUID = Query(..., description="ProductVariant id"),
    quantity: int = Query(default=1, ge=1, le=1000, description="製作件數"),
    _=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """單一規格 + 製作件數 → 物理顏料用量清單（含庫存對照）。

    錯誤情況：
    - 404：variant 或其綁定 job 不存在
    - 400 VARIANT_NOT_FINALIZED：job 尚未完成顏色對應（finalized_at 為 null）
    """
    return await service.calculate_for_variant(db, variant_id, quantity)
