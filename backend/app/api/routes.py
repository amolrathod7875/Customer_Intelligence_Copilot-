from __future__ import annotations

from dataclasses import dataclass

from fastapi import APIRouter, Depends, Request

from app.core.config import Settings
from app.models.schemas import (
    ChatRequest,
    ChatResponse,
    Citation,
    CustomerRecord,
    SourceType,
    SyncSummary,
)
from app.services.answer_service import AnswerService
from app.services.corpus_sync import CorpusSync
from app.services.customer_retriever import CustomerRetriever
from app.services.flytbase_web import FlytBaseWebRetriever
from app.services.llm_client import LlmClient, OpenAILlmClient
from app.services.query_router import EvidenceRoute, route_question
from app.services.vector_store import InMemoryVectorStore, VectorStore

router = APIRouter()


@dataclass
class Container:
    settings: Settings
    store: VectorStore
    corpus_sync: CorpusSync
    customer_retriever: CustomerRetriever
    web_retriever: FlytBaseWebRetriever
    answer_service: AnswerService


def build_container(settings: Settings) -> Container:
    store: VectorStore = InMemoryVectorStore()
    corpus_sync = CorpusSync(store=store)
    customer_retriever = CustomerRetriever(store=store)
    web_retriever = FlytBaseWebRetriever()
    llm: LlmClient = OpenAILlmClient.from_settings(settings)
    answer_service = AnswerService(llm=llm)
    return Container(
        settings=settings,
        store=store,
        corpus_sync=corpus_sync,
        customer_retriever=customer_retriever,
        web_retriever=web_retriever,
        answer_service=answer_service,
    )


def get_container(request: Request) -> Container:
    return request.app.state.container


def _record_to_citation(record: CustomerRecord) -> Citation:
    metadata = record.metadata
    title = next(
        (str(metadata[key]) for key in ("Account", "Title", "ID") if key in metadata),
        record.id,
    )
    return Citation(
        id=f"customer:{record.id}",
        source_type=SourceType.CUSTOMER_RECORD,
        title=title,
        excerpt=record.text[:4000],
        url=None,
    )


@router.post("/api/chat", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    container: Container = Depends(get_container),
) -> ChatResponse:
    route = route_question(request.question)
    customer_evidence: list[Citation] = []
    web_evidence: list[Citation] = []

    if route in {EvidenceRoute.CUSTOMER, EvidenceRoute.BOTH}:
        customer_evidence = [
            _record_to_citation(record)
            for record in container.customer_retriever.search(request.question)
        ]

    if route in {EvidenceRoute.DOCUMENTATION, EvidenceRoute.BOTH}:
        try:
            web_evidence = container.web_retriever.search(request.question)
        except Exception:
            web_evidence = []

    try:
        return container.answer_service.answer(
            question=request.question,
            route=route,
            customer_evidence=customer_evidence,
            web_evidence=web_evidence,
        )
    except Exception:
        return ChatResponse(
            answer="I could not generate an answer because the language model service was unavailable.",
            route=route.value,
            insufficiencies=["The language model service returned an error."],
            citations=[*customer_evidence, *web_evidence],
        )


@router.post("/api/corpus/sync", response_model=SyncSummary)
def corpus_sync(container: Container = Depends(get_container)) -> SyncSummary:
    return container.corpus_sync.sync(container.settings.corpus_dir)
