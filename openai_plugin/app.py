"""FastAPI shim that re-exports the MCP tools as an OpenAI plugin.

The same adapter + tool functions are imported from mcp_server so there is
zero logic duplication.
"""
from __future__ import annotations

import logging
import os
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from mcp_server.tools import search as search_tool
from mcp_server.tools import scrape as scrape_tool
from mcp_server.tools import rerank as rerank_tool
from mcp_server.tools import summarize as summarize_tool

log = logging.getLogger("research-plugin")

app = FastAPI(title="Research MCP — OpenAI plugin shim")


class ResearchBody(BaseModel):
    query: str
    sources: Optional[list[str]] = None
    max_results: int = 20
    style: str = "detailed"


class SearchBody(BaseModel):
    query: str
    sources: Optional[list[str]] = None
    max_results: int = 20


class ScrapeBody(BaseModel):
    url: str
    method: str = "firecrawl"


class RerankBody(BaseModel):
    query: str
    docs: list[str]
    model: str = "cohere"


class SummarizeBody(BaseModel):
    docs: list[str]
    query: str
    style: str = "detailed"
    model: str = "groq"


@app.get("/.well-known/openai-plugin.json")
async def manifest() -> dict:
    return {
        "schema_version": "v1",
        "name_for_model": "research",
        "name_for_human": "Multi-Source Research",
        "description_for_model": (
            "Search 9 sources (Firecrawl, GitHub trending, arXiv, X, Google, OSS Insight, "
            "dev.to, libhunt, Tavily), scrape full content, rerank with a cross-encoder, "
            "and synthesize a cited answer using a free LLM."
        ),
        "auth": {"type": "none"},
        "api": {"type": "openai", "url": os.getenv("PLUGIN_PUBLIC_URL", "https://your.host")},
        "logo_url": "https://your.host/logo.png",
        "contact_email": "kb01111@users.noreply.github.com",
        "legal_info_url": "https://github.com/KB01111/research-mcp",
    }


@app.post("/research")
async def research_endpoint(body: ResearchBody) -> dict:
    raw = await search_tool.fan_out(body.query, body.sources, body.max_results)
    full = await scrape_tool.batch(raw)
    ranked = await rerank_tool.rerank(body.query, [r.content for r in full])
    score_map = {d["index"]: d["relevance_score"] for d in ranked}
    for i, r in enumerate(full):
        r.score = score_map.get(i, 0.0)
    full.sort(key=lambda r: r.score, reverse=True)
    summary = await summarize_tool.synthesize(body.query, full, body.style)
    return {
        "summary": summary,
        "sources": [r.to_dict() for r in full],
    }


@app.post("/search")
async def search_endpoint(body: SearchBody) -> dict:
    results = await search_tool.fan_out(body.query, body.sources, body.max_results)
    return {"results": [r.to_dict() for r in results]}


@app.post("/scrape")
async def scrape_endpoint(body: ScrapeBody) -> dict:
    try:
        content = await scrape_tool.one(body.url, body.method)
    except Exception as e:
        raise HTTPException(500, str(e)) from e
    return {"url": body.url, "content": content}


@app.post("/rerank")
async def rerank_endpoint(body: RerankBody) -> dict:
    return {"results": await rerank_tool.rerank(body.query, body.docs, body.model)}


@app.post("/summarize")
async def summarize_endpoint(body: SummarizeBody) -> dict:
    return {"summary": await summarize_tool.synthesize_raw(body.query, body.docs, body.style, body.model)}


def main() -> None:
    import uvicorn

    uvicorn.run(
        "openai_plugin.app:app",
        host=os.getenv("PLUGIN_HOST", "0.0.0.0"),
        port=int(os.getenv("PLUGIN_PORT", "8000")),
        reload=bool(os.getenv("PLUGIN_RELOAD")),
    )


if __name__ == "__main__":
    main()
