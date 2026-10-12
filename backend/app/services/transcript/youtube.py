from app.services.transcript.base import TranscriptProvider


class YouTubeTranscriptProvider(TranscriptProvider):
    """
    Fetches transcripts from YouTube using youtube-transcript-api.
    Activate by setting TRANSCRIPT_PROVIDER=youtube.
    """

    def fetch(self, url: str) -> str:
        raise NotImplementedError(
            "YouTubeTranscriptProvider is not yet implemented. "
            "Set TRANSCRIPT_PROVIDER=mock to use the mock provider."
        )
