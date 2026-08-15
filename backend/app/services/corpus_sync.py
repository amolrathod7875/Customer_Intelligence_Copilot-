from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

from app.models.schemas import CustomerRecord, SyncSummary
from app.services.customer_parser import parse_customer_directory
from app.services.vector_store import InMemoryVectorStore, VectorStore


class HashingStore(VectorStore, Protocol):
    def content_hash(self, record: CustomerRecord) -> str: ...


class CorpusSync:
    def __init__(self, store: HashingStore | None = None) -> None:
        self._store = store or InMemoryVectorStore()

    def sync(self, corpus_dir: Path) -> SyncSummary:
        current = {record.id: record for record in parse_customer_directory(corpus_dir)}
        existing = {record.id: record for record in self._store.records()}
        created = updated = unchanged = 0

        for record_id, record in current.items():
            old = existing.get(record_id)
            if old is None:
                self._store.upsert(record)
                created += 1
            elif self._store.content_hash(old) != self._store.content_hash(record):
                self._store.upsert(record)
                updated += 1
            else:
                unchanged += 1

        deleted_ids = set(existing) - set(current)
        for record_id in deleted_ids:
            self._store.delete(record_id)

        return SyncSummary(
            scanned=len(current),
            created=created,
            updated=updated,
            deleted=len(deleted_ids),
            unchanged=unchanged,
            synced_at=datetime.now(timezone.utc).isoformat(),
        )
