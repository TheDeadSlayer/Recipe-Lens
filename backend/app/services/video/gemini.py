import logging
import random
import time
from urllib.parse import urlparse

from pydantic import ValidationError

from app.schemas.recipe import RecipeSchema, RecipeVideoClassification
from app.services.llm.base import RecipeExtractionError
from app.services.video.base import VideoRecipeExtractor

logger = logging.getLogger(__name__)

# ── Classification system prompt ───────────────────────────────────────────────
# Used by classify_video().  Deliberately isolated from the extraction prompt
# so the two calls remain independent — classification must never inspect or
# depend on how complete a recipe schema would be.
_CLASSIFY_SYSTEM_PROMPT = """\
You are a video content classifier. Your only task is to decide whether the \
provided video is a food or drink recipe / preparation video.

A video IS a recipe video when it demonstrates or meaningfully explains how to \
prepare a food or drink. It may still qualify even if:
- exact ingredient quantities are not given;
- macros or nutritional values are absent;
- equipment is not explicitly named;
- there is no verbal description;
- some steps are inferred from what is visually shown;
- it is a short-form clip (e.g. a YouTube Short);
- the recipe is very simple (e.g. a two-ingredient drink).

Examples that ARE recipe videos:
- cooking tutorials and walkthroughs
- meal-prep demonstrations
- baking instructions
- drink or cocktail preparation
- short recipe demonstrations with limited narration
- videos that visually show how a dish is prepared

A video is NOT a recipe video when it does not actually show or explain \
preparation, for example:
- food reviews or taste tests
- restaurant reviews
- mukbang or eating videos
- food challenges
- grocery hauls
- cooking reaction videos
- general nutrition or diet discussion
- videos where food merely appears as a prop
- advertisements for food products without preparation instructions
- completely unrelated content

Return a JSON object with exactly two fields:
  "is_recipe" : boolean — true if the video is a recipe video, false otherwise.
  "reason"    : string  — one or two sentences explaining the decision.

Base your decision solely on the video content. \
Do not consider whether recipe details are complete or extractable.
"""

_CLASSIFY_USER_PROMPT = "Is this a recipe video?"

# ── Extraction system prompt ───────────────────────────────────────────────────
# Instructs Gemini to use both spoken audio and on-screen visuals.
# Type enforcement is handled by response_schema=RecipeSchema, not the prompt
# alone — but the prompt still describes semantics clearly so the model
# understands what each field should contain.
_SYSTEM_PROMPT = """\
You are a recipe extraction assistant. Watch the cooking video and extract the \
full recipe using both the spoken audio AND any text, ingredients, or steps \
visible on screen.

Return a JSON object with exactly these fields:

  "title"        : Recipe name (string, required).
  "description"  : One or two sentences describing the dish, or null.
  "ingredients"  : List of ingredient objects, each with:
                     "name"     (string) — ingredient name
                     "quantity" (string) — amount + unit, e.g. "2 tbsp"
  "equipment"    : List of plain strings naming the cooking tools needed, \
e.g. ["saucepan", "wooden spoon"].
  "steps"        : Ordered preparation steps as complete sentences (list of strings).
  "calories"     : Calories per serving as an integer, or null.
  "protein_g"    : Grams of protein per serving as a number, or null.
  "carbs_g"      : Grams of carbohydrates per serving as a number, or null.
  "fat_g"        : Grams of fat per serving as a number, or null.

Rules:
- equipment must be a list of plain strings, not objects.
- Do not invent information not present in the video.
- Return null for optional numeric fields if the video does not mention them.
- description, equipment, and macros may be null/empty when unavailable; do \
not reject a valid recipe on account of those optional fields being absent.
"""

_USER_PROMPT = "Extract the recipe from this video."

# MIME type for YouTube URL parts.  mimetypes.guess_type() returns None for
# YouTube URLs so we must always supply this explicitly.
_VIDEO_MIME_TYPE = "video/*"

# ── Retry configuration ────────────────────────────────────────────────────────
_MAX_ATTEMPTS = 3
_BASE_DELAY_SECONDS = 2.0  # attempt 1 → ~2s, attempt 2 → ~4s
_JITTER_SECONDS = 0.5  # uniform random added to each delay

# HTTP status codes that represent transient provider failures worth retrying.
_RETRYABLE_STATUS_CODES = {
    429,  # Too Many Requests — temporary rate limit (not exhausted quota)
    503,  # Service Unavailable
    504,  # Gateway Timeout / Deadline Exceeded
}

