"""
Tests for GeminiVideoRecipeExtractor.

All tests mock the google-genai SDK so no real Gemini API calls are made
and no quota is consumed.

Patching strategy
-----------------
The extractor imports ``from google import genai`` and
``from google.genai import types`` inside __init__(), then stores the client
and types references as instance attributes (``_client``, ``_types``).

Rather than fighting Python's module cache with patch.dict(sys.modules), we
build a pre-wired extractor instance directly via __new__ and inject mock
attributes.  This is simpler, more robust, and does not depend on import order.

For construction tests we reload the module with a patched sys.modules so that
the __init__ import statements resolve to our mocks.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from app.schemas.recipe import Ingredient, RecipeSchema, RecipeVideoClassification
from app.services.llm.base import RecipeExtractionError

# ── Shared test data ──────────────────────────────────────────────────────────

_VALID_RECIPE_DICT = {
    "title": "Sheet-Pan Chicken",
    "description": "Easy one-pan weeknight dinner.",
    "ingredients": [
        {"name": "Chicken thighs", "quantity": "4 pieces"},
        {"name": "Olive oil", "quantity": "2 tbsp"},
    ],
    "equipment": ["Sheet pan", "Oven"],
    "steps": ["Preheat oven to 200°C.", "Arrange chicken on pan.", "Bake 35 min."],
    "calories": 420,
    "protein_g": 38.0,
    "carbs_g": 2.0,
    "fat_g": 28.0,
}

_VALID_RECIPE = RecipeSchema.model_validate(_VALID_RECIPE_DICT)

_YOUTUBE_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"


# ── Fake SDK error classes ─────────────────────────────────────────────────────
# Defined here so tests run without the SDK installed.  They mirror the
# google.genai.errors hierarchy that _is_transient() inspects.


class _FakeAPIError(Exception):
    def __init__(self, code: int = 500, status: str = "INTERNAL"):
        self.code = code
        self.status = status
        self.response = None
        super().__init__(f"{code} {status}")


class _FakeServerError(_FakeAPIError):
    """Mirrors google.genai.errors.ServerError (5xx)."""

    pass


class _FakeClientError(_FakeAPIError):
    """Mirrors google.genai.errors.ClientError (4xx)."""

    pass


# ── Mock factory helpers ──────────────────────────────────────────────────────


def _make_mock_types():
    """Return a minimal mock of google.genai.types."""
    mock_types = MagicMock()
    mock_types.Part.from_uri.return_value = MagicMock()
    mock_types.Part.from_text.return_value = MagicMock()
    mock_types.Content.return_value = MagicMock()
    mock_types.GenerateContentConfig.return_value = MagicMock()
    mock_types.HttpOptions.return_value = MagicMock()
    return mock_types


def _make_response(*, parsed=None, text: str | None = None):
    """Return a mock GenerateContentResponse."""
    r = MagicMock()
    r.parsed = parsed
    r.text = text
    return r


def _make_classification(is_recipe: bool, reason: str = "test reason") -> RecipeVideoClassification:
    return RecipeVideoClassification(is_recipe=is_recipe, reason=reason)


def _make_extractor(mock_client=None, mock_types=None):
    """
    Build a GeminiVideoRecipeExtractor instance with all SDK calls mocked.
    Bypasses __init__ so no env vars or SDK import is needed.
    """
    import app.services.video.gemini as gemini_mod

    extractor = gemini_mod.GeminiVideoRecipeExtractor.__new__(gemini_mod.GeminiVideoRecipeExtractor)
    extractor._model = "gemini-2.0-flash"
    extractor._timeout_ms = 300_000
    extractor._client = mock_client or MagicMock()
    extractor._types = mock_types or _make_mock_types()
    return extractor


def _patch_is_transient(module, fake_server_cls, fake_client_cls):
    """
    Patch _is_transient inside gemini.py so it uses our fake error classes
    instead of doing a live import of google.genai.errors.

    Returns a context manager.
    """
    import app.services.video.gemini as gemini_mod

    def _patched(exc):
        if isinstance(exc, fake_server_cls):
            return True
        if isinstance(exc, fake_client_cls):
            return getattr(exc, "code", 0) == 429
        return isinstance(exc, (ConnectionError, TimeoutError, OSError))

    return patch.object(gemini_mod, "_is_transient", side_effect=_patched)


# ── Construction / configuration tests ───────────────────────────────────────


class TestGeminiExtractorConstruction:
    def _reload_with_mock_sdk(self, mock_genai, mock_types):
        """Reload the gemini module with fake SDK entries in sys.modules."""
        import importlib

        import app.services.video.gemini as gemini_mod

        with patch.dict(
            "sys.modules",
            {
                "google": MagicMock(genai=mock_genai),
                "google.genai": mock_genai,
                "google.genai.types": mock_types,
            },
        ):
            importlib.reload(gemini_mod)
            yield gemini_mod

    def test_missing_api_key_raises_on_construction(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "")
        monkeypatch.setenv("GEMINI_MODEL", "gemini-2.0-flash")
        from app.core.config import get_settings

        get_settings.cache_clear()
        try:
            mock_genai = MagicMock()
            mock_types = _make_mock_types()
            import importlib

            import app.services.video.gemini as gemini_mod

            with patch.dict(
                "sys.modules",
                {
                    "google": MagicMock(genai=mock_genai),
                    "google.genai": mock_genai,
                    "google.genai.types": mock_types,
                },
            ):
                importlib.reload(gemini_mod)
                with pytest.raises(RecipeExtractionError, match="GEMINI_API_KEY"):
                    gemini_mod.GeminiVideoRecipeExtractor()
        finally:
            get_settings.cache_clear()

    def test_missing_model_raises_on_construction(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        monkeypatch.setenv("GEMINI_MODEL", "")
        from app.core.config import get_settings

        get_settings.cache_clear()
        try:
            mock_genai = MagicMock()
            mock_types = _make_mock_types()
            import importlib

            import app.services.video.gemini as gemini_mod

            with patch.dict(
                "sys.modules",
                {
                    "google": MagicMock(genai=mock_genai),
                    "google.genai": mock_genai,
                    "google.genai.types": mock_types,
                },
            ):
                importlib.reload(gemini_mod)
                with pytest.raises(RecipeExtractionError, match="GEMINI_MODEL"):
                    gemini_mod.GeminiVideoRecipeExtractor()
        finally:
            get_settings.cache_clear()


# ── Structured output — schema enforcement tests ──────────────────────────────


class TestGeminiStructuredOutput:
    """
    Verifies the structured-output contract:
    - response_schema=RecipeSchema is passed to GenerateContentConfig
    - response.parsed (already a RecipeSchema) is used directly
    - equipment is list[str], not list of objects
    - ingredients remain structured Ingredient objects
    - malformed / schema-incompatible output from the fallback path is rejected
    """

    def test_response_schema_passed_to_config(self):
        """response_schema=RecipeSchema must be in every GenerateContentConfig call."""
        mock_types = _make_mock_types()
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = _make_response(parsed=_VALID_RECIPE)
        extractor = _make_extractor(mock_client, mock_types)
        extractor.extract_from_url(_YOUTUBE_URL)

        call_kwargs = mock_types.GenerateContentConfig.call_args.kwargs
        assert call_kwargs.get("response_schema") is RecipeSchema

    def test_parsed_response_used_directly(self):
        """When response.parsed is a RecipeSchema instance it is returned as-is."""
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = _make_response(parsed=_VALID_RECIPE)
        extractor = _make_extractor(mock_client)
        result = extractor.extract_from_url(_YOUTUBE_URL)

        assert result is _VALID_RECIPE

    def test_equipment_is_list_of_strings(self):
        """equipment must come back as list[str] regardless of input path."""
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = _make_response(parsed=_VALID_RECIPE)
        extractor = _make_extractor(mock_client)
        result = extractor.extract_from_url(_YOUTUBE_URL)

        assert isinstance(result.equipment, list)
        assert all(isinstance(item, str) for item in result.equipment), (
            f"equipment must be list[str], got {result.equipment!r}"
        )

    def test_equipment_objects_rejected_via_text_fallback(self):
        """
        If the model returns equipment as objects (e.g. {"name": "saucepan"})
        and the SDK does not parse them, the text fallback must reject it with
        a RecipeExtractionError (schema validation failure, not retried).
        """
        bad_dict = {
            **_VALID_RECIPE_DICT,
            "equipment": [{"name": "saucepan"}, {"name": "lid"}],
        }
        mock_client = MagicMock()
        # parsed=None forces the text fallback path
        mock_client.models.generate_content.return_value = _make_response(
            parsed=None,
            text=json.dumps(bad_dict),
        )
        extractor = _make_extractor(mock_client)
        with pytest.raises(RecipeExtractionError, match="schema"):
            extractor.extract_from_url(_YOUTUBE_URL)

    def test_ingredients_are_structured_objects(self):
        """ingredients must be a list of Ingredient(name=, quantity=) objects."""
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = _make_response(parsed=_VALID_RECIPE)
        extractor = _make_extractor(mock_client)
        result = extractor.extract_from_url(_YOUTUBE_URL)

        assert all(isinstance(i, Ingredient) for i in result.ingredients)
        assert result.ingredients[0].name == "Chicken thighs"
        assert result.ingredients[0].quantity == "4 pieces"

    def test_text_fallback_valid_json_succeeds(self):
        """Valid JSON in response.text is accepted when response.parsed is None."""
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = _make_response(
            parsed=None,
            text=json.dumps(_VALID_RECIPE_DICT),
        )
        extractor = _make_extractor(mock_client)
        result = extractor.extract_from_url(_YOUTUBE_URL)

        assert isinstance(result, RecipeSchema)
        assert result.title == "Sheet-Pan Chicken"

    def test_text_fallback_non_json_raises_extraction_error(self):
        """Non-JSON text in fallback path raises RecipeExtractionError."""
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = _make_response(
            parsed=None,
            text="Here is your recipe: ...",
        )
        extractor = _make_extractor(mock_client)
        with pytest.raises(RecipeExtractionError, match="schema"):
            extractor.extract_from_url(_YOUTUBE_URL)

    def test_text_fallback_missing_required_field_raises(self):
        """JSON missing required 'title' fails schema validation."""
        bad = {k: v for k, v in _VALID_RECIPE_DICT.items() if k != "title"}
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = _make_response(
            parsed=None,
            text=json.dumps(bad),
        )
        extractor = _make_extractor(mock_client)
        with pytest.raises(RecipeExtractionError, match="schema"):
            extractor.extract_from_url(_YOUTUBE_URL)

    def test_text_fallback_wrong_ingredient_type_raises(self):
        """Ingredients as plain strings (not objects) fail schema validation."""
        bad = {**_VALID_RECIPE_DICT, "ingredients": ["chicken", "oil"]}
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = _make_response(
            parsed=None,
            text=json.dumps(bad),
        )
        extractor = _make_extractor(mock_client)
        with pytest.raises(RecipeExtractionError, match="schema"):
            extractor.extract_from_url(_YOUTUBE_URL)

    def test_blocked_response_raises_extraction_error(self):
        """response.text raising (blocked content) leads to RecipeExtractionError."""
        mock_response = MagicMock()
        mock_response.parsed = None
        type(mock_response).text = property(
            lambda self: (_ for _ in ()).throw(ValueError("blocked"))
        )
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        extractor = _make_extractor(mock_client)
        with pytest.raises(RecipeExtractionError):
            extractor.extract_from_url(_YOUTUBE_URL)


# ── Happy-path tests ──────────────────────────────────────────────────────────


class TestGeminiExtractorHappyPath:
    def test_returns_recipe_schema_instance(self):
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = _make_response(parsed=_VALID_RECIPE)
        result = _make_extractor(mock_client).extract_from_url(_YOUTUBE_URL)
        assert isinstance(result, RecipeSchema)

    def test_calls_generate_content_once_on_success(self):
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = _make_response(parsed=_VALID_RECIPE)
        extractor = _make_extractor(mock_client)
        extractor.extract_from_url(_YOUTUBE_URL)
        mock_client.models.generate_content.assert_called_once()

    def test_passes_video_part_with_correct_mime_type(self):
        mock_types = _make_mock_types()
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = _make_response(parsed=_VALID_RECIPE)
        extractor = _make_extractor(mock_client, mock_types)
        extractor.extract_from_url(_YOUTUBE_URL)

        mock_types.Part.from_uri.assert_called_once_with(
            file_uri=_YOUTUBE_URL,
            mime_type="video/*",
        )

    def test_null_optional_fields_pass_through(self):
        recipe_nulls = RecipeSchema(
            title="Minimal",
            ingredients=[],
            equipment=[],
            steps=[],
            description=None,
            calories=None,
            protein_g=None,
            carbs_g=None,
            fat_g=None,
        )
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = _make_response(parsed=recipe_nulls)
        result = _make_extractor(mock_client).extract_from_url(_YOUTUBE_URL)
        assert result.calories is None
        assert result.description is None


# ── Retry tests ───────────────────────────────────────────────────────────────


class TestGeminiRetry:
    """
    All sleep calls are patched to run at zero cost.
    All SDK error classes are replaced with fake local equivalents so the test
    suite does not require the google-genai SDK to be installed.
    """

    def _make_retrying_extractor(self):
        """Return an extractor with _is_transient patched to use fake error types."""
        return _make_extractor()

    # ── Transient then success ─────────────────────────────────────────────────

    def test_503_then_success_returns_recipe(self):
        """503 on first attempt, success on second → RecipeSchema returned."""
        import app.services.video.gemini as gemini_mod

        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = [
            _FakeServerError(503, "UNAVAILABLE"),
            _make_response(parsed=_VALID_RECIPE),
        ]
        extractor = _make_extractor(mock_client)

        with (
            patch.object(gemini_mod, "time") as mock_time,
            _patch_is_transient(gemini_mod, _FakeServerError, _FakeClientError),
        ):
            result = extractor.extract_from_url(_YOUTUBE_URL)

        assert isinstance(result, RecipeSchema)
        assert mock_client.models.generate_content.call_count == 2
        mock_time.sleep.assert_called_once()

    def test_504_then_success_returns_recipe(self):
        """504 DEADLINE_EXCEEDED on first attempt, success on second."""
        import app.services.video.gemini as gemini_mod

        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = [
            _FakeServerError(504, "DEADLINE_EXCEEDED"),
            _make_response(parsed=_VALID_RECIPE),
        ]
        extractor = _make_extractor(mock_client)

        with (
            patch.object(gemini_mod, "time"),
            _patch_is_transient(gemini_mod, _FakeServerError, _FakeClientError),
        ):
            result = extractor.extract_from_url(_YOUTUBE_URL)

        assert isinstance(result, RecipeSchema)
        assert mock_client.models.generate_content.call_count == 2

    def test_two_transient_failures_then_success(self):
        """Two consecutive transient errors, third attempt succeeds."""
        import app.services.video.gemini as gemini_mod

        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = [
            _FakeServerError(503, "UNAVAILABLE"),
            _FakeServerError(503, "UNAVAILABLE"),
            _make_response(parsed=_VALID_RECIPE),
        ]
        extractor = _make_extractor(mock_client)

        with (
            patch.object(gemini_mod, "time") as mock_time,
            _patch_is_transient(gemini_mod, _FakeServerError, _FakeClientError),
        ):
            result = extractor.extract_from_url(_YOUTUBE_URL)

        assert isinstance(result, RecipeSchema)
        assert mock_client.models.generate_content.call_count == 3
        assert mock_time.sleep.call_count == 2

    def test_connection_error_then_success(self):
        """Generic ConnectionError (network layer) is transient; retried once."""
        import app.services.video.gemini as gemini_mod

        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = [
            ConnectionError("ECONNREFUSED"),
            _make_response(parsed=_VALID_RECIPE),
        ]
        extractor = _make_extractor(mock_client)

        with (
            patch.object(gemini_mod, "time"),
            _patch_is_transient(gemini_mod, _FakeServerError, _FakeClientError),
        ):
            result = extractor.extract_from_url(_YOUTUBE_URL)

        assert isinstance(result, RecipeSchema)

    # ── All retries exhausted ──────────────────────────────────────────────────

    def test_three_transient_failures_raises_extraction_error(self):
        """Three consecutive 503s exhaust all retries → RecipeExtractionError."""
        import app.services.video.gemini as gemini_mod

        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = [
            _FakeServerError(503, "UNAVAILABLE"),
            _FakeServerError(503, "UNAVAILABLE"),
            _FakeServerError(503, "UNAVAILABLE"),
        ]
        extractor = _make_extractor(mock_client)

        with (
            patch.object(gemini_mod, "time"),
            _patch_is_transient(gemini_mod, _FakeServerError, _FakeClientError),
        ):
            with pytest.raises(RecipeExtractionError):
                extractor.extract_from_url(_YOUTUBE_URL)

        assert mock_client.models.generate_content.call_count == 3

    def test_exhausted_retries_sleeps_between_attempts(self):
        """sleep() is called exactly (MAX_ATTEMPTS - 1) times on full exhaustion."""
        import app.services.video.gemini as gemini_mod

        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = [
            _FakeServerError(503, "UNAVAILABLE"),
            _FakeServerError(503, "UNAVAILABLE"),
            _FakeServerError(503, "UNAVAILABLE"),
        ]
        extractor = _make_extractor(mock_client)

        with (
            patch.object(gemini_mod, "time") as mock_time,
            _patch_is_transient(gemini_mod, _FakeServerError, _FakeClientError),
        ):
            with pytest.raises(RecipeExtractionError):
                extractor.extract_from_url(_YOUTUBE_URL)

        # sleep between attempt 1→2 and 2→3; NOT after the final failure
        assert mock_time.sleep.call_count == 2

    # ── Permanent errors — must not retry ─────────────────────────────────────

    def test_auth_error_is_not_retried(self):
        """401/403 ClientError → single attempt, immediate RecipeExtractionError."""
        import app.services.video.gemini as gemini_mod

        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = _FakeClientError(401, "UNAUTHENTICATED")
        extractor = _make_extractor(mock_client)

        with (
            patch.object(gemini_mod, "time") as mock_time,
            _patch_is_transient(gemini_mod, _FakeServerError, _FakeClientError),
        ):
            with pytest.raises(RecipeExtractionError):
                extractor.extract_from_url(_YOUTUBE_URL)

        mock_client.models.generate_content.assert_called_once()
        mock_time.sleep.assert_not_called()

    def test_400_bad_request_is_not_retried(self):
        """400 ClientError (e.g. invalid video) → single attempt, no retry."""
        import app.services.video.gemini as gemini_mod

        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = _FakeClientError(400, "INVALID_ARGUMENT")
        extractor = _make_extractor(mock_client)

        with (
            patch.object(gemini_mod, "time") as mock_time,
            _patch_is_transient(gemini_mod, _FakeServerError, _FakeClientError),
        ):
            with pytest.raises(RecipeExtractionError):
                extractor.extract_from_url(_YOUTUBE_URL)

        mock_client.models.generate_content.assert_called_once()
        mock_time.sleep.assert_not_called()

    def test_429_rate_limit_is_retried(self):
        """429 ClientError is transient (temporary rate limit) → retried."""
        import app.services.video.gemini as gemini_mod

        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = [
            _FakeClientError(429, "RESOURCE_EXHAUSTED"),
            _make_response(parsed=_VALID_RECIPE),
        ]
        extractor = _make_extractor(mock_client)

        with (
            patch.object(gemini_mod, "time"),
            _patch_is_transient(gemini_mod, _FakeServerError, _FakeClientError),
        ):
            result = extractor.extract_from_url(_YOUTUBE_URL)

        assert isinstance(result, RecipeSchema)
        assert mock_client.models.generate_content.call_count == 2

    def test_schema_validation_error_is_not_retried(self):
        """
        RecipeExtractionError from _parse_response (schema/parse failure) is
        permanent and must never trigger a retry.
        """
        import app.services.video.gemini as gemini_mod

        bad = {**_VALID_RECIPE_DICT, "equipment": [{"name": "saucepan"}]}
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = _make_response(
            parsed=None,
            text=json.dumps(bad),
        )
        extractor = _make_extractor(mock_client)

        with (
            patch.object(gemini_mod, "time") as mock_time,
            _patch_is_transient(gemini_mod, _FakeServerError, _FakeClientError),
        ):
            with pytest.raises(RecipeExtractionError, match="schema"):
                extractor.extract_from_url(_YOUTUBE_URL)

        mock_client.models.generate_content.assert_called_once()
        mock_time.sleep.assert_not_called()

    # ── Backoff timing ─────────────────────────────────────────────────────────

    def test_backoff_increases_between_attempts(self):
        """Second sleep delay is ≥ first sleep delay (exponential backoff)."""
        import app.services.video.gemini as gemini_mod

        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = [
            _FakeServerError(503, "UNAVAILABLE"),
            _FakeServerError(503, "UNAVAILABLE"),
            _FakeServerError(503, "UNAVAILABLE"),
        ]
        extractor = _make_extractor(mock_client)
        sleep_calls = []

        def _record_sleep(seconds):
            sleep_calls.append(seconds)

        with (
            patch.object(gemini_mod, "time") as mock_time,
            _patch_is_transient(gemini_mod, _FakeServerError, _FakeClientError),
        ):
            mock_time.sleep.side_effect = _record_sleep
            with pytest.raises(RecipeExtractionError):
                extractor.extract_from_url(_YOUTUBE_URL)

        assert len(sleep_calls) == 2
        # Exponential: second delay ≥ first (ignoring jitter which is at most 0.5s)
        assert sleep_calls[1] >= sleep_calls[0] - 0.5  # allow for jitter overlap

    def test_retry_after_header_respected(self):
        """A Retry-After header on the error response overrides backoff."""
        import app.services.video.gemini as gemini_mod

        exc = _FakeServerError(503, "UNAVAILABLE")
        mock_response = MagicMock()
        mock_response.headers = {"retry-after": "7"}
        exc.response = mock_response

        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = [
            exc,
            _make_response(parsed=_VALID_RECIPE),
        ]
        extractor = _make_extractor(mock_client)
        sleep_calls = []

        with (
            patch.object(gemini_mod, "time") as mock_time,
            _patch_is_transient(gemini_mod, _FakeServerError, _FakeClientError),
        ):
            mock_time.sleep.side_effect = lambda s: sleep_calls.append(s)
            extractor.extract_from_url(_YOUTUBE_URL)

        assert len(sleep_calls) == 1
        assert sleep_calls[0] >= 7.0  # at least the Retry-After value


# ── Pipeline integration — VideoRecipeExtractor fast-path ─────────────────────


class TestPipelineVideoFastPath:
    """
    Verifies that run_pipeline() skips transcript retrieval when the extractor
    is a VideoRecipeExtractor.  Uses lightweight fakes — no DB, no network.
    """

    def _make_mock_db_session(self, job):
        db = MagicMock()
        db.get.return_value = job
        db.query.return_value.filter_by.return_value.first.return_value = None
        return db

    def test_video_extractor_bypasses_transcript_provider(self):
        import uuid

        from app.services.recipe_pipeline import run_pipeline
        from app.services.video.base import VideoRecipeExtractor

        job = MagicMock()
        job.id = uuid.uuid4()
        job.status = "pending"
        db = self._make_mock_db_session(job)
        transcript_provider = MagicMock()

        recipe = RecipeSchema(
            title="Test",
            ingredients=[Ingredient(name="Egg", quantity="2")],
            equipment=["Pan"],
            steps=["Crack egg.", "Cook."],
        )

        class _FakeVideoExtractor(VideoRecipeExtractor):
            def classify_video(self, url: str):
                return _make_classification(is_recipe=True, reason="Cooking tutorial.")

            def extract_from_url(self, url: str) -> RecipeSchema:
                return recipe

        run_pipeline(
            job_id=job.id,
            source_url=_YOUTUBE_URL,
            db=db,
            transcript_provider=transcript_provider,
            recipe_extractor=_FakeVideoExtractor(),
        )

        transcript_provider.fetch.assert_not_called()
        assert job.status == "completed"

    def test_text_extractor_calls_transcript_provider(self):
        import uuid

        from app.services.llm.base import RecipeExtractor
        from app.services.recipe_pipeline import run_pipeline

        job = MagicMock()
        job.id = uuid.uuid4()
        job.status = "pending"
        db = self._make_mock_db_session(job)

        recipe = RecipeSchema(
            title="Test",
            ingredients=[Ingredient(name="Egg", quantity="2")],
            equipment=["Pan"],
            steps=["Crack egg.", "Cook."],
        )

        class _FakeTranscriptProvider:
            def fetch(self, url: str) -> str:
                return "transcript text"

        class _FakeTextExtractor(RecipeExtractor):
            def extract(self, transcript: str) -> RecipeSchema:
                assert transcript == "transcript text"
                return recipe

        run_pipeline(
            job_id=job.id,
            source_url=_YOUTUBE_URL,
            db=db,
            transcript_provider=_FakeTranscriptProvider(),
            recipe_extractor=_FakeTextExtractor(),
        )

        assert job.status == "completed"


# ── Classification unit tests ──────────────────────────────────────────────────


class TestGeminiClassification:
    """
    Unit tests for classify_video() and its supporting private methods.

    All tests mock the SDK entirely — no real Gemini calls or env vars needed.
    """

    # ── Structured output happy path ───────────────────────────────────────────

    def test_recipe_video_returns_is_recipe_true(self):
        """A cooking tutorial should return is_recipe=True."""
        mock_client = MagicMock()
        classification = _make_classification(
            is_recipe=True,
            reason="The video demonstrates preparation of a pasta dish step by step.",
        )
        mock_client.models.generate_content.return_value = _make_response(parsed=classification)
        extractor = _make_extractor(mock_client)
        result = extractor.classify_video(_YOUTUBE_URL)

        assert result.is_recipe is True
        assert "pasta" in result.reason

    def test_non_recipe_video_returns_is_recipe_false(self):
        """A food review should return is_recipe=False."""
        mock_client = MagicMock()
        classification = _make_classification(
            is_recipe=False,
            reason="The video is a restaurant review and contains no preparation instructions.",
        )
        mock_client.models.generate_content.return_value = _make_response(parsed=classification)
        extractor = _make_extractor(mock_client)
        result = extractor.classify_video(_YOUTUBE_URL)

        assert result.is_recipe is False
        assert result.reason != ""

    def test_unrelated_video_returns_is_recipe_false(self):
        """A video completely unrelated to food should return is_recipe=False."""
        mock_client = MagicMock()
        classification = _make_classification(
            is_recipe=False,
            reason="The video is a car review and has no food or drink content.",
        )
        mock_client.models.generate_content.return_value = _make_response(parsed=classification)
        extractor = _make_extractor(mock_client)
        result = extractor.classify_video(_YOUTUBE_URL)

        assert result.is_recipe is False

    def test_youtube_short_can_classify_as_recipe(self):
        """Short-form videos are valid recipe candidates."""
        mock_client = MagicMock()
        classification = _make_classification(
            is_recipe=True,
            reason="The short clip visually demonstrates how to make a smoothie.",
        )
        mock_client.models.generate_content.return_value = _make_response(parsed=classification)
        short_url = "https://www.youtube.com/shorts/abc123"
        extractor = _make_extractor(mock_client)
        result = extractor.classify_video(short_url)

        assert result.is_recipe is True

    def test_classify_uses_classification_response_schema(self):
        """response_schema=RecipeVideoClassification must be passed to GenerateContentConfig."""
        mock_types = _make_mock_types()
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = _make_response(
            parsed=_make_classification(is_recipe=True)
        )
        extractor = _make_extractor(mock_client, mock_types)
        extractor.classify_video(_YOUTUBE_URL)

        call_kwargs = mock_types.GenerateContentConfig.call_args.kwargs
        assert call_kwargs.get("response_schema") is RecipeVideoClassification

    def test_classify_calls_generate_content_once_on_success(self):
        """A single successful classification makes exactly one API call."""
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = _make_response(
            parsed=_make_classification(is_recipe=True)
        )
        extractor = _make_extractor(mock_client)
        extractor.classify_video(_YOUTUBE_URL)

        mock_client.models.generate_content.assert_called_once()

    # ── Text-fallback path ─────────────────────────────────────────────────────

    def test_classify_text_fallback_valid_json(self):
        """Valid JSON classification in response.text is accepted when parsed is None."""
        import json

        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = _make_response(
            parsed=None,
            text=json.dumps({"is_recipe": False, "reason": "This is a mukbang video."}),
        )
        extractor = _make_extractor(mock_client)
        result = extractor.classify_video(_YOUTUBE_URL)

        assert result.is_recipe is False
        assert result.reason == "This is a mukbang video."

    def test_classify_text_fallback_invalid_json_raises(self):
        """Non-JSON response in classification fallback raises RecipeExtractionError."""
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = _make_response(
            parsed=None,
            text="Not a recipe video, trust me.",
        )
        extractor = _make_extractor(mock_client)
        with pytest.raises(RecipeExtractionError, match="schema"):
            extractor.classify_video(_YOUTUBE_URL)

    def test_classify_text_fallback_missing_field_raises(self):
        """JSON missing 'reason' fails schema validation for classification."""
        import json

        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = _make_response(
            parsed=None,
            text=json.dumps({"is_recipe": True}),
        )
        extractor = _make_extractor(mock_client)
        with pytest.raises(RecipeExtractionError, match="schema"):
            extractor.classify_video(_YOUTUBE_URL)

    # ── Retry behaviour ────────────────────────────────────────────────────────

    def test_classify_503_then_success(self):
        """503 on first classification attempt, success on second."""
        import app.services.video.gemini as gemini_mod

        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = [
            _FakeServerError(503, "UNAVAILABLE"),
            _make_response(parsed=_make_classification(is_recipe=True)),
        ]
        extractor = _make_extractor(mock_client)

        with (
            patch.object(gemini_mod, "time"),
            _patch_is_transient(gemini_mod, _FakeServerError, _FakeClientError),
        ):
            result = extractor.classify_video(_YOUTUBE_URL)

        assert result.is_recipe is True
        assert mock_client.models.generate_content.call_count == 2

    def test_classify_permanent_error_not_retried(self):
        """401 ClientError for classification → single attempt, RecipeExtractionError."""
        import app.services.video.gemini as gemini_mod

        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = _FakeClientError(401, "UNAUTHENTICATED")
        extractor = _make_extractor(mock_client)

        with (
            patch.object(gemini_mod, "time") as mock_time,
            _patch_is_transient(gemini_mod, _FakeServerError, _FakeClientError),
        ):
            with pytest.raises(RecipeExtractionError):
                extractor.classify_video(_YOUTUBE_URL)

        mock_client.models.generate_content.assert_called_once()
        mock_time.sleep.assert_not_called()

    def test_classify_all_retries_exhausted_raises(self):
        """Three consecutive 503s on classification exhaust all retries."""
        import app.services.video.gemini as gemini_mod

        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = [
            _FakeServerError(503, "UNAVAILABLE"),
            _FakeServerError(503, "UNAVAILABLE"),
            _FakeServerError(503, "UNAVAILABLE"),
        ]
        extractor = _make_extractor(mock_client)

        with (
            patch.object(gemini_mod, "time"),
            _patch_is_transient(gemini_mod, _FakeServerError, _FakeClientError),
        ):
            with pytest.raises(RecipeExtractionError):
                extractor.classify_video(_YOUTUBE_URL)

        assert mock_client.models.generate_content.call_count == 3


# ── Classification → extraction pipeline tests ────────────────────────────────


class TestClassificationExtractionPipeline:
    """
    Pipeline-level tests verifying the full classification → extraction flow.

    These tests use a fake VideoRecipeExtractor so they do not depend on the
    real Gemini SDK.  They exercise run_pipeline() directly.
    """

    def _make_mock_db_session(self, job):
        db = MagicMock()
        db.get.return_value = job
        db.query.return_value.filter_by.return_value.first.return_value = None
        return db

    def _make_job(self):
        import uuid

        job = MagicMock()
        job.id = uuid.uuid4()
        job.status = "pending"
        job.classification_reason = None
        job.error_message = None
        return job

    # ── Core classification-gate tests ────────────────────────────────────────

    def test_recipe_video_classification_true_extraction_runs(self):
        """When classify_video returns is_recipe=True, extract_from_url is called."""
        from app.services.recipe_pipeline import run_pipeline
        from app.services.video.base import VideoRecipeExtractor

        job = self._make_job()
        db = self._make_mock_db_session(job)

        extract_called = []

        class _FakeExtractor(VideoRecipeExtractor):
            def classify_video(self, url):
                return _make_classification(is_recipe=True, reason="Cooking tutorial.")

            def extract_from_url(self, url):
                extract_called.append(url)
                return RecipeSchema(
                    title="Test Recipe",
                    ingredients=[Ingredient(name="Egg", quantity="2")],
                    equipment=["Pan"],
                    steps=["Crack egg.", "Cook."],
                )

        run_pipeline(
            job_id=job.id,
            source_url=_YOUTUBE_URL,
            db=db,
            transcript_provider=MagicMock(),
            recipe_extractor=_FakeExtractor(),
        )

        assert extract_called, "extract_from_url should have been called"
        assert job.status == "completed"

    def test_non_recipe_video_classification_false_extraction_never_runs(self):
        """When classify_video returns is_recipe=False, extract_from_url is never called."""
        from app.services.recipe_pipeline import run_pipeline
        from app.services.video.base import VideoRecipeExtractor

        job = self._make_job()
        db = self._make_mock_db_session(job)

        extract_called = []

        class _FakeExtractor(VideoRecipeExtractor):
            def classify_video(self, url):
                return _make_classification(
                    is_recipe=False,
                    reason="The video is a food review with no preparation steps.",
                )

            def extract_from_url(self, url):
                extract_called.append(url)
                raise AssertionError("extract_from_url must not be called for non-recipe")

        run_pipeline(
            job_id=job.id,
            source_url=_YOUTUBE_URL,
            db=db,
            transcript_provider=MagicMock(),
            recipe_extractor=_FakeExtractor(),
        )

        assert not extract_called, "extract_from_url must not be called"
        assert job.status == "not_recipe"

    def test_non_recipe_job_stores_classification_reason(self):
        """classification_reason on the job must contain Gemini's explanation."""
        from app.services.recipe_pipeline import run_pipeline
        from app.services.video.base import VideoRecipeExtractor

        job = self._make_job()
        db = self._make_mock_db_session(job)
        reason = "The video is a mukbang eating video with no recipe instructions."

        class _FakeExtractor(VideoRecipeExtractor):
            def classify_video(self, url):
                return _make_classification(is_recipe=False, reason=reason)

            def extract_from_url(self, url):
                raise AssertionError("must not be called")

        run_pipeline(
            job_id=job.id,
            source_url=_YOUTUBE_URL,
            db=db,
            transcript_provider=MagicMock(),
            recipe_extractor=_FakeExtractor(),
        )

        assert job.classification_reason == reason
        assert job.error_message is None  # error_message stays clean

    def test_non_recipe_job_recipe_id_is_none(self):
        """A not_recipe job must never have a recipe_id assigned."""
        from app.services.recipe_pipeline import run_pipeline
        from app.services.video.base import VideoRecipeExtractor

        job = self._make_job()
        job.recipe_id = None
        db = self._make_mock_db_session(job)

        class _FakeExtractor(VideoRecipeExtractor):
            def classify_video(self, url):
                return _make_classification(is_recipe=False, reason="Food challenge video.")

            def extract_from_url(self, url):
                raise AssertionError("must not be called")

        run_pipeline(
            job_id=job.id,
            source_url=_YOUTUBE_URL,
            db=db,
            transcript_provider=MagicMock(),
            recipe_extractor=_FakeExtractor(),
        )

        assert job.recipe_id is None

    def test_non_recipe_no_recipe_row_created(self):
        """No Recipe ORM object is added to the session for a not_recipe job."""
        from app.services.recipe_pipeline import run_pipeline
        from app.services.video.base import VideoRecipeExtractor

        job = self._make_job()
        db = self._make_mock_db_session(job)

        class _FakeExtractor(VideoRecipeExtractor):
            def classify_video(self, url):
                return _make_classification(is_recipe=False, reason="Grocery haul video.")

            def extract_from_url(self, url):
                raise AssertionError("must not be called")

        run_pipeline(
            job_id=job.id,
            source_url=_YOUTUBE_URL,
            db=db,
            transcript_provider=MagicMock(),
            recipe_extractor=_FakeExtractor(),
        )

        db.add.assert_not_called()

    # ── Optional-field tolerance tests ────────────────────────────────────────

    def test_recipe_with_null_macros_succeeds(self):
        """A recipe with no calorie/macro data still completes successfully."""
        from app.services.recipe_pipeline import run_pipeline
        from app.services.video.base import VideoRecipeExtractor

        job = self._make_job()
        db = self._make_mock_db_session(job)

        class _FakeExtractor(VideoRecipeExtractor):
            def classify_video(self, url):
                return _make_classification(is_recipe=True, reason="Baking tutorial.")

            def extract_from_url(self, url):
                return RecipeSchema(
                    title="Plain Cake",
                    ingredients=[Ingredient(name="Flour", quantity="200g")],
                    equipment=["Oven"],
                    steps=["Mix.", "Bake."],
                    calories=None,
                    protein_g=None,
                    carbs_g=None,
                    fat_g=None,
                )

        run_pipeline(
            job_id=job.id,
            source_url=_YOUTUBE_URL,
            db=db,
            transcript_provider=MagicMock(),
            recipe_extractor=_FakeExtractor(),
        )

        assert job.status == "completed"

    def test_recipe_with_no_description_succeeds(self):
        """A recipe with description=None still completes successfully."""
        from app.services.recipe_pipeline import run_pipeline
        from app.services.video.base import VideoRecipeExtractor

        job = self._make_job()
        db = self._make_mock_db_session(job)

        class _FakeExtractor(VideoRecipeExtractor):
            def classify_video(self, url):
                return _make_classification(is_recipe=True, reason="Drink prep video.")

            def extract_from_url(self, url):
                return RecipeSchema(
                    title="Simple Juice",
                    description=None,
                    ingredients=[Ingredient(name="Orange", quantity="2")],
                    equipment=[],
                    steps=["Squeeze oranges."],
                )

        run_pipeline(
            job_id=job.id,
            source_url=_YOUTUBE_URL,
            db=db,
            transcript_provider=MagicMock(),
            recipe_extractor=_FakeExtractor(),
        )

        assert job.status == "completed"

    def test_recipe_with_empty_equipment_succeeds(self):
        """A recipe with an empty equipment list still completes successfully."""
        from app.services.recipe_pipeline import run_pipeline
        from app.services.video.base import VideoRecipeExtractor

        job = self._make_job()
        db = self._make_mock_db_session(job)

        class _FakeExtractor(VideoRecipeExtractor):
            def classify_video(self, url):
                return _make_classification(is_recipe=True, reason="Meal-prep demonstration.")

            def extract_from_url(self, url):
                return RecipeSchema(
                    title="Raw Salad",
                    ingredients=[Ingredient(name="Lettuce", quantity="1 head")],
                    equipment=[],
                    steps=["Tear lettuce.", "Toss."],
                )

        run_pipeline(
            job_id=job.id,
            source_url=_YOUTUBE_URL,
            db=db,
            transcript_provider=MagicMock(),
            recipe_extractor=_FakeExtractor(),
        )

        assert job.status == "completed"

    # ── Deduplication behaviour unchanged ─────────────────────────────────────

    def test_deduplication_still_works_for_recipe_videos(self):
        """
        When two recipe videos produce identical extracted content, the second
        job reuses the existing recipe row (dedup behaviour is unchanged).
        """
        import uuid

        from app.services.recipe_pipeline import run_pipeline
        from app.services.video.base import VideoRecipeExtractor

        recipe = RecipeSchema(
            title="Dup Recipe",
            ingredients=[Ingredient(name="Egg", quantity="1")],
            equipment=["Pan"],
            steps=["Cook egg."],
        )

        # Simulate the dedup path: the DB query finds an existing recipe.
        existing_recipe_id = uuid.uuid4()
        existing_mock = MagicMock()
        existing_mock.id = existing_recipe_id

        job = self._make_job()
        db = MagicMock()
        db.get.return_value = job
        db.query.return_value.filter_by.return_value.first.return_value = existing_mock

        class _FakeExtractor(VideoRecipeExtractor):
            def classify_video(self, url):
                return _make_classification(is_recipe=True, reason="Cooking tutorial.")

            def extract_from_url(self, url):
                return recipe

        run_pipeline(
            job_id=job.id,
            source_url=_YOUTUBE_URL,
            db=db,
            transcript_provider=MagicMock(),
            recipe_extractor=_FakeExtractor(),
        )

        # Job completed with the existing recipe's ID — no new row added.
        assert job.status == "completed"
        assert job.recipe_id == existing_recipe_id
        db.add.assert_not_called()
