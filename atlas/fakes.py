"""Réponses déterministes pour le mode hors ligne (ATLAS_FAKE_LLM=1).

Permet d'exécuter le graphe, les tests et les évaluations de trajectoire sans clé API.
Ce fichier n'est pas étudié dans le cours.
"""

from __future__ import annotations

import re

from pydantic import BaseModel

SOURCE = re.compile(r'source="(doc-[\w-]+)"')
NOTE_SOURCES = re.compile(r"\(sources : ([^)]*)\)")


def fake_object(schema: type[BaseModel], prompt: str) -> BaseModel:
    name = schema.__name__
    if name == "Plan":
        return schema(
            subquestions=[
                "Comment fonctionne une architecture superviseur ?",
                "Que sont les handoffs entre agents ?",
                "Comment se protéger de l'injection de prompt indirecte ?",
            ]
        )
    if name == "Finding":
        sub = re.search(r"Sous-question : (.*)", prompt)
        ids = SOURCE.findall(prompt)
        return schema(subquestion=sub.group(1) if sub else "?", summary="Synthèse issue des documents.", source_ids=ids[:2])
    if name == "Review":
        # Première version : demande une révision ; ensuite : approuve
        if "Révision n°0" in prompt:
            return schema(verdict="revise", issues=["Préciser les compromis de chaque architecture."], score=6)
        return schema(verdict="approve", issues=[], score=9)
    if name == "Route":
        return schema(agent="technical", reason="demande technique")
    if name == "SpecialistReply":
        # L'agent facturation transfère à la technique quand un bug est mentionné
        if "Agent : billing" in prompt and "bug" in prompt.lower():
            return schema(answer="", handoff_to="technical")
        return schema(answer="Ticket ouvert, correction sous 24 h.", handoff_to="none")
    if name == "JudgeVerdict":
        return schema(faithful=True, complete=True, rationale="Toutes les affirmations sont sourcées.")
    raise NotImplementedError(f"Pas de réponse factice pour {name}")


def fake_text(system: str, prompt: str) -> str:
    ids: list[str] = []
    for group in NOTE_SOURCES.findall(prompt):
        ids += [s.strip() for s in group.split(",") if s.strip().startswith("doc-")]
    cite = ids[0] if ids else "doc-supervisor"
    revised = "Corrections demandées" in prompt
    return (
        "## Synthèse\n\n"
        f"Un superviseur centralise la coordination des agents [{cite}].\n\n"
        + ("Il offre plus de contrôle mais crée un goulot d'étranglement.\n" if revised else "")
    )
