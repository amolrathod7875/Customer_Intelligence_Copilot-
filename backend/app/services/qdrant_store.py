from __future__ import annotations

import json
import uuid
from hashlib import sha256

import requests
from qdrant_client import QdrantClient, models

from app.core.config import Settings
from app.models.schemas import CustomerRecord
from app.services.corpus_sync import HashingStore
from app.services.vector_store import VectorStore


def _chunk_point_id(record_id: str, chunk_index: int) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"chunk:{record_id}:{chunk_index}"))


def _manifest_point_id(record_id: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"manifest:{record_id}"))


class QdrantVectorStore:
    """Qdrant store with chunking, hybrid (dense+sparse) search and rerank.

    Embeddings (dense + sparse BM25) are computed server-side by Qdrant Cloud
    Inference, and reranking is done via the Jina API - so the Render backend
    only makes HTTP calls and stays lightweight.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
            cloud_inference=True,
            timeout=60,
        )
        self._ensure_collections()

    # ---- collection setup ------------------------------------------------
    def _ensure_collections(self) -> None:
        chunks = self._settings.qdrant_collection
        manifest = self._settings.qdrant_manifest_collection
        if not self._client.collection_exists(chunks):
            self._ensure_chunk_collection(chunks)
        if not self._client.collection_exists(manifest):
            self._client.create_collection(
                collection_name=manifest,
                vectors_config={
                    "ignored": models.VectorParams(size=1, distance=models.Distance.COSINE)
                },
            )

    def _ensure_chunk_collection(self, name: str) -> None:
        self._client.create_collection(
            collection_name=name,
            vectors_config={
                "dense": models.VectorParams(
                    size=self._settings.qdrant_dim,
                    distance=models.Distance.COSINE,
                )
            },
            sparse_vectors_config={
                "sparse": models.SparseVectorParams(modifier=models.Modifier.IDF)
            },
        )

    # ---- hashing (mirrors InMemoryVectorStore) ---------------------------
    def content_hash(self, record: CustomerRecord) -> str:
        value = json.dumps(
            {"text": record.text, "metadata": record.metadata},
            sort_keys=True,
            separators=(",", ":"),
        )
        return sha256(value.encode("utf-8")).hexdigest()

    # ---- writes ----------------------------------------------------------
    def upsert(self, record: CustomerRecord) -> None:
        from app.services.chunker import chunk_text

        chunks = chunk_text(
            record.text,
            chunk_size=self._settings.chunk_size,
            chunk_overlap=self._settings.chunk_overlap,
        )
        points = [
            models.PointStruct(
                id=_chunk_point_id(record.id, index),
                vector={
                    "dense": models.Document(
                        text=chunk, model=self._settings.qdrant_dense_model
                    ),
                    "sparse": models.Document(
                        text=chunk, model=self._settings.qdrant_sparse_model
                    ),
                },
                payload={
                    "record_id": record.id,
                    "record_type": record.record_type,
                    "source_file": record.source_file,
                    "chunk_index": index,
                    "text": chunk,
                    "metadata": record.metadata,
                },
            )
            for index, chunk in enumerate(chunks)
        ]
        if points:
            self._client.upsert(
                collection_name=self._settings.qdrant_collection, points=points
            )

        # manifest keeps the full record so CorpusSync can diff incrementally
        self._client.upsert(
            collection_name=self._settings.qdrant_manifest_collection,
            points=[
                models.PointStruct(
                    id=_manifest_point_id(record.id),
                    vector={"ignored": [0.0]},
                    payload={
                        "record_id": record.id,
                        "record": record.model_dump(),
                        "content_hash": self.content_hash(record),
                    },
                )
            ],
        )

    def delete(self, record_id: str) -> None:
        selector = models.Filter(
            must=[
                models.FieldCondition(
                    key="record_id", match=models.MatchValue(value=record_id)
                )
            ]
        )
        self._client.delete(
            collection_name=self._settings.qdrant_collection, points_selector=selector
        )
        self._client.delete(
            collection_name=self._settings.qdrant_manifest_collection,
            points_selector=selector,
        )

    def records(self) -> list[CustomerRecord]:
        out: list[CustomerRecord] = []
        next_offset = None
        while True:
            points, next_offset = self._client.scroll(
                collection_name=self._settings.qdrant_manifest_collection,
                with_payload=True,
                with_vectors=False,
                offset=next_offset,
                limit=256,
            )
            for point in points:
                record_data = (point.payload or {}).get("record")
                if record_data:
                    out.append(CustomerRecord(**record_data))
            if next_offset is None:
                break
        return out

    # ---- retrieval -------------------------------------------------------
    def query(self, question: str, limit: int = 8) -> list[CustomerRecord]:
        response = self._client.query_points(
            collection_name=self._settings.qdrant_collection,
            prefetch=[
                models.Prefetch(
                    query=models.Document(
                        text=question, model=self._keyword_dense_model()
                    ),
                    using="dense",
                    limit=self._settings.retrieve_limit,
                ),
                models.Prefetch(
                    query=models.Document(
                        text=question, model=self._settings.qdrant_sparse_model
                    ),
                    using="sparse",
                    limit=self._settings.retrieve_limit,
                ),
            ],
            query=models.FusionQuery(fusion=models.Fusion.RRF),
            with_payload=True,
            limit=self._settings.retrieve_limit,
        )

        payloads = [p.payload for p in response.points if p.payload]
        if self._settings.reranker == "jina" and self._settings.jina_api_key and payloads:
            payloads = self._rerank_jina(question, payloads)

        records: list[CustomerRecord] = []
        for payload in payloads[:limit]:
            records.append(
                CustomerRecord(
                    id=f"{payload['record_id']}:{payload['chunk_index']}",
                    record_type=payload["record_type"],
                    source_file=payload["source_file"],
                    text=payload["text"],
                    metadata=payload.get("metadata", {}),
                )
            )
        return records

    def _keyword_dense_model(self) -> str:
        return self._settings.qdrant_dense_model

    def _rerank_jina(self, question: str, payloads: list[dict]) -> list[dict]:
        resp = requests.post(
            "https://api.jina.ai/v1/rerank",
            headers={"Authorization": f"Bearer {self._settings.jina_api_key}"},
            json={
                "model": "jina-reranker-v2-base-multilingual",
                "query": question,
                "documents": [p["text"] for p in payloads],
                "top_n": len(payloads),
            },
            timeout=30,
        )
        resp.raise_for_status()
        ranked: list[dict] = []
        for item in resp.json().get("results", []):
            idx = item["index"]
            if 0 <= idx < len(payloads):
                ranked.append(payloads[idx])
        return ranked

