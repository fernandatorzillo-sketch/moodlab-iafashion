"""create recommendation_clicks table

Revision ID: add_recommendation_clicks
Revises: e03fae888724
Create Date: 2026-05-15 00:00:00.000000
"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "add_recommendation_clicks"
down_revision: Union[str, Sequence[str], None] = "e03fae888724"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "recommendation_clicks",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("email", sa.String(255), nullable=True, index=True),
        sa.Column("product_id", sa.String(80), nullable=False, index=True),
        sa.Column("occasion", sa.String(80), nullable=True),
        sa.Column("source", sa.String(80), nullable=True, index=True),
        sa.Column("clicked_at", sa.DateTime(), nullable=True, index=True),
    )


def downgrade() -> None:
    op.drop_table("recommendation_clicks")
