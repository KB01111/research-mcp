# research-mcp

One MCP server + OpenAI plugin that **searches 9 sources, scrapes full content, reranks, and synthesizes a cited answer** with a free LLM.

## Sources (9)

| Source | Default? | Auth | Notes |
|---|---|---|---|
| Firecrawl (your fork) | ✅ | `FIRECRAWL_API_URL` + optional `FIRECRAWL_API_KEY` | Calls `POST /v1/search` |
| GitHub Trending | ✅ | none | HTML scrape, no key |
| arXiv | ✅ | none | Official `arxiv` lib |
| Tavily | ✅ | `TAVILY_API_KEY` | Primary fallback scraper, 1k/mo free |
| OSS Insight | ✅ | none | Trending repos, free API |
| dev.to | ✅ | none | Public API |
| libhunt | ❌ opt-in | none | HTML scrape |
| X.com (Twitter) | ❌ opt-in | `TWITTERAPI_IO_KEY` | No free public X API |
| Google SERP | ❌ opt-in | `SERPER_API_KEY` or `SERPAPI_API_KEY` | No free public SERP API |

## Free LLM & reranker

- **Summarizer:** Groq (`llama-3.3-70b-versatile`, free) → Gemini 2.0 Flash → OpenRouter free → extractive fallback
- **Reranker:** Cohere `rerank-english-v3.0` (1k/mo free) → Jina `v2` → local term-overlap
- **Scraper:** Firecrawl → Tavily extract → Jina Reader (`r.jina.ai`, no key)

## Install

```bash
cd research-mcp
pip install -e .
cp .env.example .env
# fill in whichever keys you have; the rest are optional
```

## Run the MCP (stdio, for Claude Desktop / goose)

```bash
python -m mcp_server
```

Add to your Claude Desktop config:

```json
{
  "mcpServers": {
    "research": {
      "command": "python",
      "args": ["-m", "mcp_server"],
      "cwd": "C:\\Users\\kevin\\research-mcp"
    }
  }
}
```

## Run the OpenAI plugin shim (HTTPS)

```bash
python -m openai_plugin.app
# then serve over HTTPS via Caddy/Nginx and point ChatGPT at
# https://your.host/.well-known/openai-plugin.json
```

## Tools exposed

| Tool | Purpose |
|---|---|
| `research(query, sources?, max_results?, style?)` | End-to-end: search → scrape → rerank → summarize |
| `search_all(query, sources?, max_results?)` | Search only, no LLM |
| `scrape_url(url, method?)` | Single URL scrape |
| `rerank_docs(query, docs, model?)` | Rerank a list of strings |
| `summarize_docs(docs, query, style?, model?)` | Final synthesis |

## Smoke test (no keys required)

```bash
python tests/smoke.py
```

Runs arxiv → local rerank → extractive summary. Proves the pipeline is wired correctly without spending any free-tier quota.

## Docker

```bash
docker compose --profile mcp up --build       # MCP over stdio
docker compose --profile plugin up --build    # OpenAI plugin on :8000
```

## Layout

```
mcp_server/
  server.py                # fastmcp entry
  config.py                # env-driven settings
  adapters/                # one file per source, normalized SearchResult
  tools/
    search.py              # fan-out + dedupe
    scrape.py              # Firecrawl / Tavily / Jina
    rerank.py              # Cohere / Jina / local
    summarize.py           # Groq / Gemini / OpenRouter
openai_plugin/
  app.py                   # FastAPI shim re-exporting the same tools
  manifest.json
tests/smoke.py
Dockerfile, docker-compose.yml
```
