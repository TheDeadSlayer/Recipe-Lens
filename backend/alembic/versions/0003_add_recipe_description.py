"""add recipe description

Revision ID: 0003
Revises: 0002
Create Date: 2024-01-03 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "recipes",
        sa.Column("description", sa.Text, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("recipes", "description")
