# Customer Intelligence Copilot Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Build a grounded conversational application that answers questions over the provided synthetic customer corpus and live FlytBase documentation/release notes, with verifiable citations and incremental corpus synchronization.

**Architecture:** A React/Vite frontend calls a FastAPI backend. The backend parses local Markdown records into a persistent Chroma collection, routes each question to customer search, live FlytBase web retrieval, or both, then uses an LLM to synthesize only from retrieved evidence. Every answer is returned with structured source citations, and a sync process uses file hashes to re-index only changed customer files.

**Tech Stack:** Python 3.11, FastAPI, Pydantic, pytest, ChromaDB, sentence-transformers, httpx, BeautifulSoup4, React, TypeScript, Vite, Vitest, React Testing Library. LLM provider remains configurable via environment variables (default adapter targets an OpenAI-compatible API such as Cerebras).

---

## Current Context / Assumptions

- No application repository was found under the active workspace (`C:\Users\shiva`); this plan creates a new project at `customer-intelligence-copilot/`.
- The supplied synthetic corpus will be copied or placed under `customer-intelligence-copilot/data/customer/` and must include `accounts.md`, `issues.md`, `feature_requests.md`, `tasks.md`, and `meeting_notes.md`.
- `docs.flytbase.com` and `releases.flytbase.com` are public live sources. The app must fetch them during docs-related retrieval, not answer only from a pre-downloaded corpus.
- The exact LLM API key and preferred provider are not yet chosen. Do not hard-code a secret; implement a provider interface and document the required environment variables.
- The MVP must satisfy all mandatory requirements before adding bonuses: customer-only answers, live-docs-only answers, cross-source answers, source grounding, honest insufficiency handling, and changed-corpus sync.

## Product Scope and Acceptance Criteria

1. A user can ask a customer-data-only question and receive an answer supported by records from the supplied corpus.
2. A user can ask a product question and receive an answer supported by a **live** FlytBase docs or release-notes URL.
3. A user can ask a combined question and receive one answer that compares customer evidence with live product evidence.
4. Each answer returns structured citations: title/record label, source kind, excerpt, and URL for web sources.
5. If either required source has no evidence, the response says exactly what was not found rather than inferring it.
6. A sync action detects edited, added, and deleted local files/records and updates the index without recreating the entire corpus.
7. The UI visibly distinguishes customer evidence from live documentation/release evidence.

## Proposed Project Layout

```text
customer-intelligence-copilot/
├── backend/
│   ├── app/
│   │   ├── api/routes.py
│   │   ├── core/config.py
│   │   ├── models/schemas.py
│   │   ├── services/customer_parser.py
│   │   ├── services/corpus_sync.py
│   │   ├── services/customer_retriever.py
│   │   ├── services/flytbase_web.py
│   │   ├── services/query_router.py
│   │   ├── services/answer_service.py
│   │   ├── services/llm_client.py
│   │   └── main.py
│   ├── tests/
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/components/ChatPanel.tsx
│   ├── src/components/CitationPanel.tsx
│   ├── src/components/SyncStatus.tsx
│   ├── src/api/client.ts
│   ├── src/App.tsx
│   └── src/types.ts
├── data/customer/.gitkeep
├── README.md
└── .gitignore
```

## API Contract

### `POST /api/chat`

Request:

```json
{"question":"Which accounts requested feature X, and is it released?"}
```

Response:

```json
{
  "answer": "...",
  "route": "both",
  "insufficiencies": [],
  "citations": [
    {
      "id": "customer:feature_requests:FR-018",
      "source_type": "customer_record",
      "title": "FR-018 — Account name",
      "excerpt": "...",
      "url": null
    },
    {
      "id": "web:https://releases.flytbase.com/...",
      "source_type": "release_note",
      "title": "Release title",
      "excerpt": "...",
      "url": "https://releases.flytbase.com/..."
    }
  ]
}
```

### `POST /api/corpus/sync`

Response reports scanned/created/updated/deleted record counts and the sync time. It must be safe to call repeatedly.

---

### Task 1: Create the repository skeleton and reproducible local setup

**Objective:** Establish an empty but runnable backend/frontend structure, sample environment configuration, and a test command for each layer.

