import logging

from app.services.transcript.base import (
    CaptchaRequiredError,
    NoTranscriptFoundError,
    TranscriptProvider,
)

logger = logging.getLogger(__name__)

# Errors on which the fallback is activated.
# Hard failures (InvalidYouTubeURLError, VideoUnavailableError) are deliberately
# excluded — there is no point attempting audio download for a non-existent video
# or a non-YouTube URL.
_FALLBACK_ON = (CaptchaRequiredError, NoTranscriptFoundError)


class WithFallbackTranscriptProvider(TranscriptProvider):
    """
    Composes a primary and a fallback TranscriptProvider.

    Behaviour:
      - Calls primary.fetch(url) first.
      - If primary succeeds, returns its result immediately.
      - If primary raises a fallback-triggering error (CaptchaRequiredError or
        NoTranscriptFoundError), activates fallback.fetch(url).
      - Hard failures (InvalidYouTubeURLError, VideoUnavailableError, and any other
        TranscriptUnavailableError not in the fallback set) propagate immediately
        without attempting the fallback.
      - If the fallback itself raises, that error propagates and the job is marked
        failed via the normal pipeline error handler.

    Both providers must implement TranscriptProvider.
    """

    def __init__(
        self,
        primary: TranscriptProvider,
        fallback: TranscriptProvider,
    ) -> None:
        self._primary = primary
        self._fallback = fallback

    def fetch(self, url: str) -> str:
        try:
            transcript = self._primary.fetch(url)
            logger.info(
                "transcript_provider primary succeeded url=%s provider=%s",
                url,
                type(self._primary).__name__,
            )
            return transcript

        except _FALLBACK_ON as primary_exc:
            logger.warning(
                "transcript_provider primary failed triggering_fallback url=%s "
                "provider=%s reason=%s",
                url,
                type(self._primary).__name__,
                primary_exc,
            )

        # Primary raised a fallback-triggering error — attempt the fallback.
        logger.info(
            "transcript_provider activating_fallback url=%s provider=%s",
            url,
            type(self._fallback).__name__,
        )
        # Any exception from the fallback propagates directly to the pipeline,
        # which marks the job as failed with fallback's error message.
        return self._fallback.fetch(url)
