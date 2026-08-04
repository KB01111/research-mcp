"""arXiv adapter — uses the official arxiv Python library (free, no key)."""
from __future__ import annotations

import logging

import arxiv

from .base import SearchResult

log = logging.getLogger(__name__)


class ArxivAdapter:
    name = "arxiv"

    async def search(self, query: str, max_results: int = 10) -> list[SearchResult]:
        try:
            client = arxiv.Client(page_size=max_results, delay_seconds=3, num_retries=3)
            search = arxiv.Search(
                query=query,
                max_results=max_results,
                sort_by=arxiv.SortCriterion.Relevance,
            )
            results = list(client.results(search))
        except Exception as e:
            log.warning("arxiv search failed: %s", e)
            return []

        out: list[SearchResult] = []
        for r in results:
            out.append(
                SearchResult(
                    title=r.title,
                    url=r.entry_id,
                    snippet=r.summary[:300],
                    content=r.summary,
                    source=self.name,
                    metadata={
                        "authors": [a.name for a in r.authors],
                        "published": r.published.isoformat() if r.published else None,
                        "pdf_url": r.pdf_url,
                    },
                )
            )
        return out
