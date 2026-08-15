from __future__ import annotations

import json
import uuid
from hashlib import sha256

from qdrant_client import QdrantClient, models

from app.core.config import Settings
from app.models.schemas import CustomerRecord
from app.services.corpus_sync import HashingStore, VectorStore


def _chunk_point_id(record_id: str, chunk_index: int) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"chunk:{record_id}:{chunk_index}"))


def _manifest_point_id(record_id: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"manifest:{record_id}"))


class QdrantVectorStore:
    """Qdrant store with chunking, hybrid (dense+sparse) retrieval and
    server-side late-interaction (ColBERT) reranking.

    All embeddings (dense, sparse BM25, late-interaction multi-vector) are
    computed by Qdrant Cloud Inference, so the Render backend only issues HTTP
    calls and stays lightweight. Retrieval runs a dense+sparse prefetch and lets
    Qdrant rerank the candidates with the ColBERT multi-vector (MaxSim).
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

        # Recreate if the chunk collection is missing or predates the
        # late-interaction ("multi") vector, so a full re-ingest adds it.
        recreate = True
        if self._client.collection_exists(chunks):
            info = self._client.get_collection(chunks)
            vectors = info.config.params.vectors
            has_multi = isinstance(vectors, dict) and "multi" in vectors
            recreate = not has_multi

        if recreate:
            if self._client.collection_exists(chunks):
                self._client.delete_collection(chunks)
            if self._client.collection_exists(manifest):
                self._client.delete_collection(manifest)
            self._create_chunk_collection(chunks)
            self._create_manifest_collection(manifest)

        # Needed so CorpusSync can delete by record_id (filtered delete).
        self._ensure_record_id_index(chunks)
        self._ensure_record_id_index(manifest)

    def _ensure_record_id_index(self, name: str) -> None:
        if not self._client.collection_exists(name):
            return
        try:
            self._client.create_payload_index(
                name, "record_id", models.PayloadSchemaType.KEYWORD
            )
        except Exception:
            # Already indexed or transient; non-fatal.
            pass

    def _create_chunk_collection(self, name: str) -> None:
        self._client.create_collection(
            collection_name=name,
            vectors_config={
                "dense": models.VectorParams(
                    size=self._settings.qdrant_dim,
                    distance=models.Distance.COSINE,
                ),
                "multi": models.VectorParams(
                    size=self._settings.qdrant_multi_dim,
                    distance=models.Distance.COSINE,
                    multivector_config=models.MultiVectorConfig(
                        comparator=models.MultiVectorComparator.MAX_SIM
                    ),
                    hnsw_config=models.HnswConfigDiff(m=0),  # rerank-only: skip ANN index
                ),
            },
            sparse_vectors_config={
                "sparse": models.SparseVectorParams(modifier=models.Modifier.IDF)
            },
        )

    def _create_manifest_collection(self, name: str) -> None:
        self._client.create_collection(
            collection_name=name,
            vectors_config={
                "ignored": models.VectorParams(size=1, distance=models.Distance.COSINE)
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
                    "multi": models.Document(
                        text=chunk, model=self._settings.qdrant_late_interaction_model
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
                        text=question, model=self._settings.qdrant_dense_model
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
            query=models.Document(
                text=question, model=self._settings.qdrant_late_interaction_model
            ),
            using="multi",
            with_payload=True,
            limit=limit,
        )

        records: list[CustomerRecord] = []
        for point in response.points:
            payload = point.payload
            if not payload:
                continue
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
