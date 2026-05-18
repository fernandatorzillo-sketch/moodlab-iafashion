"""merge price branch

Revision ID: e03fae888724
Revises: a349bc2003f4, add_price_columns
Create Date: 2026-05-08 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

revision: str = "e03fae888724"
down_revision = ("a349bc2003f4", "add_price_columns")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
