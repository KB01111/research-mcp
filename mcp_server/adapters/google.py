"""Google SERP adapter — Serper.dev (2500 free) or SerpAPI (100 free) when keys are set.

Google has no free SERP API. If neither key is set, this adapter returns [].
"""
from __future__ import annotations

import logging

import httpx

from .base import SearchResult
from mcp_server.config import settings

log = logging.getLogger(__name__)


class GoogleAdapter:
    name = "google"

    def __init__(self) -> None:
        self.serper = settings.serper_api_key
        self.serpapi = settings.serpapi_api_key

    async def search(self, query: str, max_results: int = 10) -> list[SearchResult]:
        if self.serper:
            return await self._serper(query, max_results)
        if self.serpapi:
            return await self._serpapi(query, max_results)
        log.info("google adapter: no SERP key set, skipping")
        return []

    async def _serper(self, query: str, n: int) -> list[SearchResult]:
        try:
            async with httpx.AsyncClient(timeout=30) as c:
                r = await c.post(
                    "https://google.serper.dev/search",
                    json={"q": query, "num": n},
                    headers={"X-API-KEY": self.serper, "Content-Type": "application/json"},
                )
                r.raise_for_status()
                data = r.json()
        except Exception as e:
            log.warning("serper failed: %s", e)
            return []
        out: list[SearchResult] = []
        for it in data.get("organic", [])[:n]:
            out.append(
                SearchResult(
                    title=it.get("title", ""),
                    url=it.get("link", ""),
                    snippet=it.get("snippet", ""),
                    source=self.name,
                )
            )
        return out

    async def _serpapi(self, query: str, n: int) -> list[SearchResult]:
        try:
            async with httpx.AsyncClient(timeout=30) as c:
                r = await c.get(
                    "https://serpapi.com/search",
                    params={"q": query, "num": n, "api_key": self.serpapi, "engine": "google"},
                )
                r.raise_for_status()
                data = r.json()
        except Exception as e:
            log.warning("serpapi failed: %s", e)
            return []
        out: list[SearchResult] = []
        for it in data.get("organic_results", [])[:n]:
            out.append(
                SearchResult(
                    title=it.get("title", ""),
                    url=it.get("link", ""),
                    snippet=it.get("snippet", ""),
                    source=self.name,
                )
            )
        return out
