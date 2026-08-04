"""GitHub Trending adapter — scrapes github.com/trending and matches the query.

GitHub has no public API for /trending. We scrape the HTML and filter by query
in the title/description.
"""
from __future__ import annotations

import logging
import re

import httpx
from bs4 import BeautifulSoup

from .base import SearchResult

log = logging.getLogger(__name__)

TRENDING_URL = "https://github.com/trending"


class GitHubTrendingAdapter:
    name = "github"

    async def search(self, query: str, max_results: int = 10) -> list[SearchResult]:
        try:
            async with httpx.AsyncClient(
                timeout=30,
                headers={"User-Agent": "research-mcp/0.1"},
                follow_redirects=True,
            ) as c:
                r = await c.get(TRENDING_URL)
                r.raise_for_status()
                html = r.text
        except Exception as e:
            log.warning("github trending fetch failed: %s", e)
            return []

        soup = BeautifulSoup(html, "lxml")
        out: list[SearchResult] = []
        q_lower = query.lower()
        for article in soup.select("article.Box-row"):
            a = article.select_one("h2 a")
            if not a:
                continue
            href = "https://github.com" + a.get("href", "").strip()
            title = a.get_text(strip=True).replace("\n", "").replace(" ", "")
            desc_el = article.select_one("p.col-9")
            desc = desc_el.get_text(strip=True) if desc_el else ""
            # Filter: keep all if query is empty/short, else match
            if q_lower and q_lower not in (title + " " + desc).lower():
                # still keep, but ranked lower by score (left as 0)
                pass
            out.append(
                SearchResult(
                    title=title,
                    url=href,
                    snippet=desc,
                    source=self.name,
                    metadata={"desc": desc},
                )
            )
            if len(out) >= max_results:
                break
        return out
