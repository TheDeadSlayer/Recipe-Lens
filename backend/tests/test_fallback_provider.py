"""
Tests for WithFallbackTranscriptProvider.

All providers are replaced with lightweight fakes — no network calls.
"""

import pytest

from app.services.transcript.base import (
    CaptchaRequiredError,
    InvalidYouTubeURLError,
    NoTranscriptFoundError,
    TranscriptProvider,
    TranscriptUnavailableError,
    VideoUnavailableError,
)
from app.services.transcript.fallback import WithFallbackTranscriptProvider


# ── Fake provider helpers ─────────────────────────────────────────────────────

class _SuccessProvider(TranscriptProvider):
    def __init__(self, text: str = "Primary transcript."):
        self._text = text
        self.call_count = 0

    def fetch(self, url: str) -> str:
        self.call_count += 1
        return self._text


class _RaisingProvider(TranscriptProvider):
    def __init__(self, exc: Exception):
        self._exc = exc
        self.call_count = 0

    def fetch(self, url: str) -> str:
        self.call_count += 1
        raise self._exc


_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"


# ── Primary success — fallback never called ───────────────────────────────────

def test_primary_success_returns_primary_transcript():
    primary = _SuccessProvider("Primary transcript.")
    fallback = _SuccessProvider("Fallback transcript.")
    provider = WithFallbackTranscriptProvider(primary, fallback)

    result = provider.fetch(_URL)

    assert result == "Primary transcript."
    assert primary.call_count == 1
    assert fallback.call_count == 0


def test_primary_success_never_calls_fallback():
    primary = _SuccessProvider()
    fallback = _RaisingProvider(AssertionError("fallback must not be called"))
    provider = WithFallbackTranscriptProvider(primary, fallback)

    provider.fetch(_URL)  # must not raise


# ── Fallback-triggering errors ────────────────────────────────────────────────

def test_captcha_required_activates_fallback():
    primary = _RaisingProvider(CaptchaRequiredError("rate limited"))
    fallback = _SuccessProvider("Fallback transcript.")
    provider = WithFallbackTranscriptProvider(primary, fallback)

    result = provider.fetch(_URL)

    assert result == "Fallback transcript."
    assert primary.call_count == 1
    assert fallback.call_count == 1


def test_no_transcript_found_activates_fallback():
    primary = _RaisingProvider(NoTranscriptFoundError("no captions"))
    fallback = _SuccessProvider("Fallback transcript.")
    provider = WithFallbackTranscriptProvider(primary, fallback)

    result = provider.fetch(_URL)

    assert result == "Fallback transcript."
    assert fallback.call_count == 1


# ── Hard failures — fallback must NOT be called ───────────────────────────────

def test_invalid_url_error_propagates_without_fallback():
    primary = _RaisingProvider(InvalidYouTubeURLError("bad url"))
    fallback = _RaisingProvider(AssertionError("fallback must not be called"))
    provider = WithFallbackTranscriptProvider(primary, fallback)

    with pytest.raises(InvalidYouTubeURLError):
        provider.fetch(_URL)


def test_video_unavailable_propagates_without_fallback():
    primary = _RaisingProvider(VideoUnavailableError("video gone"))
    fallback = _RaisingProvider(AssertionError("fallback must not be called"))
    provider = WithFallbackTranscriptProvider(primary, fallback)

    with pytest.raises(VideoUnavailableError):
        provider.fetch(_URL)


def test_generic_transcript_unavailable_propagates_without_fallback():
    """A TranscriptUnavailableError that is not in the fallback set propagates."""
    primary = _RaisingProvider(TranscriptUnavailableError("some retrieval error"))
    fallback = _RaisingProvider(AssertionError("fallback must not be called"))
    provider = WithFallbackTranscriptProvider(primary, fallback)

    with pytest.raises(TranscriptUnavailableError):
        provider.fetch(_URL)


# ── Fallback failure propagates ───────────────────────────────────────────────

def test_fallback_failure_propagates_to_caller():
    """If the fallback itself fails, the error must propagate (job marked failed)."""
    primary = _RaisingProvider(CaptchaRequiredError("rate limited"))
    fallback = _RaisingProvider(TranscriptUnavailableError("whisper also failed"))
    provider = WithFallbackTranscriptProvider(primary, fallback)

    with pytest.raises(TranscriptUnavailableError, match="whisper also failed"):
        provider.fetch(_URL)


def test_fallback_failure_does_not_retry_primary():
    primary = _RaisingProvider(CaptchaRequiredError("rate limited"))
    fallback = _RaisingProvider(TranscriptUnavailableError("fallback error"))
    provider = WithFallbackTranscriptProvider(primary, fallback)

    with pytest.raises(TranscriptUnavailableError):
        provider.fetch(_URL)

    assert primary.call_count == 1   # primary called exactly once
    assert fallback.call_count == 1  # fallback called exactly once


# ── Correct fallback error type preserved ────────────────────────────────────

def test_fallback_error_type_is_preserved():
    """The exact exception type raised by the fallback must reach the caller."""
    class _CustomError(TranscriptUnavailableError):
        pass

    primary = _RaisingProvider(CaptchaRequiredError("blocked"))
    fallback = _RaisingProvider(_CustomError("custom fallback error"))
    provider = WithFallbackTranscriptProvider(primary, fallback)

    with pytest.raises(_CustomError):
        provider.fetch(_URL)
