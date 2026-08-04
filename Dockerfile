FROM python:3.11-slim

WORKDIR /app

# System deps for lxml/beautifulsoup
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libxml2-dev libxslt1-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY mcp_server ./mcp_server
COPY openai_plugin ./openai_plugin

RUN pip install --no-cache-dir -e .

ENV PYTHONUNBUFFERED=1

# Default: run the MCP server over stdio
CMD ["python", "-m", "mcp_server"]
