import uuid
from enum import StrEnum

from sqlalchemy import (
    TIMESTAMP,
    Boolean,
    Column,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

from core.database import Base


class DetailEnum(StrEnum):
    rough = "rough"
    standard = "standard"
    detailed = "detailed"
    premium = "premium"


class DifficultyEnum(StrEnum):
    beginner = "beginner"
    elementary = "elementary"
    intermediate = "intermediate"
    advanced = "advanced"


class ModeEnum(StrEnum):
    standard = "standard"
    sam_refine = "sam_refine"
    sam_weighted = "sam_weighted"


class JobStatusEnum(StrEnum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class Image(Base):
    __tablename__ = "images"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    uploader_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    original_url = Column(String, nullable=False)
    filename = Column(String, nullable=False)
    width = Column(Integer, nullable=False)
    height = Column(Integer, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())


class ProductionJob(Base):
    __tablename__ = "production_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    image_id = Column(UUID(as_uuid=True), ForeignKey("images.id"), nullable=True)
    custom_request_id = Column(
        UUID(as_uuid=True), ForeignKey("custom_requests.id"), nullable=True
    )
    status = Column(
        Enum(JobStatusEnum), nullable=False, default=JobStatusEnum.pending
    )
    approved = Column(Boolean, nullable=False, default=False)
    detail = Column(Enum(DetailEnum), nullable=False)
    difficulty = Column(Enum(DifficultyEnum), nullable=False)
    mode = Column(Enum(ModeEnum), nullable=False, default=ModeEnum.standard)
    canvas_w_cm = Column(Numeric(6, 1), nullable=False)
    canvas_h_cm = Column(Numeric(6, 1), nullable=False)
    num_colors = Column(Integer, nullable=True)
    blur_ksize = Column(Integer, nullable=True)
    blur_sigma_color = Column(Numeric(6, 2), nullable=True)
    blur_sigma_space = Column(Numeric(6, 2), nullable=True)
    prune_iterations = Column(Integer, nullable=True)
    pruning_threshold = Column(Numeric(10, 8), nullable=True)
    min_ratio_multiplier = Column(Numeric(6, 2), nullable=True)
    bg_extra_blur = Column(Integer, nullable=True)
    min_brush_diam_cm = Column(Numeric(4, 2), nullable=False, default=1.0)
    extra_colors = Column(Integer, nullable=True)
    weight_ratio = Column(Numeric(4, 2), nullable=True)
    sam_points = Column(JSONB, nullable=True)
    polygons = Column(JSONB, nullable=True)
    mask_url = Column(String, nullable=True)
    mask_coverage = Column(Numeric(6, 2), nullable=True)
    svg_url = Column(String, nullable=True)
    filled_template_url = Column(String, nullable=True)
    snapped_rgb_url = Column(String, nullable=True)
    palette_json = Column(JSONB, nullable=True)
    num_colors_used = Column(Integer, nullable=True)
    # Finalize 後產出的「實體色版最終模板」與 palette legend；NULL = 尚未 finalize。
    # 並存於 Firebase（不覆蓋 svg_url 演算法版），PDF 匯出優先用 final 版。
    template_final_url = Column(String, nullable=True)
    palette_final_url = Column(String, nullable=True)
    # 「實體色版」filled preview：snapped_rgb 的每個 algorithm RGB pixel 替換成
    # 對應 mapping 的物理色 RGB。給 admin 看真實塗色後效果（vs filled_template_url
    # 是演算法量化色預覽）。
    filled_template_final_url = Column(String, nullable=True)
    finalized_at = Column(TIMESTAMP(timezone=True), nullable=True)
    # post-process（admin 在 palette 頁按「更新模板」）最後一次成功完成的時間。
    # 與 finalized_at 比對：若 post_processed_at > finalized_at → finalize 結果已過期，
    # admin UI 需顯示「演算法量化版（新模板）」而非「實體色版（舊模板的）」。
    # NULL = 從未 post-process 過（首次 production 完成不算 post-process）。
    post_processed_at = Column(TIMESTAMP(timezone=True), nullable=True)
    # 「原始版」備份（第一次成功 finalize 後被搬到 archive/ 路徑保留）。
    # 之後 admin 再按完成對應、覆蓋 latest 的同時，原始版欄位不被觸碰 — 給 admin
    # 比對「我這次調得比上次好還是更糟」。NULL = 從未 archive 過。
    original_template_final_url = Column(String, nullable=True)
    original_palette_final_url = Column(String, nullable=True)
    original_filled_template_final_url = Column(String, nullable=True)
    original_finalized_at = Column(TIMESTAMP(timezone=True), nullable=True)
    # 「待確認的自動合併建議」：finalize 時 svg_consolidate 偵測到微小色塊、視覺上合
    # 進相近鄰居、產生 (tiny_template_id → target_template_id) 建議清單。
    # admin 看了滿意才呼叫 confirm 把 mapping 真的改掉、不滿意呼叫 reject 清空。
    # 結構：[{"tiny_template_id": int, "target_template_id": int, "tiny_area": float}]
    # NULL = 沒有 pending（從未 finalize / 已 confirm / 已 reject / 沒有 tiny polygons）
    pending_auto_merges = Column(JSONB, nullable=True)
    notes = Column(Text, nullable=True)
    batch_id = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    approved_at = Column(TIMESTAMP(timezone=True), nullable=True)
