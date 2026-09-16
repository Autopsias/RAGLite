"""Report LLM cost to the fleet Phoenix.

HAND-WRITTEN spans, not SDK auto-instrumentation. Measured 2026-09-16: every
openinference instrumentor needs a MAJOR SDK version this repo does not have --
anthropic>=1.0.0 against the pinned <1.0.0 (0.69.0), mistralai>=2.0.0 against
1.9.11, openai>=2.8.0 against 1.109.1. Worse, an instrumentor that cannot attach
does NOT raise: it logs a DependencyConflict and silently does nothing, so the
fleet dashboard would have read this repo as $0.00 while it spent money.
Upgrading those three SDKs is a breaking change and is not this module's call.

So the CLIENT is wrapped once, in shared.clients, by TracedClient below: it reads
the token counts the provider already returns. Wrapping the factory rather than
the 16 call sites is deliberate -- a 17th call site is then traced without anyone
remembering to trace it. Raw calls that hold no client use llm_span() directly.

Opt-OUT, not opt-in: tracing somebody has to remember to switch on reports
nothing. Set PHOENIX_TRACING=0 to turn it off, or PHOENIX_COLLECTOR_ENDPOINT to
send it elsewhere. Every failure here is swallowed -- reporting cost must never
break a query -- which is why setup() RETURNS whether it worked.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from raglite.shared.logging import get_logger

logger = get_logger(__name__)

DEFAULT_ENDPOINT = "http://127.0.0.1:6007"
PROJECT = "RAGLite"

_PROVIDER: Any = None


def setup() -> bool:
    """Start tracing once. -> True if spans will now be sent."""
    global _PROVIDER
    if _PROVIDER is not None:
        return True

    if os.getenv("PHOENIX_TRACING", "1") == "0":
        logger.debug("phoenix tracing disabled by PHOENIX_TRACING=0")
        return False

    base = os.getenv("PHOENIX_COLLECTOR_ENDPOINT", DEFAULT_ENDPOINT).rstrip("/")
    try:
        from phoenix.otel import register

        # set_global_tracer_provider=False: this process may already have its own
        # provider, and taking the global one is not ours to do.
        _PROVIDER = register(
            project_name=os.getenv("PHOENIX_PROJECT", PROJECT),
            endpoint=f"{base}/v1/traces",
            batch=True,
            set_global_tracer_provider=False,
        )
    except Exception as exc:  # noqa: BLE001 -- tracing never breaks the caller
        logger.warning("phoenix tracing failed to start", extra={"error": str(exc)})
        return False

    logger.info("phoenix tracing started", extra={"project": PROJECT, "endpoint": base})
    return True


@contextmanager
def llm_span(model: str, provider: str) -> Iterator[dict[str, Any]]:
    """Record one LLM call. Yields a dict: put the response's usage fields in it.

        with llm_span("gpt-5-nano", "openai") as usage:
            response = client.chat.completions.create(...)
            usage.update(response.usage.model_dump())

    Accepts the OpenAI/Mistral spelling (prompt_tokens / completion_tokens /
    total_tokens) and the Anthropic one (input_tokens / output_tokens). A call
    that raises still records the span, because a failed call can still cost.
    Phoenix prices only models it knows, so pass the provider's real model name.
    """
    if _PROVIDER is None:
        yield {}
        return

    usage: dict[str, Any] = {}
    tracer = _PROVIDER.get_tracer(__name__)
    with tracer.start_as_current_span(f"{provider}.chat") as span:
        try:
            yield usage
        finally:
            # Only the RECORDING is swallowed. An exception from the caller's own
            # code must travel on untouched -- catching it here would hide a real
            # failure behind a tracing message.
            try:
                _record(span, model, usage)
            except Exception as exc:  # noqa: BLE001 -- never break the caller
                logger.debug("phoenix span not recorded: %s", exc)


def _record(span: Any, model: str, usage: dict[str, Any]) -> None:
    """Copy token counts onto the span in the shape Phoenix reads."""
    prompt = usage.get("prompt_tokens", usage.get("input_tokens"))
    completion = usage.get("completion_tokens", usage.get("output_tokens"))
    total = usage.get("total_tokens")
    if total is None and prompt is not None and completion is not None:
        total = prompt + completion

    span.set_attribute("openinference.span.kind", "LLM")
    span.set_attribute("llm.model_name", model)
    span.set_attribute("llm.provider", "raglite")
    for key, value in (("prompt", prompt), ("completion", completion), ("total", total)):
        if isinstance(value, int):
            span.set_attribute(f"llm.token_count.{key}", value)


def absorb(usage: dict[str, Any], response: Any) -> None:
    """Copy an SDK response's usage onto a span's dict, whatever shape it has."""
    reported = getattr(response, "usage", None)
    if reported is None:
        return
    dump = getattr(reported, "model_dump", None)
    if callable(dump):
        try:
            usage.update(dump())
            return
        except Exception:  # noqa: BLE001 -- fall through to attribute reads
            pass
    for name in (
        "prompt_tokens",
        "completion_tokens",
        "total_tokens",
        "input_tokens",
        "output_tokens",
    ):
        value = getattr(reported, name, None)
        if isinstance(value, int):
            usage[name] = value


class _TracedChat:
    """The `.chat` of a wrapped client: same object, plus a span per call."""

    def __init__(self, chat: Any, provider: str) -> None:
        self._chat = chat
        self._provider = provider

    def __getattr__(self, name: str) -> Any:
        return getattr(self._chat, name)

    def complete(self, *args: Any, **kwargs: Any) -> Any:
        with llm_span(kwargs.get("model", "unknown"), self._provider) as usage:
            response = self._chat.complete(*args, **kwargs)
            absorb(usage, response)
            return response

    async def complete_async(self, *args: Any, **kwargs: Any) -> Any:
        with llm_span(kwargs.get("model", "unknown"), self._provider) as usage:
            response = await self._chat.complete_async(*args, **kwargs)
            absorb(usage, response)
            return response


class _TracedMessages:
    """The `.messages` of a wrapped Anthropic client."""

    def __init__(self, messages: Any, provider: str) -> None:
        self._messages = messages
        self._provider = provider

    def __getattr__(self, name: str) -> Any:
        return getattr(self._messages, name)

    def create(self, *args: Any, **kwargs: Any) -> Any:
        with llm_span(kwargs.get("model", "unknown"), self._provider) as usage:
            response = self._messages.create(*args, **kwargs)
            absorb(usage, response)
            return response


class TracedClient:
    """An SDK client that reports what each call cost.

    Wrapping the client in the FACTORY, rather than wrapping 16 call sites, is
    what makes this hold: a call site added next month is traced without anyone
    remembering to trace it. Everything not named here is delegated untouched, so
    the wrapped client behaves exactly like the real one.
    """

    def __init__(self, client: Any, provider: str) -> None:
        self._client = client
        self._provider = provider

    def __getattr__(self, name: str) -> Any:
        inner = getattr(self._client, name)
        if name == "chat":
            return _TracedChat(inner, self._provider)
        if name == "messages":
            return _TracedMessages(inner, self._provider)
        return inner
