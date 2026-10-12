from typing import Union

from app.core.config import get_settings
from app.services.llm.base import RecipeExtractor
from app.services.video.base import VideoRecipeExtractor


def get_recipe_extractor() -> Union[RecipeExtractor, VideoRecipeExtractor]:
    """
    Factory: returns the active recipe extractor based on LLM_PROVIDER env var.

    Returns either a RecipeExtractor (mock, openai) which operates on a
    pre-fetched transcript, or a VideoRecipeExtractor (gemini) which takes a
    video URL directly and bypasses the transcript provider.
    """
    settings = get_settings()
    provider = settings.llm_provider.lower()

    if provider == "mock":
        from app.services.llm.mock import MockRecipeExtractor
        return MockRecipeExtractor()

    if provider == "openai":
        from app.services.llm.openai import OpenAIRecipeExtractor
        return OpenAIRecipeExtractor()

    if provider == "gemini":
        from app.services.video.gemini import GeminiVideoRecipeExtractor
        return GeminiVideoRecipeExtractor()

    raise ValueError(
        f"Unknown LLM_PROVIDER '{provider}'. Valid options: mock, openai, gemini."
    )
