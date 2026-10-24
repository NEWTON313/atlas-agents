"""Module 3 — Consommer le serveur MCP d'Atlas, puis le brancher sur Claude.

Exécution : python examples/03_mcp_client.py
Sans clé API, le script s'arrête après la découverte et l'appel direct des outils.
"""

import asyncio
import os
import sys

from mcp import Client, StdioServerParameters

from atlas.llm import MODEL


async def main() -> None:
    # Le serveur tourne dans un sous-processus et dialogue via stdin/stdout
    server = StdioServerParameters(command=sys.executable, args=["-m", "atlas.mcp_server"])

    async with Client(server) as mcp_client:
        listing = await mcp_client.list_tools()
        for tool in listing.tools:
            print(f"- {tool.name} : {tool.description}")

        result = await mcp_client.call_tool("search_knowledge", {"query": "handoff", "k": 2})
        print("Appel direct :", result.structured_content)

        if not os.environ.get("ANTHROPIC_API_KEY"):
            return

        # Pont MCP → outils Claude : chaque outil MCP devient un outil du Tool Runner
        from anthropic import AsyncAnthropic
        from anthropic.lib.tools.mcp import async_mcp_tool

        runner = AsyncAnthropic().beta.messages.tool_runner(
            model=MODEL,
            max_tokens=16000,
            tools=[async_mcp_tool(t, mcp_client.session) for t in listing.tools],
            messages=[{"role": "user", "content": "Explique MCP en citant tes sources."}],
        )
        async for message in runner:
            for block in message.content:
                if block.type == "text":
                    print(block.text)


asyncio.run(main())