**Files:**
- Create: `customer-intelligence-copilot/backend/app/main.py`
- Create: `customer-intelligence-copilot/backend/requirements.txt`
- Create: `customer-intelligence-copilot/backend/.env.example`
- Create: `customer-intelligence-copilot/backend/tests/test_health.py`
- Create: `customer-intelligence-copilot/frontend/package.json`
- Create: `customer-intelligence-copilot/frontend/vite.config.ts`
- Create: `customer-intelligence-copilot/frontend/src/App.tsx`
- Create: `customer-intelligence-copilot/README.md`
- Create: `customer-intelligence-copilot/.gitignore`

**Step 1: Write failing backend health test**

```python
from fastapi.testclient import TestClient
from app.main import app


def test_health_endpoint_returns_service_status():
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

**Step 2: Run test to verify failure**

Run: `cd customer-intelligence-copilot/backend && pytest tests/test_health.py -v`

Expected: FAIL because `app.main` or `/health` does not exist.

**Step 3: Implement the minimal FastAPI health endpoint**

```python
from fastapi import FastAPI

app = FastAPI(title="Customer Intelligence Copilot")

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
```

**Step 4: Verify backend and frontend scaffolds**

Run:

```bash
cd customer-intelligence-copilot/backend && pytest tests/test_health.py -v
cd ../frontend && npm test -- --run
```

Expected: backend health test passes; frontend test runner exits successfully after a smoke test is added.

**Step 5: Commit**

```bash
git add customer-intelligence-copilot
git commit -m "chore: scaffold customer intelligence copilot"
```

---

### Task 2: Define source, citation, sync, and chat response schemas

**Objective:** Create one explicit contract so retrieval, answer generation, API routes, and UI share the same grounded-answer format.

**Files:**
- Create: `customer-intelligence-copilot/backend/app/models/schemas.py`
- Create: `customer-intelligence-copilot/backend/tests/test_schemas.py`

**Step 1: Write failing schema test**

```python
from app.models.schemas import Citation, SourceType


def test_web_citation_requires_a_live_url():
    citation = Citation(
        id="web:1",
        source_type=SourceType.DOCUMENTATION,
        title="Mission Planning",
        excerpt="FlytBase supports ...",
        url="https://docs.flytbase.com/example",
    )
    assert citation.url.startswith("https://docs.flytbase.com/")
```

**Step 2: Run test to verify failure**

Run: `cd customer-intelligence-copilot/backend && pytest tests/test_schemas.py::test_web_citation_requires_a_live_url -v`

Expected: FAIL because schemas are missing.

**Step 3: Implement minimal Pydantic schemas**

Create enums for `customer_record`, `documentation`, and `release_note`; models for `Citation`, `ChatRequest`, `ChatResponse`, and `SyncSummary`. Validate that customer citations have no mandatory URL and that web citations have a valid `https` URL.

**Step 4: Verify pass**

Run: `cd customer-intelligence-copilot/backend && pytest tests/test_schemas.py -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add backend/app/models backend/tests/test_schemas.py
git commit -m "feat: define grounded answer schemas"
```

---

### Task 3: Parse the supplied Markdown corpus into stable customer records

**Objective:** Turn each dataset file into chunks with stable IDs, provenance metadata, and raw text suitable for retrieval and citation.

**Files:**
- Create: `customer-intelligence-copilot/backend/app/services/customer_parser.py`
- Create: `customer-intelligence-copilot/backend/tests/fixtures/customer/feature_requests.md`
- Create: `customer-intelligence-copilot/backend/tests/test_customer_parser.py`

**Step 1: Write failing parser test**

```python
from pathlib import Path
from app.services.customer_parser import parse_customer_file


def test_parser_preserves_source_and_stable_record_id():
    records = parse_customer_file(Path("tests/fixtures/customer/feature_requests.md"))
    assert len(records) == 1
    assert records[0].source_file == "feature_requests.md"
    assert records[0].record_type == "feature_request"
    assert records[0].id.startswith("feature_requests:")
    assert "Acme" in records[0].text
