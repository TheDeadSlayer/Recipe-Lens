"""add source_video_id to recipes

Adds a source_video_id VARCHAR(20) column to the recipes table and backfills
it from existing source_url values using a PostgreSQL regex.  A partial unique
index (WHERE source_video_id IS NOT NULL) enforces uniqueness without blocking
NULL values from non-YouTube sources or rows that could not be parsed.

Duplicate source_video_id values in the backfill (the same video submitted
more than once before Layer 1 dedup existed) are resolved by keeping the
oldest recipe row's ID and nullifying source_video_id on all newer duplicates.
Those newer rows are already linked to job rows with status=completed and
recipe_id pointing to the winning row (via Layer 2 content-hash dedup), so
the data remains consistent.

Revision ID: 0005
Revises: 0004
Create Date: 2024-01-05 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Add nullable column ────────────────────────────────────────────────────
    op.add_column(
        "recipes",
        sa.Column("source_video_id", sa.String(20), nullable=True),
    )

    # ── Backfill from source_url using PostgreSQL regex ────────────────────────
    # Three URL patterns are handled in priority order:
    #   1. youtu.be/<ID>         — short links
    #   2. ?v=<ID> / &v=<ID>    — standard watch URLs
    #   3. /shorts/<ID>         — YouTube Shorts
    #
    # The CASE expression returns the first non-NULL match, or NULL when the
    # source_url does not contain a recognisable YouTube video ID.
    op.execute(
        """
        UPDATE recipes
        SET source_video_id = (
            CASE
                WHEN source_url ~ 'youtu\\.be/([A-Za-z0-9_-]{11})'
                    THEN substring(source_url FROM 'youtu\\.be/([A-Za-z0-9_-]{11})')
                WHEN source_url ~ '[?&]v=([A-Za-z0-9_-]{11})'
                    THEN substring(source_url FROM '[?&]v=([A-Za-z0-9_-]{11})')
                WHEN source_url ~ '/shorts/([A-Za-z0-9_-]{11})'
                    THEN substring(source_url FROM '/shorts/([A-Za-z0-9_-]{11})')
                ELSE NULL
            END
        )
        WHERE source_video_id IS NULL
        """
    )

    # ── Deduplicate: nullify source_video_id on all but the oldest row per ID ─
    # Before adding the unique index we must resolve any existing duplicates
    # that arose when the same video was submitted multiple times prior to this
    # migration.  The oldest recipe row (smallest created_at; ties broken by
    # smallest id) wins; all others have their source_video_id set to NULL.
    op.execute(
        """
        UPDATE recipes AS r
        SET source_video_id = NULL
        WHERE source_video_id IS NOT NULL
          AND r.id NOT IN (
              SELECT DISTINCT ON (source_video_id) id
              FROM recipes
              WHERE source_video_id IS NOT NULL
              ORDER BY source_video_id, created_at ASC, id ASC
          )
        """
    )

    # ── Partial unique index (NULLs excluded) ──────────────────────────────────
    # Using a partial index instead of a UNIQUE column constraint so that NULL
    # values (non-YouTube sources, unparseable URLs, pre-migration duplicates)
    # never conflict with each other while still guaranteeing uniqueness for
    # all non-NULL video IDs going forward.
    op.create_index(
        "uq_recipes_source_video_id",
        "recipes",
        ["source_video_id"],
        unique=True,
        postgresql_where=sa.text("source_video_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_recipes_source_video_id", table_name="recipes")
    op.drop_column("recipes", "source_video_id")
