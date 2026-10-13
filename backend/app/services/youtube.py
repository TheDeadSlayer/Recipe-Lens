"""
Server-side YouTube video ID extraction.

Parses all common YouTube URL formats to a canonical 11-character video ID:
  - https://www.youtube.com/watch?v=VIDEO_ID
  - https://youtu.be/VIDEO_ID
  - https://www.youtube.com/shorts/VIDEO_ID
  - URLs with additional query parameters / tracking fragments

Returns None for any URL that is not a recognisable YouTube video link so the
caller can decide how to handle non-YouTube sources without raising exceptions.
"""

import re
from urllib.parse import parse_qs, urlparse

# YouTube video IDs are exactly 11 characters of [A-Za-z0-9_-].
_VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")

# Hosts that carry watch URLs  (www.youtube.com, youtube.com, m.youtube.com)
_WATCH_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com"}

# Short-link host
_SHORT_HOST = "youtu.be"


def extract_video_id(url: str) -> str | None:
    """
    Return the 11-character YouTube video ID for *url*, or None when the URL
    is not a recognisable YouTube video link.

    Handles:
      - /watch?v=ID                    (standard watch page)
      - /shorts/ID                     (YouTube Shorts)
      - /embed/ID                      (embedded player)
      - /v/ID                          (legacy)
      - youtu.be/ID                    (short link)
      - Any of the above with extra query params, anchors, or utm_* tracking.
    """
    url = url.strip()
    if not url:
        return None

    try:
        parsed = urlparse(url)
    except Exception:
        return None

    host = parsed.netloc.lower()
    # Strip port if present (e.g. localhost:8080)
    if ":" in host:
        host = host.split(":")[0]

    # ── youtu.be short links ──────────────────────────────────────────────────
    if host == _SHORT_HOST:
        # Path is /VIDEO_ID (possibly with a trailing slash)
        video_id = parsed.path.lstrip("/").split("/")[0].split("?")[0]
        return video_id if _VIDEO_ID_RE.match(video_id) else None

    # ── youtube.com family ────────────────────────────────────────────────────
    if host not in _WATCH_HOSTS:
        return None

    path = parsed.path.rstrip("/")

    # /shorts/VIDEO_ID
    if path.startswith("/shorts/"):
        video_id = path[len("/shorts/"):].split("/")[0]
        return video_id if _VIDEO_ID_RE.match(video_id) else None

    # /embed/VIDEO_ID
    if path.startswith("/embed/"):
        video_id = path[len("/embed/"):].split("/")[0]
        return video_id if _VIDEO_ID_RE.match(video_id) else None

    # /v/VIDEO_ID  (legacy)
    if path.startswith("/v/"):
        video_id = path[len("/v/"):].split("/")[0]
        return video_id if _VIDEO_ID_RE.match(video_id) else None

    # /watch?v=VIDEO_ID  (most common)
    if path == "/watch" or path == "":
        params = parse_qs(parsed.query)
        ids = params.get("v", [])
        if ids:
            video_id = ids[0]
            return video_id if _VIDEO_ID_RE.match(video_id) else None

    return None
