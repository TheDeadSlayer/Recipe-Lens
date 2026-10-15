import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Recipe(Base):
    __tablename__ = "recipes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Structured list: [{"name": "...", "quantity": "..."}]
    ingredients: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    equipment: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    steps: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    calories: Mapped[int | None] = mapped_column(Integer, nullable=True)
    protein_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    carbs_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    fat_g: Mapped[float | None] = mapped_column(Float, nullable=True)

    # SHA-256 hex digest of canonical recipe content — used for exact duplicate detection.
    # nullable=True to remain compatible with rows created before this column existed.
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)

    # Extracted YouTube video ID (e.g. "dQw4w9WgXcQ") — used for fast source-level
    # duplicate detection before any Gemini processing.
    # nullable=True so non-YouTube sources and pre-migration rows remain valid.
    # Uniqueness is enforced by a partial index in migration 0005 (NULL rows excluded).
    source_video_id: Mapped[str | None] = mapped_column(String(20), nullable=True, index=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
