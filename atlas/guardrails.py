"""Garde-fous (module 4) : budgets, contenus non fiables, vérification des citations."""

from __future__ import annotations

import functools
import html
import re
from dataclasses import dataclass
from typing import Any, Callable

from . import tracing


class BudgetExceeded(RuntimeError):
    """Le système a dépassé son budget d'appels ou de coût : on s'arrête proprement."""


@dataclass
class Budget:
    max_llm_calls: int = 40
    max_cost_usd: float = 2.0

    def check(self) -> None:
        usage = tracing.summary()
        if usage["llm_calls"] >= self.max_llm_calls:
            raise BudgetExceeded(f"{usage['llm_calls']} appels LLM (limite {self.max_llm_calls})")
        if usage["cost_usd"] >= self.max_cost_usd:
            raise BudgetExceeded(f"{usage['cost_usd']} $ dépensés (limite {self.max_cost_usd} $)")


BUDGET = Budget()


def guarded(node: Callable[..., Any]) -> Callable[..., Any]:
    """Décore un nœud du graphe : vérification du budget + span de traçage nommé."""

    @functools.wraps(node)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        BUDGET.check()
        with tracing.span(f"node.{node.__name__}"):
            return node(*args, **kwargs)

    return wrapper


# --- Contenus non fiables ---------------------------------------------------------------

INJECTION_PATTERNS = [
    r"ignore (all |the )?(previous|above) instructions",
    r"ignore[sz]? (toutes )?les instructions",
    r"you are now",
    r"tu es (maintenant|désormais)",
    r"system prompt",
    r"<\s*/?\s*(system|instructions?)\s*>",
]


def looks_like_injection(text: str) -> bool:
    return any(re.search(p, text, flags=re.IGNORECASE) for p in INJECTION_PATTERNS)


def wrap_untrusted(source_id: str, text: str) -> str:
    """Encadre un contenu externe : le modèle le traite comme une donnée, pas comme une consigne."""
    flag = ' suspicious="true"' if looks_like_injection(text) else ""
    return f'<document source="{html.escape(source_id)}"{flag}>\n{html.escape(text)}\n</document>'


# --- Vérification déterministe des sorties -----------------------------------------------

CITATION = re.compile(r"\[(doc-[\w-]+)\]")


def check_citations(draft: str, allowed_ids: set[str]) -> list[str]:
    """Contrôles sans LLM : chaque citation doit exister, et le texte doit en contenir."""
    cited = set(CITATION.findall(draft))
    problems = [f"Source inconnue citée : {c}" for c in sorted(cited - allowed_ids)]
    if not cited:
        problems.append("Aucune source citée : chaque affirmation doit renvoyer à un document [doc-…].")
    return problems
