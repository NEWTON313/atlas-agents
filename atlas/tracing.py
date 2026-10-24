"""Traçage minimaliste : spans imbriqués, durées et consommation de tokens.

Volontairement sans dépendance pour être lisible. Le module 5 montre comment
exporter les mêmes spans vers OpenTelemetry / Langfuse.
"""

from __future__ import annotations

import contextvars
import json
import time
import uuid
from contextlib import contextmanager, nullcontext
from dataclasses import asdict, dataclass, field
from typing import Any, Iterator

# OpenTelemetry est optionnel : s'il est installé, chaque span est aussi émis au format standard
try:
    from opentelemetry import trace as _otel

    _tracer = _otel.get_tracer("atlas")
except ImportError:  # pragma: no cover
    _tracer = None

# Tarifs indicatifs en $ par million de tokens (entrée, sortie) — à tenir à jour
PRICES = {
    "claude-opus-5-5": (4.00, 20.00),
    "claude-sonnet-5-5": (2.00, 10.00),
    "claude-haiku-5-5": (0.10, 0.50),
}


@dataclass
class Span:
    name: str
    trace_id: str
    span_id: str
    parent_id: str | None
    attributes: dict[str, Any] = field(default_factory=dict)
    start: float = field(default_factory=time.perf_counter)
    duration_ms: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    error: str | None = None
    otel: Any = field(default=None, repr=False)

    def record_usage(self, model: str, usage: Any) -> None:
        self.input_tokens += getattr(usage, "input_tokens", 0) or 0
        self.output_tokens += getattr(usage, "output_tokens", 0) or 0
        price_in, price_out = PRICES.get(model, (0.0, 0.0))
        self.cost_usd = (self.input_tokens * price_in + self.output_tokens * price_out) / 1_000_000
        if self.otel is not None:  # conventions sémantiques OpenTelemetry GenAI
            self.otel.set_attribute("gen_ai.request.model", model)
            self.otel.set_attribute("gen_ai.usage.input_tokens", self.input_tokens)
            self.otel.set_attribute("gen_ai.usage.output_tokens", self.output_tokens)


SPANS: list[Span] = []
_current: contextvars.ContextVar[Span | None] = contextvars.ContextVar("current_span", default=None)


@contextmanager
def span(name: str, **attributes: Any) -> Iterator[Span]:
    parent = _current.get()
    current = Span(
        name=name,
        trace_id=parent.trace_id if parent else uuid.uuid4().hex,
        span_id=uuid.uuid4().hex[:16],
        parent_id=parent.span_id if parent else None,
        attributes=attributes,
    )
    token = _current.set(current)
    otel_cm = _tracer.start_as_current_span(name, attributes=_primitive(attributes)) if _tracer else nullcontext()
    try:
        with otel_cm as otel_span:
            current.otel = otel_span
            yield current
    except Exception as exc:
        current.error = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        current.duration_ms = (time.perf_counter() - current.start) * 1000
        current.otel = None
        _current.reset(token)
        SPANS.append(current)


def _primitive(attributes: dict[str, Any]) -> dict[str, Any]:
    return {k: v if isinstance(v, (str, bool, int, float)) else str(v) for k, v in attributes.items()}


def summary() -> dict[str, Any]:
    llm = [s for s in SPANS if s.name.startswith("llm.")]
    return {
        "llm_calls": len(llm),
        "input_tokens": sum(s.input_tokens for s in llm),
        "output_tokens": sum(s.output_tokens for s in llm),
        "cost_usd": round(sum(s.cost_usd for s in llm), 4),
        "errors": [s.error for s in SPANS if s.error],
    }


def export_json(path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump([{k: v for k, v in asdict(s).items() if k != "otel"} for s in SPANS], f, ensure_ascii=False, indent=2)


def reset() -> None:
    SPANS.clear()
