"""加 production_jobs.pending_auto_merges JSONB 欄位

存放 finalize 時 svg_consolidate 偵測到的微小色塊自動合併建議
（[{tiny_template_id, target_template_id, tiny_area}, ...]）；admin 看了
模板預覽後可確認寫入 DB 或拒絕。

nullable + 無 default。

Revision ID: t0o1p2q3r4s5
Revises: s9n0o1p2q3r4
Create Date: 2026-05-29
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "t0o1p2q3r4s5"
down_revision: str | None = "s9n0o1p2q3r4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "production_jobs",
        sa.Column("pending_auto_merges", JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("production_jobs", "pending_auto_merges")
