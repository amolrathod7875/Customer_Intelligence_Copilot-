from pathlib import Path

import pytest
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


class FakeLlm:
    def generate(self, question, evidence):
        return "Grounded summary."


class FakeWebRetriever(FlytBaseWebRetriever):
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


@pytest.fixture
def api_client():
    settings = Settings.from_environment()
    store = InMemoryVectorStore()

    corpus_dir = Path(__file__).resolve().parent.parent.parent / "se-dataset"
    for record in parse_customer_directory(corpus_dir):
        store.upsert(record)
    # Deterministic seed so the combined-flow test is not corpus-text dependent.
    store.upsert(
        CustomerRecord(
            id="feature_requests:FR-SEED",
            record_type="feature_request",
            source_file="feature_requests.md",
            text="Acme requested geofencing support for drone fleets.",
            metadata={"ID": "FR-SEED", "Account": "Acme"},
        )
    )

    container = Container(
        settings=settings,
        store=store,
        corpus_sync=CorpusSync(store=store),
        customer_retriever=CustomerRetriever(store=store),
        web_retriever=FakeWebRetriever(),
        answer_service=AnswerService(llm=FakeLlm()),
    )

    app = create_app()
    app.state.container = container
    with TestClient(app) as client:
        yield client