# google.genai status strings that map to transient failures.
_RETRYABLE_STATUSES = {
    "UNAVAILABLE",
    "DEADLINE_EXCEEDED",
    "RESOURCE_EXHAUSTED",  # covers 429 from the Gemini side
}


def _normalize_youtube_url(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.netloc.lower().removeprefix("www.")

    if host in {"youtube.com", "m.youtube.com"} and parsed.path.startswith("/shorts/"):
        parts = parsed.path.strip("/").split("/")

        if len(parts) >= 2 and parts[1]:
            video_id = parts[1]
            return f"https://www.youtube.com/watch?v={video_id}"

    return url


def _is_transient(exc: Exception) -> bool:
    """
    Return True if *exc* represents a transient provider failure that is safe
    to retry, False for permanent client errors that should never be retried.

    Transient:
      - google.genai ServerError (5xx) with status UNAVAILABLE or
        DEADLINE_EXCEEDED
      - google.genai ClientError with HTTP 429 (temporary rate limit)
      - generic network/OS errors: ConnectionError, TimeoutError, OSError

    Permanent (must NOT retry):
      - ClientError 400/401/403/404 (bad request, auth, invalid video, etc.)
      - ValidationError / RecipeExtractionError from schema parsing
      - Any other ValueError / TypeError
    """
    # Lazy import so the module can be loaded without the SDK installed.
    try:
        from google.genai.errors import APIError, ClientError, ServerError
    except ImportError:
        # SDK not installed — treat all non-network errors as permanent.
        return isinstance(exc, ConnectionError | TimeoutError | OSError)

    if isinstance(exc, ServerError):
        # 5xx — always transient
        return True

    if isinstance(exc, ClientError):
        # 429 only; all other 4xx are permanent.
        return getattr(exc, "code", 0) == 429

    if isinstance(exc, APIError):
        # Catch-all for any other SDK error; rely on status string.
        return getattr(exc, "status", "") in _RETRYABLE_STATUSES

    # Network / OS layer errors are transient.
    return isinstance(exc, ConnectionError | TimeoutError | OSError)


def _retry_after_seconds(exc: Exception) -> float | None:
    """
    Extract the Retry-After header value (in seconds) from an APIError
    response, if present.  Returns None when unavailable.
    """
    try:
        response = getattr(exc, "response", None)
        if response is None:
            return None
        headers = getattr(response, "headers", {}) or {}
        value = headers.get("retry-after") or headers.get("Retry-After")
        if value:
            return float(value)
    except Exception:
        pass
    return None


class GeminiVideoRecipeExtractor(VideoRecipeExtractor):
    """
    Extracts a structured recipe from a YouTube video URL using the Gemini API.

    The video URL is passed directly to Gemini as a multimodal input part.
    Gemini processes audio, speech, and on-screen visuals as a single unit —
    no transcript retrieval step.

    Structured output
    -----------------
    ``response_schema=RecipeSchema`` is passed to GenerateContentConfig so
    Gemini enforces the JSON schema at the API level.  When the SDK returns a
    ``response.parsed`` value that is already a RecipeSchema instance it is
    used directly.  A fallback path using ``RecipeSchema.model_validate_json``
    is used when ``response.parsed`` is unavailable.

    Retry behaviour
    ---------------
    Transient provider failures (503 UNAVAILABLE, 504 DEADLINE_EXCEEDED,
    429 temporary rate-limit, network errors) are retried up to
    ``_MAX_ATTEMPTS`` times with exponential backoff and jitter.  Permanent
    errors (auth, bad arguments, schema validation failures) are never retried.

    Configuration (all via environment variables):
      GEMINI_API_KEY          : required when LLM_PROVIDER=gemini
      GEMINI_MODEL            : e.g. "gemini-2.0-flash" (default)
      GEMINI_TIMEOUT_SECONDS  : HTTP timeout in seconds (default 300)
    """

    def __init__(self) -> None:
        from google import genai
        from google.genai import types

        from app.core.config import get_settings

        settings = get_settings()

        api_key = settings.gemini_api_key.get_secret_value()
        if not api_key:
            raise RecipeExtractionError(
                "GEMINI_API_KEY is not set. "
                "Provide it via the environment or set LLM_PROVIDER=mock."
            )

        model = settings.gemini_model
        if not model:
            raise RecipeExtractionError(
                "GEMINI_MODEL is not set. "
                "Provide a model name such as 'gemini-2.0-flash' or set LLM_PROVIDER=mock."
            )

        self._model = model
        self._timeout_ms = settings.gemini_timeout_seconds * 1000
        self._client = genai.Client(api_key=api_key)
        self._types = types

        logger.info("GeminiVideoRecipeExtractor initialised model=%s", self._model)

    # ── Public interface ───────────────────────────────────────────────────────

    def classify_video(self, url: str) -> RecipeVideoClassification:
        """
        Ask Gemini whether the video is a genuine recipe video.

        Returns a RecipeVideoClassification with is_recipe and reason fields.
        Retries on transient failures up to _MAX_ATTEMPTS times using the same
        exponential backoff logic as extract_from_url().
        Raises RecipeExtractionError on permanent failure or exhausted retries.
        """
        last_exc: Exception | None = None

        for attempt in range(1, _MAX_ATTEMPTS + 1):
            try:
                url = _normalize_youtube_url(url)
                return self._call_gemini_classify(url)

            except RecipeExtractionError:
                raise

            except Exception as exc:
                if not _is_transient(exc):
                    logger.error(
                        "Gemini classification permanent error model=%s error_type=%s",
                        self._model,
                        type(exc).__name__,
                    )
                    raise RecipeExtractionError(
                        f"Gemini classification API error ({type(exc).__name__}): {exc}"
                    ) from exc

                last_exc = exc

                if attempt == _MAX_ATTEMPTS:
                    break

                delay = self._backoff_delay(attempt, exc)
                logger.warning(
                    "Gemini classification temporarily unavailable model=%s "
                    "attempt=%d/%d retry_in=%.1fs error_type=%s status=%s",
                    self._model,
                    attempt,
                    _MAX_ATTEMPTS,
                    delay,
                    type(exc).__name__,
                    getattr(exc, "code", "n/a"),
                )
                time.sleep(delay)

        assert last_exc is not None
        logger.error(
            "Gemini classification failed after %d attempts model=%s error_type=%s",
            _MAX_ATTEMPTS,
            self._model,
            type(last_exc).__name__,
        )
        raise RecipeExtractionError(
            f"Gemini classification API error ({type(last_exc).__name__}): {last_exc}"
        ) from last_exc

    def extract_from_url(self, url: str) -> RecipeSchema:
        """
        Call the Gemini API with the YouTube URL as a video part and return a
        validated RecipeSchema.

        Retries on transient failures up to _MAX_ATTEMPTS times.
        Raises RecipeExtractionError on permanent failure or exhausted retries.
        """
        last_exc: Exception | None = None

        for attempt in range(1, _MAX_ATTEMPTS + 1):
            try:
                url = _normalize_youtube_url(url)
                return self._call_gemini(url)

            except RecipeExtractionError:
                # Schema / parse errors are permanent — never retry.
                raise

            except Exception as exc:
                if not _is_transient(exc):
                    # Permanent provider error (auth, invalid args, etc.)
                    logger.error(
                        "Gemini permanent error model=%s error_type=%s",
                        self._model,
                        type(exc).__name__,
                    )
                    raise RecipeExtractionError(
                        f"Gemini API error ({type(exc).__name__}): {exc}"
                    ) from exc

                last_exc = exc

                if attempt == _MAX_ATTEMPTS:
                    break  # exhausted — fall through to final raise

                delay = self._backoff_delay(attempt, exc)
                logger.warning(
                    "Gemini temporarily unavailable model=%s attempt=%d/%d "
                    "retry_in=%.1fs error_type=%s status=%s",
                    self._model,
                    attempt,
                    _MAX_ATTEMPTS,
                    delay,
                    type(exc).__name__,
                    getattr(exc, "code", "n/a"),
                )
                time.sleep(delay)

        # All retries exhausted.
        assert last_exc is not None
        logger.error(
            "Gemini failed after %d attempts model=%s error_type=%s",
            _MAX_ATTEMPTS,
            self._model,
            type(last_exc).__name__,
        )
        raise RecipeExtractionError(
            f"Gemini API error ({type(last_exc).__name__}): {last_exc}"
        ) from last_exc

    # ── Private helpers ────────────────────────────────────────────────────────

    def _call_gemini_classify(self, url: str) -> RecipeVideoClassification:
        """
        Make a single generate_content call for classification and return a
        RecipeVideoClassification.

        Raises:
          RecipeExtractionError  — for schema / parse failures (permanent).
          Any SDK / network exception — caller decides whether to retry.
        """
        types = self._types

        video_part = types.Part.from_uri(
            file_uri=url,
            mime_type=_VIDEO_MIME_TYPE,
        )
        text_part = types.Part.from_text(text=_CLASSIFY_USER_PROMPT)

        config = types.GenerateContentConfig(
            system_instruction=_CLASSIFY_SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=RecipeVideoClassification,
            http_options=types.HttpOptions(timeout=self._timeout_ms),
        )

        response = self._client.models.generate_content(
            model=self._model,
            contents=[types.Content(parts=[video_part, text_part], role="user")],
            config=config,
        )

        return self._parse_classification_response(response)

    def _parse_classification_response(self, response) -> RecipeVideoClassification:
        """
        Parse a GenerateContentResponse into a RecipeVideoClassification.

        Uses the same preference order as _parse_response:
          1. response.parsed when already a RecipeVideoClassification instance.
          2. response.text fallback via model_validate_json().

        Raises RecipeExtractionError (permanent) on any parse / validation failure.
        """
        parsed = getattr(response, "parsed", None)
        if isinstance(parsed, RecipeVideoClassification):
            logger.info(
                "classification result (parsed) model=%s is_recipe=%s reason=%r",
                self._model,
                parsed.is_recipe,
                parsed.reason,
            )
            return parsed

        raw_text = ""
        try:
            raw_text = response.text or ""
        except Exception:
            pass

        try:
            result = RecipeVideoClassification.model_validate_json(raw_text)
        except (ValidationError, ValueError) as exc:
            logger.error(
                "Gemini classification response failed schema validation model=%s "
                "preview=%.200r errors=%s",
                self._model,
                raw_text,
                exc,
            )
            raise RecipeExtractionError(
                f"Gemini classification response did not match the expected schema: {exc}"
            ) from exc

        logger.info(
            "classification result (text) model=%s is_recipe=%s reason=%r",
            self._model,
            result.is_recipe,
            result.reason,
        )
        return result

    def _call_gemini(self, url: str) -> RecipeSchema:
        """
        Make a single generate_content call and return a RecipeSchema.

        Raises:
          RecipeExtractionError  — for schema / parse failures (permanent).
          Any SDK / network exception — caller decides whether to retry.
        """
        types = self._types

        video_part = types.Part.from_uri(
            file_uri=url,
            mime_type=_VIDEO_MIME_TYPE,
        )
        text_part = types.Part.from_text(text=_USER_PROMPT)

        config = types.GenerateContentConfig(
            system_instruction=_SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=RecipeSchema,
            http_options=types.HttpOptions(timeout=self._timeout_ms),
        )

        # SDK exceptions propagate directly — let the retry wrapper decide.
        response = self._client.models.generate_content(
            model=self._model,
            contents=[types.Content(parts=[video_part, text_part], role="user")],
            config=config,
        )

        return self._parse_response(response)

    def _parse_response(self, response) -> RecipeSchema:
        """
        Parse a GenerateContentResponse into a RecipeSchema.

        Preference order:
          1. response.parsed — already a RecipeSchema when response_schema is
             a Pydantic model; no further validation needed.
          2. response.text — fallback: validate via model_validate_json().

        Raises RecipeExtractionError (permanent) on any parse / validation
        failure.
        """
        # ── Fast path: structured output already parsed by the SDK ─────────────
        parsed = getattr(response, "parsed", None)
        if isinstance(parsed, RecipeSchema):
            logger.info(
                "recipe extracted (parsed) model=%s title=%r ingredients=%d steps=%d",
                self._model,
                parsed.title,
                len(parsed.ingredients),
                len(parsed.steps),
            )
            return parsed

        # ── Fallback: parse from raw text ──────────────────────────────────────
        raw_text = ""
        try:
            raw_text = response.text or ""
        except Exception:
            # .text raises when the response is blocked or empty.
            pass

        try:
            recipe = RecipeSchema.model_validate_json(raw_text)
        except (ValidationError, ValueError) as exc:
            logger.error(
                "Gemini response failed schema validation model=%s preview=%.200r errors=%s",
                self._model,
                raw_text,
                exc,
            )
            raise RecipeExtractionError(
                f"Gemini response did not match the expected recipe schema: {exc}"
            ) from exc

        logger.info(
            "recipe extracted (text) model=%s title=%r ingredients=%d steps=%d",
            self._model,
            recipe.title,
            len(recipe.ingredients),
            len(recipe.steps),
        )
        return recipe

    @staticmethod
    def _backoff_delay(attempt: int, exc: Exception) -> float:
        """
        Return the number of seconds to wait before the next attempt.

        Uses exponential backoff (base * 2^(attempt-1)) plus uniform jitter.
        Respects a Retry-After header from the server when present.
        """
        retry_after = _retry_after_seconds(exc)
        if retry_after is not None:
            return retry_after + random.uniform(0, _JITTER_SECONDS)

        backoff = _BASE_DELAY_SECONDS * (2 ** (attempt - 1))
        return backoff + random.uniform(0, _JITTER_SECONDS)
