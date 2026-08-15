"""Robust structured-output helpers for LLM JSON generation."""

from __future__ import annotations

import json
from typing import Any, TypeVar

from pydantic import BaseModel

from aegisops.llm.base import ModelAdapter
from aegisops.llm.models import LLMMessage

T = TypeVar("T", bound=BaseModel)


class StructuredOutputError(RuntimeError):
    """LLM returned text that cannot be parsed into the requested schema."""


def parse_json_object(text: str) -> dict[str, Any]:
    """Extract the first JSON object from LLM text (handles code fences)."""
    if not text:
        raise StructuredOutputError("empty response")
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end <= start:
        raise StructuredOutputError(f"no JSON object found in: {text[:200]!r}")
    try:
        parsed = json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError as exc:
        raise StructuredOutputError(f"malformed JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise StructuredOutputError("top-level JSON value is not an object")
    return parsed


def json_schema_response_format(name: str, schema: dict[str, Any]) -> dict[str, Any]:
    """OpenAI-compatible response_format carrying a schema name for FakeLLM."""
    return {
        "type": "json_schema",
        "json_schema": {
            "name": name,
            "schema": schema,
            "strict": False,
        },
    }


async def generate_structured(
    adapter: ModelAdapter,
    messages: list[LLMMessage],
    *,
    schema_name: str,
    output_model: type[T],
    max_retries: int = 1,
) -> T:
    """Generate and validate a Pydantic model; retry once on malformed output."""
    response_format = json_schema_response_format(schema_name, output_model.model_json_schema())
    last_error: Exception | None = None
    for attempt in range(max_retries + 1):
        if attempt > 0:
            messages = [
                *messages,
                LLMMessage(
                    role="user",
                    content=f"Your previous output was not valid JSON ({last_error}). Return ONLY a JSON object matching the schema.",
                ),
            ]
        turn = await adapter.generate(messages, response_format=response_format)
        try:
            payload = parse_json_object(turn.content or "")
            return output_model.model_validate(payload)
        except (StructuredOutputError, ValueError) as exc:
            last_error = exc
    raise StructuredOutputError(f"structured output failed after {max_retries + 1} attempts: {last_error}")
