import logging
import uuid
from datetime import datetime, timezone
from typing import Union

from sqlalchemy.orm import Session

from app.models.job import Job
from app.models.recipe import Recipe
from app.schemas.recipe import RecipeSchema
from app.services.hashing import compute_recipe_hash
from app.services.llm.base import RecipeExtractor
from app.services.transcript.base import TranscriptProvider
from app.services.video.base import VideoRecipeExtractor
from app.services.youtube import extract_video_id

logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def run_pipeline(
    job_id: uuid.UUID,
    source_url: str,
    db: Session,
    transcript_provider: TranscriptProvider,
    recipe_extractor: Union[RecipeExtractor, VideoRecipeExtractor],
) -> None:
    """
    Runs the full transcript → extraction → persist pipeline for a job.
    Updates job status in PostgreSQL at each stage.

    NOTE: This runs inside a FastAPI BackgroundTask. A dedicated DB session is
    opened and managed here because the request session closes before this task runs.

    Production systems would replace BackgroundTasks with a durable queue
    (e.g. Celery + Redis or Azure Service Bus) to survive pod restarts.
    """
    job = db.get(Job, job_id)
    if job is None:
        logger.error("Pipeline started for unknown job_id=%s", job_id)
        return

    # ── Mark as processing ────────────────────────────────────────────────────
    job.status = "processing"
    job.updated_at = _now()
    db.commit()
    logger.info("job_id=%s status=processing", job_id)

    try:
        # ── Fetch transcript + extract recipe ─────────────────────────────────
        # When the extractor is a VideoRecipeExtractor (e.g. Gemini), classify
        # the video first.  Only when classification.is_recipe is True proceed
        # to extraction.  The transcript_provider argument is preserved for the
        # mock/OpenAI paths and remains unused in the Gemini path.
        if isinstance(recipe_extractor, VideoRecipeExtractor):
            # Step 1 — classification
            logger.info(
                "job_id=%s video_extractor=%s classifying url=%s",
                job_id,
                type(recipe_extractor).__name__,
                source_url,
            )
            classification = recipe_extractor.classify_video(source_url)
            logger.info(
                "job_id=%s classification is_recipe=%s reason=%r",
                job_id,
                classification.is_recipe,
                classification.reason,
            )

            if not classification.is_recipe:
                # Valid business outcome — mark the job as not_recipe and stop.
                # Do not hash, dedup, or create a recipe row.
                job.status = "not_recipe"
                job.classification_reason = classification.reason
                job.updated_at = _now()
                db.commit()
                logger.info(
                    "job_id=%s status=not_recipe reason=%r",
                    job_id,
                    classification.reason,
                )
                return

            # Step 2 — extraction (only reached when is_recipe is True)
            logger.info(
                "job_id=%s video_extractor=%s extracting_from_url url=%s",
                job_id,
                type(recipe_extractor).__name__,
                source_url,
            )
            recipe_schema: RecipeSchema = recipe_extractor.extract_from_url(source_url)
        else:
            logger.info("job_id=%s fetching transcript url=%s", job_id, source_url)
            transcript = transcript_provider.fetch(source_url)
            logger.info("job_id=%s extracting recipe", job_id)
            recipe_schema = recipe_extractor.extract(transcript)

        # ── Compute content hash ──────────────────────────────────────────────
        content_hash = compute_recipe_hash(recipe_schema)

        # ── Deduplicate: reuse existing recipe if content is identical ────────
        existing = db.query(Recipe).filter_by(content_hash=content_hash).first()
        if existing is not None:
            logger.info(
                "job_id=%s duplicate detected recipe_id=%s content_hash=%s",
                job_id,
                existing.id,
                content_hash,
            )
            job.status = "completed"
            job.recipe_id = existing.id
            job.updated_at = _now()
            db.commit()
            return

        # ── Persist new recipe ────────────────────────────────────────────────
        recipe = Recipe(
            id=uuid.uuid4(),
            job_id=job_id,
            source_url=source_url,
            source_video_id=extract_video_id(source_url),
            title=recipe_schema.title,
            description=recipe_schema.description,
            ingredients=[i.model_dump() for i in recipe_schema.ingredients],
            equipment=recipe_schema.equipment,
            steps=recipe_schema.steps,
            calories=recipe_schema.calories,
            protein_g=recipe_schema.protein_g,
            carbs_g=recipe_schema.carbs_g,
            fat_g=recipe_schema.fat_g,
            content_hash=content_hash,
        )
        db.add(recipe)
        db.flush()

        # ── Mark job completed ────────────────────────────────────────────────
        job.status = "completed"
        job.recipe_id = recipe.id
        job.updated_at = _now()
        db.commit()
        logger.info("job_id=%s status=completed recipe_id=%s", job_id, recipe.id)

    except Exception as exc:  # noqa: BLE001
        db.rollback()
        job = db.get(Job, job_id)
        if job:
            job.status = "failed"
            job.error_message = str(exc)
            job.updated_at = _now()
            db.commit()
        logger.exception("job_id=%s status=failed error=%s", job_id, exc)
