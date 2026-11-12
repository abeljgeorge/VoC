"""LLM adapter — one entry point, three backends, uniform behaviour.

    complete(prompt, schema, route=...) -> validated `schema` instance

Routes:
  'local'       -> Ollama (per-review work: stages 2, 3-naming, 5)
  'recommender' -> Groq   (stage 6)   [cloud]
  'critic'      -> Gemini (stage 7)   [cloud]

Guarantees (from DESIGN §5):
  - Output is parsed into the given Pydantic model or the call fails (I3).
  - Validation-aware retry: on a parse/validation error we retry once with the
    error echoed back into the prompt (materially lifts valid-JSON rate on small
    models).
  - Cloud routes are redaction-gated (I4): a cloud call must be marked
    `cloud_safe=True` by the caller, which only sends redacted theme summaries.
  - Cloud failure or missing key falls back to the local model.

Only the local route is wired here; the cloud routes currently fall back to
local with a warning. They get real Groq/Gemini clients when stages 6-7 land —
the call sites won't change.
"""
from __future__ import annotations

import os
from typing import TypeVar

from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)

LOCAL_MODEL = os.environ.get("VOC_LOCAL_MODEL", "phi4-mini")

_CLOUD_ROUTES = {"recommender", "critic"}


class LLMError(RuntimeError):
    """Raised when a call cannot produce a valid `schema` instance."""


def complete(
    prompt: str,
    schema: type[T],
    *,
    route: str = "local",
    model: str | None = None,
    system: str | None = None,
    max_retries: int = 1,
    cloud_safe: bool = False,
) -> T:
    if route in _CLOUD_ROUTES:
        if not cloud_safe:
            raise LLMError(
                f"route '{route}' is a cloud route; refusing to send a payload not "
                f"marked cloud_safe (redaction gate, invariant I4)"
            )
        # TODO(stages 6-7): wire Groq (recommender) and Gemini (critic). Until
        # then, degrade to local so the pipeline still runs end-to-end.
        print(f"    [llm] cloud route '{route}' not wired yet — falling back to local")
        route = "local"

    if route != "local":
        raise LLMError(f"unknown route '{route}'")

    return _complete_local(prompt, schema, model or LOCAL_MODEL, system, max_retries)


def _complete_local(
    prompt: str, schema: type[T], model: str, system: str | None, max_retries: int
) -> T:
    try:
        import ollama
    except ImportError as exc:  # keep the message actionable
        raise LLMError(
            "ollama is not installed. `pip install ollama` and install the Ollama "
            "runtime, then `ollama pull " + model + "`."
        ) from exc

    json_schema = schema.model_json_schema()
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    last_err: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            resp = ollama.chat(
                model=model,
                messages=messages,
                format=json_schema,          # Ollama structured output
                options={"temperature": 0},  # deterministic
            )
            content = _content_of(resp)
            return schema.model_validate_json(content)
        except (ValidationError, ValueError) as exc:
            last_err = exc
            if attempt < max_retries:
                # Echo the error so the model can correct its own output.
                messages.append({"role": "assistant", "content": _content_of(resp)})
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "That did not match the required schema. Error:\n"
                            f"{exc}\nReturn corrected JSON only."
                        ),
                    }
                )
        except Exception as exc:  # network/runtime — not worth a schema retry
            raise LLMError(f"local LLM call failed: {type(exc).__name__}: {exc}") from exc

    raise LLMError(f"could not get valid {schema.__name__} after retries: {last_err}")


def _content_of(resp: object) -> str:
    """Pull message content across ollama client versions."""
    try:
        return resp.message.content  # type: ignore[attr-defined]
    except AttributeError:
        return resp["message"]["content"]  # type: ignore[index]
