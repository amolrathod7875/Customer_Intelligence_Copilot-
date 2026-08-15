from pathlib import Path

from fastapi.testclient import TestClient

from app.api.routes import Container
from app.core.config import Settings
from app.main import create_app
from app.models.schemas import Citation, CustomerRecord, SourceType
from app.services.answer_service import AnswerService
from app.services.corpus_sync import CorpusSync
from app.services.customer_parser import parse_customer_directory
from app.services.customer_retriever import CustomerRetriever
from app.services.flytbase_web import FlytBaseWebRetriever
from app.services.vector_store import InMemoryVectorStore


class _FakeLlm:
    def generate(self, question, evidence):
        return "Grounded summary."


class _FakeWebRetriever(FlytBaseWebRetriever):
    def search(self, query, limit=5):
        return [
            Citation(
                id="web:1",
                source_type=SourceType.DOCUMENTATION,
                title="Geofencing",
                excerpt="Geofencing is supported.",
                url="https://docs.flytbase.com/geofencing",
            )
        ]

    def fetch(self, url):
        return None


def _fake_container() -> Container:
    settings = Settings.from_environment()
    store = InMemoryVectorStore()
    corpus_dir = Path(__file__).resolve().parent.parent / "se-dataset"
    for record in parse_customer_directory(corpus_dir):
        store.upsert(record)
    container = Container(
        settings=settings,
        store=store,
        corpus_sync=CorpusSync(store=store),
        customer_retriever=CustomerRetriever(store=store),
        web_retriever=_FakeWebRetriever(),
        answer_service=AnswerService(llm=_FakeLlm()),
    )
    return container


def test_chat_returns_grounded_response_shape():
    app = create_app()
    app.state.container = _fake_container()
    with TestClient(app) as client:
        response = client.post(
            "/api/chat", json={"question": "What open bugs does Acme have?"}
        )
    assert response.status_code == 200
    body = response.json()
    assert body["route"] == "customer"
    assert isinstance(body["citations"], list)
    assert "answer" in body


def test_corpus_sync_returns_summary():
    app = create_app()
    app.state.container = _fake_container()
    with TestClient(app) as client:
        response = client.post("/api/corpus/sync")
    assert response.status_code == 200
    body = response.json()
    assert "scanned" in body
    assert "synced_at" in body
    for key in ("created", "updated", "deleted", "unchanged"):
        assert isinstance(body[key], int)
