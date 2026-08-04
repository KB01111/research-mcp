"""Centralized env-driven settings."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


def _csv(name: str, default: str) -> list[str]:
    raw = os.getenv(name, default)
    return [s.strip() for s in raw.split(",") if s.strip()]


@dataclass(frozen=True)
class Settings:
    # Scraping
    firecrawl_api_url: str = os.getenv("FIRECRAWL_API_URL", "http://localhost:3002")
    firecrawl_api_key: str = os.getenv("FIRECRAWL_API_KEY", "")
    tavily_api_key: str = os.getenv("TAVILY_API_KEY", "")
    jina_api_key: str = os.getenv("JINA_API_KEY", "")

    # LLMs
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    google_api_key: str = os.getenv("GOOGLE_API_KEY", "")
    openrouter_api_key: str = os.getenv("OPENROUTER_API_KEY", "")

    # Rerankers
    cohere_api_key: str = os.getenv("COHERE_API_KEY", "")

    # X / Google
    twitterapi_io_key: str = os.getenv("TWITTERAPI_IO_KEY", "")
    serper_api_key: str = os.getenv("SERPER_API_KEY", "")
    serpapi_api_key: str = os.getenv("SERPAPI_API_KEY", "")

    # Behavior
    default_sources: list[str] = field(
        default_factory=lambda: _csv(
            "DEFAULT_SOURCES", "firecrawl,github,arxiv,ossinsight,devto,tavily"
        )
    )
    summarizer_model: str = os.getenv("SUMMARIZER_MODEL", "groq")
    reranker_model: str = os.getenv("RERANKER_MODEL", "cohere")
    scraper_method: str = os.getenv("SCRAPER_METHOD", "firecrawl")
    max_results_per_source: int = int(os.getenv("MAX_RESULTS_PER_SOURCE", "10"))
    max_concurrent_scrapes: int = int(os.getenv("MAX_CONCURRENT_SCRAPES", "10"))


settings = Settings()
__all__ = ["settings", "Settings"]
