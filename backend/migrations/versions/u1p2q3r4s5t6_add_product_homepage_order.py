"""加 products.homepage_order INTEGER + check constraint + 部分索引

首頁置頂商品功能（Module 22）：
- homepage_order：NULL = 不上首頁；≥1 表示首頁顯示順序（越小越前面）
- CheckConstraint：NULL 或 ≥1（防止 0 / 負數）
- 部分索引：只索引 homepage_order IS NOT NULL 的列（節省空間 + ORDER BY 快）

Revision ID: u1p2q3r4s5t6
Revises: t0o1p2q3r4s5
Create Date: 2026-06-02
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "u1p2q3r4s5t6"
down_revision: str | None = "t0o1p2q3r4s5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "products",
        sa.Column("homepage_order", sa.Integer(), nullable=True),
    )
    op.create_check_constraint(
        "ck_products_homepage_order_positive",
        "products",
        "homepage_order IS NULL OR homepage_order >= 1",
    )
    op.create_index(
        "idx_products_homepage_order",
        "products",
        ["homepage_order"],
        postgresql_where=sa.text("homepage_order IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("idx_products_homepage_order", table_name="products")
    op.drop_constraint("ck_products_homepage_order_positive", "products", type_="check")
    op.drop_column("products", "homepage_order")
