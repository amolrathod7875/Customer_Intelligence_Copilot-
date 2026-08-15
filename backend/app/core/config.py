import os
from dataclasses import dataclass
from os import getenv
from pathlib import Path


def _load_env_files() -> None:
    """Best-effort ``.env`` loading without requiring python-dotenv."""
    backend_dir = Path(__file__).resolve().parent.parent
    for path in (backend_dir / ".env", backend_dir.parent / ".env"):
        if not path.exists():
            continue
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key, value = key.strip(), value.strip().strip('"').strip("'")
            if key:
                os.environ.setdefault(key, value)


_load_env_files()


@dataclass(frozen=True)
class Settings:
    llm_base_url: str | None
    llm_api_key: str | None
    llm_model: str | None
    corpus_dir: Path
    chroma_dir: Path
    frontend_origin: str

    # Qdrant / hybrid search
    qdrant_url: str | None
    qdrant_api_key: str | None
    qdrant_collection: str
    qdrant_manifest_collection: str
    qdrant_dense_model: str
    qdrant_sparse_model: str
    qdrant_late_interaction_model: str
    qdrant_dim: int
    qdrant_multi_dim: int
    chunk_size: int
    chunk_overlap: int
    retrieve_limit: int

    @classmethod
    def from_environment(cls) -> "Settings":
        return cls(
            llm_base_url=getenv("LLM_BASE_URL") or None,
            llm_api_key=getenv("LLM_API_KEY") or None,
            llm_model=getenv("LLM_MODEL") or None,
            corpus_dir=Path(getenv("CORPUS_DIR", "../se-dataset")),
            chroma_dir=Path(getenv("CHROMA_DIR", ".data/chroma")),
            frontend_origin=getenv("FRONTEND_ORIGIN", "http://localhost:5173"),
            qdrant_url=getenv("QDRANT_URL") or None,
            qdrant_api_key=getenv("QDRANT_API_KEY") or None,
            qdrant_collection=getenv("QDRANT_COLLECTION", "customer_chunks"),
            qdrant_manifest_collection=getenv("QDRANT_MANIFEST_COLLECTION", "customer_manifest"),
            qdrant_dense_model=getenv("QDRANT_DENSE_MODEL", "sentence-transformers/all-MiniLM-L6-v2"),
            qdrant_sparse_model=getenv("QDRANT_SPARSE_MODEL", "Qdrant/bm25"),
            qdrant_late_interaction_model=getenv(
                "QDRANT_LATE_INTERACTION_MODEL", "answerdotai/answerai-colbert-small-v1"
            ),
            qdrant_dim=int(getenv("QDRANT_DIM", "384")),
            qdrant_multi_dim=int(getenv("QDRANT_MULTI_DIM", "96")),
            chunk_size=int(getenv("CHUNK_SIZE", "800")),
            chunk_overlap=int(getenv("CHUNK_OVERLAP", "150")),
            retrieve_limit=int(getenv("RETRIEVE_LIMIT", "30")),
        )
