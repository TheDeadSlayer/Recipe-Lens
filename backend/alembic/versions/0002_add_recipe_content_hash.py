"""add recipe content_hash

Revision ID: 0002
Revises: 0001
Create Date: 2024-01-02 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "recipes",
        sa.Column("content_hash", sa.String(64), nullable=True),
    )
    op.create_unique_constraint(
        "uq_recipes_content_hash", "recipes", ["content_hash"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_recipes_content_hash", "recipes", type_="unique")
    op.drop_column("recipes", "content_hash")
