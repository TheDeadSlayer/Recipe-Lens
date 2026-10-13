"""
Source-level (Layer 1) deduplication tests.

Layer 1 dedup: when a recipe with the same source_video_id already exists,
POST /api/v1/jobs returns immediately with already_exists=True and the
existing recipe inline — no job created, no background task started,
no Gemini calls.

Layer 2 dedup (content-hash) is exercised by test_duplicate_recipe.py and
is unchanged by this feature.
"""

import pytest

from app.models.recipe import Recipe
from app.schemas.recipe import Ingredient, RecipeSchema
from app.services.youtube import extract_video_id


# ── YouTube URL parsing unit tests ────────────────────────────────────────────

class TestExtractVideoId:
    """Unit tests for the server-side YouTube video ID parser."""

    def test_standard_watch_url(self):
        assert extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_youtu_be_short_link(self):
        assert extract_video_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_youtube_shorts_url(self):
        assert extract_video_id("https://www.youtube.com/shorts/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_watch_url_with_tracking_params(self):
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&feature=share&utm_source=email"
        assert extract_video_id(url) == "dQw4w9WgXcQ"

    def test_watch_url_with_timestamp(self):
        assert extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=42s") == "dQw4w9WgXcQ"

    def test_youtu_be_with_query_params(self):
        assert extract_video_id("https://youtu.be/dQw4w9WgXcQ?si=abc123&t=10") == "dQw4w9WgXcQ"

    def test_embed_url(self):
        assert extract_video_id("https://www.youtube.com/embed/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_no_www_prefix(self):
        assert extract_video_id("https://youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_shorts_no_www(self):
        assert extract_video_id("https://youtube.com/shorts/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_non_youtube_url_returns_none(self):
        assert extract_video_id("https://vimeo.com/123456789") is None

    def test_non_video_url_returns_none(self):
        assert extract_video_id("https://example.com/recipe") is None

    def test_empty_string_returns_none(self):
        assert extract_video_id("") is None

    def test_youtube_channel_url_returns_none(self):
        assert extract_video_id("https://www.youtube.com/channel/UCxxxxxx") is None

    def test_watch_url_missing_v_param_returns_none(self):
        assert extract_video_id("https://www.youtube.com/watch?list=PLxxx") is None

    def test_different_video_ids_are_distinct(self):
        id1 = extract_video_id("https://www.youtube.com/watch?v=AAAAAAAAAAA")
        id2 = extract_video_id("https://www.youtube.com/watch?v=BBBBBBBBBBB")
        assert id1 != id2
        assert id1 == "AAAAAAAAAAA"
        assert id2 == "BBBBBBBBBBB"

    def test_same_video_different_url_formats_return_same_id(self):
        """All four URL forms for the same video must return the same ID."""
        vid = "dQw4w9WgXcQ"
        urls = [
            f"https://www.youtube.com/watch?v={vid}",
            f"https://youtu.be/{vid}",
            f"https://www.youtube.com/shorts/{vid}",
            f"https://www.youtube.com/embed/{vid}",
        ]
        assert all(extract_video_id(u) == vid for u in urls)


# ── API-level Layer 1 dedup tests ─────────────────────────────────────────────

def _seed_recipe(db, *, source_url: str, video_id: str) -> Recipe:
    """Insert a job + recipe row with a known source_video_id directly via ORM."""
    import uuid as _uuid
    from app.models.job import Job as _Job

    # A real recipe requires a parent job row because of the FK constraint.
    job = _Job(source_url=source_url, status="completed")
    db.add(job)
    db.flush()  # assign job.id without committing

    recipe = Recipe(
        job_id=job.id,
        source_url=source_url,
        source_video_id=video_id,
        title="Seeded Recipe",
        description=None,
        ingredients=[{"name": "Egg", "quantity": "2"}],
        equipment=["Pan"],
        steps=["Crack egg.", "Cook."],
        calories=None,
        protein_g=None,
        carbs_g=None,
        fat_g=None,
        content_hash=None,
    )
    db.add(recipe)
    db.commit()
    db.refresh(recipe)
    return recipe


def test_duplicate_video_returns_already_exists(client, db):
    """
    Submitting a URL whose video ID already has a recipe returns already_exists=True
    synchronously with the existing recipe, and no new job is created.
    """
    video_id = "dQw4w9WgXcQ"
    seeded = _seed_recipe(
        db,
        source_url=f"https://www.youtube.com/watch?v={video_id}",
        video_id=video_id,
    )

    resp = client.post(
        "/api/v1/jobs",
        json={"source_url": f"https://www.youtube.com/watch?v={video_id}"},
    )
    assert resp.status_code == 202
    data = resp.json()
    assert data["already_exists"] is True
    assert data["recipe_id"] == str(seeded.id)
    assert data["job_id"] is None
    assert data["recipe"] is not None
    assert data["recipe"]["id"] == str(seeded.id)
    assert data["recipe"]["title"] == "Seeded Recipe"


def test_duplicate_video_different_url_format(client, db):
    """
    A youtu.be URL that resolves to the same video ID as an existing recipe
    must also trigger already_exists=True.
    """
    video_id = "dQw4w9WgXcQ"
    seeded = _seed_recipe(
        db,
        source_url=f"https://www.youtube.com/watch?v={video_id}",
        video_id=video_id,
    )

    resp = client.post(
        "/api/v1/jobs",
        json={"source_url": f"https://youtu.be/{video_id}"},
    )
    assert resp.status_code == 202
    data = resp.json()
    assert data["already_exists"] is True
    assert data["recipe_id"] == str(seeded.id)


def test_duplicate_video_shorts_url(client, db):
    """YouTube Shorts URL resolving to the same ID triggers already_exists."""
    video_id = "dQw4w9WgXcQ"
    seeded = _seed_recipe(
        db,
        source_url=f"https://www.youtube.com/watch?v={video_id}",
        video_id=video_id,
    )

    resp = client.post(
        "/api/v1/jobs",
        json={"source_url": f"https://www.youtube.com/shorts/{video_id}"},
    )
    assert resp.status_code == 202
    data = resp.json()
    assert data["already_exists"] is True
    assert data["recipe_id"] == str(seeded.id)


def test_new_video_does_not_trigger_dedup(client, db):
    """A URL for a video ID not yet in the database returns already_exists=False."""
    # Seed with a different video ID
    _seed_recipe(
        db,
        source_url="https://www.youtube.com/watch?v=AAAAAAAAAAA",
        video_id="AAAAAAAAAAA",
    )

    resp = client.post(
        "/api/v1/jobs",
        json={"source_url": "https://www.youtube.com/watch?v=BBBBBBBBBBB"},
    )
    assert resp.status_code == 202
    data = resp.json()
    assert data["already_exists"] is False
    assert data["job_id"] is not None
    assert data["recipe_id"] is None


def test_non_youtube_url_skips_dedup(client):
    """Non-YouTube URLs (no parseable video ID) proceed to job creation normally."""
    resp = client.post(
        "/api/v1/jobs",
        json={"source_url": "https://example.com/some-recipe-video"},
    )
    assert resp.status_code == 202
    data = resp.json()
    assert data["already_exists"] is False
    assert data["job_id"] is not None


def test_duplicate_video_no_new_job_row(client, db):
    """When already_exists=True no Job row is created in the database."""
    from app.models.job import Job

    video_id = "dQw4w9WgXcQ"
    _seed_recipe(
        db,
        source_url=f"https://www.youtube.com/watch?v={video_id}",
        video_id=video_id,
    )

    before_count = db.query(Job).count()
    resp = client.post(
        "/api/v1/jobs",
        json={"source_url": f"https://www.youtube.com/watch?v={video_id}"},
    )
    assert resp.status_code == 202
    assert resp.json()["already_exists"] is True

    after_count = db.query(Job).count()
    assert after_count == before_count, "No new Job row must be created for a duplicate"


def test_duplicate_video_inline_recipe_fields(client, db):
    """The inline recipe in an already_exists response includes all expected fields."""
    video_id = "dQw4w9WgXcQ"
    _seed_recipe(
        db,
        source_url=f"https://www.youtube.com/watch?v={video_id}",
        video_id=video_id,
    )

    resp = client.post(
        "/api/v1/jobs",
        json={"source_url": f"https://www.youtube.com/watch?v={video_id}"},
    )
    recipe = resp.json()["recipe"]
    for field in ("id", "job_id", "source_url", "source_video_id", "title",
                  "ingredients", "equipment", "steps", "created_at"):
        assert field in recipe, f"Field '{field}' missing from inline recipe"
    assert recipe["source_video_id"] == video_id


def test_duplicate_with_tracking_params(client, db):
    """UTM / tracking query params on the URL do not defeat dedup."""
    video_id = "dQw4w9WgXcQ"
    _seed_recipe(
        db,
        source_url=f"https://www.youtube.com/watch?v={video_id}",
        video_id=video_id,
    )

    resp = client.post(
        "/api/v1/jobs",
        json={
            "source_url": (
                f"https://www.youtube.com/watch?v={video_id}"
                "&utm_source=email&utm_medium=social&t=42s"
            )
        },
    )
    assert resp.json()["already_exists"] is True
