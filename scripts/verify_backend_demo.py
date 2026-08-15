"""Backend demo verification.

Exercises the three mandatory judge-facing flows against the real corpus and
(live) FlytBase documentation. Requires network access for docs/release flows
and LLM env vars for answer generation. Prints a clear PASS/INCOMPLETE report
or a clear live-network failure.
"""
from __future__ import annotations

from app.api.routes import build_container
from app.core.config import Settings
from app.models.schemas import Citation, SourceType
from app.services.query_router import EvidenceRoute, route_question


def _record_to_citation(record) -> Citation:
    metadata = record.metadata
    title = next(
        (str(metadata[k]) for k in ("Account", "Title", "ID") if k in metadata),
        record.id,
    )
    return Citation(
        id=f"customer:{record.id}",
        source_type=SourceType.CUSTOMER_RECORD,
        title=title,
        excerpt=record.text[:4000],
        url=None,
    )


def main() -> int:
    settings = Settings.from_environment()
    container = build_container(settings)
    container.corpus_sync.sync(settings.corpus_dir)

    questions = {
        "customer-only": "What open bugs does Acme have?",
        "docs-only": "Is geofencing supported according to the docs?",
        "combined": "Which accounts requested geofencing and is it supported?",
    }

    ok = True
    for label, question in questions.items():
        route = route_question(question)
        customer_evidence = (
            [_record_to_citation(r) for r in container.customer_retriever.search(question)]
            if route in (EvidenceRoute.CUSTOMER, EvidenceRoute.BOTH)
            else []
        )
        web_evidence = []
        if route in (EvidenceRoute.DOCUMENTATION, EvidenceRoute.BOTH):
            try:
                web_evidence = container.web_retriever.search(question)
            except Exception as exc:  # network failure
                print(f"[{label}] LIVE NETWORK FAILURE fetching FlytBase evidence: {exc}")
                ok = False
        try:
            response = container.answer_service.answer(
                question, route, customer_evidence, web_evidence
            )
        except Exception as exc:
            print(f"[{label}] ANSWER GENERATION ERROR: {exc}")
            response = None

        types = {c.source_type.value for c in (response.citations if response else [])}
        print(
            f"[{label}] route={route.value} citations={sorted(types)} "
            f"answer_present={bool(response and response.answer)}"
        )
        if label == "customer-only" and "customer_record" not in types:
            ok = False
        if label == "docs-only" and not (types & {"documentation", "release_note"}):
            ok = False
        if label == "combined" and not (
            "customer_record" in types and types & {"documentation", "release_note"}
        ):
            ok = False

    print("DEMO VERIFICATION:", "PASS" if ok else "INCOMPLETE (see above)")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
