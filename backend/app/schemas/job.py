import uuid
from datetime import datetime

from pydantic import BaseModel, field_validator


class JobCreate(BaseModel):
    source_url: str

    @field_validator("source_url")
    @classmethod
    def source_url_must_be_http(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("source_url must not be empty")
        if not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("source_url must be an http or https URL")
        return v


class JobRead(BaseModel):
    id: uuid.UUID
    source_url: str
    status: str
    recipe_id: uuid.UUID | None
    error_message: str | None
    classification_reason: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# Imported here (not at top-level) to avoid a circular import at parse time.
# recipe.py → (no job imports) so the only risk is if job.py is imported before
# recipe.py has been fully defined.  Placing it at the end of the module ensures
# both classes are registered in sys.modules before the reference is resolved.
from app.schemas.recipe import RecipeRead  # noqa: E402


class JobCreateResponse(BaseModel):
    """
    Response to POST /api/v1/jobs.

    When already_exists=True the request was a duplicate: no new job was
    created, no background task was started, and Gemini was never called.
    The existing recipe_id and the full recipe object are returned inline so
    the client can display the result immediately without polling.

    When already_exists=False a new job was created and queued.  The client
    should poll GET /api/v1/jobs/{job_id} until a terminal status is reached.
    """

    already_exists: bool
    job_id: uuid.UUID | None  # None when already_exists=True
    recipe_id: uuid.UUID | None
    recipe: RecipeRead | None = None
