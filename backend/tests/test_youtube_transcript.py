"""
Tests for YouTubeTranscriptProvider (youtube-transcript-api 1.x).

All tests patch YouTubeTranscriptApi so no network calls are made.
"""

from unittest.mock import MagicMock, patch

import pytest
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
    TranscriptUnavailableError,
    TranscriptsDisabledError,
    VideoUnavailableError,
)
from app.services.transcript.youtube import (
    YouTubeTranscriptProvider,
    _extract_video_id,
    _join_snippets,
)

# ── _extract_video_id unit tests ──────────────────────────────────────────────

@pytest.mark.parametrize("url,expected_id", [
    ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
    ("https://youtu.be/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
    ("https://www.youtube.com/shorts/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
    ("https://www.youtube.com/embed/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
    ("https://www.youtube.com/watch?list=PL123&v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
    ("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=42s", "dQw4w9WgXcQ"),
])
def test_extract_video_id_valid_urls(url, expected_id):
    assert _extract_video_id(url) == expected_id


@pytest.mark.parametrize("url", [
    "https://example.com/video",
    "https://vimeo.com/123456789",
    "not-a-url",
    "",
    "https://www.youtube.com/",
    "https://www.youtube.com/channel/UCxxx",
])
def test_extract_video_id_invalid_urls(url):
    with pytest.raises(InvalidYouTubeURLError):
        _extract_video_id(url)


# ── _join_snippets unit tests ─────────────────────────────────────────────────

def test_join_snippets_basic():
    snippets = [
        {"text": "Hello", "start": 0.0, "duration": 1.0},
        {"text": "world", "start": 1.0, "duration": 1.0},
    ]
    assert _join_snippets(snippets) == "Hello world"


def test_join_snippets_strips_whitespace():
    snippets = [
        {"text": "  Hello  ", "start": 0.0, "duration": 1.0},
        {"text": "  world  ", "start": 1.0, "duration": 1.0},
    ]
    assert _join_snippets(snippets) == "Hello world"


def test_join_snippets_skips_empty():
    snippets = [
        {"text": "Hello", "start": 0.0, "duration": 1.0},
        {"text": "   ", "start": 1.0, "duration": 1.0},
        {"text": "world", "start": 2.0, "duration": 1.0},
    ]
    assert _join_snippets(snippets) == "Hello world"


def test_join_snippets_empty_list():
    assert _join_snippets([]) == ""


# ── Mock transcript list helpers ──────────────────────────────────────────────

def _make_transcript(lang_code: str, is_generated: bool, snippets: list[dict]):
    t = MagicMock()
    t.language_code = lang_code
    t.is_generated = is_generated
    t.fetch.return_value = snippets
    return t


def _make_transcript_list(manual: dict[str, list], generated: dict[str, list]):
    manual_transcripts = {
        lang: _make_transcript(lang, False, snips)
        for lang, snips in manual.items()
    }
    generated_transcripts = {
        lang: _make_transcript(lang, True, snips)
        for lang, snips in generated.items()
    }
    all_transcripts = list(manual_transcripts.values()) + list(generated_transcripts.values())

    tl = MagicMock()

    def find_manually_created(langs):
        for lang in langs:
            if lang in manual_transcripts:
                return manual_transcripts[lang]
        raise NoTranscriptFound("VIDEOID", langs, {})

    def find_generated(langs):
        for lang in langs:
            if lang in generated_transcripts:
                return generated_transcripts[lang]
        raise NoTranscriptFound("VIDEOID", langs, {})

    tl.find_manually_created_transcript.side_effect = find_manually_created
    tl.find_generated_transcript.side_effect = find_generated
    tl.__iter__ = MagicMock(return_value=iter(all_transcripts))
    return tl


_SNIPPETS = [{"text": "Preheat oven.", "start": 0.0, "duration": 2.0}]
_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
_VID = "dQw4w9WgXcQ"

# ── Language selection tests ──────────────────────────────────────────────────

@patch("app.services.transcript.youtube.YouTubeTranscriptApi")
def test_prefers_manual_english(mock_api):
    mock_api.list_transcripts.return_value = _make_transcript_list(
        manual={"en": _SNIPPETS},
        generated={"en": _SNIPPETS, "fr": _SNIPPETS},
    )
    assert YouTubeTranscriptProvider().fetch(_URL) == "Preheat oven."


@patch("app.services.transcript.youtube.YouTubeTranscriptApi")
def test_falls_back_to_auto_english_when_no_manual(mock_api):
    mock_api.list_transcripts.return_value = _make_transcript_list(
        manual={},
        generated={"en": _SNIPPETS, "fr": _SNIPPETS},
    )
    assert YouTubeTranscriptProvider().fetch(_URL) == "Preheat oven."


@patch("app.services.transcript.youtube.YouTubeTranscriptApi")
def test_falls_back_to_non_english_when_no_english(mock_api):
    fr_snippets = [{"text": "Préchauffer le four.", "start": 0.0, "duration": 2.0}]
    mock_api.list_transcripts.return_value = _make_transcript_list(
        manual={},
        generated={"fr": fr_snippets},
    )
    assert YouTubeTranscriptProvider().fetch(_URL) == "Préchauffer le four."


@patch("app.services.transcript.youtube.YouTubeTranscriptApi")
def test_returns_plain_text_string(mock_api):
    mock_api.list_transcripts.return_value = _make_transcript_list(
        manual={"en": _SNIPPETS}, generated={},
    )
    result = YouTubeTranscriptProvider().fetch(_URL)
    assert isinstance(result, str) and len(result) > 0


# ── Invalid URL tests ─────────────────────────────────────────────────────────

def test_invalid_url_raises_before_api_call():
    with pytest.raises(InvalidYouTubeURLError):
        YouTubeTranscriptProvider().fetch("https://example.com/not-youtube")


def test_non_url_raises_invalid_url_error():
    with pytest.raises(InvalidYouTubeURLError):
        YouTubeTranscriptProvider().fetch("just a string")


# ── 1.x error-mapping tests: list_transcripts ────────────────────────────────

@patch("app.services.transcript.youtube.YouTubeTranscriptApi")
def test_request_blocked_maps_to_captcha_required(mock_api):
    """RequestBlocked (PoToken/IP block) must map to CaptchaRequiredError."""
    mock_api.list_transcripts.side_effect = RequestBlocked(_VID)
    with pytest.raises(CaptchaRequiredError):
        YouTubeTranscriptProvider().fetch(_URL)


@patch("app.services.transcript.youtube.YouTubeTranscriptApi")
def test_video_unavailable_maps_to_video_unavailable_error(mock_api):
    mock_api.list_transcripts.side_effect = VideoUnavailable(_VID)
    with pytest.raises(VideoUnavailableError):
        YouTubeTranscriptProvider().fetch(_URL)


@patch("app.services.transcript.youtube.YouTubeTranscriptApi")
def test_transcripts_disabled_maps_to_transcripts_disabled_error(mock_api):
    mock_api.list_transcripts.side_effect = TranscriptsDisabled(_VID)
    with pytest.raises(TranscriptsDisabledError):
        YouTubeTranscriptProvider().fetch(_URL)


@patch("app.services.transcript.youtube.YouTubeTranscriptApi")
def test_no_transcript_found_maps_to_no_transcript_found_error(mock_api):
    mock_api.list_transcripts.side_effect = NoTranscriptFound(_VID, [], {})
    with pytest.raises(NoTranscriptFoundError):
        YouTubeTranscriptProvider().fetch(_URL)


@patch("app.services.transcript.youtube.YouTubeTranscriptApi")
def test_youtube_request_failed_maps_to_transcript_unavailable(mock_api):
    """YouTubeRequestFailed (HTTP error) is a CouldNotRetrieveTranscript subclass."""
    mock_api.list_transcripts.side_effect = YouTubeRequestFailed(_VID, Exception("503"))
    with pytest.raises(TranscriptUnavailableError):
        YouTubeTranscriptProvider().fetch(_URL)


@patch("app.services.transcript.youtube.YouTubeTranscriptApi")
def test_could_not_retrieve_transcript_catch_all(mock_api):
    """Any other CouldNotRetrieveTranscript subclass maps to TranscriptUnavailableError."""
    mock_api.list_transcripts.side_effect = CouldNotRetrieveTranscript(_VID)
    with pytest.raises(TranscriptUnavailableError):
        YouTubeTranscriptProvider().fetch(_URL)


@patch("app.services.transcript.youtube.YouTubeTranscriptApi")
def test_no_transcript_tracks_at_all_raises_no_transcript_found(mock_api):
    """Empty transcript list (iteration yields nothing) → NoTranscriptFoundError."""
    tl = MagicMock()
    tl.find_manually_created_transcript.side_effect = NoTranscriptFound(_VID, ["en"], {})
    tl.find_generated_transcript.side_effect = NoTranscriptFound(_VID, ["en"], {})
    tl.__iter__ = MagicMock(return_value=iter([]))
    mock_api.list_transcripts.return_value = tl
    with pytest.raises(NoTranscriptFoundError):
        YouTubeTranscriptProvider().fetch(_URL)


@patch("app.services.transcript.youtube.YouTubeTranscriptApi")
def test_network_error_wraps_as_transcript_unavailable(mock_api):
    mock_api.list_transcripts.side_effect = ConnectionError("timeout")
    with pytest.raises(TranscriptUnavailableError):
        YouTubeTranscriptProvider().fetch(_URL)


# ── 1.x error-mapping tests: transcript.fetch() ──────────────────────────────

@patch("app.services.transcript.youtube.YouTubeTranscriptApi")
def test_request_blocked_during_fetch_maps_to_captcha_required(mock_api):
    """RequestBlocked during content fetch also maps to CaptchaRequiredError."""
    transcript = _make_transcript("en", False, _SNIPPETS)
    transcript.fetch.side_effect = RequestBlocked(_VID)
    tl = MagicMock()
    tl.find_manually_created_transcript.return_value = transcript
    mock_api.list_transcripts.return_value = tl
    with pytest.raises(CaptchaRequiredError):
        YouTubeTranscriptProvider().fetch(_URL)


@patch("app.services.transcript.youtube.YouTubeTranscriptApi")
def test_fetch_connection_error_wraps_as_transcript_unavailable(mock_api):
    transcript = _make_transcript("en", False, _SNIPPETS)
    transcript.fetch.side_effect = ConnectionError("network error during fetch")
    tl = MagicMock()
    tl.find_manually_created_transcript.return_value = transcript
    mock_api.list_transcripts.return_value = tl
    with pytest.raises(TranscriptUnavailableError):
        YouTubeTranscriptProvider().fetch(_URL)


@patch("app.services.transcript.youtube.YouTubeTranscriptApi")
def test_empty_snippets_maps_to_captcha_required(mock_api):
    """
    An empty snippets list after a successful fetch is treated as a PoToken block
    and maps to CaptchaRequiredError (triggers audio fallback, not hard failure).
    """
    transcript = _make_transcript("en", True, [])
    tl = MagicMock()
    tl.find_manually_created_transcript.side_effect = NoTranscriptFound(_VID, ["en"], {})
    tl.find_generated_transcript.return_value = transcript
    mock_api.list_transcripts.return_value = tl
    with pytest.raises(CaptchaRequiredError):
        YouTubeTranscriptProvider().fetch(_URL)


# ── Error hierarchy tests ─────────────────────────────────────────────────────

def test_captcha_required_is_transcript_unavailable():
    assert issubclass(CaptchaRequiredError, TranscriptUnavailableError)


def test_video_unavailable_is_transcript_unavailable():
    assert issubclass(VideoUnavailableError, TranscriptUnavailableError)


def test_transcripts_disabled_is_transcript_unavailable():
    assert issubclass(TranscriptsDisabledError, TranscriptUnavailableError)


def test_no_transcript_found_is_transcript_unavailable():
    assert issubclass(NoTranscriptFoundError, TranscriptUnavailableError)


def test_invalid_url_is_transcript_unavailable():
    assert issubclass(InvalidYouTubeURLError, TranscriptUnavailableError)
