"""Tavily adapter — primary search + scrape fallback. 1000 calls/mo free."""
from __future__ import annotations

import logging

import httpx

from .base import SearchResult
from mcp_server.config import settings

log = logging.getLogger(__name__)

API_URL = "https://api.tavily.com/search"


class TavilyAdapter:
    name = "tavily"

    def __init__(self) -> None:
        self.key = settings.tavily_api_key

    async def search(self, query: str, max_results: int = 10) -> list[SearchResult]:
        if not self.key:
            log.info("tavily: TAVILY_API_KEY not set, skipping")
            return []
        payload = {
            "api_key": self.key,
            "query": query,
            "max_results": max_results,
            "include_raw_content": True,
        }
        try:
            async with httpx.AsyncClient(timeout=60) as c:
                r = await c.post(API_URL, json=payload)
                r.raise_for_status()
                data = r.json()
        except Exception as e:
            log.warning("tavily search failed: %s", e)
            return []

        out: list[SearchResult] = []
        for it in data.get("results", []):
            out.append(
                SearchResult(
                    title=it.get("title", ""),
                    url=it.get("url", ""),
                    snippet=it.get("content", "")[:300],
                    content=it.get("raw_content") or it.get("content", ""),
                    source=self.name,
                    metadata={"score": it.get("score")},
                )
            )
        return out
