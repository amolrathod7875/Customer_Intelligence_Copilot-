from app.models.schemas import Citation, SourceType
from app.services.answer_service import AnswerService
from app.services.query_router import EvidenceRoute


class FailIfCalledLlm:
    def generate(self, question, evidence):
        raise AssertionError("LLM must not run without the required evidence")


class EchoLlm:
    def generate(self, question, evidence):
        return "Grounded summary."


def test_missing_live_evidence_returns_insufficiency_without_llm_claim():
    result = AnswerService(llm=FailIfCalledLlm()).answer(
        question="Is feature Z supported?",
        route=EvidenceRoute.DOCUMENTATION,
        customer_evidence=[],
        web_evidence=[],
    )

    assert "could not find" in result.answer.lower()
    assert result.citations == []
    assert result.insufficiencies == ["No live FlytBase documentation or release-note evidence was found."]


def test_combined_answer_keeps_customer_and_live_citations():
    customer = Citation(
        id="customer:feature_requests:1",
        source_type=SourceType.CUSTOMER_RECORD,
        title="Requested by Acme",
        excerpt="Acme requested geofencing.",
    )
    web = Citation(
        id="web:1",
        source_type=SourceType.DOCUMENTATION,
        title="Geofencing",
        excerpt="Geofencing is supported.",
        url="https://docs.flytbase.com/geofencing",
    )

    result = AnswerService(llm=EchoLlm()).answer("Is geofencing supported?", EvidenceRoute.BOTH, [customer], [web])

    assert result.answer == "Grounded summary."
    assert {citation.source_type for citation in result.citations} == {SourceType.CUSTOMER_RECORD, SourceType.DOCUMENTATION}
