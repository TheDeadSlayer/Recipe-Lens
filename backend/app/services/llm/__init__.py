from app.core.config import get_settings
from app.services.llm.base import RecipeExtractor


def get_recipe_extractor() -> RecipeExtractor:
    """Factory: returns the active RecipeExtractor based on LLM_PROVIDER env var."""
    settings = get_settings()
    provider = settings.llm_provider.lower()

    if provider == "mock":
        from app.services.llm.mock import MockRecipeExtractor
        return MockRecipeExtractor()

    if provider == "openai":
        from app.services.llm.openai import OpenAIRecipeExtractor
        return OpenAIRecipeExtractor()

    raise ValueError(
        f"Unknown LLM_PROVIDER '{provider}'. Valid options: mock, openai."
    )
