from abc import ABC, abstractmethod

from app.schemas.recipe import RecipeSchema


class RecipeExtractor(ABC):
    @abstractmethod
    def extract(self, transcript: str) -> RecipeSchema:
        """Extract a structured recipe from a plain-text transcript."""
