"""Module 1 — Un agent minimal écrit à la main : LLM + outils + boucle de contrôle.

Exécution : python examples/01_agent_loop.py "Qu'est-ce qu'un handoff ?"
(nécessite ANTHROPIC_API_KEY)
"""

import json
import sys

from atlas import knowledge
from atlas.llm import MODEL, client

TOOLS = [
    {
        "name": "search_knowledge",
        "description": "Recherche dans la base documentaire. Renvoie jusqu'à k documents (id, titre, extrait). "
        "À utiliser avant toute affirmation factuelle.",
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}, "k": {"type": "integer"}},
            "required": ["query", "k"],
            "additionalProperties": False,
        },
    },
    {
        "name": "read_document",
        "description": "Texte intégral d'un document à partir d'un id renvoyé par search_knowledge.",
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": {"doc_id": {"type": "string"}},
            "required": ["doc_id"],
            "additionalProperties": False,
        },
    },
]


def run_tool(name: str, args: dict) -> tuple[str, bool]:
    """Exécute un outil ; renvoie (résultat, est_une_erreur). Une erreur est une information pour l'agent."""
    if name == "search_knowledge":
        return json.dumps(knowledge.search(args["query"], args["k"]), ensure_ascii=False), False
    if name == "read_document":
        text = knowledge.read(args["doc_id"])
        return text, text.startswith("Erreur")
    return f"Outil inconnu : {name}", True


def agent(question: str, max_steps: int = 8) -> str:
    messages = [{"role": "user", "content": question}]
    for _ in range(max_steps):  # borne dure : un agent ne boucle jamais indéfiniment
        response = client().messages.create(
            model=MODEL,
            max_tokens=16000,
            system="Tu es un assistant de recherche. Appuie chaque affirmation sur les documents "
            "obtenus avec tes outils et cite leurs identifiants entre crochets.",
            tools=TOOLS,
            messages=messages,
        )
        if response.stop_reason == "refusal":
            return "Requête déclinée par le modèle."
        # On ajoute la réponse COMPLÈTE (blocs de réflexion et tool_use compris) à l'historique
        messages.append({"role": "assistant", "content": response.content})

        tool_calls = [b for b in response.content if b.type == "tool_use"]
        if not tool_calls:
            return "".join(b.text for b in response.content if b.type == "text")

        results = []
        for call in tool_calls:  # tous les résultats repartent dans UN SEUL message utilisateur
            output, is_error = run_tool(call.name, call.input)
            results.append({"type": "tool_result", "tool_use_id": call.id, "content": output, "is_error": is_error})
        messages.append({"role": "user", "content": results})

    return "Arrêt : nombre maximal d'étapes atteint."


if __name__ == "__main__":
    print(agent(sys.argv[1] if len(sys.argv) > 1 else "Quels sont les compromis d'une architecture superviseur ?"))
