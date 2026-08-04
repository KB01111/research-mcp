"""Scrape tool: Firecrawl (primary), Tavily extract, Jina Reader (no-key fallback)."""
from __future__ import annotations

import asyncio
import logging
from typing import Optional

import httpx

from mcp_server.adapters.base import SearchResult
from mcp_server.config import settings

log = logging.getLogger(__name__)


async def one(url: str, method: Optional[str] = None) -> str:
    m = (method or settings.scraper_method).lower()
    if m == "firecrawl":
        return await _firecrawl(url)
    if m == "tavily":
        return await _tavily(url)
    if m == "jina":
        return await _jina(url)
    raise ValueError(f"unknown scrape method: {m}")


async def batch(results: list[SearchResult], max_concurrency: Optional[int] = None) -> list[SearchResult]:
    """Scrape each result that doesn't already have content (e.g. from Firecrawl/Tavily search)."""
    sem = asyncio.Semaphore(max_concurrency or settings.max_concurrent_scrapes)

    async def _one(r: SearchResult) -> SearchResult:
        if r.content and len(r.content) > 200:
            return r  # already populated by search
        if not r.url:
            return r
        async with sem:
            try:
                r.content = await one(r.url)
            except Exception as e:
                log.warning("scrape failed for %s: %s", r.url, e)
        return r

    out = await asyncio.gather(*[_one(r) for r in results])
    return list(out)


# -------- scraper backends --------

async def _firecrawl(url: str) -> str:
    endpoint = f"{settings.firecrawl_api_url.rstrip('/')}/v1/scrape"
    headers = {"Content-Type": "application/json"}
    if settings.firecrawl_api_key:
        headers["Authorization"] = f"Bearer {settings.firecrawl_api_key}"
    payload = {"url": url, "formats": ["markdown"]}
    async with httpx.AsyncClient(timeout=90) as c:
        r = await c.post(endpoint, json=payload, headers=headers)
        r.raise_for_status()
        data = r.json()
    if isinstance(data, dict) and data.get("success") and "data" in data:
        return (data["data"].get("markdown") or "")
    return data.get("markdown", "") if isinstance(data, dict) else ""


async def _tavily(url: str) -> str:
    if not settings.tavily_api_key:
        return ""
    endpoint = "https://api.tavily.com/extract"
    payload = {"api_key": settings.tavily_api_key, "urls": [url]}
    async with httpx.AsyncClient(timeout=60) as c:
        r = await c.post(endpoint, json=payload)
        r.raise_for_status()
        data = r.json()
    results = data.get("results", [])
    if not results:
        return ""
    return results[0].get("raw_content", "") or results[0].get("content", "")


async def _jina(url: str) -> str:
    headers = {"Accept": "text/plain"}
    if settings.jina_api_key:
        headers["Authorization"] = f"Bearer {settings.jina_api_key}"
    async with httpx.AsyncClient(timeout=60) as c:
        r = await c.get(f"https://r.jina.ai/{url}", headers=headers)
        r.raise_for_status()
        return r.text
