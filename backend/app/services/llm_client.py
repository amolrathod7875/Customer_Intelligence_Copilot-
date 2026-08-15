from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.core.config import Settings
from app.models.schemas import Citation


@runtime_checkable
class LlmClient(Protocol):
    """Contract consumed by ``AnswerService``."""

    def generate(self, question: str, evidence: list[Citation]) -> str:  # pragma: no cover - protocol
        ...


class OpenAILlmClient:
    """Production adapter for any OpenAI-compatible chat completions endpoint.

    Configured purely through environment variables via ``Settings``; no API
    keys are ever hard-coded in source. The ``openai`` SDK is imported lazily
    so the rest of the backend (and its network-free tests) do not require it.
    """

    def __init__(
        self,
        base_url: str | None,
        api_key: str | None,
        model: str | None,
        client: object | None = None,
    ) -> None:
        self._model = model or "gpt-4o-mini"
        if client is not None:
            self._client = client
        else:
            from openai import OpenAI

            self._client = OpenAI(base_url=base_url, api_key=api_key or "missing")

    @classmethod
    def from_settings(cls, settings: Settings) -> "OpenAILlmClient":
        return cls(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
            model=settings.llm_model,
        )

    @staticmethod
    def _build_prompt(question: str, evidence: list[Citation]) -> str:
        if not evidence:
            return question
        blocks: list[str] = []
        for citation in evidence:
            url = citation.url or "n/a"
            blocks.append(
                f"[{citation.id}] ({citation.source_type.value}) {citation.title}\n"
                f"URL: {url}\n{citation.excerpt}"
            )
        context = "\n\n".join(blocks)
        return (
            "Answer the question using ONLY the cited sources below. "
            "Reference every factual claim with its source id in brackets, "
            "e.g. [customer:feature_requests:FR-018]. "
            "If the sources do not contain the answer, reply that you could "
            "not find sufficient evidence and do not invent capabilities.\n\n"
            f"Sources:\n{context}\n\nQuestion: {question}"
        )

    def generate(self, question: str, evidence: list[Citation]) -> str:
        prompt = self._build_prompt(question, evidence)
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        return response.choices[0].message.content or ""
