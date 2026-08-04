"""X/Twitter adapter — uses TwitterAPI.io (free tier) when TWITTERAPI_IO_KEY is set.

X.com itself has no free public API. We deliberately do not scrape x.com.
If the key isn't set, this adapter returns []. Wire TWITTERAPI_IO_KEY to enable.
"""
from __future__ import annotations

import logging

import httpx

from .base import SearchResult
from mcp_server.config import settings

log = logging.getLogger(__name__)


class XTwitterAdapter:
    name = "x"

    def __init__(self) -> None:
        self.key = settings.twitterapi_io_key

    async def search(self, query: str, max_results: int = 10) -> list[SearchResult]:
        if not self.key:
            log.info("x adapter: TWITTERAPI_IO_KEY not set, skipping")
            return []
        url = "https://api.twitterapi.io/twitter/tweet/advanced_search"
        params = {"query": query, "limit": max_results}
        headers = {"x-api-key": self.key}
        try:
            async with httpx.AsyncClient(timeout=30) as c:
                r = await c.get(url, params=params, headers=headers)
                r.raise_for_status()
                data = r.json()
        except Exception as e:
            log.warning("x search failed: %s", e)
            return []

        out: list[SearchResult] = []
        tweets = data.get("tweets") or data.get("data") or []
        for t in tweets:
            out.append(
                SearchResult(
                    title=(t.get("text", "")[:80] + "…") if t.get("text") else "Tweet",
                    url=t.get("url") or f"https://x.com/i/status/{t.get('id','')}",
                    snippet=t.get("text", "")[:300],
                    content=t.get("text", ""),
                    source=self.name,
                    metadata={"author": t.get("author", {}).get("userName"), "likes": t.get("likeCount")},
                )
            )
            if len(out) >= max_results:
                break
        return out
