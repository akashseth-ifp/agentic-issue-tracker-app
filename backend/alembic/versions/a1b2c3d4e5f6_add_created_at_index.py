"""add_created_at_index

Revision ID: a1b2c3d4e5f6
Revises: 7ef8cd3349aa
Create Date: 2026-06-18 13:21:12.321857

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '7ef8cd3349aa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index("ix_issues_created_at", "issues", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_issues_created_at", table_name="issues")
