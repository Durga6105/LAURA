"""
LAURA - JSON Parser

Reusable JSON parser for Gemini/LLM responses.
"""

from __future__ import annotations

import json
from typing import Any


def parse_json_response(response: str) -> Any:
    """
    Parse JSON returned by an LLM.

    Handles:
    - Normal JSON
    - Markdown ```json fences
    - Markdown ``` fences
    """

    if not response or not response.strip():
        raise ValueError("Empty JSON response.")

    cleaned = response.strip()

    # Remove Markdown code fences.
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()

        # Remove opening fence.
        if lines:
            lines = lines[1:]

        # Remove closing fence.
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        cleaned = "\n".join(lines).strip()

    try:
        return json.loads(cleaned)

    except json.JSONDecodeError as exc:
        raise ValueError(
            "LLM returned invalid JSON."
        ) from exc