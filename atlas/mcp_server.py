"""Serveur MCP exposant la base de connaissances d'Atlas (module 3).

Lancement en local (stdio) :      python -m atlas.mcp_server
Inspection interactive :          mcp dev atlas/mcp_server.py
"""

from __future__ import annotations

from mcp.server import MCPServer

from atlas import knowledge

mcp = MCPServer("atlas-knowledge")


@mcp.tool()
def search_knowledge(query: str, k: int = 3) -> list[dict]:
    """Recherche dans la base documentaire d'Atlas. Renvoie au plus k documents (id, titre, extrait)."""
    return knowledge.search(query, k)


@mcp.tool()
def read_document(doc_id: str) -> str:
    """Renvoie le texte intégral d'un document à partir d'un identifiant obtenu avec search_knowledge."""
    return knowledge.read(doc_id)


if __name__ == "__main__":
    mcp.run()  # transport stdio par défaut
