import uuid
from datetime import datetime

from pydantic import BaseModel


class Ingredient(BaseModel):
    name: str
    quantity: str


class RecipeRead(BaseModel):
    id: uuid.UUID
    job_id: uuid.UUID
    source_url: str
    title: str
    description: str | None
    ingredients: list[Ingredient]
    equipment: list[str]
    steps: list[str]
    calories: int | None
    protein_g: float | None
    carbs_g: float | None
    fat_g: float | None
    created_at: datetime

    model_config = {"from_attributes": True}


class RecipeSchema(BaseModel):
    """Internal schema returned by RecipeExtractor implementations."""

    title: str
    description: str | None = None
    ingredients: list[Ingredient]
    equipment: list[str]
    steps: list[str]
    calories: int | None = None
    protein_g: float | None = None
    carbs_g: float | None = None
    fat_g: float | None = None
