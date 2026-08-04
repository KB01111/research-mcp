"""libhunt adapter — scrapes libhunt.com search (no public API)."""
from __future__ import annotations

import logging
import urllib.parse

import httpx
from bs4 import BeautifulSoup

from .base import SearchResult

log = logging.getLogger(__name__)


class LibHuntAdapter:
    name = "libhunt"

    async def search(self, query: str, max_results: int = 10) -> list[SearchResult]:
        url = "https://www.libhunt.com/search?" + urllib.parse.urlencode({"q": query})
        try:
            async with httpx.AsyncClient(
                timeout=30,
                headers={"User-Agent": "research-mcp/0.1"},
                follow_redirects=True,
            ) as c:
                r = await c.get(url)
                r.raise_for_status()
                html = r.text
        except Exception as e:
            log.warning("libhunt fetch failed: %s", e)
            return []

        soup = BeautifulSoup(html, "lxml")
        out: list[SearchResult] = []
        # Be lenient: try a few selectors since libhunt markup shifts
        for sel in ("div.project-item", "article", "a.project-link"):
            for el in soup.select(sel)[: max_results * 2]:
                a = el if el.name == "a" else el.select_one("a")
                if not a:
                    continue
                href = a.get("href", "")
                if not href.startswith("/"):
                    continue
                full = "https://www.libhunt.com" + href
                title = a.get_text(strip=True) or href.strip("/")
                out.append(
                    SearchResult(
                        title=title,
                        url=full,
                        snippet="",
                        source=self.name,
                    )
                )
                if len(out) >= max_results:
                    break
            if out:
                break
        return out
