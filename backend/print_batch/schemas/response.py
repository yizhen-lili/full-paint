from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class CostBreakdown(BaseModel):
    print_cost: float
    cut_cost: float
    total_cost: float


class CandidateInfo(BaseModel):
    production_job_id: UUID
    product_title: str | None
    # 'product'  → 一般商品 job（已綁 ProductVariant）
    # 'custom'   → 客製訂單 job（CustomRequest 路徑）
    # 'unbound'  → 既無 product 也無 custom_request（fallback，不該發生）
    kind: Literal["product", "custom", "unbound"]
    # filled_template 的預覽圖（已轉 signed URL）— 讓 admin 視覺確認要印什麼
    preview_url: str | None
    canvas_w_cm: float
    canvas_h_cm: float
    inch_per_unit: float


class CandidateListResponse(BaseModel):
    items: list[CandidateInfo]


class SuggestedComboItem(BaseModel):
    production_job_id: UUID
    product_title: str | None
    kind: Literal["product", "custom", "unbound"]
    preview_url: str | None
    quantity: int
    inch_per_unit: float


class SuggestedCombo(BaseModel):
    label: str
    items: list[SuggestedComboItem]
    total_inch_count: float
    billable_inch_count: float
    waste_inch: float
    cost_breakdown: CostBreakdown


class PreviewResponse(BaseModel):
    required_inch_count: float
    billable_inch_count: float
    waste_inch: float
    cost_breakdown: CostBreakdown
    suggestions: list[SuggestedCombo]
    available_candidates: list[CandidateInfo]


class BatchItemResponse(BaseModel):
    id: UUID
    source_type: str
    source_order_item_id: UUID | None
    production_job_id: UUID
    quantity: int
    inch_per_unit: float
    canvas_w_cm: float
    canvas_h_cm: float


class PrintBatchDetailResponse(BaseModel):
    id: UUID
    status: str
    total_inch_count: float
    billable_inch_count: float
    print_cost: float
    cut_cost: float
    total_cost: float
    pdf_url: str | None
    admin_notes: str | None
    created_at: datetime
    finalized_at: datetime | None
    items: list[BatchItemResponse]


class PrintBatchSummary(BaseModel):
    id: UUID
    status: str
    total_inch_count: float
    total_cost: float
    pdf_url: str | None
    item_count: int
    created_at: datetime
    finalized_at: datetime | None


class PrintBatchListResponse(BaseModel):
    items: list[PrintBatchSummary]
    total: int
    page: int
    page_size: int
