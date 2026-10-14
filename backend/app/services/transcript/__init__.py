import os

from app.core.config import get_settings
from app.services.transcript.base import TranscriptProvider


def get_transcript_provider() -> TranscriptProvider:
    """
    Factory: returns the active TranscriptProvider based on TRANSCRIPT_PROVIDER env var.

    mock    → MockTranscriptProvider

    youtube → YouTubeTranscriptProvider
              + Whisper fallback only when OPENAI_API_KEY is configured
    """
    settings = get_settings()
    provider = settings.transcript_provider.lower()

    if provider == "mock":
        from app.services.transcript.mock import MockTranscriptProvider

        return MockTranscriptProvider()

    if provider == "youtube":
        from app.services.transcript.youtube import YouTubeTranscriptProvider

        primary = YouTubeTranscriptProvider()

        # Whisper is optional. Do not prevent the application from starting
        # just because the fallback provider is not configured.
        if not os.getenv("OPENAI_API_KEY"):
            return primary

        from app.services.transcript.fallback import WithFallbackTranscriptProvider
        from app.services.transcript.whisper import WhisperTranscriptProvider

        return WithFallbackTranscriptProvider(
            primary=primary,
            fallback=WhisperTranscriptProvider(),
        )

    raise ValueError(
        f"Unknown TRANSCRIPT_PROVIDER '{provider}'. Valid options: mock, youtube."
    )