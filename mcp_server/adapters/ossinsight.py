"""OSS Insight adapter — uses api.ossinsight.io (free, no key)."""
from __future__ import annotations

import logging

import httpx

from .base import SearchResult

log = logging.getLogger(__name__)

SEARCH_URL = "https://api.ossinsight.io/v1/trends/repos/"


class OSSInsightAdapter:
    name = "ossinsight"

    async def search(self, query: str, max_results: int = 10) -> list[SearchResult]:
        # OSS Insight doesn't have free-text search; it has trending repos.
        # We use it as a discovery feed and filter by query in the title/description.
        try:
            async with httpx.AsyncClient(timeout=30) as c:
                r = await c.get(SEARCH_URL, params={"period": "past_24_hours", "limit": 50})
                r.raise_for_status()
                data = r.json()
        except Exception as e:
            log.warning("ossinsight fetch failed: %s", e)
            return []

        rows = (data.get("data") or {}).get("rows") or []
        out: list[SearchResult] = []
        q_lower = query.lower()
        for row in rows:
            name = row.get("repo_name", "")
            desc = row.get("description", "") or ""
            if q_lower and q_lower not in (name + " " + desc).lower():
                continue
            out.append(
                SearchResult(
                    title=name,
                    url=f"https://github.com/{name}",
                    snippet=desc,
                    source=self.name,
                    metadata={"stars": row.get("stars"), "language": row.get("language")},
                )
            )
            if len(out) >= max_results:
                break
        # If query didn't match any, return top trending anyway (capped)
        if not out and not q_lower:
            for row in rows[:max_results]:
                name = row.get("repo_name", "")
                out.append(
                    SearchResult(
                        title=name,
                        url=f"https://github.com/{name}",
                        snippet=row.get("description", "") or "",
                        source=self.name,
                    )
                )
        return out
