"""Assemblage du système Atlas en graphe LangGraph (topologie superviseur + map-reduce + boucle critique)."""

from __future__ import annotations

import operator
from typing import Annotated, TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import START, StateGraph
from langgraph.types import Send

from .agents import critic, human_review, planner, researcher, writer


class State(TypedDict, total=False):
    question: str
    plan: list[str]
    findings: Annotated[list[dict], operator.add]  # reducer : les chercheurs parallèles ajoutent, sans s'écraser
    draft: str
    review: dict | None
    revisions: int
    approved: bool


def dispatch(state: State) -> list[Send]:
    """Map : une tâche de recherche par sous-question, exécutées en parallèle."""
    return [Send("researcher", {"subquestion": q}) for q in state["plan"]]


def build_graph(checkpointer=None):
    builder = StateGraph(State)
    builder.add_node("planner", planner)
    builder.add_node("researcher", researcher)
    builder.add_node("writer", writer)
    builder.add_node("critic", critic)  # route lui-même via Command
    builder.add_node("human_review", human_review)  # route lui-même via Command

    builder.add_edge(START, "planner")
    builder.add_conditional_edges("planner", dispatch, ["researcher"])
    builder.add_edge("researcher", "writer")  # reduce : le rédacteur attend tous les chercheurs
    builder.add_edge("writer", "critic")

    # Un checkpointer est obligatoire pour interrupt() ; en production : Postgres, Redis…
    return builder.compile(checkpointer=checkpointer or InMemorySaver())
