import logging
import subprocess
import tempfile
from pathlib import Path

import openai

from app.services.transcript.base import TranscriptProvider, TranscriptUnavailableError

logger = logging.getLogger(__name__)


class WhisperTranscriptProvider(TranscriptProvider):
    """
    Transcribes audio from a YouTube video URL using yt-dlp + OpenAI Whisper API.

    Used as the fallback when YouTubeTranscriptProvider cannot retrieve captions
    (PoToken blocking, TooManyRequests, no captions available).

    Flow:
      1. yt-dlp downloads the best available audio-only stream to a temp file.
      2. The audio file is sent to the OpenAI audio.transcriptions.create() endpoint.
      3. The plain-text transcription is returned.
      4. The temp file is deleted regardless of success or failure.

    Configuration (via environment — nothing hardcoded):
      OPENAI_API_KEY         : reuses the same key as the LLM provider
      WHISPER_MODEL          : default "whisper-1"
      WHISPER_TIMEOUT_SECONDS: default 300 (long videos can take time)
    """

    # yt-dlp arguments that produce the smallest usable audio file:
    #   -x                  extract audio only (discard video stream)
    #   --audio-format mp3  re-encode to mp3 (wide codec support, small files)
    #   --audio-quality 5   mid-quality VBR — sufficient for speech transcription
    #   -o <path>           output path template
    #   --no-playlist       never download a playlist if a playlist URL is given
    #   --quiet             suppress yt-dlp progress output (it's noisy in logs)
    _YTDLP_ARGS = [
        "yt-dlp",
        "-x",
        "--audio-format",
        "mp3",
        "--audio-quality",
        "5",
        "--no-playlist",
        "--quiet",
        "--no-warnings",
    ]

    def __init__(self) -> None:
        from app.core.config import get_settings

        settings = get_settings()

        api_key = settings.openai_api_key.get_secret_value()
        if not api_key:
            raise TranscriptUnavailableError(
                "OPENAI_API_KEY is not set. The Whisper audio fallback requires an OpenAI API key."
            )

        self._client = openai.OpenAI(
            api_key=api_key,
            timeout=float(settings.whisper_timeout_seconds),
        )
        self._model = settings.whisper_model
        logger.info("WhisperTranscriptProvider initialised model=%s", self._model)

    def fetch(self, url: str) -> str:
        """
        Download audio from url and transcribe it with the Whisper API.

        Raises TranscriptUnavailableError for all failure modes:
          - yt-dlp not installed or returned a non-zero exit code
          - OpenAI API errors (auth, rate limit, network, timeout)
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            audio_path = self._download_audio(url, Path(tmpdir))
            return self._transcribe(audio_path, url)

    # ── Private helpers ───────────────────────────────────────────────────────

    def _download_audio(self, url: str, tmpdir: Path) -> Path:
        """
        Run yt-dlp to download the audio stream to tmpdir.
        Returns the path of the downloaded audio file.
        Raises TranscriptUnavailableError on failure.
        """
        output_template = str(tmpdir / "audio.%(ext)s")
        cmd = self._YTDLP_ARGS + ["-o", output_template, url]

        logger.info("whisper_fallback downloading audio url=%s", url)
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,  # download timeout separate from transcription timeout
            )
        except FileNotFoundError:
            raise TranscriptUnavailableError(
                "yt-dlp is not installed or not on PATH. "
                "The Whisper audio fallback requires yt-dlp."
            ) from None
        except subprocess.TimeoutExpired:
            raise TranscriptUnavailableError(
                f"yt-dlp timed out downloading audio for URL: {url}"
            ) from None

        if result.returncode != 0:
            # yt-dlp writes useful diagnostics to stderr — log them but never
            # expose the full output through the API error message.
            logger.error(
                "yt-dlp failed url=%s returncode=%d stderr=%.500s",
                url,
                result.returncode,
                result.stderr,
            )
            raise TranscriptUnavailableError(
                f"Failed to download audio for URL: {url}. "
                "The video may be unavailable, region-locked, or require authentication."
            )

        # yt-dlp writes the output file with the extension it chose (e.g. audio.mp3).
        # Find whatever it created in the temp directory.
        candidates = list(tmpdir.iterdir())
        if not candidates:
            raise TranscriptUnavailableError(
                f"yt-dlp succeeded but produced no output file for URL: {url}"
            )

        audio_path = candidates[0]
        logger.info(
            "whisper_fallback audio downloaded path=%s size_bytes=%d",
            audio_path.name,
            audio_path.stat().st_size,
        )
        return audio_path

    def _transcribe(self, audio_path: Path, source_url: str) -> str:
        """
        Send the audio file to the OpenAI Whisper API and return the transcript text.
        Raises TranscriptUnavailableError on API failure.
        """
        logger.info(
            "whisper_fallback transcribing model=%s file=%s",
            self._model,
            audio_path.name,
        )

        try:
            with audio_path.open("rb") as audio_file:
                response = self._client.audio.transcriptions.create(
                    model=self._model,
                    file=audio_file,
                    response_format="text",
                )
        except openai.AuthenticationError as exc:
            raise TranscriptUnavailableError(
                "OpenAI authentication failed for Whisper transcription. "
                "Check that OPENAI_API_KEY is correct."
            ) from exc
        except openai.RateLimitError as exc:
            raise TranscriptUnavailableError(
                "OpenAI rate limit exceeded during Whisper transcription."
            ) from exc
        except openai.APITimeoutError as exc:
            raise TranscriptUnavailableError(
                f"Whisper transcription timed out after {self._client.timeout}s "
                f"for URL: {source_url}"
            ) from exc
        except openai.APIConnectionError as exc:
            raise TranscriptUnavailableError(
                "Could not connect to the OpenAI API for Whisper transcription."
            ) from exc
        except openai.APIError as exc:
            raise TranscriptUnavailableError(
                f"OpenAI Whisper API error ({type(exc).__name__}): {exc.message}"
            ) from exc

        # response_format="text" returns the transcript as a plain string directly.
        transcript = str(response).strip()
        if not transcript:
            raise TranscriptUnavailableError(
                f"Whisper returned an empty transcription for URL: {source_url}"
            )

        logger.info(
            "whisper_fallback transcription complete url=%s chars=%d",
            source_url,
            len(transcript),
        )
        return transcript
