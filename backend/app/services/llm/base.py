from abc import ABC, abstractmethod

from app.schemas.recipe import RecipeSchema


class RecipeExtractionError(Exception):
    """
    Raised when a recipe cannot be extracted from a transcript.

    Sub-cases:
      - LLM API call failed (auth error, rate limit, network error, timeout)
      - LLM returned a response that could not be parsed as JSON
      - Parsed JSON did not pass RecipeSchema validation
    """


class RecipeExtractor(ABC):
    @abstractmethod
    def extract(self, transcript: str) -> RecipeSchema:
        """Extract a structured recipe from a plain-text transcript."""
