"""加 users.google_sub + 改 password_hash 為 nullable（store customer Google Sign-in）

Module: store 客戶端 Google 登入整合（2026-06-04）

改動：
- users.password_hash 從 NOT NULL 改成 nullable — Google-only 用戶沒密碼
- 新增 users.google_sub VARCHAR nullable + 部分 UNIQUE 索引（只索引非 NULL）
- google_sub 是 Google ID token 的 "sub" claim，唯一識別一個 Google 帳號

Revision ID: v2q3r4s5t6u7
Revises: u1p2q3r4s5t6
Create Date: 2026-06-04
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "v2q3r4s5t6u7"
down_revision: str | None = "u1p2q3r4s5t6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("users", "password_hash", existing_type=sa.String(), nullable=True)
    op.add_column("users", sa.Column("google_sub", sa.String(), nullable=True))
    op.create_index(
        "ux_users_google_sub",
        "users",
        ["google_sub"],
        unique=True,
        postgresql_where=sa.text("google_sub IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ux_users_google_sub", table_name="users")
    op.drop_column("users", "google_sub")
    # downgrade password_hash 回 NOT NULL 前須清掉 Google-only 用戶；這裡只還原 schema 限制
    op.alter_column("users", "password_hash", existing_type=sa.String(), nullable=False)
