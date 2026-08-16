"""
LAURA - Gemini Client

Centralized Gemini API client used by:
- validation
- correction
- follow-up Q&A
"""

from __future__ import annotations

import time
from typing import Any

from google import genai
from google.genai import types

from config.settings import settings


class GeminiClient:
    """Reusable client for Gemini API operations."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        max_retries: int = 3,
    ) -> None:

        self.api_key = (
            api_key or settings.gemini_api_key
        )

        self.model = (
            model or settings.gemini_model
        )

        self.max_retries = max_retries

        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY is not configured."
            )

        self.client = genai.Client(
            api_key=self.api_key
        )

    # =====================================================
    # TEXT GENERATION
    # =====================================================

    def generate_text(
        self,
        prompt: str,
        system_instruction: str | None = None,
    ) -> str:
        """Generate a normal text response from Gemini."""

        if not prompt.strip():
            raise ValueError(
                "Gemini prompt cannot be empty."
            )

        config_kwargs: dict[str, Any] = {}

        if system_instruction:
            config_kwargs["system_instruction"] = (
                system_instruction
            )

        config = types.GenerateContentConfig(
            **config_kwargs
        )

        return self._generate(
            prompt=prompt,
            config=config,
        )

    # =====================================================
    # JSON GENERATION
    # =====================================================

    def generate_json(
        self,
        prompt: str,
        response_schema: dict[str, Any],
        system_instruction: str | None = None,
    ) -> str:
        """
        Generate a JSON response constrained by a schema.
        """

        if not prompt.strip():
            raise ValueError(
                "Gemini prompt cannot be empty."
            )

        config_kwargs: dict[str, Any] = {
            "response_mime_type": "application/json",
            "response_schema": response_schema,
        }

        if system_instruction:
            config_kwargs["system_instruction"] = (
                system_instruction
            )

        config = types.GenerateContentConfig(
            **config_kwargs
        )

        return self._generate(
            prompt=prompt,
            config=config,
        )

    # =====================================================
    # INTERNAL GENERATION
    # =====================================================

    def _generate(
        self,
        prompt: str,
        config: types.GenerateContentConfig,
    ) -> str:
        """
        Generate content with intelligent retry handling.

        429 quota errors are NOT retried unnecessarily.
        The original Gemini error is preserved so the
        API can report a meaningful message.
        """

        last_error: Exception | None = None

        for attempt in range(
            1,
            self.max_retries + 1,
        ):

            try:

                response = (
                    self.client.models.generate_content(
                        model=self.model,
                        contents=prompt,
                        config=config,
                    )
                )

                text = response.text

                if not text:
                    raise RuntimeError(
                        "Gemini returned an empty response."
                    )

                return text.strip()

            except Exception as exc:

                last_error = exc

                error_text = str(exc)

                # -------------------------------------------------
                # Gemini quota / rate-limit error
                # -------------------------------------------------

                if (
                    "429" in error_text
                    or "RESOURCE_EXHAUSTED"
                    in error_text
                    or "quota" in error_text.lower()
                    or "rate limit"
                    in error_text.lower()
                ):

                    raise RuntimeError(
                        "Gemini API quota/rate limit "
                        "exceeded. "
                        f"Model: {self.model}. "
                        "Please wait for the quota to reset "
                        "or use a Gemini API project with "
                        "available quota. "
                        f"Original error: {error_text}"
                    ) from exc

                # -------------------------------------------------
                # Model not found / unavailable
                # -------------------------------------------------

                if (
                    "404" in error_text
                    or "NOT_FOUND" in error_text
                ):

                    raise RuntimeError(
                        "Gemini model is unavailable: "
                        f"{self.model}. "
                        "Please update GEMINI_MODEL "
                        "in your configuration. "
                        f"Original error: {error_text}"
                    ) from exc

                # -------------------------------------------------
                # Other errors
                # -------------------------------------------------

                if attempt == self.max_retries:
                    break

                # Exponential backoff:
                #
                # attempt 1 -> 1 second
                # attempt 2 -> 2 seconds
                #
                time.sleep(
                    2 ** (attempt - 1)
                )

        raise RuntimeError(
            "Gemini request failed after "
            f"{self.max_retries} attempts. "
            f"Last error: {last_error}"
        ) from last_error