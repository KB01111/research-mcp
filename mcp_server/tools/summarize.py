"""Summarization tool. Free LLM backends: Groq, Gemini, OpenRouter."""
from __future__ import annotations

import logging
from typing import Optional

from mcp_server.adapters.base import SearchResult
from mcp_server.config import settings

log = logging.getLogger(__name__)


def _format_results(results: list[SearchResult], max_chars_per_doc: int = 2500) -> str:
    blocks: list[str] = []
    total = 0
    for i, r in enumerate(results, 1):
        chunk = r.content or r.snippet
        if not chunk:
            continue
        chunk = chunk[:max_chars_per_doc]
        block = f"[{i}] {r.title}\nSource: {r.source} | {r.url}\n{chunk}\n"
        blocks.append(block)
        total += len(block)
        if total > 50_000:  # hard cap to keep prompts sane
            blocks.append("\n[...truncated for length...]")
            break
    return "\n---\n".join(blocks)


_SYSTEM = (
    "You are a research synthesis assistant. You will be given numbered source documents "
    "from multiple origins (web search, arXiv, dev blogs, package registries, etc.). "
    "Produce a faithful synthesis that:\n"
    "  1. Directly answers the user's query.\n"
    "  2. Cites sources inline as [n] matching the document numbers.\n"
    "  3. Flags conflicting claims.\n"
    "  4. Does not fabricate facts not present in the sources."
)


def _style_instruction(style: str) -> str:
    return {
        "tldr": "Write a 3-5 sentence TL;DR.",
        "bullets": "Write a bulleted list of the 7-12 most important findings.",
        "detailed": "Write a detailed synthesis with section headers.",
    }.get(style, "Write a detailed synthesis.")


async def synthesize(query: str, results: list[SearchResult], style: str = "detailed") -> str:
    if not results:
        return f"No sources returned results for: {query}"
    docs = _format_results(results)
    return await _call_llm(query, docs, style)


async def synthesize_raw(query: str, docs: list[str], style: str, model: Optional[str] = None) -> str:
    """For when caller has plain strings, not SearchResult objects."""
    if not docs:
        return f"No documents to summarize for: {query}"
    blocks = "\n---\n".join(d[:2500] for d in docs)
    return await _call_llm(query, blocks, style, model)


async def _call_llm(query: str, docs: str, style: str, model: Optional[str] = None) -> str:
    m = (model or settings.summarizer_model).lower()
    user = f"Query: {query}\n\nStyle: {_style_instruction(style)}\n\nSources:\n{docs}"
    if m == "groq":
        return await _groq(_SYSTEM, user)
    if m == "gemini":
        return await _gemini(_SYSTEM, user)
    if m == "openrouter":
        return await _openrouter(_SYSTEM, user)
    raise ValueError(f"unknown summarizer model: {m}")


# -------- LLM backends --------

async def _groq(system: str, user: str) -> str:
    if not settings.groq_api_key:
        return _fallback_summary(user, "groq key missing")
    from groq import Groq

    c = Groq(api_key=settings.groq_api_key)
    resp = c.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=0.2,
        max_tokens=2000,
    )
    return resp.choices[0].message.content or ""


async def _gemini(system: str, user: str) -> str:
    if not settings.google_api_key:
        return _fallback_summary(user, "gemini key missing")
    import google.generativeai as genai

    genai.configure(api_key=settings.google_api_key)
    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash",
        system_instruction=system,
    )
    resp = await model.generate_content_async(user)
    return resp.text or ""


async def _openrouter(system: str, user: str) -> str:
    if not settings.openrouter_api_key:
        return _fallback_summary(user, "openrouter key missing")
    import httpx

    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type": "application/json",
    }
    body = {
        "model": "meta-llama/llama-3.3-70b-instruct:free",
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
    }
    async with httpx.AsyncClient(timeout=60) as c:
        r = await c.post("https://openrouter.ai/api/v1/chat/completions", json=body, headers=headers)
        r.raise_for_status()
        data = r.json()
    return data["choices"][0]["message"]["content"]


def _fallback_summary(user: str, reason: str) -> str:
    """No-key path: return a deterministic extractive summary so the tool still works."""
    log.warning("LLM fallback (%s); returning extractive summary", reason)
    lines = [ln.strip() for ln in user.splitlines() if ln.strip()]
    return (
        f"## Extractive summary (no LLM key configured — {reason})\n\n"
        + "\n".join(f"- {ln[:200]}" for ln in lines[:30])
    )
