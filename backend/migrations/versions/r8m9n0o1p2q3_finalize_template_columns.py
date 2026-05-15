"""對應完成 finalize：production_jobs 加 template_final / palette_final / finalized_at；palette_color_mappings 加 output_label

對應 admin 完成顏色對應後產出「實體色版最終模板」流程：
- production_jobs.template_final_url：Firebase 上 template_final.svg 的 gs:// 路徑
- production_jobs.palette_final_url：Firebase 上 palette_final.json 的 gs:// 路徑
- production_jobs.finalized_at：finalize 完成時間戳
- palette_color_mappings.output_label：1..N 的實體色版編號（同物理色 → 同 label；NULL = 尚未 finalize）

全部 nullable，向後相容，舊 job 不受影響。

Revision ID: r8m9n0o1p2q3
Revises: q7l8m9n0o1p2
Create Date: 2026-05-12
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "r8m9n0o1p2q3"
down_revision: str | None = "q7l8m9n0o1p2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "production_jobs",
        sa.Column("template_final_url", sa.String(), nullable=True),
    )
    op.add_column(
        "production_jobs",
        sa.Column("palette_final_url", sa.String(), nullable=True),
    )
    op.add_column(
        "production_jobs",
        sa.Column("finalized_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.add_column(
        "palette_color_mappings",
        sa.Column("output_label", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("palette_color_mappings", "output_label")
    op.drop_column("production_jobs", "finalized_at")
    op.drop_column("production_jobs", "palette_final_url")
    op.drop_column("production_jobs", "template_final_url")
