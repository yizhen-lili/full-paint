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


# ── 批次刪除（含結構化引用回報，沿用 production 模式）──────────────────────

class BatchReferenceItem(BaseModel):
    """單筆引用該 batch 的具體 row（給 UI 顯示）."""
    id: str
    display: str


class BatchReferenceGroup(BaseModel):
    """引用 batch 的某一類資料群（目前只有 order_item）."""
    type: str                          # "order_item"
    label: str                         # UI 顯示中文
    cascadeable: bool                  # 永遠 False（訂單不可繞過）
    blocking_reason: str | None = None
    items: list[BatchReferenceItem]


class BatchDeleteBatchResult(BaseModel):
    """批次刪除單筆結果（成功 or 失敗）."""
    batch_id: UUID
    ok: bool
    error: str | None = None
    references: list[BatchReferenceGroup] | None = None


class BatchDeleteBatchesResponse(BaseModel):
    total: int
    success: int
    failed: int
    results: list[BatchDeleteBatchResult]
