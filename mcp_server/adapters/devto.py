"""dev.to adapter — public API, free, no key."""
from __future__ import annotations

import logging

import httpx

from .base import SearchResult

log = logging.getLogger(__name__)


class DevToAdapter:
    name = "devto"

    async def search(self, query: str, max_results: int = 10) -> list[SearchResult]:
        try:
            async with httpx.AsyncClient(timeout=30) as c:
                r = await c.get(
                    "https://dev.to/api/articles",
                    params={"search": query, "per_page": max_results},
                )
                r.raise_for_status()
                items = r.json()
        except Exception as e:
            log.warning("dev.to search failed: %s", e)
            return []

        out: list[SearchResult] = []
        for it in items:
            out.append(
                SearchResult(
                    title=it.get("title", ""),
                    url=it.get("url", ""),
                    snippet=(it.get("description") or "")[:300],
                    source=self.name,
                    metadata={
                        "author": it.get("user", {}).get("username"),
                        "tags": it.get("tag_list", []),
                        "reactions": it.get("public_reactions_count"),
                    },
                )
            )
        return out
