"""保留原始 finalize 版：production_jobs 加 4 個 original_* 欄位

對應 admin 在 mapping 頁面比對「原始版 vs 最新版」需求：
- 第一次 finalize 後再次 finalize 時，舊版 template_final / palette_final /
  filled_template_final 會被搬到 archive/ 路徑保留，原 latest 路徑覆蓋為新版
- 4 個欄位指向 archive 路徑的 gs:// URL，NULL = 從未 archive 過

全 nullable、無 backfill；既有資料下次 finalize 時自動成為「原始版」。

Revision ID: s9n0o1p2q3r4
Revises: r8m9n0o1p2q3
Create Date: 2026-05-28
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "s9n0o1p2q3r4"
down_revision: str | None = "r8m9n0o1p2q3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "production_jobs",
        sa.Column("original_template_final_url", sa.String(), nullable=True),
    )
    op.add_column(
        "production_jobs",
        sa.Column("original_palette_final_url", sa.String(), nullable=True),
    )
    op.add_column(
        "production_jobs",
        sa.Column("original_filled_template_final_url", sa.String(), nullable=True),
    )
    op.add_column(
        "production_jobs",
        sa.Column("original_finalized_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("production_jobs", "original_finalized_at")
    op.drop_column("production_jobs", "original_filled_template_final_url")
    op.drop_column("production_jobs", "original_palette_final_url")
    op.drop_column("production_jobs", "original_template_final_url")
