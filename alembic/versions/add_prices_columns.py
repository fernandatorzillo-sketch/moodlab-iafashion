"""add price column to catalog_products and customer_recommendations

Revision ID: add_price_columns
Revises: 115690b64e9c
Create Date: 2026-05-08 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "add_price_columns"
down_revision: Union[str, Sequence[str], None] = "115690b64e9c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Adiciona price em catalog_products
    op.add_column(
        "catalog_products",
        sa.Column("price", sa.Float(), nullable=True),
    )
    # Adiciona price em customer_recommendations
    op.add_column(
        "customer_recommendations",
        sa.Column("price", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("customer_recommendations", "price")
    op.drop_column("catalog_products", "price")
