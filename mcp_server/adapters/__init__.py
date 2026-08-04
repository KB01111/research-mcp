"""Adapter registry. All adapters implement async search(query, max_results) -> list[SearchResult]."""
from __future__ import annotations

from .firecrawl import FirecrawlAdapter
from .github import GitHubTrendingAdapter
from .arxiv import ArxivAdapter
from .x_twitter import XTwitterAdapter
from .google import GoogleAdapter
from .ossinsight import OSSInsightAdapter
from .devto import DevToAdapter
from .libhunt import LibHuntAdapter
from .tavily import TavilyAdapter

ADAPTERS = {
    "firecrawl": FirecrawlAdapter,
    "github": GitHubTrendingAdapter,
    "arxiv": ArxivAdapter,
    "x": XTwitterAdapter,
    "google": GoogleAdapter,
    "ossinsight": OSSInsightAdapter,
    "devto": DevToAdapter,
    "libhunt": LibHuntAdapter,
    "tavily": TavilyAdapter,
}

__all__ = ["ADAPTERS"]
