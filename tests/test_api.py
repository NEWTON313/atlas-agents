"""Test du service HTTP en mode hors ligne : ATLAS_FAKE_LLM=1 python -m pytest tests/"""

import os
import sys

os.environ["ATLAS_FAKE_LLM"] = "1"
os.environ.pop("ATLAS_DB_URI", None)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi.testclient import TestClient  # noqa: E402

from atlas.api import app  # noqa: E402


def test_brief_lifecycle():
    with TestClient(app) as http:  # « with » déclenche le lifespan (création du graphe)
        created = http.post("/briefs", json={"question": "Comment orchestrer des agents ?"})
        assert created.status_code == 202
        brief_id = created.json()["id"]

        # TestClient exécute les tâches de fond avant de rendre la main : la note attend la validation
        state = http.get(f"/briefs/{brief_id}").json()
        assert state["status"] == "awaiting_review" and state["draft"]

        assert http.post(f"/briefs/{brief_id}/decision", json={"approved": True}).status_code == 202
        assert http.get(f"/briefs/{brief_id}").json()["status"] == "published"

        # Plus rien à valider : conflit
        assert http.post(f"/briefs/{brief_id}/decision", json={"approved": True}).status_code == 409


def test_validation_and_unknown():
    with TestClient(app) as http:
        assert http.post("/briefs", json={"question": "x"}).status_code == 422
        assert http.get("/briefs/inconnu").status_code == 404


if __name__ == "__main__":
    test_brief_lifecycle()
    test_validation_and_unknown()
    print("✓ API : tous les tests passent.")
