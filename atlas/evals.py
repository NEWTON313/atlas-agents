"""Évaluation (module 5) : trajectoire + résultat."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from .llm import extract
from .schemas import JudgeVerdict

SYSTEM_JUDGE = """Tu es un évaluateur rigoureux. On te donne une question, des notes de recherche
sourcées et une note de synthèse. Vérifie que chaque affirmation de la note est soutenue
par les notes (fidélité) et que la question est entièrement traitée (complétude).
Justifie brièvement. En cas de doute, réponds false."""


@dataclass
class Trajectory:
    steps: list[str]
    interrupted: bool
    state: dict


def run_until_review(graph, question: str) -> Trajectory:
    """Exécute le graphe jusqu'à la validation humaine en enregistrant chaque étape."""
    config = {"configurable": {"thread_id": uuid.uuid4().hex}, "recursion_limit": 50}
    steps: list[str] = []
    interrupted = False
    for update in graph.stream({"question": question, "revisions": 0}, config, stream_mode="updates"):
        for node in update:
            if node == "__interrupt__":
                interrupted = True
            else:
                steps.append(node)
    return Trajectory(steps=steps, interrupted=interrupted, state=graph.get_state(config).values)


def check_trajectory(t: Trajectory, max_revisions: int = 2) -> list[str]:
    """Règles sur le chemin suivi, indépendantes du contenu produit."""
    errors: list[str] = []
    if not t.steps or t.steps[0] != "planner":
        errors.append("Le planificateur doit s'exécuter en premier.")
    if t.steps.count("researcher") != len(t.state.get("plan", [])):
        errors.append("Il doit y avoir exactement un chercheur par sous-question.")
    if t.steps.count("writer") > max_revisions + 1:
        errors.append("Trop d'itérations de rédaction : la boucle critique ne converge pas.")
    if not t.interrupted:
        errors.append("Le graphe aurait dû s'arrêter pour validation humaine.")
    return errors


def judge(question: str, findings: list[dict], draft: str) -> JudgeVerdict:
    notes = "\n".join(f"- {f['summary']} (sources : {', '.join(f['source_ids'])})" for f in findings)
    return extract(SYSTEM_JUDGE, f"Question : {question}\n\nNotes :\n{notes}\n\nNote de synthèse :\n{draft}", JudgeVerdict)
