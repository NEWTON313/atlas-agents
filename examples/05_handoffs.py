"""Module 2 — Topologie en réseau : des agents qui se passent la main (handoffs).

Un agent de triage oriente la demande ; chaque spécialiste peut répondre ou
transférer à un collègue. Un compteur borne le nombre de transferts.

Exécution : python examples/05_handoffs.py "Ma facture est fausse depuis le bug d'hier"
Hors ligne : ATLAS_FAKE_LLM=1 python examples/05_handoffs.py
"""

import operator
import sys
import uuid
from typing import Annotated, Literal, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import Command
from pydantic import BaseModel

from atlas.llm import WORKER_MODEL, extract

MAX_HANDOFFS = 3


class Route(BaseModel):
    agent: Literal["billing", "technical"]
    reason: str


class SpecialistReply(BaseModel):
    answer: str
    handoff_to: Literal["billing", "technical", "none"]


class SupportState(TypedDict):
    request: str
    transcript: Annotated[list[str], operator.add]
    handoffs: int


def triage(state: SupportState) -> Command[Literal["billing", "technical"]]:
    text = state["request"].lower()
    # Règles déterministes d'abord : gratuites, instantanées, testables
    if any(w in text for w in ("facture", "remboursement", "paiement")):
        target, reason = "billing", "mot-clé de facturation"
    else:
        route = extract("Oriente la demande vers le bon service.", state["request"], Route, model=WORKER_MODEL)
        target, reason = route.agent, route.reason
    return Command(goto=target, update={"transcript": [f"triage → {target} ({reason})"]})


def make_specialist(name: str, expertise: str):
    def specialist(state: SupportState) -> Command[Literal["billing", "technical", "__end__"]]:
        reply = extract(
            f"Tu es l'agent {name} du support ({expertise}). Réponds si la demande relève de ton domaine ; "
            "sinon, transfère au collègue compétent via handoff_to.",
            f"Agent : {name}\nDemande : {state['request']}\nHistorique : {state['transcript']}",
            SpecialistReply,
            model=WORKER_MODEL,
        )
        can_transfer = reply.handoff_to not in ("none", name) and state["handoffs"] < MAX_HANDOFFS
        if can_transfer:
            return Command(
                goto=reply.handoff_to,
                update={"transcript": [f"{name} → {reply.handoff_to}"], "handoffs": state["handoffs"] + 1},
            )
        return Command(goto=END, update={"transcript": [f"{name} : {reply.answer}"]})

    specialist.__name__ = name
    return specialist


builder = StateGraph(SupportState)
builder.add_node("triage", triage)
builder.add_node("billing", make_specialist("billing", "factures, paiements, remboursements"))
builder.add_node("technical", make_specialist("technical", "bugs, accès, intégrations"))
builder.add_edge(START, "triage")
graph = builder.compile()

if __name__ == "__main__":
    request = sys.argv[1] if len(sys.argv) > 1 else "Ma facture est fausse depuis le bug d'hier"
    result = graph.invoke(
        {"request": request, "transcript": [], "handoffs": 0},
        {"configurable": {"thread_id": uuid.uuid4().hex}, "recursion_limit": 10},
    )
    print("\n".join(result["transcript"]))