```

**Step 2: Run test to verify failure**

Run: `cd customer-intelligence-copilot/backend && pytest tests/test_customer_parser.py::test_parser_preserves_source_and_stable_record_id -v`

Expected: FAIL because parser is missing.

**Step 3: Implement only the supported corpus formats**

- Map each known filename to a record type.
- Split Markdown on clear record headings or table rows, preserving the original text.
- Generate a deterministic ID from filename plus an explicit dataset ID if present, otherwise filename plus normalized record content hash.
- Return a typed `CustomerRecord` object with `id`, `record_type`, `source_file`, `text`, and extracted metadata when clearly available.

Do not invent a generic Markdown parser beyond the provided dataset formats.

**Step 4: Add edge-case test and verify pass**

Add a test ensuring an empty section produces no blank record, then run:

```bash
cd customer-intelligence-copilot/backend && pytest tests/test_customer_parser.py -v
```

Expected: PASS.

**Step 5: Commit**

```bash
git add backend/app/services/customer_parser.py backend/tests
git commit -m "feat: parse customer corpus with provenance"
```

---

### Task 4: Build incremental corpus sync and persistent local retrieval index

**Objective:** Index added/changed records and remove deleted records without rebuilding unchanged data.

**Files:**
- Create: `customer-intelligence-copilot/backend/app/services/corpus_sync.py`
- Create: `customer-intelligence-copilot/backend/app/services/customer_retriever.py`
- Create: `customer-intelligence-copilot/backend/tests/test_corpus_sync.py`
- Create: `customer-intelligence-copilot/backend/tests/test_customer_retriever.py`
- Modify: `customer-intelligence-copilot/backend/app/core/config.py`
- Modify: `customer-intelligence-copilot/backend/requirements.txt`

**Step 1: Write failing sync test**

```python
def test_sync_reindexes_only_changed_file_and_removes_deleted_record(tmp_path):
    # Arrange a fixture corpus and a fake/in-memory vector store.
    first = sync_customer_corpus(tmp_path)
    assert first.created == 2

    # Edit one source record and remove another.
    second = sync_customer_corpus(tmp_path)
    assert second.updated == 1
    assert second.deleted == 1
    assert second.unchanged == 0
```

**Step 2: Run test to verify failure**

Run: `cd customer-intelligence-copilot/backend && pytest tests/test_corpus_sync.py::test_sync_reindexes_only_changed_file_and_removes_deleted_record -v`

Expected: FAIL because sync service is missing.

**Step 3: Implement minimal incremental sync**

- Persist file and record fingerprints in a small local SQLite database or Chroma metadata collection.
- Hash normalized record text, not only file modification time.
- Upsert only created/changed records into Chroma.
- Delete index entries whose stable record IDs no longer exist after a source scan.
- Return a `SyncSummary` count for created, updated, deleted, and unchanged records.
- Keep embedding and store access behind interfaces so tests use an in-memory fake rather than a real embedding model.

**Step 4: Verify retrieval behavior**

Write a retrieval test with injected deterministic embeddings that asserts the returned record retains `source_file` and `id`. Run:

```bash
cd customer-intelligence-copilot/backend && pytest tests/test_corpus_sync.py tests/test_customer_retriever.py -v
```

Expected: PASS.

**Step 5: Commit**

```bash
git add backend/app/core backend/app/services backend/tests
git commit -m "feat: add incremental customer corpus sync"
```

---

### Task 5: Retrieve FlytBase documentation and releases live with safe domain controls

**Objective:** Search/fetch only allowed FlytBase public pages at query time and convert them into citeable evidence.

**Files:**
- Create: `customer-intelligence-copilot/backend/app/services/flytbase_web.py`
- Create: `customer-intelligence-copilot/backend/tests/test_flytbase_web.py`
- Modify: `customer-intelligence-copilot/backend/requirements.txt`

**Step 1: Write failing live-retrieval test**

```python
import httpx
from app.services.flytbase_web import FlytBaseWebRetriever


def test_retriever_returns_a_documentation_citation_from_live_html():
    transport = httpx.MockTransport(lambda request: httpx.Response(
        200,
        text="<html><title>Mission Planning</title><main>FlytBase supports missions.</main></html>",
    ))
    retriever = FlytBaseWebRetriever(client=httpx.Client(transport=transport))
    result = retriever.fetch("https://docs.flytbase.com/mission-planning")
    assert result.source_type.value == "documentation"
    assert result.title == "Mission Planning"
    assert "supports missions" in result.excerpt
