"""Base de connaissances de démonstration et outils de recherche.

En production, remplacez ce corpus par votre moteur de recherche, une base vectorielle
ou un serveur MCP (voir module 3). L'interface — search / read — reste la même.
"""

from __future__ import annotations

import re

CORPUS: list[dict[str, str]] = [
    {
        "id": "doc-react",
        "title": "ReAct : raisonner et agir en alternance",
        "text": "Le pattern ReAct alterne une étape de raisonnement et une action (appel d'outil). "
        "L'observation renvoyée par l'outil alimente le raisonnement suivant. Il réduit les "
        "hallucinations sur les tâches factuelles car chaque affirmation peut s'appuyer sur une observation.",
    },
    {
        "id": "doc-supervisor",
        "title": "Architecture superviseur",
        "text": "Un agent superviseur décompose la demande, délègue chaque sous-tâche à un agent "
        "spécialisé puis agrège les résultats. Il centralise le contrôle et simplifie le débogage, "
        "au prix d'un goulot d'étranglement et de coûts de coordination.",
    },
    {
        "id": "doc-handoff",
        "title": "Handoffs entre agents",
        "text": "Un handoff transfère le contrôle d'un agent à un autre avec un état partagé. "
        "Les architectures en réseau utilisent les handoffs pour éviter un coordinateur central, "
        "mais rendent la terminaison et l'observabilité plus difficiles.",
    },
    {
        "id": "doc-mcp",
        "title": "Model Context Protocol",
        "text": "MCP standardise la manière dont une application expose outils, ressources et prompts "
        "à un modèle. Un serveur MCP écrit une fois peut être consommé par n'importe quel client "
        "compatible, ce qui découple les agents de leurs intégrations.",
    },
    {
        "id": "doc-injection",
        "title": "Injection de prompt indirecte",
        "text": "Une injection indirecte cache des instructions dans un contenu lu par l'agent "
        "(page web, e-mail, document). La défense repose sur l'isolation des privilèges : les "
        "contenus non fiables ne doivent jamais pouvoir déclencher d'action sensible sans validation.",
    },
    {
        "id": "doc-eval",
        "title": "Évaluer un système agentique",
        "text": "On évalue un agent sur le résultat final mais aussi sur sa trajectoire : outils "
        "appelés, ordre des étapes, nombre d'itérations, coût. Un LLM juge doit être calibré "
        "sur des exemples annotés par des humains pour être fiable.",
    },
]


def _tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"\w+", text.lower()) if len(t) > 2}


def search(query: str, k: int = 3) -> list[dict[str, str]]:
    """Recherche lexicale simple : renvoie les k documents les plus pertinents (id, titre, extrait)."""
    q = _tokens(query)
    scored = sorted(CORPUS, key=lambda d: len(q & _tokens(d["title"] + " " + d["text"])), reverse=True)
    return [{"id": d["id"], "title": d["title"], "excerpt": d["text"][:220]} for d in scored[:k] if q & _tokens(d["title"] + " " + d["text"])]


def read(doc_id: str) -> str:
    """Texte intégral d'un document, ou un message d'erreur exploitable par l'agent."""
    for d in CORPUS:
        if d["id"] == doc_id:
            return d["text"]
    return f"Erreur : document « {doc_id} » introuvable. Utilisez un identifiant renvoyé par search."
