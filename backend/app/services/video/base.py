from abc import ABC, abstractmethod

from app.schemas.recipe import RecipeSchema, RecipeVideoClassification


class VideoRecipeExtractor(ABC):
    """
    Abstract base for video-native recipe extractors.

    Unlike RecipeExtractor (which operates on a pre-fetched plain-text
    transcript), VideoRecipeExtractor receives the public video URL directly
    and is responsible for both understanding the video and extracting the
    recipe.

    This abstraction deliberately lives in services/video/ rather than
    services/llm/ because it bypasses the transcript retrieval layer entirely:
    the implementing model (e.g. Gemini) processes audio, speech, and
    on-screen visuals as a single multimodal unit.

    The pipeline always calls classify_video() first.  Only when the result's
    is_recipe flag is True will extract_from_url() be called.
    """

    @abstractmethod
    def classify_video(self, url: str) -> RecipeVideoClassification:
        """
        Determine whether the video is a genuine food or drink recipe video.

        The decision must be based on the semantic purpose and content of the
        video, not on the completeness of any recipe schema.

        Raises RecipeExtractionError (from app.services.llm.base) for all
        failure modes so the pipeline's existing error handler can treat it
        uniformly.
        """

    @abstractmethod
    def extract_from_url(self, url: str) -> RecipeSchema:
        """
        Extract a structured recipe directly from a public video URL.

        Called only after classify_video() returns is_recipe=True.

        The implementation is responsible for calling the underlying model API
        and validating the response against RecipeSchema.

        Raises RecipeExtractionError (from app.services.llm.base) for all
        failure modes so the pipeline's existing error handler can treat it
        uniformly with text-based extractors.
        """
