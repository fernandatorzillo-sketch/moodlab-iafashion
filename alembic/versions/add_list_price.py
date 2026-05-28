"""add list_price to catalog_products

Revision ID: add_list_price
Revises: add_recommendation_clicks
Create Date: 2026-05-28

Motivo: list_price (preço "De") nunca foi criado. O commertialOffer.ListPrice
já está no raw_json["sku"] — esse backfill extrai de lá.
"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "add_list_price"
down_revision: Union[str, Sequence[str], None] = "add_recommendation_clicks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "catalog_products",
        sa.Column("list_price", sa.Float(), nullable=True),
    )
    op.create_index("ix_catalog_products_list_price", "catalog_products", ["list_price"])


def downgrade() -> None:
    op.drop_index("ix_catalog_products_list_price", table_name="catalog_products")
    op.drop_column("catalog_products", "list_price")
