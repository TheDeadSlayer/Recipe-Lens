import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.recipe import Recipe
from app.schemas.recipe import RecipeRead

router = APIRouter(prefix="/recipes", tags=["recipes"])


@router.get("", response_model=list[RecipeRead])
def list_recipes(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[Recipe]:
    stmt = select(Recipe).order_by(Recipe.created_at.desc()).offset(skip).limit(limit)
    return list(db.scalars(stmt).all())


@router.get("/{recipe_id}", response_model=RecipeRead)
def get_recipe(recipe_id: uuid.UUID, db: Session = Depends(get_db)) -> Recipe:
    recipe = db.get(Recipe, recipe_id)
    if recipe is None:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return recipe