```

**Step 2: Run test to verify failure**

Run: `cd customer-intelligence-copilot/backend && pytest tests/test_flytbase_web.py::test_retriever_returns_a_documentation_citation_from_live_html -v`

Expected: FAIL because retriever is missing.

**Step 3: Implement focused live retrieval**

- Allow only HTTPS URLs hosted by `docs.flytbase.com` or `releases.flytbase.com`.
- Use a bounded HTTP timeout, response-size limit, user agent, and clear failure message.
- Extract title and meaningful main/article text using BeautifulSoup.
- Return the exact fetched URL in the citation.
- Add a `search(query)` adapter that uses a configurable search provider or site-search strategy; keep it interface-based so it can be tested without live network calls.
- Never turn a failed fetch into asserted product information.

**Step 4: Add security/error tests and verify pass**

Test rejection of `https://example.com`, timeout/fetch failure conversion to an evidence-unavailable result, and release-notes source typing. Run:

```bash
cd customer-intelligence-copilot/backend && pytest tests/test_flytbase_web.py -v
```

Expected: PASS.

**Step 5: Commit**

```bash
git add backend/app/services/flytbase_web.py backend/tests/test_flytbase_web.py backend/requirements.txt
git commit -m "feat: retrieve live FlytBase evidence"
```

---

### Task 6: Route questions to customer, documentation, releases, or both

**Objective:** Ensure product questions trigger live retrieval while customer-only questions avoid unnecessary web work.

**Files:**
- Create: `customer-intelligence-copilot/backend/app/services/query_router.py`
- Create: `customer-intelligence-copilot/backend/tests/test_query_router.py`

**Step 1: Write failing routing tests**

```python
from app.services.query_router import route_question


def test_account_issue_question_routes_to_customer_only():
    assert route_question("What open bugs does Acme have?") == "customer"


def test_support_status_question_routes_to_both_sources():
    assert route_question("Which customers requested geofencing and is it supported?") == "both"
```

**Step 2: Run tests to verify failure**

Run: `cd customer-intelligence-copilot/backend && pytest tests/test_query_router.py -v`

Expected: FAIL because router is missing.

**Step 3: Implement a transparent, testable router**

Use rule-based intent signals for the MVP: account/issue/task/meeting terminology implies customer; `how does`, `supported`, `documentation`, `release`, `shipped` implies web; both signal groups imply both. Return `both` for uncertain capability-plus-customer requests so source coverage is conservative. Include a reason string for logging/debugging but do not expose internal chain-of-thought.

**Step 4: Verify pass**

Run: `cd customer-intelligence-copilot/backend && pytest tests/test_query_router.py -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add backend/app/services/query_router.py backend/tests/test_query_router.py
git commit -m "feat: route questions by evidence source"
```

---

### Task 7: Generate evidence-bound answers and explicitly report gaps

**Objective:** Produce a readable answer only from retrieved records/pages, preserve citations, and reject unsupported claims.

**Files:**
- Create: `customer-intelligence-copilot/backend/app/services/llm_client.py`
- Create: `customer-intelligence-copilot/backend/app/services/answer_service.py`
- Create: `customer-intelligence-copilot/backend/tests/test_answer_service.py`
- Modify: `customer-intelligence-copilot/backend/.env.example`

**Step 1: Write failing insufficiency test**

```python
from app.services.answer_service import AnswerService


def test_answer_service_reports_missing_documentation_instead_of_guessing():
    result = AnswerService(llm=FakeLlm()).answer(
        question="Is feature Z supported?",
        customer_evidence=[],
        web_evidence=[],
        route="documentation",
    )
    assert "could not find" in result.answer.lower()
    assert result.citations == []
    assert result.insufficiencies == ["No live FlytBase documentation or release-note evidence was found."]
```

**Step 2: Run test to verify failure**

Run: `cd customer-intelligence-copilot/backend && pytest tests/test_answer_service.py::test_answer_service_reports_missing_documentation_instead_of_guessing -v`

Expected: FAIL because answer service is missing.

**Step 3: Implement evidence-bound prompt construction and fallback**

- Accept only normalized customer records and live web citations as context.
- Build a concise system instruction: use supplied evidence only, never invent a feature status, identify missing source coverage, and cite every factual statement by citation ID.
- If required evidence for the selected route is empty, do not call the LLM for factual synthesis; return a deterministic insufficiency message.
- Parse/carry citation IDs from the answer and return only citations actually used.
- Make the LLM adapter configurable via `LLM_BASE_URL`, `LLM_API_KEY`, and `LLM_MODEL`; use a fake adapter in tests.

**Step 4: Add combined-answer test and verify pass**

Test that a cross-source answer receives both a customer citation and a live documentation/release citation. Run:

```bash
cd customer-intelligence-copilot/backend && pytest tests/test_answer_service.py -v
```

