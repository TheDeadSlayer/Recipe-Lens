from app.core.config import get_settings
from app.services.transcript.base import TranscriptProvider


def get_transcript_provider() -> TranscriptProvider:
    """
    Factory: returns the active TranscriptProvider based on TRANSCRIPT_PROVIDER env var.

    mock    → MockTranscriptProvider (no external calls; for tests and local dev)
    youtube → WithFallbackTranscriptProvider(
                  primary=YouTubeTranscriptProvider(),   # caption fast-path
                  fallback=WhisperTranscriptProvider()   # audio transcription fallback
              )
    """
    settings = get_settings()
    provider = settings.transcript_provider.lower()

    if provider == "mock":
        from app.services.transcript.mock import MockTranscriptProvider
        return MockTranscriptProvider()

    if provider == "youtube":
        from app.services.transcript.fallback import WithFallbackTranscriptProvider
        from app.services.transcript.whisper import WhisperTranscriptProvider
        from app.services.transcript.youtube import YouTubeTranscriptProvider
        return WithFallbackTranscriptProvider(
            primary=YouTubeTranscriptProvider(),
            fallback=WhisperTranscriptProvider(),
        )

    raise ValueError(
        f"Unknown TRANSCRIPT_PROVIDER '{provider}'. Valid options: mock, youtube."
    )
