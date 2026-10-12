from abc import ABC, abstractmethod


class TranscriptUnavailableError(Exception):
    """Raised when a transcript cannot be obtained for the given URL."""


class TranscriptProvider(ABC):
    @abstractmethod
    def fetch(self, url: str) -> str:
        """Fetch and return a plain-text transcript for the given video URL."""
