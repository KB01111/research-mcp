"""Search fan-out + dedupe."""
from __future__ import annotations

import asyncio
import logging
from typing import Optional
from urllib.parse import urlparse, urlunparse

from mcp_server.adapters import ADAPTERS
from mcp_server.adapters.base import SearchResult
from mcp_server.config import settings

log = logging.getLogger(__name__)


def _normalize_url(u: str) -> str:
    """Strip tracking params so the same article isn't deduped as 3 results."""
    try:
        p = urlparse(u)
        return urlunparse((p.scheme, p.netloc, p.path.rstrip("/"), "", "", ""))
    except Exception:
        return u


def dedupe(results: list[SearchResult]) -> list[SearchResult]:
    seen: dict[str, SearchResult] = {}
    for r in results:
        key = _normalize_url(r.url) or r.title
        if not key:
            continue
        if key not in seen:
            seen[key] = r
        else:
            # Keep the one with the longest snippet
            if len(r.snippet) > len(seen[key].snippet):
                seen[key].snippet = r.snippet
    return list(seen.values())


async def fan_out(
    query: str,
    sources: Optional[list[str]] = None,
    max_results: Optional[int] = None,
) -> list[SearchResult]:
    srcs = sources or settings.default_sources
    n = max_results or settings.max_results_per_source

    coros = []
    for s in srcs:
        cls = ADAPTERS.get(s)
        if not cls:
            log.warning("unknown source: %s", s)
            continue
        coros.append(cls().search(query, n))

    results = await asyncio.gather(*coros, return_exceptions=True)
    flat: list[SearchResult] = []
    for r in results:
        if isinstance(r, Exception):
            log.warning("adapter raised: %s", r)
            continue
        flat.extend(r)
    return dedupe(flat)
