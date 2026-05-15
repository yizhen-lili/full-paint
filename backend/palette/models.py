import uuid
from enum import StrEnum

from sqlalchemy import (
    TIMESTAMP,
    Column,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

from core.database import Base


class MappedByEnum(StrEnum):
    system = "system"
    manual = "manual"


class PaletteColorMapping(Base):
    __tablename__ = "palette_color_mappings"
    __table_args__ = (UniqueConstraint("production_job_id", "template_id"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    production_job_id = Column(
        UUID(as_uuid=True), ForeignKey("production_jobs.id"), nullable=False
    )
    template_id = Column(Integer, nullable=False)
    algorithm_rgb = Column(JSONB, nullable=False)
    physical_color_id = Column(
        UUID(as_uuid=True), ForeignKey("physical_colors.id"), nullable=False
    )
    required_ml = Column(Numeric(8, 4), nullable=True)
    # 對應完成（finalize）後填入 1..N 的「實體色版編號」。
    # 多個 template_id 對到同一物理色 → output_label 相同；NULL 表尚未 finalize。
    output_label = Column(Integer, nullable=True)
    mapped_by = Column(
        Enum(MappedByEnum), nullable=False, default=MappedByEnum.system
    )
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
