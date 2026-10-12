import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.db.session import SessionLocal, get_db
from app.models.job import Job
from app.schemas.job import JobCreate, JobRead
from app.services.llm.base import RecipeExtractor
from app.services.recipe_pipeline import run_pipeline
from app.services.transcript.base import TranscriptProvider

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


@router.post("", response_model=JobRead, status_code=status.HTTP_202_ACCEPTED)
def create_job(
    payload: JobCreate,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> Job:
    # Providers are initialised once at app startup and stored on app.state
    transcript_provider: TranscriptProvider = request.app.state.transcript_provider
    recipe_extractor: RecipeExtractor = request.app.state.recipe_extractor

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

    return job


@router.get("/{job_id}", response_model=JobRead)
def get_job(job_id: uuid.UUID, db: Session = Depends(get_db)) -> Job:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
