"""Service HTTP d'Atlas (module 6) : soumettre une question, suivre, valider.

Lancement :  uvicorn atlas.api:app --reload
Production :  ATLAS_DB_URI=postgresql://… (checkpointer persistant) + plusieurs workers
"""

from __future__ import annotations

import os
import uuid
from contextlib import asynccontextmanager

from fastapi import BackgroundTasks, FastAPI, HTTPException
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command
from pydantic import BaseModel, Field

from .graph import build_graph

MAX_QUESTION_CHARS = 2_000
FAILURES: dict[str, str] = {}  # en production : une table en base
graph = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global graph
    db_uri = os.environ.get("ATLAS_DB_URI")
    if db_uri:
        # pip install langgraph-checkpoint-postgres "psycopg[binary]"
        from langgraph.checkpoint.postgres import PostgresSaver

        with PostgresSaver.from_conn_string(db_uri) as checkpointer:
            checkpointer.setup()  # crée les tables au premier lancement
            graph = build_graph(checkpointer)
            yield
    else:
        graph = build_graph(InMemorySaver())  # développement uniquement : perdu au redémarrage
        yield


app = FastAPI(title="Atlas", lifespan=lifespan)


class BriefRequest(BaseModel):
    question: str = Field(min_length=3, max_length=MAX_QUESTION_CHARS)


class Decision(BaseModel):
    approved: bool
    feedback: str | None = None


def _config(brief_id: str) -> dict:
    return {"configurable": {"thread_id": brief_id}, "recursion_limit": 50}


def _execute(brief_id: str, payload) -> None:
    """Tâche de fond : exécute (ou reprend) le graphe jusqu'à la prochaine pause ou la fin."""
    try:
        graph.invoke(payload, _config(brief_id))
    except Exception as exc:  # l'échec devient un statut consultable, pas une erreur perdue
        FAILURES[brief_id] = f"{type(exc).__name__}: {exc}"


@app.post("/briefs", status_code=202)
def create_brief(request: BriefRequest, background: BackgroundTasks) -> dict:
    brief_id = uuid.uuid4().hex
    question = " ".join(request.question.split())
    background.add_task(_execute, brief_id, {"question": question, "revisions": 0})
    return {"id": brief_id, "status": "running"}


@app.get("/briefs/{brief_id}")
def get_brief(brief_id: str) -> dict:
    if brief_id in FAILURES:
        return {"id": brief_id, "status": "failed", "error": FAILURES[brief_id]}
    snapshot = graph.get_state(_config(brief_id))
    if not snapshot.values:
        raise HTTPException(404, "Note inconnue (ou pas encore démarrée).")
    values = snapshot.values
    if snapshot.interrupts:
        pending = snapshot.interrupts[0].value
        return {"id": brief_id, "status": "awaiting_review", "draft": pending["draft"], "review": pending["review"]}
    if values.get("approved"):
        return {"id": brief_id, "status": "published", "draft": values["draft"]}
    return {"id": brief_id, "status": "running", "next": list(snapshot.next)}


@app.post("/briefs/{brief_id}/decision", status_code=202)
def decide(brief_id: str, decision: Decision, background: BackgroundTasks) -> dict:
    snapshot = graph.get_state(_config(brief_id))
    if not snapshot.interrupts:
        raise HTTPException(409, "Aucune validation en attente pour cette note.")
    background.add_task(_execute, brief_id, Command(resume=decision.model_dump()))
    return {"id": brief_id, "status": "running"}
