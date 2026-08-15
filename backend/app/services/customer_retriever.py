from app.models.schemas import CustomerRecord
from app.services.vector_store import VectorStore


class CustomerRetriever:
    def __init__(self, store: VectorStore) -> None:
        self._store = store

    def search(self, question: str, limit: int = 8) -> list[CustomerRecord]:
        return self._store.query(question, limit=limit)
