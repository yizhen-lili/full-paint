from datetime import datetime

from pydantic import BaseModel


# ── 顏料需求查詢 response ──────────────────────────────────────────────


class PaintRequirementItem(BaseModel):
    physical_color_id: str
    # 已 finalize 後派發的「模板色號」（1..N）；同物理色多 template 共用一號
    output_label: int | None
    code: str
    name: str
    hex: str
    # 單件用量（finalize 時計算並存入 palette_color_mappings.required_ml）
    required_per_unit_ml: float
    # 總用量 = required_per_unit_ml × quantity，進位到小數第 2 位
    total_required_ml: float
    stock_ml: float
    # max(0, total_required_ml - stock_ml)；判斷是否需採購
    shortage_ml: float
    is_short: bool


class PaintRequirementsSummary(BaseModel):
    total_colors: int
    short_count: int
    total_required_ml: float


class PaintRequirementsResponse(BaseModel):
    production_job_id: str
    quantity: int
    canvas_w_cm: float
    canvas_h_cm: float
    items: list[PaintRequirementItem]
    summary: PaintRequirementsSummary


# ── Sources（picker）response ──────────────────────────────────────────


class SourceVariantInfo(BaseModel):
    variant_id: str
    production_job_id: str
    canvas_w_cm: float
    canvas_h_cm: float
    price: float
    # filled_template 短期 signed URL（15-min TTL）— picker 視覺辨識用
    preview_url: str | None
    is_finalized: bool


class SourceProductGroup(BaseModel):
    id: str
    title: str
    status: str
    variants: list[SourceVariantInfo]


class SourceCustomRequest(BaseModel):
    custom_request_id: str
    production_job_id: str
    label: str
    status: str
    canvas_w_cm: float
    canvas_h_cm: float
    preview_url: str | None
    is_finalized: bool


class SourceStandaloneJob(BaseModel):
    production_job_id: str
    label: str
    canvas_w_cm: float
    canvas_h_cm: float
    detail: str
    difficulty: str
    created_at: datetime
    preview_url: str | None
    is_finalized: bool


class PaintRequirementSourcesResponse(BaseModel):
    products: list[SourceProductGroup]
    custom_requests: list[SourceCustomRequest]
    standalone_jobs: list[SourceStandaloneJob]
