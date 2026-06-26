"""Shared helpers for invoking an agent with structured output and a graceful fallback.

The Portfolio Manager, Trader, and Research Manager all follow the same
canonical pattern:

1. At agent creation, wrap the LLM with ``with_structured_output(Schema)``
   so the model returns a typed Pydantic instance. If the provider does
   not support structured output (rare; mostly older Ollama models), the
   wrap is skipped and the agent uses free-text generation instead.
2. At invocation, run the structured call and render the result back to
   markdown. If the structured call itself fails for any reason
   (malformed JSON from a weak model, transient provider issue), fall
   back to a plain ``llm.invoke`` so the pipeline never blocks.

Centralising the pattern here keeps the agent factories small and ensures
all three agents log the same warnings when fallback fires.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import Any, TypeVar

from pydantic import BaseModel

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


def bind_structured(llm: Any, schema: type[T], agent_name: str) -> Any | None:
    """Return ``llm.with_structured_output(schema)`` or ``None`` if unsupported.

    Logs a warning when the binding fails so the user understands the agent
    will use free-text generation for every call instead of one-shot fallback.
    """
    try:
        return llm.with_structured_output(schema)
    except (NotImplementedError, AttributeError) as exc:
        logger.warning(
            "%s: provider does not support with_structured_output (%s); "
            "falling back to free-text generation",
            agent_name, exc,
        )
        return None


def _model_name(llm: Any) -> str:
    name = getattr(llm, "model_name", "")
    return name if isinstance(name, str) else ""


def _is_transient_llm_error(exc: Exception) -> bool:
    """True for timeouts / connection drops / provider 5xx on proxy endpoints."""
    name = type(exc).__name__
    if name in {
        "APIConnectionError",
        "APITimeoutError",
        "TimeoutError",
        "ConnectError",
        "ReadTimeout",
        "InternalServerError",
        "ServiceUnavailableError",
        "RateLimitError",
    }:
        return True
    msg = str(exc).lower()
    return any(
        token in msg
        for token in ("connection error", "timeout", "timed out", "internal server error")
    )


def _invoke_freetext_with_retry(plain_llm: Any, prompt: Any, agent_name: str) -> str:
    """Free-text fallback with short backoff for transient provider failures."""
    last_exc: Exception | None = None
    for attempt in range(2):
        try:
            response = plain_llm.invoke(prompt)
            return response.content
        except Exception as exc:
            last_exc = exc
            if attempt == 0 and _is_transient_llm_error(exc):
                logger.warning(
                    "%s: free-text fallback failed (%s); retrying once",
                    agent_name, exc,
                )
                time.sleep(5)
                continue
            raise
    if last_exc is not None:
        raise last_exc
    raise RuntimeError("free-text fallback failed without exception")


def _structured_method_order(llm: Any) -> list[str]:
    """Return structured-output methods to try, best-first for this model."""
    from tradingagents.llm_clients.capabilities import get_capabilities

    caps = get_capabilities(_model_name(llm))
    order: list[str] = []
    for method in (
        caps.preferred_structured_method,
        "json_schema",
        "json_mode",
        "function_calling",
    ):
        if method == "none" or method in order:
            continue
        if method == "json_schema" and not caps.supports_json_schema:
            continue
        if method == "json_mode" and not caps.supports_json_mode:
            continue
        order.append(method)
    return order


def _bind_structured_method(llm: Any, schema: type[T], method: str) -> Any:
    """Bind schema with provider-aware kwargs (e.g. suppress tool_choice)."""
    from tradingagents.llm_clients.capabilities import get_capabilities

    kwargs: dict[str, Any] = {}
    if method == "function_calling":
        caps = get_capabilities(_model_name(llm))
        if not caps.supports_tool_choice:
            kwargs["tool_choice"] = None
    return llm.with_structured_output(schema, method=method, **kwargs)


def _try_alternate_structured_methods(
    plain_llm: Any,
    schema: type[T],
    prompt: Any,
    agent_name: str,
    *,
    skip_methods: set[str] | None = None,
) -> T | None:
    """Try remaining structured-output methods when the default binding fails."""
    skip = skip_methods or set()
    for method in _structured_method_order(plain_llm):
        if method in skip:
            continue
        try:
            bound = _bind_structured_method(plain_llm, schema, method)
            result = bound.invoke(prompt)
            if result is not None:
                return result
        except Exception as exc:
            continue
    return None


def invoke_structured_or_freetext(
    structured_llm: Any | None,
    plain_llm: Any,
    prompt: Any,
    render: Callable[[T], str],
    agent_name: str,
    schema: type[T] | None = None,
) -> str:
    """Run the structured call and render to markdown; fall back to free-text on any failure.

    ``prompt`` is whatever the underlying LLM accepts (a string for chat
    invocations, a list of message dicts for chat models that take that
    shape). The same value is forwarded to the free-text path so the
    fallback sees the same input the structured call did.
    """
    primary_method = None
    if structured_llm is not None:
        caps_method = _structured_method_order(plain_llm)
        primary_method = caps_method[0] if caps_method else None
        try:
            result = structured_llm.invoke(prompt)
            if result is None:
                # A thinking model can answer in plain text instead of calling
                # the tool, leaving the parser with nothing to return. Treat it
                # as a structured miss and fall back, with a clear reason.
                raise ValueError("structured output returned no parsed result")
            return render(result)
        except Exception as exc:
            logger.warning(
                "%s: structured-output invocation failed (%s); %s",
                agent_name,
                exc,
                "falling back to free text"
                if _is_transient_llm_error(exc)
                else "retrying alternate methods",
            )
            if _is_transient_llm_error(exc):
                return _invoke_freetext_with_retry(plain_llm, prompt, agent_name)

    if schema is not None:
        skip = {primary_method} if primary_method else set()
        alt = _try_alternate_structured_methods(
            plain_llm, schema, prompt, agent_name, skip_methods=skip,
        )
        if alt is not None:
            return render(alt)
        logger.warning(
            "%s: all structured-output methods failed; falling back to free text",
            agent_name,
        )

    return _invoke_freetext_with_retry(plain_llm, prompt, agent_name)
