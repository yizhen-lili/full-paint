"""add themes table + product_series.theme_id

Revision ID: j0e1f2g3h4i5
Revises: i9d0e1f2g3h4
Create Date: 2026-04-28 22:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'j0e1f2g3h4i5'
down_revision: str | Sequence[str] | None = 'i9d0e1f2g3h4'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'themes',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('cover_image_url', sa.String(), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column(
            'created_at', sa.TIMESTAMP(timezone=True),
            nullable=False, server_default=sa.func.now(),
        ),
        sa.Column(
            'updated_at', sa.TIMESTAMP(timezone=True),
            nullable=False, server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        sa.CheckConstraint('sort_order >= 0', name='ck_themes_sort_order_non_negative'),
    )

    op.create_index(
        'ix_themes_sort_order_created',
        'themes',
        ['sort_order', sa.text('created_at DESC')],
    )

    op.add_column(
        'product_series',
        sa.Column('theme_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        'fk_product_series_theme_id',
        source_table='product_series',
        referent_table='themes',
        local_cols=['theme_id'],
        remote_cols=['id'],
        ondelete='SET NULL',
    )


def downgrade() -> None:
    op.drop_constraint('fk_product_series_theme_id', 'product_series', type_='foreignkey')
    op.drop_column('product_series', 'theme_id')
    op.drop_index('ix_themes_sort_order_created', table_name='themes')
    op.drop_table('themes')
