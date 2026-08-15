from __future__ import annotations

from hashlib import sha256
import json
import re
from typing import Protocol

from app.models.schemas import CustomerRecord


class VectorStore(Protocol):
    def upsert(self, record: CustomerRecord) -> None: ...
    def delete(self, record_id: str) -> None: ...
    def records(self) -> list[CustomerRecord]: ...
    def query(self, question: str, limit: int = 8) -> list[CustomerRecord]: ...


class InMemoryVectorStore:
    """Deterministic store used in unit tests and local development."""

    def __init__(self) -> None:
        self._records: dict[str, CustomerRecord] = {}

    def upsert(self, record: CustomerRecord) -> None:
        self._records[record.id] = record

    def delete(self, record_id: str) -> None:
        self._records.pop(record_id, None)

    def records(self) -> list[CustomerRecord]:
        return list(self._records.values())

    def query(self, question: str, limit: int = 8) -> list[CustomerRecord]:
        terms = set(_terms(question))
        scored = [
            (len(terms & set(_terms(_searchable_text(record)))), record)
            for record in self._records.values()
        ]
        return [record for score, record in sorted(scored, key=lambda item: (-item[0], item[1].id)) if score > 0][:limit]

    def content_hash(self, record: CustomerRecord) -> str:
        value = json.dumps(
            {"text": record.text, "metadata": record.metadata},
            sort_keys=True,
            separators=(",", ":"),
        )
        return sha256(value.encode("utf-8")).hexdigest()


def _searchable_text(record: CustomerRecord) -> str:
    return f"{record.text} {' '.join(str(value) for value in record.metadata.values())}"


def _terms(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())
