from datetime import date

from pydantic import BaseModel


class SalesPeriod(BaseModel):
    from_: date | None
    to: date | None

    model_config = {"populate_by_name": True}


class SalesReportResponse(BaseModel):
    period: dict
    total_orders: int
    total_revenue: float
    note: str
