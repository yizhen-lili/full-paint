"""custom_requests 加 display_consent — 客戶是否同意作品於 IG / 網站作品案例展示

對應 docs/yii_mui_static_pages_spec.md 第九頁智財權條款：
> 我同意 yii.mui 可以使用此照片於 IG / 網站作品展示（可選）

預設 false（不展示）。客戶在 CustomApplyForm 自行勾選同意。

Revision ID: p6k7l8m9n0o1
Revises: o5j6k7l8m9n0
Create Date: 2026-05-10
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "p6k7l8m9n0o1"
down_revision: str | None = "o5j6k7l8m9n0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "custom_requests",
        sa.Column(
            "display_consent",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("custom_requests", "display_consent")
