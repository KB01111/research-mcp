"""Smoke test: search -> scrape -> rerank -> summarize with zero network calls for arxiv fallback."""
import asyncio
import os
import sys

# Make src importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp_server.adapters.base import SearchResult
from mcp_server.tools import search as search_tool
from mcp_server.tools import scrape as scrape_tool
from mcp_server.tools import rerank as rerank_tool
from mcp_server.tools import summarize as summarize_tool


async def main() -> None:
    # 1) Search (will only succeed for sources that don't need keys, given a clean .env)
    results = await search_tool.fan_out("agent frameworks 2026", sources=["arxiv"], max_results=3)
    assert results, "expected arxiv adapter to return something"
    print(f"[search] {len(results)} results")
    for r in results[:3]:
        print(f"  - {r.source}: {r.title[:80]}")

    # 2) Scrape (skip; arxiv results already have content)
    full = await scrape_tool.batch(results)
    assert all(r.content for r in full), "expected arxiv results to have content"

    # 3) Rerank (local fallback, no key required)
    ranked = await rerank_tool.rerank("agent frameworks 2026", [r.content for r in full], model="local")
    assert ranked and len(ranked) == len(full)
    print(f"[rerank] top score = {ranked[0]['relevance_score']:.3f}")

    # 4) Summarize (no key -> fallback extractive summary)
    summary = await summarize_tool.synthesize("agent frameworks 2026", full, style="bullets")
    assert summary
    print(f"[summary] {len(summary)} chars")
    print("---")
    print(summary[:400])


if __name__ == "__main__":
    asyncio.run(main())
