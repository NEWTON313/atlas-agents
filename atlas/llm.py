"""Point d'accès unique au modèle pour tout le projet Atlas.

Centraliser les appels LLM ici permet de changer de modèle, d'ajouter du traçage,
des budgets ou des garde-fous à un seul endroit (voir modules 4 et 5 du cours).
"""

from __future__ import annotations

import os
from typing import TypeVar

import anthropic
from pydantic import BaseModel

from . import tracing

# Modèle principal (raisonnement, rédaction, critique) et modèle « ouvrier » rapide et économique
MODEL = os.environ.get("ATLAS_MODEL", "claude-opus-5-5")
WORKER_MODEL = os.environ.get("ATLAS_WORKER_MODEL", "claude-haiku-5-5")

# Mode hors ligne : réponses déterministes, sans clé API (tests, CI, démonstrations)
FAKE = os.environ.get("ATLAS_FAKE_LLM") == "1"

T = TypeVar("T", bound=BaseModel)
_client: anthropic.Anthropic | None = None


class RefusalError(RuntimeError):
    """Le modèle a décliné la requête (stop_reason == "refusal")."""


def client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()  # lit ANTHROPIC_API_KEY (ou un profil `ant auth login`)
    return _client


def _fallback_options(model: str) -> dict:
    # Repli côté serveur en cas de refus : disponible sur Opus / Sonnet / Fable, pas sur Haiku.
    if model.startswith("claude-haiku"):
        return {}
    return {"betas": ["server-side-fallback-2026-07-01"], "fallbacks": "default"}


def complete(system: str, prompt: str, *, model: str = MODEL, effort: str = "medium", max_tokens: int = 16000) -> str:
    """Appel texte simple : instructions système + une requête utilisateur → texte."""
    with tracing.span("llm.complete", model=model) as span:
        if FAKE:
            from .fakes import fake_text

            return fake_text(system, prompt)

        response = client().beta.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
            output_config={"effort": effort},
            **_fallback_options(model),
        )
        span.record_usage(model, response.usage)
        if response.stop_reason == "refusal":
            raise RefusalError(f"Requête déclinée : {response.stop_details}")
        return "".join(block.text for block in response.content if block.type == "text")


def extract(system: str, prompt: str, schema: type[T], *, model: str = MODEL, max_tokens: int = 16000) -> T:
    """Sortie structurée validée par Pydantic (contrat de message entre agents)."""
    with tracing.span("llm.extract", model=model, schema=schema.__name__) as span:
        if FAKE:
            from .fakes import fake_object

            return fake_object(schema, prompt)

        response = client().messages.parse(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
            output_format=schema,
        )
        span.record_usage(model, response.usage)
        if response.stop_reason == "refusal":
            raise RefusalError(f"Requête déclinée : {response.stop_details}")
        if response.parsed_output is None:
            raise ValueError(f"Sortie non conforme au schéma {schema.__name__}")
        return response.parsed_output
