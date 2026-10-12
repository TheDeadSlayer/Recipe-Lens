"""
Tests for OpenAIRecipeExtractor.

All tests patch openai.OpenAI so no real API calls are made.
The extractor is constructed with a patched client; settings are injected
via monkeypatch so tests are fully isolated from the environment.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from app.schemas.recipe import Ingredient, RecipeSchema
from app.services.llm.base import RecipeExtractionError


# ── Helpers ───────────────────────────────────────────────────────────────────

_VALID_RECIPE_DICT = {
    "title": "Test Pasta",
    "description": "A quick weeknight pasta.",
    "ingredients": [
        {"name": "Pasta", "quantity": "200g"},
        {"name": "Tomato sauce", "quantity": "1 cup"},
    ],
    "equipment": ["Pot", "Strainer"],
    "steps": ["Boil water.", "Cook pasta.", "Drain and serve."],
    "calories": 400,
    "protein_g": 12.0,
    "carbs_g": 70.0,
    "fat_g": 5.0,
}


def _make_openai_response(content: str) -> MagicMock:
    """Build a minimal mock that looks like openai.ChatCompletion."""
    message = MagicMock()
    message.content = content
    choice = MagicMock()
    choice.message = message
    response = MagicMock()
    response.choices = [choice]
    return response


def _make_extractor(mock_openai_cls, return_content: str):
    """
    Configure mock_openai_cls so that:
      - OpenAI(api_key=...) returns a mock client
      - client.chat.completions.create(...) returns a response with the given content
    Returns a constructed OpenAIRecipeExtractor.
    """
    mock_client = MagicMock()
    mock_client.timeout = 60
    mock_client.chat.completions.create.return_value = _make_openai_response(return_content)
    mock_openai_cls.return_value = mock_client
    from app.services.llm.openai import OpenAIRecipeExtractor
    return OpenAIRecipeExtractor()


# ── Construction / configuration tests ───────────────────────────────────────

def test_missing_api_key_raises_on_construction(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4o")
    # Clear the lru_cache so monkeypatched env is picked up.
    from app.core.config import get_settings
    get_settings.cache_clear()
    try:
        from app.services.llm.openai import OpenAIRecipeExtractor
        with pytest.raises(RecipeExtractionError, match="OPENAI_API_KEY"):
            OpenAIRecipeExtractor()
    finally:
        get_settings.cache_clear()


def test_missing_model_raises_on_construction(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    monkeypatch.setenv("OPENAI_MODEL", "")
    from app.core.config import get_settings
    get_settings.cache_clear()
    try:
        from app.services.llm.openai import OpenAIRecipeExtractor
        with pytest.raises(RecipeExtractionError, match="OPENAI_MODEL"):
            OpenAIRecipeExtractor()
    finally:
        get_settings.cache_clear()


# ── Happy-path tests ──────────────────────────────────────────────────────────

@patch("app.services.llm.openai.openai.OpenAI")
def test_extract_returns_recipe_schema(mock_openai_cls, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4o")
    from app.core.config import get_settings
    get_settings.cache_clear()
    try:
        extractor = _make_extractor(mock_openai_cls, json.dumps(_VALID_RECIPE_DICT))
        result = extractor.extract("Some transcript text.")
        assert isinstance(result, RecipeSchema)
        assert result.title == "Test Pasta"
        assert len(result.ingredients) == 2
        assert result.ingredients[0].name == "Pasta"
        assert result.calories == 400
    finally:
        get_settings.cache_clear()


@patch("app.services.llm.openai.openai.OpenAI")
def test_extract_handles_null_optional_fields(mock_openai_cls, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4o")
    from app.core.config import get_settings
    get_settings.cache_clear()
    try:
        recipe_dict = {**_VALID_RECIPE_DICT, "calories": None, "protein_g": None,
                       "carbs_g": None, "fat_g": None, "description": None}
        extractor = _make_extractor(mock_openai_cls, json.dumps(recipe_dict))
        result = extractor.extract("Some transcript.")
        assert result.calories is None
        assert result.description is None
    finally:
        get_settings.cache_clear()


# ── Malformed response tests ──────────────────────────────────────────────────

@patch("app.services.llm.openai.openai.OpenAI")
def test_non_json_response_raises_extraction_error(mock_openai_cls, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4o")
    from app.core.config import get_settings
    get_settings.cache_clear()
    try:
        extractor = _make_extractor(mock_openai_cls, "Here is your recipe: ...")
        with pytest.raises(RecipeExtractionError, match="JSON"):
            extractor.extract("transcript")
    finally:
        get_settings.cache_clear()


@patch("app.services.llm.openai.openai.OpenAI")
def test_missing_required_field_raises_extraction_error(mock_openai_cls, monkeypatch):
    """A response missing the required 'title' field must fail validation."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4o")
    from app.core.config import get_settings
    get_settings.cache_clear()
    try:
        bad_dict = {k: v for k, v in _VALID_RECIPE_DICT.items() if k != "title"}
        extractor = _make_extractor(mock_openai_cls, json.dumps(bad_dict))
        with pytest.raises(RecipeExtractionError, match="schema"):
            extractor.extract("transcript")
    finally:
        get_settings.cache_clear()


