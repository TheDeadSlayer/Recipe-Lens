import hashlib
import json

from app.schemas.recipe import RecipeSchema


def _canonical(recipe: RecipeSchema) -> dict:
    """
    Build a deterministic dict of all meaningful recipe content.

    Rules:
    - Every string value is stripped of leading/trailing whitespace.
    - Lists preserve order (order is meaningful for steps/ingredients).
    - Dicts are serialised with sort_keys=True by json.dumps.
    - Optional numeric fields absent from the recipe are stored as None so
      that a recipe with no calorie data hashes differently from one with
      calories=0.
    - description is included for forward-compatibility; it is None until
      the field is added to RecipeSchema.
    """

    def _strip(v: str) -> str:
        return v.strip()

    return {
        "title": _strip(recipe.title),
        "description": _strip(recipe.description) if recipe.description is not None else None,
        "ingredients": [
            {"name": _strip(i.name), "quantity": _strip(i.quantity)} for i in recipe.ingredients
        ],
        "equipment": [_strip(e) for e in recipe.equipment],
        "steps": [_strip(s) for s in recipe.steps],
        "calories": recipe.calories,
        "protein_g": recipe.protein_g,
        "carbs_g": recipe.carbs_g,
        "fat_g": recipe.fat_g,
    }


def compute_recipe_hash(recipe: RecipeSchema) -> str:
    """Return a lowercase hex SHA-256 digest of the canonical recipe content."""
    payload = json.dumps(_canonical(recipe), sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode()).hexdigest()
