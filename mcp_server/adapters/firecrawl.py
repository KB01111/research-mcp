"""Firecrawl adapter — calls your fork's /v1/search endpoint.

Default URL: http://localhost:3002 (set FIRECRAWL_API_URL to change).
Auth: Bearer FIRECRAWL_API_KEY (leave empty if your fork runs unauthed).
"""
from __future__ import annotations

import logging
from typing import Optional

import httpx

from .base import SearchResult
from mcp_server.config import settings

log = logging.getLogger(__name__)


class FirecrawlAdapter:
    name = "firecrawl"

    def __init__(self) -> None:
        self.url = settings.firecrawl_api_url.rstrip("/")
        self.key = settings.firecrawl_api_key

    def _headers(self) -> dict:
        h = {"Content-Type": "application/json"}
        if self.key:
            h["Authorization"] = f"Bearer {self.key}"
        return h

    async def search(self, query: str, max_results: int = 10) -> list[SearchResult]:
        """POST /v1/search — returns array of {url, title, markdown, description}."""
        payload = {
            "query": query,
            "limit": max_results,
            "scrapeOptions": {"formats": ["markdown"]},
        }
        try:
            async with httpx.AsyncClient(timeout=60) as c:
                r = await c.post(f"{self.url}/v1/search", json=payload, headers=self._headers())
                r.raise_for_status()
                data = r.json()
        except Exception as e:
            log.warning("firecrawl search failed: %s", e)
            return []

        out: list[SearchResult] = []
        # Firecrawl /v1/search returns {success, data: [...]}
        items = data.get("data") if isinstance(data, dict) else data
        if not items:
            return out
        for it in items:
            out.append(
                SearchResult(
                    title=it.get("title") or it.get("metadata", {}).get("title", ""),
                    url=it.get("url", ""),
                    snippet=it.get("description") or it.get("markdown", "")[:300],
                    content=it.get("markdown", ""),
                    source=self.name,
                    metadata=it.get("metadata", {}),
                )
            )
        return out
