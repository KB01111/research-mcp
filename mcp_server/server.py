"""Multi-source research MCP server.

Tools exposed:
    research(query, sources, max_results, style)  - end-to-end
    search_all(query, sources, max_results)       - fan-out search only
    scrape_url(url, method)                       - extract content
    rerank_docs(query, docs, model)               - rerank a list of docs
    summarize_docs(docs, query, style, model)     - final synthesis
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Optional

from dotenv import load_dotenv
from fastmcp import FastMCP

from mcp_server.tools import search as search_tool
from mcp_server.tools import scrape as scrape_tool
from mcp_server.tools import rerank as rerank_tool
from mcp_server.tools import summarize as summarize_tool

load_dotenv()
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
log = logging.getLogger("research-mcp")

mcp = FastMCP("research-mcp")


@mcp.tool()
async def research(
    query: str,
    sources: Optional[list[str]] = None,
    max_results: int = 20,
    style: str = "detailed",
) -> str:
    """End-to-end: search all sources -> scrape -> rerank -> summarize.

    Args:
        query: natural language research question.
        sources: optional list of source names; defaults to env DEFAULT_SOURCES.
        max_results: max results per source.
        style: "detailed" | "bullets" | "tldr".
    """
    log.info("research start: %r", query)
    raw = await search_tool.fan_out(query, sources, max_results)
    log.info("search returned %d raw", len(raw))
    full = await scrape_tool.batch(raw)
    ranked = await rerank_tool.rerank(query, [r.content for r in full])
    # Map rerank scores back onto results
    score_map = {d["index"]: d["relevance_score"] for d in ranked}
    for i, r in enumerate(full):
        r.score = score_map.get(i, 0.0)
    full.sort(key=lambda r: r.score, reverse=True)
    return await summarize_tool.synthesize(query, full, style)


@mcp.tool()
async def search_all(
    query: str,
    sources: Optional[list[str]] = None,
    max_results: int = 20,
) -> list[dict]:
    """Fan out the query to every source and return deduped SearchResult dicts."""
    results = await search_tool.fan_out(query, sources, max_results)
    return [r.to_dict() for r in results]


@mcp.tool()
async def scrape_url(url: str, method: str = "firecrawl") -> str:
    """Scrape a single URL and return markdown content.

    method: "firecrawl" | "tavily" | "jina"
    """
    return await scrape_tool.one(url, method)


@mcp.tool()
async def rerank_docs(
    query: str,
    docs: list[str],
    model: str = "cohere",
) -> list[dict]:
    """Rerank a list of document strings by relevance to the query.

    model: "cohere" | "jina" | "local"
    Returns: [{index, relevance_score}, ...] sorted desc.
    """
    return await rerank_tool.rerank(query, docs, model)


@mcp.tool()
async def summarize_docs(
    docs: list[str],
    query: str,
    style: str = "detailed",
    model: str = "groq",
) -> str:
    """Synthesize a final answer from a list of document strings.

    style: "detailed" | "bullets" | "tldr"
    model: "groq" | "gemini" | "openrouter"
    """
    return await summarize_tool.synthesize_raw(query, docs, style, model)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
