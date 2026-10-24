"""Contrats de messages entre agents (module 3).

Chaque agent produit un objet validé, jamais du texte libre que le suivant devrait deviner.
Les contraintes « métier » (nombre d'éléments, bornes) sont vérifiées dans le code :
le schéma décrit la forme, le code garantit les invariants.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class Plan(BaseModel):
    subquestions: list[str] = Field(description="2 à 4 sous-questions indépendantes, chacune traitable seule")


class Finding(BaseModel):
    subquestion: str
    summary: str = Field(description="Synthèse factuelle, uniquement à partir des documents fournis")
    source_ids: list[str] = Field(description="Identifiants des documents réellement utilisés")


class Review(BaseModel):
    verdict: Literal["approve", "revise"]
    issues: list[str] = Field(description="Problèmes concrets et actionnables ; vide si approuvé")
    score: int = Field(description="Note globale de 1 à 10")


class JudgeVerdict(BaseModel):
    faithful: bool = Field(description="Chaque affirmation est-elle soutenue par une source ?")
    complete: bool = Field(description="La question est-elle entièrement traitée ?")
    rationale: str
