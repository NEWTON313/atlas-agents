# Atlas — code compagnon du cours « Orchestration d'Agents IA Complexes »

> Projet compagnon du cours gratuit **Orchestration d'agents IA complexes** — https://iamaestro.academy/fr/courses/multi-agent-orchestration

Atlas est une équipe d'agents de recherche construite pas à pas pendant le cours :
un **planificateur** décompose la question, des **chercheurs** travaillent en parallèle,
un **rédacteur** produit une note sourcée, un **critique** la relit, et un **humain** valide.

```
question
   │
   ▼
planificateur ──Send×N──► chercheur │ chercheur │ chercheur   (parallèle, modèle économique)
                                     │
                                     ▼  reduce (operator.add)
                                 rédacteur ◄──── révision (≤ 2) ────┐
                                     │                              │
                                     ▼                              │
                                  critique ─────────────────────────┘
                                     │ approuvé
                                     ▼
                              validation humaine (interrupt) ──► publié
                                     │ retour
                                     └──────────► rédacteur
```

## Installation

Python 3.11 ou plus récent.

```bash
python -m venv .venv && source .venv/bin/activate   # Windows : .venv\Scripts\activate
pip install -e .
export ANTHROPIC_API_KEY=sk-ant-...                  # ou : ant auth login
```

## Lancer

```bash
python examples/01_agent_loop.py "Qu'est-ce qu'un handoff ?"   # module 1 : boucle d'agent à la main
python examples/02_tool_runner.py                              # module 1 : Tool Runner du SDK
python examples/03_mcp_client.py                               # module 3 : serveur et client MCP
python examples/04_run_atlas.py "Votre question"               # module 6 : le système complet
python examples/05_handoffs.py                                 # module 2 : handoffs entre agents
uvicorn atlas.api:app --reload                                 # module 6 : service HTTP (pip install -e ".[api]")
```

## Sans clé API

Toute la logique d'orchestration se teste hors ligne avec des réponses déterministes :

```bash
ATLAS_FAKE_LLM=1 python examples/04_run_atlas.py
ATLAS_FAKE_LLM=1 python -m pytest tests/
```

## Configuration

| Variable | Défaut | Rôle |
|---|---|---|
| `ATLAS_MODEL` | `claude-opus-5-5` | Planification, rédaction, critique |
| `ATLAS_WORKER_MODEL` | `claude-haiku-5-5` | Chercheurs (tâches bornées et répétées) |
| `ATLAS_FAKE_LLM` | — | `1` : mode hors ligne |

## Plan des fichiers

| Fichier | Module | Contenu |
|---|---|---|
| `atlas/llm.py` | 1, 4 | Accès unique au modèle, sorties structurées, repli en cas de refus |
| `atlas/knowledge.py` | 1 | Base documentaire de démonstration (search / read) |
| `atlas/schemas.py` | 3 | Contrats de messages entre agents |
| `atlas/agents.py` | 2, 4 | Les cinq agents |
| `atlas/graph.py` | 2 | Assemblage LangGraph |
| `atlas/mcp_server.py` | 3 | Serveur MCP |
| `atlas/guardrails.py` | 4 | Budgets, contenus non fiables, citations |
| `atlas/tracing.py` | 5 | Spans, tokens, coûts |
| `atlas/evals.py` | 5 | Évaluation de trajectoire et LLM juge |
| `atlas/api.py` | 6 | Service HTTP (FastAPI), checkpointer Postgres |

Versions vérifiées : `anthropic` 1.13, `langgraph` 1.2, `mcp` 2.3, `pydantic` 2.14, `fastapi` 0.143, `opentelemetry-sdk` 1.45.

## Licence

Le code est distribué sous licence MIT (voir `LICENSE`) : vous pouvez l'utiliser, le modifier et le redistribuer, y compris dans des projets professionnels. Les textes du cours restent protégés par le droit d'auteur. Les modèles téléchargés restent soumis à leurs propres licences.

Le cours complet, gratuit, en français et en anglais : https://iamaestro.academy/fr/courses/multi-agent-orchestration
