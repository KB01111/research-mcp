"""Shared schema for adapter results."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str = ""
    source: str = ""
    score: float = 0.0
    content: str = ""
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = asdict(self)
        # Don't ship huge content blobs when just listing
        d.pop("content", None)
        return d
