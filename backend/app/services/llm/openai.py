import json
import logging

import openai
from pydantic import ValidationError

from app.schemas.recipe import RecipeSchema
from app.services.llm.base import RecipeExtractionError, RecipeExtractor

logger = logging.getLogger(__name__)

# ── System prompt ─────────────────────────────────────────────────────────────
# Instructs the model to return a single JSON object whose keys match
# RecipeSchema exactly. Every field is documented inline so the model
# has no ambiguity about types or required vs optional fields.
_SYSTEM_PROMPT = """\
You are a recipe extraction assistant. Your only job is to read a cooking video \
transcript and return a single JSON object with the recipe information.

Return ONLY a JSON object — no markdown, no code fences, no explanation.

The JSON object must have exactly these fields:

  "title"        (string, required)       : Recipe name.
  "description"  (string or null)         : One or two sentences describing the dish. \
Null if no description can be inferred.
  "ingredients"  (array, required)        : List of objects, each with:
                                              "name"     (string) ingredient name
                                              "quantity" (string) amount + unit, e.g. "2 tbsp"
  "equipment"    (array of strings, required) : Cooking tools and equipment needed.
  "steps"        (array of strings, required) : Ordered preparation steps as complete sentences.
  "calories"     (integer or null)        : Calories per serving. Null if not mentioned.
  "protein_g"    (number or null)         : Grams of protein per serving. Null if not mentioned.
  "carbs_g"      (number or null)         : Grams of carbohydrates per serving. Null if not mentioned.
  "fat_g"        (number or null)         : Grams of fat per serving. Null if not mentioned.

Rules:
- Do not invent information not present in the transcript.
- Do not add keys beyond those listed above.
- Return null for optional numeric fields if the transcript does not mention them.
- If the transcript contains no recipe at all, return {"title": "Unknown", \
"description": null, "ingredients": [], "equipment": [], "steps": [], \
"calories": null, "protein_g": null, "carbs_g": null, "fat_g": null}.
"""

_USER_PROMPT_TEMPLATE = "Extract the recipe from this transcript:\n\n{transcript}"


class OpenAIRecipeExtractor(RecipeExtractor):
    """
    Extracts a structured recipe from a transcript using the OpenAI chat completions API.

    Configuration (all via environment variables — nothing hardcoded):
      OPENAI_API_KEY      : required when LLM_PROVIDER=openai
      OPENAI_MODEL        : e.g. "gpt-4o" or "gpt-4o-mini"
      OPENAI_TIMEOUT_SECONDS : HTTP timeout in seconds (default 60)
      OPENAI_MAX_RETRIES  : number of automatic retries on transient errors (default 2)

    The constructor reads settings once at provider initialisation time (app startup).
    The openai.OpenAI client is created once and reused across all extract() calls.
    """

    def __init__(self) -> None:
        from app.core.config import get_settings

        settings = get_settings()

        api_key = settings.openai_api_key.get_secret_value()
        if not api_key:
            raise RecipeExtractionError(
                "OPENAI_API_KEY is not set. "
                "Provide it via the environment or set LLM_PROVIDER=mock."
            )

        model = settings.openai_model
        if not model:
            raise RecipeExtractionError(
                "OPENAI_MODEL is not set. "
                "Provide a model name such as 'gpt-4o' or set LLM_PROVIDER=mock."
            )

        self._model = model
        # The OpenAI client handles connection pooling internally.
        # timeout and max_retries are passed at construction so they apply to
        # every request made by this client instance.
        self._client = openai.OpenAI(
            api_key=api_key,
            timeout=float(settings.openai_timeout_seconds),
            max_retries=settings.openai_max_retries,
        )
        # Log the model name but never the key.
        logger.info("OpenAIRecipeExtractor initialised model=%s", self._model)

    def extract(self, transcript: str) -> RecipeSchema:
        """
        Call the OpenAI chat completions API and parse the response into a RecipeSchema.

        Raises RecipeExtractionError for all failure modes:
          - API authentication / authorisation errors
          - Rate limit errors
          - Network / timeout errors
          - Response that cannot be parsed as JSON
          - JSON that does not satisfy the RecipeSchema
        """
        user_message = _USER_PROMPT_TEMPLATE.format(transcript=transcript)

        try:
            response = self._client.chat.completions.create(
                model=self._model,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
            )
        except openai.AuthenticationError as exc:
            # Do not include the exception message — it may contain partial key info.
            raise RecipeExtractionError(
                "OpenAI authentication failed. Check that OPENAI_API_KEY is correct."
            ) from exc
        except openai.RateLimitError as exc:
            raise RecipeExtractionError(
                "OpenAI rate limit exceeded. The request will be retried on the next job."
            ) from exc
        except openai.APITimeoutError as exc:
            raise RecipeExtractionError(
                f"OpenAI request timed out after {self._client.timeout}s."
            ) from exc
        except openai.APIConnectionError as exc:
            raise RecipeExtractionError(
                "Could not connect to the OpenAI API. Check network connectivity."
            ) from exc
        except openai.APIError as exc:
            # Catch-all for any other openai SDK error (e.g. 500 from OpenAI).
            raise RecipeExtractionError(
                f"OpenAI API error ({type(exc).__name__}): {exc.message}"
            ) from exc

        # ── Parse response ────────────────────────────────────────────────────
        raw_content = response.choices[0].message.content or ""

        try:
            data = json.loads(raw_content)
        except json.JSONDecodeError as exc:
            logger.error(
                "OpenAI returned non-JSON response model=%s preview=%.200r",
                self._model,
                raw_content,
            )
            raise RecipeExtractionError("LLM response could not be parsed as JSON.") from exc

        # ── Validate against schema ───────────────────────────────────────────
        try:
            recipe = RecipeSchema.model_validate(data)
        except ValidationError as exc:
            logger.error(
                "OpenAI response failed schema validation model=%s errors=%s",
                self._model,
                exc.errors(),
            )
            raise RecipeExtractionError(
                f"LLM response did not match the expected recipe schema: {exc}"
            ) from exc

        logger.info(
            "recipe extracted model=%s title=%r ingredients=%d steps=%d",
            self._model,
            recipe.title,
            len(recipe.ingredients),
            len(recipe.steps),
        )
        return recipe
