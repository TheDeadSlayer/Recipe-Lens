"""add not_recipe job status and classification_reason

Revision ID: 0004
Revises: 0003
Create Date: 2024-01-04 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def _drop_status_check(bind) -> None:
    """
    Drop any CHECK constraint on jobs whose sqltext references 'status'.

    Uses SQLAlchemy's cross-version inspector API instead of querying
    pg_constraint system-catalog columns directly (consrc / conbin do not
    exist on all PostgreSQL versions and were removed / renamed over time).

    Handles three possible states safely:
      1. No status CHECK exists — nothing to drop.
      2. A CHECK exists under the expected name ("ck_jobs_status").
      3. A CHECK exists under a generated name (e.g. "jobs_status_check").
    Unnamed constraints (name is None or empty) are silently skipped because
    Alembic cannot drop a constraint without a name.
    """
    inspector = inspect(bind)
    for check in inspector.get_check_constraints("jobs"):
        name = check.get("name")
        sqltext = (check.get("sqltext") or "").lower()
        if "status" in sqltext:
            if name:
                op.drop_constraint(name, "jobs", type_="check")


def upgrade() -> None:
    bind = op.get_bind()

    # ── Drop any pre-existing CHECK constraint on jobs.status ─────────────────
    _drop_status_check(bind)

    # ── Create canonical named constraint including not_recipe ─────────────────
    op.create_check_constraint(
        "ck_jobs_status",
        "jobs",
        "status IN ('pending', 'processing', 'completed', 'failed', 'not_recipe')",
    )

    # ── Add nullable classification_reason column ──────────────────────────────
    # Stores the Gemini classification explanation when a video is determined
    # not to be a recipe.  Intentionally separate from error_message, which is
    # reserved for genuine processing / application failures.
    op.add_column(
        "jobs",
        sa.Column("classification_reason", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("jobs", "classification_reason")

    # ── Drop the 5-value constraint (found by inspector, not assumed name) ─────
    bind = op.get_bind()
    _drop_status_check(bind)

    # ── Restore original 4-value constraint ───────────────────────────────────
    op.create_check_constraint(
        "ck_jobs_status",
        "jobs",
        "status IN ('pending', 'processing', 'completed', 'failed')",
    )
