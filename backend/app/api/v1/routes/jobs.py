import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.db.session import SessionLocal, get_db
from app.models.job import Job
from app.models.recipe import Recipe
from app.schemas.job import JobCreate, JobCreateResponse, JobRead
from app.schemas.recipe import RecipeRead
from app.services.llm.base import RecipeExtractor
from app.services.recipe_pipeline import run_pipeline
from app.services.transcript.base import TranscriptProvider
from app.services.youtube import extract_video_id

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _run_pipeline_with_own_session(
    job_id: uuid.UUID,
    source_url: str,
    transcript_provider: TranscriptProvider,
    recipe_extractor: RecipeExtractor,
) -> None:
    """
    Opens a dedicated DB session for the background task.
    The request session is closed before BackgroundTasks execute, so we must
    not reuse it here.
    """
    db = SessionLocal()
    try:
        run_pipeline(
            job_id=job_id,
            source_url=source_url,
            db=db,
            transcript_provider=transcript_provider,
            recipe_extractor=recipe_extractor,
        )
    finally:
        db.close()


@router.post("", response_model=JobCreateResponse, status_code=status.HTTP_202_ACCEPTED)
def create_job(
    payload: JobCreate,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> JobCreateResponse:
    # Providers are initialised once at app startup and stored on app.state
    transcript_provider: TranscriptProvider = request.app.state.transcript_provider
    recipe_extractor: RecipeExtractor = request.app.state.recipe_extractor

    # ── Layer 1: source-video deduplication ───────────────────────────────────
    # Extract the canonical YouTube video ID from the submitted URL.  When a
    # recipe already exists for this video ID we return it immediately without
    # creating a job or invoking Gemini.
    video_id = extract_video_id(payload.source_url)
    if video_id is not None:
        existing_recipe = db.query(Recipe).filter_by(source_video_id=video_id).first()
        if existing_recipe is not None:
            recipe_read = RecipeRead.model_validate(existing_recipe)
            return JobCreateResponse(
                already_exists=True,
                job_id=None,
                recipe_id=existing_recipe.id,
                recipe=recipe_read,
            )

    # ── New job: create and queue ─────────────────────────────────────────────
    job = Job(source_url=payload.source_url)
    db.add(job)
    db.commit()
    db.refresh(job)

    background_tasks.add_task(
        _run_pipeline_with_own_session,
        job_id=job.id,
        source_url=job.source_url,
        transcript_provider=transcript_provider,
        recipe_extractor=recipe_extractor,
    )

    return JobCreateResponse(
        already_exists=False,
        job_id=job.id,
        recipe_id=None,
        recipe=None,
    )


@router.get("/{job_id}", response_model=JobRead)
def get_job(job_id: uuid.UUID, db: Session = Depends(get_db)) -> Job:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