@patch("app.services.llm.openai.openai.OpenAI")
def test_wrong_ingredient_type_raises_extraction_error(mock_openai_cls, monkeypatch):
    """Ingredients that are plain strings instead of {name, quantity} objects must fail."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4o")
    from app.core.config import get_settings
    get_settings.cache_clear()
    try:
        bad_dict = {**_VALID_RECIPE_DICT, "ingredients": ["Pasta", "Sauce"]}
        extractor = _make_extractor(mock_openai_cls, json.dumps(bad_dict))
        with pytest.raises(RecipeExtractionError, match="schema"):
            extractor.extract("transcript")
    finally:
        get_settings.cache_clear()


@patch("app.services.llm.openai.openai.OpenAI")
def test_empty_response_raises_extraction_error(mock_openai_cls, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4o")
    from app.core.config import get_settings
    get_settings.cache_clear()
    try:
        extractor = _make_extractor(mock_openai_cls, "")
        with pytest.raises(RecipeExtractionError):
            extractor.extract("transcript")
    finally:
        get_settings.cache_clear()


# ── API error tests ───────────────────────────────────────────────────────────

def _extractor_with_api_error(mock_openai_cls, monkeypatch, side_effect):
    """Shared setup: build an extractor whose create() call raises side_effect."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4o")
    from app.core.config import get_settings
    get_settings.cache_clear()
    mock_client = MagicMock()
    mock_client.timeout = 60
    mock_client.chat.completions.create.side_effect = side_effect
    mock_openai_cls.return_value = mock_client
    from app.services.llm.openai import OpenAIRecipeExtractor
    return OpenAIRecipeExtractor()


@patch("app.services.llm.openai.openai.OpenAI")
def test_authentication_error_raises_extraction_error(mock_openai_cls, monkeypatch):
    import openai as openai_lib
    extractor = _extractor_with_api_error(
        mock_openai_cls, monkeypatch,
        openai_lib.AuthenticationError("bad key", response=MagicMock(), body={})
    )
    try:
        with pytest.raises(RecipeExtractionError, match="authentication"):
            extractor.extract("transcript")
    finally:
        from app.core.config import get_settings
        get_settings.cache_clear()


@patch("app.services.llm.openai.openai.OpenAI")
def test_rate_limit_error_raises_extraction_error(mock_openai_cls, monkeypatch):
    import openai as openai_lib
    extractor = _extractor_with_api_error(
        mock_openai_cls, monkeypatch,
        openai_lib.RateLimitError("rate limited", response=MagicMock(), body={})
    )
    try:
        with pytest.raises(RecipeExtractionError, match="rate limit"):
            extractor.extract("transcript")
    finally:
        from app.core.config import get_settings
        get_settings.cache_clear()


@patch("app.services.llm.openai.openai.OpenAI")
def test_timeout_error_raises_extraction_error(mock_openai_cls, monkeypatch):
    import openai as openai_lib
    extractor = _extractor_with_api_error(
        mock_openai_cls, monkeypatch,
        openai_lib.APITimeoutError(request=MagicMock())
    )
    try:
        with pytest.raises(RecipeExtractionError, match="timed out"):
            extractor.extract("transcript")
    finally:
        from app.core.config import get_settings
        get_settings.cache_clear()


@patch("app.services.llm.openai.openai.OpenAI")
def test_connection_error_raises_extraction_error(mock_openai_cls, monkeypatch):
    import openai as openai_lib
    extractor = _extractor_with_api_error(
        mock_openai_cls, monkeypatch,
        openai_lib.APIConnectionError(request=MagicMock())
    )
    try:
        with pytest.raises(RecipeExtractionError, match="connect"):
            extractor.extract("transcript")
    finally:
        from app.core.config import get_settings
        get_settings.cache_clear()
