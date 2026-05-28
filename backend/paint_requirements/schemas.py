from pydantic import BaseModel


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
    variant_id: str
    production_job_id: str
    quantity: int
    canvas_w_cm: float
    canvas_h_cm: float
    items: list[PaintRequirementItem]
    summary: PaintRequirementsSummary
