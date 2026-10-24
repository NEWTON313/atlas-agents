"""Module 1 — Le même agent avec le Tool Runner du SDK : la boucle est gérée pour vous.

Exécution : python examples/02_tool_runner.py (nécessite ANTHROPIC_API_KEY)
"""

import json

from anthropic import beta_tool

from atlas import knowledge
from atlas.llm import MODEL, client


@beta_tool
def search_knowledge(query: str, k: int = 3) -> str:
    """Recherche dans la base documentaire et renvoie jusqu'à k documents (id, titre, extrait).

    Args:
        query: Requête en langage naturel.
        k: Nombre maximal de documents à renvoyer.
    """
    return json.dumps(knowledge.search(query, k), ensure_ascii=False)


@beta_tool
def read_document(doc_id: str) -> str:
    """Renvoie le texte intégral d'un document.

    Args:
        doc_id: Identifiant renvoyé par search_knowledge.
    """
    return knowledge.read(doc_id)


runner = client().beta.messages.tool_runner(
    model=MODEL,
    max_tokens=16000,
    system="Tu es un assistant de recherche. Cite les identifiants des documents utilisés.",
    tools=[search_knowledge, read_document],
    messages=[{"role": "user", "content": "Comment se protéger de l'injection de prompt indirecte ?"}],
)

for message in runner:  # un message par tour ; s'arrête quand le modèle n'appelle plus d'outil
    for block in message.content:
        if block.type == "tool_use":
            print(f"→ {block.name}({block.input})")
        elif block.type == "text":
            print(block.text)
