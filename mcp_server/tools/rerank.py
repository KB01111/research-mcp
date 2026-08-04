"""Rerank tool. Free backends: Cohere (1000/mo), Jina, BGE-local."""
from __future__ import annotations

import logging
from typing import Optional

from mcp_server.config import settings

log = logging.getLogger(__name__)


async def rerank(query: str, docs: list[str], model: Optional[str] = None) -> list[dict]:
    """Return [{index, relevance_score}, ...] sorted desc by relevance."""
    if not docs:
        return []
    m = (model or settings.reranker_model).lower()
    if m == "cohere":
        return await _cohere(query, docs)
    if m == "jina":
        return await _jina(query, docs)
    if m == "local":
        return _local_bm25_like(query, docs)
    raise ValueError(f"unknown rerank model: {m}")


async def _cohere(query: str, docs: list[str]) -> list[dict]:
    if not settings.cohere_api_key:
        log.warning("COHERE_API_KEY not set; falling back to local rerank")
        return _local_bm25_like(query, docs)
    import cohere

    c = cohere.Client(settings.cohere_api_key)
    try:
        resp = c.rerank(
            model="rerank-english-v3.0",  # free tier default
            query=query,
            documents=docs,
            top_n=len(docs),
        )
    except Exception as e:
        log.warning("cohere rerank failed (%s); falling back to local", e)
        return _local_bm25_like(query, docs)
    return [
        {"index": r.index, "relevance_score": float(r.relevance_score)}
        for r in resp.results
    ]


async def _jina(query: str, docs: list[str]) -> list[dict]:
    import httpx

    if not settings.jina_api_key:
        log.warning("JINA_API_KEY not set; falling back to local rerank")
        return _local_bm25_like(query, docs)
    headers = {
        "Authorization": f"Bearer {settings.jina_api_key}",
        "Content-Type": "application/json",
    }
    payload = {"model": "jina-reranker-v2-base-multilingual", "query": query, "documents": docs}
    try:
        async with httpx.AsyncClient(timeout=60) as c:
            r = await c.post("https://api.jina.ai/v1/rerank", json=payload, headers=headers)
            r.raise_for_status()
            data = r.json()
    except Exception as e:
        log.warning("jina rerank failed (%s); falling back to local", e)
        return _local_bm25_like(query, docs)
    return [
        {"index": it["index"], "relevance_score": float(it["relevance_score"])}
        for it in data.get("results", [])
    ]


def _local_bm25_like(query: str, docs: list[str]) -> list[dict]:
    """Zero-dep reranker: simple term-overlap score. Good enough as a fallback."""
    import re

    q_tokens = set(re.findall(r"\w+", query.lower()))
    if not q_tokens:
        return [{"index": i, "relevance_score": 0.0} for i in range(len(docs))]
    scored = []
    for i, d in enumerate(docs):
        d_tokens = set(re.findall(r"\w+", (d or "").lower()))
        if not d_tokens:
            scored.append({"index": i, "relevance_score": 0.0})
            continue
        overlap = len(q_tokens & d_tokens) / max(1, len(q_tokens))
        scored.append({"index": i, "relevance_score": overlap})
    scored.sort(key=lambda x: x["relevance_score"], reverse=True)
    return scored
