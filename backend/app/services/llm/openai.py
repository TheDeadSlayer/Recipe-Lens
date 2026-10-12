from app.schemas.recipe import RecipeSchema
from app.services.llm.base import RecipeExtractor


class OpenAIRecipeExtractor(RecipeExtractor):
    """
    Extracts a structured recipe using the OpenAI API.
    Activate by setting LLM_PROVIDER=openai.
    Requires OPENAI_API_KEY and OPENAI_MODEL environment variables.
    """

    def extract(self, transcript: str) -> RecipeSchema:
        raise NotImplementedError(
            "OpenAIRecipeExtractor is not yet implemented. "
            "Set LLM_PROVIDER=mock to use the mock provider."
        )
