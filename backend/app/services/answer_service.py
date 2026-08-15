from __future__ import annotations

from app.models.schemas import ChatResponse, Citation
from app.services.llm_client import LlmClient
from app.services.query_router import EvidenceRoute


class AnswerService:
    def __init__(self, llm: LlmClient) -> None:
        self._llm = llm

    def answer(
        self,
        question: str,
        route: EvidenceRoute,
        customer_evidence: list[Citation],
        web_evidence: list[Citation],
    ) -> ChatResponse:
        insufficiencies = _missing_evidence(route, customer_evidence, web_evidence)
        if insufficiencies:
            return ChatResponse(
                answer="I could not find sufficient grounded evidence to answer that question.",
                route=route.value,
                insufficiencies=insufficiencies,
                citations=[],
            )
        citations = [*customer_evidence, *web_evidence]
        return ChatResponse(
            answer=self._llm.generate(question, citations),
            route=route.value,
            insufficiencies=[],
            citations=citations,
        )


def _missing_evidence(
    route: EvidenceRoute, customer_evidence: list[Citation], web_evidence: list[Citation]
) -> list[str]:
    missing: list[str] = []
    if route in {EvidenceRoute.CUSTOMER, EvidenceRoute.BOTH} and not customer_evidence:
        missing.append("No matching customer-record evidence was found.")
    if route in {EvidenceRoute.DOCUMENTATION, EvidenceRoute.BOTH} and not web_evidence:
        missing.append("No live FlytBase documentation or release-note evidence was found.")
    return missing
