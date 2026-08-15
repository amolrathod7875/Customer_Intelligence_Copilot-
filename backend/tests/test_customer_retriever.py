from app.models.schemas import CustomerRecord
from app.services.customer_retriever import CustomerRetriever
from app.services.vector_store import InMemoryVectorStore


def test_retriever_returns_keyword_relevant_customer_record():
    store = InMemoryVectorStore()
    store.upsert(
        CustomerRecord(
            id="issues:ISS-1",
            record_type="issue",
            source_file="issues.md",
            text="Acme has an open camera-feed bug.",
            metadata={"Account": "Acme", "Status": "Open"},
        )
    )
    store.upsert(
        CustomerRecord(
            id="issues:ISS-2",
            record_type="issue",
            source_file="issues.md",
            text="Beta asked a billing question.",
            metadata={"Account": "Beta", "Status": "Closed"},
        )
    )

    evidence = CustomerRetriever(store).search("What open camera bug does Acme have?")

    assert [record.id for record in evidence] == ["issues:ISS-1"]
