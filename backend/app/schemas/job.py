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
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
