from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from dependencies.auth import require_admin
from reports import service
from reports.schemas.response import SalesReportResponse

router = APIRouter(tags=["Reports"])


@router.get("/admin/reports/sales", response_model=SalesReportResponse)
async def sales_report(
    _=Depends(require_admin),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    return await service.sales_summary(db, date_from, date_to)
