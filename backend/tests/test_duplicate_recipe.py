"""
Exact duplicate recipe protection tests.

Covers:
- Submitting the same recipe twice creates only one recipe row.
- Both jobs complete successfully and reference the same recipe ID.
- A recipe is considered different when ANY single field differs:
  title, ingredients, equipment, steps, calories, protein_g, carbs_g, fat_g.
"""

import time

from app.models.recipe import Recipe
from app.schemas.recipe import Ingredient, RecipeSchema
from app.services.llm.base import RecipeExtractor
from app.services.llm.mock import MockRecipeExtractor, _MOCK_RECIPE


# ── Helpers ───────────────────────────────────────────────────────────────────

def _wait_for_terminal(client, job_id: str, *, retries: int = 10) -> dict:
    """Poll until the job reaches a terminal state and return its payload."""
    for _ in range(retries):
        data = client.get(f"/api/v1/jobs/{job_id}").json()
        if data["status"] in ("completed", "failed"):
            return data
        time.sleep(0.05)
    return data


def _submit_and_wait(client, url: str) -> dict:
    resp = client.post("/api/v1/jobs", json={"source_url": url})
    assert resp.status_code == 202
    return _wait_for_terminal(client, resp.json()["id"])


def _swap_extractor(client, extractor: RecipeExtractor):
    """Set a custom extractor on the live app state."""
    client.app.state.recipe_extractor = extractor


def _reset_extractor(client):
    """Restore the default mock extractor."""
    client.app.state.recipe_extractor = MockRecipeExtractor()


def _make_extractor(overrides: dict) -> RecipeExtractor:
    """Return a one-shot extractor that yields _MOCK_RECIPE with the given field overrides."""
    modified = _MOCK_RECIPE.model_copy(update=overrides)

    class _E(RecipeExtractor):
        def extract(self, transcript: str) -> RecipeSchema:  # noqa: ARG002
            return modified

    return _E()


# ── Duplicate tests ───────────────────────────────────────────────────────────

def test_duplicate_submission_creates_one_recipe_row(client, db):
    """Two jobs with identical content must produce exactly one recipe row."""
    job1 = _submit_and_wait(client, "https://example.com/dup-video")
    job2 = _submit_and_wait(client, "https://example.com/dup-video")

    recipes = db.query(Recipe).filter(Recipe.content_hash != None).all()  # noqa: E711
    hashes = {r.content_hash for r in recipes}
    assert len(hashes) == 1, f"Expected 1 unique recipe, found {len(hashes)}"
    assert job1["recipe_id"] == job2["recipe_id"]


def test_duplicate_jobs_both_complete(client):
    """Both jobs for the same content must finish with status='completed'."""
    job1 = _submit_and_wait(client, "https://example.com/dup-complete")
    job2 = _submit_and_wait(client, "https://example.com/dup-complete")

    assert job1["status"] == "completed", f"job1 failed: {job1}"
    assert job2["status"] == "completed", f"job2 failed: {job2}"
    assert job1["recipe_id"] == job2["recipe_id"]


# ── Single-field difference tests ─────────────────────────────────────────────

def test_different_description_creates_separate_recipe(client):
    job1 = _submit_and_wait(client, "https://example.com/desc-a")
    _swap_extractor(client, _make_extractor({"description": "A zesty twist on the classic."}))
    try:
        job2 = _submit_and_wait(client, "https://example.com/desc-b")
    finally:
        _reset_extractor(client)

    assert job1["recipe_id"] != job2["recipe_id"], "Different description must produce a separate recipe"


def test_different_title_creates_separate_recipe(client):
    job1 = _submit_and_wait(client, "https://example.com/title-a")
    _swap_extractor(client, _make_extractor({"title": "Garlic Butter Chicken"}))
    try:
        job2 = _submit_and_wait(client, "https://example.com/title-b")
    finally:
        _reset_extractor(client)

    assert job1["recipe_id"] != job2["recipe_id"], "Different title must produce a separate recipe"


def test_different_ingredients_create_separate_recipe(client):
    job1 = _submit_and_wait(client, "https://example.com/ing-a")
    new_ingredients = list(_MOCK_RECIPE.ingredients) + [Ingredient(name="Butter", quantity="50g")]
    _swap_extractor(client, _make_extractor({"ingredients": new_ingredients}))
    try:
        job2 = _submit_and_wait(client, "https://example.com/ing-b")
    finally:
        _reset_extractor(client)

    assert job1["recipe_id"] != job2["recipe_id"], "Different ingredients must produce a separate recipe"


def test_different_equipment_creates_separate_recipe(client):
    job1 = _submit_and_wait(client, "https://example.com/equip-a")
    _swap_extractor(client, _make_extractor({"equipment": _MOCK_RECIPE.equipment + ["Thermometer"]}))
    try:
        job2 = _submit_and_wait(client, "https://example.com/equip-b")
    finally:
        _reset_extractor(client)

    assert job1["recipe_id"] != job2["recipe_id"], "Different equipment must produce a separate recipe"


def test_different_steps_create_separate_recipe(client):
    job1 = _submit_and_wait(client, "https://example.com/steps-a")
    _swap_extractor(client, _make_extractor({"steps": _MOCK_RECIPE.steps + ["Garnish with parsley."]}))
    try:
        job2 = _submit_and_wait(client, "https://example.com/steps-b")
    finally:
        _reset_extractor(client)

    assert job1["recipe_id"] != job2["recipe_id"], "Different steps must produce a separate recipe"


def test_different_calories_creates_separate_recipe(client):
    job1 = _submit_and_wait(client, "https://example.com/cal-a")
    _swap_extractor(client, _make_extractor({"calories": 999}))
    try:
        job2 = _submit_and_wait(client, "https://example.com/cal-b")
    finally:
        _reset_extractor(client)

    assert job1["recipe_id"] != job2["recipe_id"], "Different calories must produce a separate recipe"


def test_different_protein_creates_separate_recipe(client):
    job1 = _submit_and_wait(client, "https://example.com/protein-a")
    _swap_extractor(client, _make_extractor({"protein_g": 99.0}))
    try:
        job2 = _submit_and_wait(client, "https://example.com/protein-b")
    finally:
        _reset_extractor(client)

    assert job1["recipe_id"] != job2["recipe_id"], "Different protein_g must produce a separate recipe"


def test_different_carbs_creates_separate_recipe(client):
    job1 = _submit_and_wait(client, "https://example.com/carbs-a")
    _swap_extractor(client, _make_extractor({"carbs_g": 99.0}))
    try:
        job2 = _submit_and_wait(client, "https://example.com/carbs-b")
    finally:
        _reset_extractor(client)

    assert job1["recipe_id"] != job2["recipe_id"], "Different carbs_g must produce a separate recipe"


def test_different_fat_creates_separate_recipe(client):
    job1 = _submit_and_wait(client, "https://example.com/fat-a")
    _swap_extractor(client, _make_extractor({"fat_g": 99.0}))
    try:
        job2 = _submit_and_wait(client, "https://example.com/fat-b")
    finally:
        _reset_extractor(client)

    assert job1["recipe_id"] != job2["recipe_id"], "Different fat_g must produce a separate recipe"