Expected: PASS.

**Step 5: Commit**

```bash
git add backend/app/services/llm_client.py backend/app/services/answer_service.py backend/tests/test_answer_service.py backend/.env.example
git commit -m "feat: generate grounded answers with gap handling"
```

---

### Task 8: Expose sync and chat through FastAPI

**Objective:** Connect routing, sync, retrieval, and answer generation behind stable HTTP endpoints.

**Files:**
- Create: `customer-intelligence-copilot/backend/app/api/routes.py`
- Create: `customer-intelligence-copilot/backend/tests/test_api.py`
- Modify: `customer-intelligence-copilot/backend/app/main.py`

**Step 1: Write failing API test**

```python
from fastapi.testclient import TestClient
from app.main import app


def test_chat_returns_grounded_response_contract():
    client = TestClient(app)
    response = client.post("/api/chat", json={"question": "What open bugs does Acme have?"})
    assert response.status_code == 200
    body = response.json()
    assert body["route"] == "customer"
    assert "answer" in body
    assert isinstance(body["citations"], list)
```

**Step 2: Run test to verify failure**

Run: `cd customer-intelligence-copilot/backend && pytest tests/test_api.py::test_chat_returns_grounded_response_contract -v`

Expected: FAIL because route is missing.

**Step 3: Implement endpoints with dependency injection**

- `POST /api/corpus/sync`: call the sync service and return `SyncSummary`.
- `POST /api/chat`: route question, retrieve appropriate evidence, create evidence-bound answer, return `ChatResponse`.
- Initialize dependencies through FastAPI lifespan/config, allowing tests to inject fakes.
- Add CORS only for the frontend development origin; do not use a wildcard in production configuration.

**Step 4: Verify endpoint behavior**

Run:

```bash
cd customer-intelligence-copilot/backend && pytest tests/test_api.py -v
pytest tests/ -q
```

Expected: PASS.

**Step 5: Commit**

```bash
git add backend/app/api backend/app/main.py backend/tests/test_api.py
git commit -m "feat: add chat and corpus sync APIs"
```

---

### Task 9: Build the chat experience and source evidence panel

**Objective:** Make the mandatory grounded-answer behavior visible and easy to demonstrate.

**Files:**
- Create: `customer-intelligence-copilot/frontend/src/api/client.ts`
- Create: `customer-intelligence-copilot/frontend/src/types.ts`
- Create: `customer-intelligence-copilot/frontend/src/components/ChatPanel.tsx`
- Create: `customer-intelligence-copilot/frontend/src/components/CitationPanel.tsx`
- Create: `customer-intelligence-copilot/frontend/src/components/SyncStatus.tsx`
- Create: `customer-intelligence-copilot/frontend/src/components/CitationPanel.test.tsx`
- Modify: `customer-intelligence-copilot/frontend/src/App.tsx`

**Step 1: Write failing UI citation test**

```tsx
import { render, screen } from "@testing-library/react";
import { CitationPanel } from "./CitationPanel";

it("renders a live source as a clickable external link", () => {
  render(<CitationPanel citations={[{
    id: "web:1", source_type: "documentation", title: "Mission Planning",
    excerpt: "Relevant text", url: "https://docs.flytbase.com/mission"
  }]} />);
  expect(screen.getByRole("link", { name: "Mission Planning" })).toHaveAttribute(
    "href", "https://docs.flytbase.com/mission"
  );
});
```

**Step 2: Run test to verify failure**

Run: `cd customer-intelligence-copilot/frontend && npm test -- --run src/components/CitationPanel.test.tsx`

Expected: FAIL because the component is missing.

**Step 3: Implement the smallest usable interface**

- `ChatPanel`: question input, submit state, answer card, quick demo-question buttons.
- `CitationPanel`: two labeled groups—**Customer Evidence** and **Live FlytBase Evidence**—with excerpts and external links for web citations.
- `SyncStatus`: button calls `/api/corpus/sync` and displays created/updated/deleted counts.
- `App`: responsive two-column layout; use accessible labels and status text.
- Do not add authentication, account management, analytics, or long-term chat history in the MVP.

**Step 4: Verify pass and build**

Run:

```bash
cd customer-intelligence-copilot/frontend
npm test -- --run
npm run build
```

Expected: all UI tests pass and Vite produces a production build.

**Step 5: Commit**

