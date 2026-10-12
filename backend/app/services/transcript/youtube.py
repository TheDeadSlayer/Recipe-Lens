import logging
import re

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    CouldNotRetrieveTranscript,
    NoTranscriptFound,
    RequestBlocked,
    TranscriptsDisabled,
    VideoUnavailable,
    YouTubeRequestFailed,
)

from app.services.transcript.base import (
    CaptchaRequiredError,
    InvalidYouTubeURLError,
    NoTranscriptFoundError,
    TranscriptProvider,
    TranscriptsDisabledError,
    TranscriptUnavailableError,
    VideoUnavailableError,
)

logger = logging.getLogger(__name__)

# Matches the standard video ID found in the most common YouTube URL formats:
#   https://www.youtube.com/watch?v=XXXXXXXXXXX
#   https://youtu.be/XXXXXXXXXXX
#   https://www.youtube.com/shorts/XXXXXXXXXXX
#   https://www.youtube.com/embed/XXXXXXXXXXX
# Video IDs are always 11 characters consisting of [A-Za-z0-9_-].
_VIDEO_ID_RE = re.compile(
    r"""
    (?:
        youtu\.be/                  # youtu.be/<id>
        | youtube\.com/(?:
            watch\?(?:.*&)?v=       # watch?v=<id>  (with optional extra params)
            | shorts/               # shorts/<id>
            | embed/                # embed/<id>
            | v/                    # v/<id>  (old format)
        )
    )
    ([A-Za-z0-9_-]{11})             # capture group: the 11-char video ID
    """,
    re.VERBOSE,
)

# Preferred language codes, in priority order.
# Manual captions take precedence over auto-generated ones within each code.
_PREFERRED_LANGUAGES = ["en", "en-US", "en-GB"]


def _extract_video_id(url: str) -> str:
    """
    Parse a YouTube video ID from a URL string.
    Raises InvalidYouTubeURLError if the URL does not match a known YouTube pattern.
    """
    match = _VIDEO_ID_RE.search(url)
    if not match:
        raise InvalidYouTubeURLError(
            f"Could not extract a YouTube video ID from URL: {url!r}. "
            "Expected a standard youtube.com or youtu.be URL."
        )
    return match.group(1)


def _join_snippets(snippet_list: list[dict]) -> str:
    """
    Convert the list of transcript snippet dicts returned by youtube-transcript-api
    into a single normalised plain-text string.

    Each snippet has the shape: {"text": str, "start": float, "duration": float}.
    We strip individual snippets and join with a single space.
    """
    return " ".join(s["text"].strip() for s in snippet_list if s.get("text", "").strip())


class YouTubeTranscriptProvider(TranscriptProvider):
    """
    Fetches transcripts from YouTube using youtube-transcript-api 1.x.
    Activate by setting TRANSCRIPT_PROVIDER=youtube.

    Language selection:
      1. Prefer manual English transcripts.
      2. Fall back to auto-generated English.
      3. Fall back to the first available transcript in any language.
      4. Never translate — preserve the original caption text.

    Error mapping (1.x error hierarchy → application errors):
      RequestBlocked           → CaptchaRequiredError   (triggers audio fallback)
        (covers IpBlocked, PoTokenRequired as subclasses)
      NoTranscriptFound        → NoTranscriptFoundError (triggers audio fallback)
      TranscriptsDisabled      → TranscriptsDisabledError (hard fail — owner disabled)
      VideoUnavailable         → VideoUnavailableError    (hard fail — video gone)
      YouTubeRequestFailed     → TranscriptUnavailableError
      CouldNotRetrieveTranscript (base) → TranscriptUnavailableError
    """

    def fetch(self, url: str) -> str:
        video_id = _extract_video_id(url)

        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        except RequestBlocked as exc:
            raise CaptchaRequiredError(
                f"YouTube requires PoToken/captcha proof-of-origin for video {video_id}. "
                "Caption delivery is blocked from this IP. "
                "The audio transcription fallback will be used."
            ) from exc
        except VideoUnavailable as exc:
            raise VideoUnavailableError(
                f"YouTube video is unavailable (private, removed, or does not exist): {video_id}"
            ) from exc
        except TranscriptsDisabled as exc:
            raise TranscriptsDisabledError(
                f"Transcripts are disabled for YouTube video: {video_id}"
            ) from exc
        except NoTranscriptFound as exc:
            raise NoTranscriptFoundError(
                f"No transcripts are available for YouTube video: {video_id}"
            ) from exc
        except CouldNotRetrieveTranscript as exc:
            # Catch-all for any other 1.x retrieval error (YouTubeRequestFailed, etc.)
            raise TranscriptUnavailableError(
                f"Could not retrieve transcript list for YouTube video {video_id}: {exc}"
            ) from exc
        except Exception as exc:
            # Network errors, unexpected API changes, etc.
            raise TranscriptUnavailableError(
                f"Unexpected error retrieving transcript list for YouTube video {video_id}: {exc}"
            ) from exc

        # ── Language selection ────────────────────────────────────────────────
        transcript = None
        selected_language: str | None = None
        selected_kind: str | None = None  # "manual" or "auto-generated"

        # Pass 1: prefer manual English transcripts
        for lang in _PREFERRED_LANGUAGES:
            try:
                transcript = transcript_list.find_manually_created_transcript([lang])
                selected_language = lang
                selected_kind = "manual"
                break
            except NoTranscriptFound:
                continue

        # Pass 2: fall back to auto-generated English transcripts
        if transcript is None:
            for lang in _PREFERRED_LANGUAGES:
                try:
                    transcript = transcript_list.find_generated_transcript([lang])
                    selected_language = lang
                    selected_kind = "auto-generated"
                    break
                except NoTranscriptFound:
                    continue

        # Pass 3: fall back to the first available transcript in any language
        if transcript is None:
            available = list(transcript_list)
            if not available:
                raise NoTranscriptFoundError(
                    f"No transcript tracks available for YouTube video: {video_id}"
                )
            transcript = available[0]
            selected_language = transcript.language_code
            selected_kind = "auto-generated" if transcript.is_generated else "manual"

        logger.info(
            "transcript selected video_id=%s language=%s kind=%s",
            video_id,
            selected_language,
            selected_kind,
        )

        # ── Fetch and normalise ───────────────────────────────────────────────
        try:
            snippets = transcript.fetch()
        except RequestBlocked as exc:
            # Blocking can also surface during the content fetch.
            raise CaptchaRequiredError(
                f"YouTube requires PoToken/captcha to fetch caption content for video {video_id} "
                f"(language={selected_language})."
            ) from exc
        except CouldNotRetrieveTranscript as exc:
            raise TranscriptUnavailableError(
                f"Failed to fetch transcript content for YouTube video {video_id} "
                f"(language={selected_language}): {exc}"
            ) from exc
        except Exception as exc:
            raise TranscriptUnavailableError(
                f"Unexpected error fetching transcript content for YouTube video {video_id} "
                f"(language={selected_language}): {exc}"
            ) from exc

        if not snippets:
            # A successful fetch returning an empty list is treated as a retrieval
            # failure that should trigger the audio fallback, not a hard failure.
            raise CaptchaRequiredError(
                f"YouTube returned an empty transcript for video {video_id} "
                f"(language={selected_language}). This may indicate PoToken blocking."
            )

        return _join_snippets(snippets)
