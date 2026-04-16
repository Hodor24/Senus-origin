from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class SourceHit:
    source_name: str
    title: str
    document_id: str
    summary: str
    jurisdiction: str
    archive: str
    url: str | None = None


class SourceAdapter(Protocol):
    name: str

    def search(self, query: str) -> list[SourceHit]:
        ...

    def fetch_metadata(self, document_id: str) -> dict[str, str]:
        ...

    def fetch_document(self, document_id: str) -> bytes:
        ...

    def rate_limit_state(self) -> dict[str, str]:
        ...
