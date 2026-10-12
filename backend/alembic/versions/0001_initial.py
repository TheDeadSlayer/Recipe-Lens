"""initial

Revision ID: 0001
Revises:
Create Date: 2024-01-01 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "jobs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("source_url", sa.Text, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("recipe_id", UUID(as_uuid=True), nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'processing', 'completed', 'failed')",
            name="ck_jobs_status",
        ),
    )
    op.create_index("ix_jobs_status", "jobs", ["status"])

    op.create_table(
        "recipes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "job_id",
            UUID(as_uuid=True),
            sa.ForeignKey("jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source_url", sa.Text, nullable=False),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("ingredients", JSONB, nullable=False),
        sa.Column("equipment", JSONB, nullable=False),
        sa.Column("steps", JSONB, nullable=False),
        sa.Column("calories", sa.Integer, nullable=True),
        sa.Column("protein_g", sa.Float, nullable=True),
        sa.Column("carbs_g", sa.Float, nullable=True),
        sa.Column("fat_g", sa.Float, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_recipes_job_id", "recipes", ["job_id"])


def downgrade() -> None:
    op.drop_index("ix_recipes_job_id", table_name="recipes")
    op.drop_table("recipes")
    op.drop_index("ix_jobs_status", table_name="jobs")
    op.drop_table("jobs")
