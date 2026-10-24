"""Module 6 — Lancer Atlas en ligne de commande, avec validation humaine.

Exécution : python examples/04_run_atlas.py "Comment orchestrer plusieurs agents ?"
Hors ligne : ATLAS_FAKE_LLM=1 python examples/04_run_atlas.py
"""

import json
import sys
import uuid

from langgraph.types import Command

from atlas import tracing
from atlas.graph import build_graph

question = sys.argv[1] if len(sys.argv) > 1 else "Comment orchestrer une équipe d'agents de manière fiable ?"
graph = build_graph()
config = {"configurable": {"thread_id": uuid.uuid4().hex}, "recursion_limit": 50}

result = graph.invoke({"question": question, "revisions": 0}, config)
while "__interrupt__" in result:
    pending = result["__interrupt__"][0].value
    print("\n" + pending["draft"])
    print(f"\nAvis du critique : {pending['review']['verdict']} ({pending['review']['score']}/10)")
    answer = input("\nPublier ? [o]ui / sinon, tapez votre retour : ").strip()
    decision = {"approved": True} if answer.lower() in {"o", "oui", "y", "yes"} else {"approved": False, "feedback": answer}
    result = graph.invoke(Command(resume=decision), config)

print("\n✓ Note publiée.")
print(json.dumps(tracing.summary(), indent=2, ensure_ascii=False))
