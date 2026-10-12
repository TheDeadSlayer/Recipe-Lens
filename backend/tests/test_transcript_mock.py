import pytest

from app.services.transcript.base import TranscriptUnavailableError
from app.services.transcript.mock import FAIL_URL, MockTranscriptProvider


def test_mock_transcript_returns_string():
    provider = MockTranscriptProvider()
    result = provider.fetch("https://www.youtube.com/watch?v=fake")
    assert isinstance(result, str)
    assert len(result) > 50  # non-trivial content


def test_mock_transcript_ignores_url():
    provider = MockTranscriptProvider()
    result_a = provider.fetch("https://example.com/video1")
    result_b = provider.fetch("https://example.com/video2")
    assert result_a == result_b  # mock always returns same content


def test_mock_transcript_raises_on_fail_url():
    provider = MockTranscriptProvider()
    with pytest.raises(TranscriptUnavailableError):
        provider.fetch(FAIL_URL)
