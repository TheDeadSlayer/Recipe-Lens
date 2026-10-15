"""
Tests for WhisperTranscriptProvider.

All external calls (yt-dlp subprocess, OpenAI API) are mocked.
No network access and no real API keys required.
"""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.services.transcript.base import TranscriptUnavailableError

# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_provider(monkeypatch):
    """
    Build a WhisperTranscriptProvider with settings injected and OpenAI patched.
    Returns (provider, mock_openai_client).
    """
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("WHISPER_MODEL", "whisper-1")
    monkeypatch.setenv("WHISPER_TIMEOUT_SECONDS", "300")
    from app.core.config import get_settings

    get_settings.cache_clear()

    mock_client = MagicMock()
    mock_client.timeout = 300.0

    with patch("app.services.transcript.whisper.openai.OpenAI", return_value=mock_client):
        from app.services.transcript.whisper import WhisperTranscriptProvider

        provider = WhisperTranscriptProvider()

    return provider, mock_client


def _fake_run_success(tmpdir: Path):
    """Return a side_effect callable that creates a fake audio file and returns success."""

    def _run(cmd, **kwargs):
        # yt-dlp writes to the path specified by -o; create a fake file there
        o_idx = cmd.index("-o")
        template = cmd[o_idx + 1]
        # template ends with audio.%(ext)s — write audio.mp3
        out_path = template.replace("%(ext)s", "mp3")
        Path(out_path).write_bytes(b"FAKE_AUDIO")
        result = MagicMock()
        result.returncode = 0
        result.stderr = ""
        return result

    return _run


# ── Construction tests ────────────────────────────────────────────────────────


def test_missing_api_key_raises_on_construction(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "")
    from app.core.config import get_settings

    get_settings.cache_clear()
    try:
        from app.services.transcript.whisper import WhisperTranscriptProvider

        with pytest.raises(TranscriptUnavailableError, match="OPENAI_API_KEY"):
            WhisperTranscriptProvider()
    finally:
        get_settings.cache_clear()


# ── Happy-path test ───────────────────────────────────────────────────────────


def test_fetch_returns_transcript_on_success(monkeypatch, tmp_path):
    provider, mock_client = _make_provider(monkeypatch)
    mock_client.audio.transcriptions.create.return_value = "Preheat the oven to 200 degrees."

    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    with patch(
        "app.services.transcript.whisper.subprocess.run", side_effect=_fake_run_success(tmp_path)
    ):
        result = provider.fetch(url)

    assert result == "Preheat the oven to 200 degrees."
    mock_client.audio.transcriptions.create.assert_called_once()
    call_kwargs = mock_client.audio.transcriptions.create.call_args
    assert call_kwargs.kwargs.get("model") == "whisper-1"
    assert call_kwargs.kwargs.get("response_format") == "text"


# ── yt-dlp failure tests ──────────────────────────────────────────────────────


def test_ytdlp_not_installed_raises_transcript_unavailable(monkeypatch):
    provider, _ = _make_provider(monkeypatch)
    with patch("app.services.transcript.whisper.subprocess.run", side_effect=FileNotFoundError):
        with pytest.raises(TranscriptUnavailableError, match="yt-dlp"):
            provider.fetch("https://www.youtube.com/watch?v=dQw4w9WgXcQ")


def test_ytdlp_timeout_raises_transcript_unavailable(monkeypatch):
    provider, _ = _make_provider(monkeypatch)
    with patch(
        "app.services.transcript.whisper.subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd="yt-dlp", timeout=120),
    ):
        with pytest.raises(TranscriptUnavailableError, match="timed out"):
            provider.fetch("https://www.youtube.com/watch?v=dQw4w9WgXcQ")


def test_ytdlp_nonzero_exit_raises_transcript_unavailable(monkeypatch):
    provider, _ = _make_provider(monkeypatch)
    failed_result = MagicMock()
    failed_result.returncode = 1
    failed_result.stderr = "ERROR: Video unavailable"
    with patch("app.services.transcript.whisper.subprocess.run", return_value=failed_result):
        with pytest.raises(TranscriptUnavailableError, match="Failed to download audio"):
            provider.fetch("https://www.youtube.com/watch?v=dQw4w9WgXcQ")


def test_ytdlp_no_output_file_raises_transcript_unavailable(monkeypatch):
    """yt-dlp exits 0 but writes nothing — should raise."""
    provider, _ = _make_provider(monkeypatch)

    def _run_no_output(cmd, **kwargs):
        result = MagicMock()
        result.returncode = 0
        result.stderr = ""
        return result

    with patch("app.services.transcript.whisper.subprocess.run", side_effect=_run_no_output):
        with pytest.raises(TranscriptUnavailableError, match="no output file"):
            provider.fetch("https://www.youtube.com/watch?v=dQw4w9WgXcQ")


# ── OpenAI API error tests ────────────────────────────────────────────────────


def _patch_successful_download(provider_fetch_fn, tmp_path):
    """Decorator-style helper: patches subprocess.run with a successful download."""
    return patch(
        "app.services.transcript.whisper.subprocess.run",
        side_effect=_fake_run_success(tmp_path),
    )


def test_whisper_auth_error_raises_transcript_unavailable(monkeypatch, tmp_path):
    import openai as openai_lib

    provider, mock_client = _make_provider(monkeypatch)
    mock_client.audio.transcriptions.create.side_effect = openai_lib.AuthenticationError(
        "bad key", response=MagicMock(), body={}
    )
    with _patch_successful_download(provider.fetch, tmp_path):
        with pytest.raises(TranscriptUnavailableError, match="authentication"):
            provider.fetch("https://www.youtube.com/watch?v=dQw4w9WgXcQ")


def test_whisper_rate_limit_raises_transcript_unavailable(monkeypatch, tmp_path):
    import openai as openai_lib

    provider, mock_client = _make_provider(monkeypatch)
    mock_client.audio.transcriptions.create.side_effect = openai_lib.RateLimitError(
        "rate limited", response=MagicMock(), body={}
    )
    with _patch_successful_download(provider.fetch, tmp_path):
        with pytest.raises(TranscriptUnavailableError, match="rate limit"):
            provider.fetch("https://www.youtube.com/watch?v=dQw4w9WgXcQ")


def test_whisper_timeout_raises_transcript_unavailable(monkeypatch, tmp_path):
    import openai as openai_lib

    provider, mock_client = _make_provider(monkeypatch)
    mock_client.audio.transcriptions.create.side_effect = openai_lib.APITimeoutError(
        request=MagicMock()
    )
    with _patch_successful_download(provider.fetch, tmp_path):
        with pytest.raises(TranscriptUnavailableError, match="timed out"):
            provider.fetch("https://www.youtube.com/watch?v=dQw4w9WgXcQ")


def test_whisper_connection_error_raises_transcript_unavailable(monkeypatch, tmp_path):
    import openai as openai_lib

    provider, mock_client = _make_provider(monkeypatch)
    mock_client.audio.transcriptions.create.side_effect = openai_lib.APIConnectionError(
        request=MagicMock()
    )
    with _patch_successful_download(provider.fetch, tmp_path):
        with pytest.raises(TranscriptUnavailableError, match="connect"):
            provider.fetch("https://www.youtube.com/watch?v=dQw4w9WgXcQ")


def test_whisper_empty_response_raises_transcript_unavailable(monkeypatch, tmp_path):
    provider, mock_client = _make_provider(monkeypatch)
    mock_client.audio.transcriptions.create.return_value = "   "
    with _patch_successful_download(provider.fetch, tmp_path):
        with pytest.raises(TranscriptUnavailableError, match="empty"):
            provider.fetch("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