```bash
git add frontend/src
git commit -m "feat: add grounded chat and citation UI"
```

---

### Task 10: Add end-to-end demo data, documentation, and final validation

**Objective:** Make setup, required inputs, and all three judge-facing demonstrations repeatable.

**Files:**
- Create: `customer-intelligence-copilot/scripts/verify_demo.py`
- Create: `customer-intelligence-copilot/backend/tests/test_demo_flows.py`
- Modify: `customer-intelligence-copilot/README.md`
- Modify: `customer-intelligence-copilot/backend/.env.example`

**Step 1: Write failing demo-flow test**

```python
def test_cross_source_demo_returns_customer_and_live_web_citations(api_client):
    response = api_client.post("/api/chat", json={
        "question": "Which accounts requested this feature and is it already available?"
    })
    assert response.status_code == 200
    types = {item["source_type"] for item in response.json()["citations"]}
    assert "customer_record" in types
    assert types & {"documentation", "release_note"}
```

**Step 2: Run test to verify failure**

Run: `cd customer-intelligence-copilot/backend && pytest tests/test_demo_flows.py::test_cross_source_demo_returns_customer_and_live_web_citations -v`

Expected: FAIL until test fixtures/dependencies are wired to provide both evidence types.

**Step 3: Implement demo verification and setup documentation**

README must include:
- prerequisites and environment variables;
- corpus placement instructions;
- commands to install/run backend and frontend;
- the sync command/button behavior;
- exactly three required demo questions (customer-only, docs-only, combined);
- how to show citations and explain a no-evidence response;
- a warning that live public docs are fetched at query time and results depend on network availability.

`verify_demo.py` should call the local API and check response schema/citation categories using configured known test questions; it must not fake successful live web responses in a real demo run.

**Step 4: Run full validation**

Run:

```bash
cd customer-intelligence-copilot/backend && pytest tests/ -q
cd ../frontend && npm test -- --run && npm run build
cd .. && python scripts/verify_demo.py
```

Expected: backend tests, frontend tests/build, and local API verification all pass. In addition, manually run the three judge-facing questions against live FlytBase pages and open the cited URLs to confirm they resolve.

**Step 5: Commit**

```bash
git add README.md scripts backend/tests backend/.env.example
git commit -m "docs: add setup and demo validation guide"
```

---

## Risks, Tradeoffs, and Mitigations

| Risk | Mitigation |
|---|---|
| Live FlytBase page structure/search behavior changes | Keep fetch/extraction and search behind `FlytBaseWebRetriever`; show a clear evidence-unavailable result rather than guessing. |
| Search engine API access is unavailable | Use a configurable provider adapter and test it with fixtures; for demo, seed a small allowlisted set of live entry URLs only as discovery hints, then fetch each result live. |
| LLM hallucinates product claims | Require retrieved evidence, use strict answer instructions, return deterministic no-evidence messages, and display citations next to answers. |
| Corpus Markdown structure differs by file | Inspect actual supplied files before finalizing parser delimiters; retain raw source excerpts for citations even when metadata extraction is incomplete. |
| Embedding models slow startup | Persist Chroma store locally; use lazy initialization and mock embeddings in unit tests. |
| Network failure during the demo | Demonstrate customer-only flow first; show explicit live-evidence failure handling if needed, but test connectivity shortly before presenting. Do not claim static fallback meets the live-source requirement. |
| Scope creep | Defer customer-360 pages, analytics, contradiction dashboard, and multi-turn memory until all mandatory flows pass. |

## Deferred Bonus Enhancements

1. Contradiction detector: flag a customer request whose matching capability appears in a live release note.
2. Faceted analytics: most-requested features by industry, date, region, and account tier.
3. Multi-part query planner that decomposes queries and presents a short execution summary.
4. Question-frequency dashboard using privacy-safe local query logging.

## Final Definition of Done

- [ ] All backend and frontend tests pass.
- [ ] Customer-only question returns customer-record citations.
- [ ] Docs-only question fetches and cites a current `docs.flytbase.com` or `releases.flytbase.com` page.
- [ ] Combined question returns both customer and live web citations.
- [ ] No-evidence response makes no unsupported factual claim.
- [ ] Corpus sync test proves changed and deleted records are handled incrementally.
- [ ] Demo UI visibly separates customer and live FlytBase evidence.
- [ ] README enables a teammate to set up and demo the project without verbal instructions.
