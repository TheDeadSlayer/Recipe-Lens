from app.services.llm import get_recipe_extractor
from app.services.llm.base import RecipeExtractor
from app.services.transcript import get_transcript_provider
from app.services.transcript.base import TranscriptProvider


def get_providers() -> tuple[TranscriptProvider, RecipeExtractor]:
    """Return the configured transcript provider and recipe extractor pair."""
    return get_transcript_provider(), get_recipe_extractor()
