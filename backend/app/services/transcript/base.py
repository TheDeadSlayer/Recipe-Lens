from abc import ABC, abstractmethod


class TranscriptUnavailableError(Exception):
    """
    Raised when a transcript cannot be obtained for the given URL.

    Sub-cases (all share this base so the pipeline's except block stays simple):
      - InvalidYouTubeURLError   : URL is not a recognisable YouTube URL
      - VideoUnavailableError    : video does not exist, is private, or is removed
      - TranscriptsDisabledError : the video owner has disabled captions
      - NoTranscriptFoundError   : no caption track exists in any language
      - CaptchaRequiredError     : YouTube requires PoToken/captcha to serve captions
    """


class InvalidYouTubeURLError(TranscriptUnavailableError):
    """Raised when the URL cannot be parsed as a YouTube video URL."""


class VideoUnavailableError(TranscriptUnavailableError):
    """Raised when the YouTube video does not exist, is private, or has been removed."""


class TranscriptsDisabledError(TranscriptUnavailableError):
    """Raised when the video owner has disabled captions for the video."""


class NoTranscriptFoundError(TranscriptUnavailableError):
    """Raised when no caption track is available in any language."""


class CaptchaRequiredError(TranscriptUnavailableError):
    """
    Raised when YouTube rate-limits caption delivery or requires PoToken/proof-of-origin
    (TooManyRequests in youtube-transcript-api 1.x, or an empty caption body in 0.6.x).

    This signals WithFallbackTranscriptProvider to activate the audio transcription path.
    It is NOT a hard failure — the job should continue via the fallback provider.
    """


class TranscriptProvider(ABC):
    @abstractmethod
    def fetch(self, url: str) -> str:
        """Fetch and return a plain-text transcript for the given video URL."""
