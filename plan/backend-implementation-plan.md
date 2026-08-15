# Customer Intelligence Copilot — Backend Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Build a FastAPI backend that answers questions using the local synthetic customer corpus and **live** FlytBase documentation/release notes, with source citations and incremental corpus synchronization.

**Architecture:** The backend parses records from the existing `se-dataset/` Markdown files, stores searchable chunks plus source metadata in a persistent vector index, and routes questions to customer retrieval, live web retrieval, or both. An evidence-bound answer service sends only retrieved material to a configurable LLM adapter and returns a typed response with citations or an explicit no-evidence result.

**Tech Stack:** Python 3.11, FastAPI, Pydantic, pytest, ChromaDB, sentence-transformers, SQLite, httpx, BeautifulSoup4, and an OpenAI-compatible LLM client (configured only by environment variables).

---

## Current Context and Scope

- Project root: `D:\Knowledge_Base_Over_Customer_Data`.
- Existing customer corpus:
  - `se-dataset/accounts.md`
  - `se-dataset/issues.md`
  - `se-dataset/feature_requests.md`
  - `se-dataset/tasks.md`
  - `se-dataset/meeting_notes.md`
- Mandatory live external sources: `https://docs.flytbase.com` and `https://releases.flytbase.com`.
- This plan owns only `backend/`, its tests, backend configuration, and backend documentation. The frontend is specified separately in `frontend-implementation-plan.md`.
- Do not treat downloaded/static documentation as compliance with the requirement; docs/release evidence must be fetched from the live public sites for docs-related queries.

## Backend Acceptance Criteria

1. `POST /api/chat` returns a typed answer, route, insufficiencies, and citations.
2. Customer-only questions cite records from `se-dataset`.
3. Documentation/release-only questions cite a successfully fetched live FlytBase URL.
4. Cross-source questions cite at least one customer record and one live doc/release page when evidence exists.
5. If evidence is absent or live retrieval fails, the backend returns a clear insufficiency instead of claiming a product capability.
6. `POST /api/corpus/sync` incrementally handles created, updated, and deleted customer records.
7. Unit tests never call an external LLM or live network service; they use injected fakes/transports.

## API Contract

### `POST /api/chat`

```json
{"question":"Which accounts requested a feature and is it already released?"}
```

```json
{
  "answer":"...",
  "route":"both",
  "insufficiencies":[],
  "citations":[
    {
      "id":"customer:feature_requests:FR-018",
      "source_type":"customer_record",
      "title":"FR-018 — Account name",
      "excerpt":"...",
      "url":null
    },
    {
      "id":"web:https://releases.flytbase.com/...",
      "source_type":"release_note",
      "title":"Release title",
      "excerpt":"...",
      "url":"https://releases.flytbase.com/..."
    }
  ]
}
```

### `POST /api/corpus/sync`

```json
{
  "scanned": 1816,
  "created": 0,
  "updated": 3,
  "deleted": 1,
  "unchanged": 1812,
  "synced_at": "2026-08-15T...Z"
}
```

---

### Task 1: Scaffold the backend and testable application factory

**Objective:** Create the backend layout, dependency manifest, configuration model, and health endpoint.

**Files:**

- Create: `backend/app/main.py`
- Create: `backend/app/core/config.py`
- Create: `backend/app/__init__.py`
- Create: `backend/requirements.txt`
- Create: `backend/.env.example`
- Create: `backend/tests/test_health.py`

**Step 1: Write the failing test**

```python
from fastapi.testclient import TestClient
from app.main import create_app


def test_health_endpoint_returns_ok():
    response = TestClient(create_app()).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

**Step 2: Verify RED**

Run: `cd D:/Knowledge_Base_Over_Customer_Data/backend && pytest tests/test_health.py -v`

Expected: FAIL because `create_app` does not exist.

**Step 3: Implement the minimum code**

```python
from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI(title="Customer Intelligence Copilot")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
```

Add `.env.example` with `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`, `CORPUS_DIR=../se-dataset`, and `CHROMA_DIR=.data/chroma`; never place a real key in source control.

**Step 4: Verify GREEN**

Run: `cd D:/Knowledge_Base_Over_Customer_Data/backend && pytest tests/test_health.py -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add backend
git commit -m "chore: scaffold FastAPI backend"
```

---

### Task 2: Define the shared request, evidence, and response schemas

**Objective:** Establish a strict contract that prevents an answer from losing its provenance.

**Files:**

- Create: `backend/app/models/schemas.py`
- Create: `backend/tests/test_schemas.py`

**Step 1: Write the failing test**

```python
import pytest
from pydantic import ValidationError
from app.models.schemas import Citation, SourceType


def test_documentation_citation_requires_https_url():
    with pytest.raises(ValidationError):
        Citation(
            id="web:1", source_type=SourceType.DOCUMENTATION,
            title="Mission Planning", excerpt="text", url=None,
        )
```

**Step 2: Verify RED**

Run: `cd D:/Knowledge_Base_Over_Customer_Data/backend && pytest tests/test_schemas.py -v`

Expected: FAIL because schema module is missing.

**Step 3: Implement the minimum code**

Create:

- `SourceType`: `customer_record`, `documentation`, `release_note`
- `Citation`: `id`, `source_type`, `title`, `excerpt`, `url`
- `ChatRequest`, `ChatResponse`, `SyncSummary`
- `CustomerRecord` internal model: stable `id`, `record_type`, `source_file`, `text`, `metadata`

Validate that web citations use a HTTPS URL from an allowed FlytBase host. Customer citations may have `url=None`.

**Step 4: Verify GREEN**

Run: `cd D:/Knowledge_Base_Over_Customer_Data/backend && pytest tests/test_schemas.py -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add backend/app/models backend/tests/test_schemas.py
git commit -m "feat: add grounded answer schemas"
```

---

### Task 3: Parse the five corpus files into stable customer records

**Objective:** Transform actual records in `se-dataset/` into searchable chunks while preserving exact source text and file provenance.

**Files:**

- Create: `backend/app/services/customer_parser.py`
- Create: `backend/tests/fixtures/customer/feature_requests.md`
- Create: `backend/tests/test_customer_parser.py`

**Step 1: Write the failing test**

```python
from pathlib import Path
from app.services.customer_parser import parse_customer_file


def test_parser_keeps_record_provenance_and_deterministic_id():
    records = parse_customer_file(Path("tests/fixtures/customer/feature_requests.md"))
    assert len(records) == 1
    assert records[0].source_file == "feature_requests.md"
    assert records[0].record_type == "feature_request"
    assert records[0].id.startswith("feature_requests:")
    assert "Acme" in records[0].text
```

**Step 2: Verify RED**

Run: `cd D:/Knowledge_Base_Over_Customer_Data/backend && pytest tests/test_customer_parser.py::test_parser_keeps_record_provenance_and_deterministic_id -v`

Expected: FAIL because parser does not exist.

**Step 3: Implement the minimum code**

- Inspect the actual Markdown structures before writing delimiters.
- Map known filenames to record types.
- Split on the dataset's record headings/table rows only; do not build an unnecessary universal Markdown parser.
- Prefer an explicit record ID from the source; otherwise create `filename:sha256(normalized-record-text)`.
- Preserve raw record text for the citation excerpt.
- Extract metadata only when clearly stated (account, category, date, industry, etc.).

**Step 4: Verify GREEN**

Add a second test proving empty sections do not yield blank records, then run:

```bash
cd D:/Knowledge_Base_Over_Customer_Data/backend && pytest tests/test_customer_parser.py -v
```

Expected: PASS.

**Step 5: Commit**

```bash
git add backend/app/services/customer_parser.py backend/tests
git commit -m "feat: parse customer dataset with provenance"
```

---

### Task 4: Implement incremental sync and customer retrieval

**Objective:** Persist customer chunks and update only added/changed/deleted records when the dataset changes.

**Files:**

- Create: `backend/app/services/corpus_sync.py`
- Create: `backend/app/services/customer_retriever.py`
- Create: `backend/app/services/vector_store.py`
- Create: `backend/tests/test_corpus_sync.py`
- Create: `backend/tests/test_customer_retriever.py`
- Modify: `backend/app/core/config.py`
- Modify: `backend/requirements.txt`

**Step 1: Write the failing sync test**

```python
def test_sync_upserts_changed_record_and_removes_deleted_record(tmp_path):
    store = InMemoryVectorStore()
    first = CorpusSync(store=store).sync(tmp_path)
    assert first.created == 2

    # Edit one record and remove another in the fixture corpus.
    second = CorpusSync(store=store).sync(tmp_path)
    assert second.updated == 1
    assert second.deleted == 1
```

**Step 2: Verify RED**

Run: `cd D:/Knowledge_Base_Over_Customer_Data/backend && pytest tests/test_corpus_sync.py::test_sync_upserts_changed_record_and_removes_deleted_record -v`

Expected: FAIL because sync abstractions are missing.

**Step 3: Implement the minimum code**

- Define a vector-store protocol with `upsert`, `delete`, and `query`.
- Use an in-memory implementation for unit tests and ChromaDB in production.
- Persist per-record content hashes in SQLite or Chroma metadata.
- Upsert new/changed records only.
- Remove vectors whose record IDs disappear after a scan.
- Use deterministic/fake embeddings in tests; no model downloads during pytest.

**Step 4: Verify GREEN**

Run:

```bash
cd D:/Knowledge_Base_Over_Customer_Data/backend
pytest tests/test_corpus_sync.py tests/test_customer_retriever.py -v
```

Expected: PASS.

**Step 5: Commit**

```bash
git add backend/app/core backend/app/services backend/tests
git commit -m "feat: add incremental corpus sync and retrieval"
```

---

### Task 5: Fetch and search FlytBase documentation/release pages live

**Objective:** Return trustworthy, citeable live public evidence while rejecting off-domain URLs and failed fetches.

**Files:**

- Create: `backend/app/services/flytbase_web.py`
- Create: `backend/tests/test_flytbase_web.py`
- Modify: `backend/requirements.txt`

**Step 1: Write the failing test**

```python
import httpx
from app.services.flytbase_web import FlytBaseWebRetriever


def test_fetch_turns_live_documentation_html_into_citation():
    transport = httpx.MockTransport(lambda _: httpx.Response(
        200, text="<html><title>Mission Planning</title><main>Supports missions.</main></html>"
    ))
    retriever = FlytBaseWebRetriever(client=httpx.Client(transport=transport))
    evidence = retriever.fetch("https://docs.flytbase.com/mission-planning")
    assert evidence.source_type.value == "documentation"
    assert evidence.title == "Mission Planning"
    assert evidence.url == "https://docs.flytbase.com/mission-planning"
```

**Step 2: Verify RED**

Run: `cd D:/Knowledge_Base_Over_Customer_Data/backend && pytest tests/test_flytbase_web.py::test_fetch_turns_live_documentation_html_into_citation -v`

Expected: FAIL because retriever is missing.

**Step 3: Implement the minimum code**

- Allow only HTTPS `docs.flytbase.com` and `releases.flytbase.com` URLs.
- Use timeouts, a response-size cap, and a truthful user agent.
- Extract title plus `main`/`article` text with BeautifulSoup.
- Implement a `search(query)` adapter with a configurable search provider/site-search strategy; dependency-inject it in tests.
- Classify source type from host.
- Return an evidence-unavailable result for errors; never replace it with invented product text.

**Step 4: Verify GREEN**

Add tests for off-domain rejection, timeout handling, and release-note classification. Run:

```bash
cd D:/Knowledge_Base_Over_Customer_Data/backend && pytest tests/test_flytbase_web.py -v
```

Expected: PASS.

**Step 5: Commit**

```bash
git add backend/app/services/flytbase_web.py backend/tests/test_flytbase_web.py backend/requirements.txt
git commit -m "feat: add live FlytBase retrieval"
```

---

### Task 6: Add the evidence-source query router

**Objective:** Use customer retrieval, live web retrieval, or both only when the question warrants it.

**Files:**

- Create: `backend/app/services/query_router.py`
- Create: `backend/tests/test_query_router.py`

**Step 1: Write the failing tests**

```python
from app.services.query_router import route_question


def test_account_bug_question_routes_to_customer_only():
    assert route_question("What open bugs does Acme have?") == "customer"


def test_feature_support_question_routes_to_both_sources():
    assert route_question("Which customers requested geofencing and is it supported?") == "both"
```

**Step 2: Verify RED**

Run: `cd D:/Knowledge_Base_Over_Customer_Data/backend && pytest tests/test_query_router.py -v`

Expected: FAIL because route function is missing.

**Step 3: Implement the minimum code**

Use transparent MVP rules:

- customer terms: account, issue, task, meeting, request, ticket;
- web terms: docs, release, shipped, supported, how does, capability;
- combined signals result in `both`.

Return a route enum and non-sensitive reason label for application logs. Do not expose internal reasoning text to the API response.

**Step 4: Verify GREEN**

Run: `cd D:/Knowledge_Base_Over_Customer_Data/backend && pytest tests/test_query_router.py -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add backend/app/services/query_router.py backend/tests/test_query_router.py
git commit -m "feat: route questions by evidence source"
```

---

### Task 7: Build evidence-bound answer generation and no-evidence behavior

**Objective:** Generate useful summaries without unsupported claims and keep only citations actually used in the response.

**Files:**

- Create: `backend/app/services/llm_client.py`
- Create: `backend/app/services/answer_service.py`
- Create: `backend/tests/test_answer_service.py`
- Modify: `backend/.env.example`

**Step 1: Write the failing test**

```python
from app.services.answer_service import AnswerService


def test_missing_live_evidence_returns_insufficiency_without_llm_claim():
    result = AnswerService(llm=FailIfCalledLlm()).answer(
        question="Is feature Z supported?",
        route="documentation",
        customer_evidence=[],
        web_evidence=[],
    )
    assert "could not find" in result.answer.lower()
    assert result.citations == []
    assert result.insufficiencies == [
        "No live FlytBase documentation or release-note evidence was found."
    ]
```

**Step 2: Verify RED**

Run: `cd D:/Knowledge_Base_Over_Customer_Data/backend && pytest tests/test_answer_service.py::test_missing_live_evidence_returns_insufficiency_without_llm_claim -v`

Expected: FAIL because service is missing.

**Step 3: Implement the minimum code**

- Define an LLM protocol with a production OpenAI-compatible adapter and test fakes.
- Build prompts only from the retrieved source excerpts and IDs.
- Require every factual answer sentence to reference source IDs internally, then map used IDs to structured citations.
- When a route requires evidence that is absent, return a deterministic insufficiency and do not call the LLM.
- For `both`, identify missing customer vs. missing web evidence separately.

**Step 4: Verify GREEN**

Add a test that a combined answer includes both a `customer_record` and a web source citation. Run:

```bash
cd D:/Knowledge_Base_Over_Customer_Data/backend && pytest tests/test_answer_service.py -v
```

Expected: PASS.

**Step 5: Commit**

```bash
git add backend/app/services/llm_client.py backend/app/services/answer_service.py backend/tests/test_answer_service.py backend/.env.example
git commit -m "feat: generate evidence-bound answers"
```

---

### Task 8: Wire services into `/api/chat` and `/api/corpus/sync`

**Objective:** Deliver the frontend-ready HTTP API through dependency-injected FastAPI routes.

**Files:**

- Create: `backend/app/api/routes.py`
- Create: `backend/tests/test_api.py`
- Modify: `backend/app/main.py`

**Step 1: Write the failing API test**

```python
from fastapi.testclient import TestClient
from app.main import create_app


def test_chat_returns_grounded_response_shape():
    response = TestClient(create_app()).post(
        "/api/chat", json={"question": "What open bugs does Acme have?"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["route"] == "customer"
    assert isinstance(body["citations"], list)
    assert "answer" in body
```

**Step 2: Verify RED**

Run: `cd D:/Knowledge_Base_Over_Customer_Data/backend && pytest tests/test_api.py::test_chat_returns_grounded_response_shape -v`

Expected: FAIL because API routes are missing.

**Step 3: Implement the minimum code**

- Configure dependencies through app lifespan/config.
- `POST /api/corpus/sync`: return `SyncSummary`.
- `POST /api/chat`: route, retrieve evidence, answer, return `ChatResponse`.
- Enable CORS only for the configured frontend dev origin; do not ship a production wildcard.
- Map network/LLM failures to honest, user-safe error/insufficiency responses.

**Step 4: Verify GREEN**

Run:

```bash
cd D:/Knowledge_Base_Over_Customer_Data/backend
pytest tests/test_api.py -v
pytest tests/ -q
```

Expected: PASS.

**Step 5: Commit**

```bash
git add backend/app/api backend/app/main.py backend/tests/test_api.py
git commit -m "feat: expose chat and sync endpoints"
```

---

### Task 9: Add backend demo verification and backend README section

**Objective:** Prove the three mandatory judge-facing data flows before handing the API to the frontend.

**Files:**

- Create: `backend/tests/test_demo_flows.py`
- Create: `scripts/verify_backend_demo.py`
- Modify: `README.md`

**Step 1: Write the failing test**

```python
def test_combined_query_has_customer_and_live_web_citations(api_client):
    response = api_client.post("/api/chat", json={
        "question": "Which accounts requested this feature and is it already available?"
    })
    types = {citation["source_type"] for citation in response.json()["citations"]}
    assert "customer_record" in types
    assert types & {"documentation", "release_note"}
```

**Step 2: Verify RED**

Run: `cd D:/Knowledge_Base_Over_Customer_Data/backend && pytest tests/test_demo_flows.py::test_combined_query_has_customer_and_live_web_citations -v`

Expected: FAIL until fixtures/dependencies supply both source types.

**Step 3: Implement the minimum verification**

Document and script checks for:

1. Customer-only question → customer citation.
2. Docs-only question → fetched FlytBase URL citation.
3. Combined question → both citation categories.
4. Corpus edit + sync → updated answer reflects changed record.

The real demo verification must use actual network access for live pages; fixture tests remain network-free.

**Step 4: Verify GREEN and full suite**

Run:

```bash
cd D:/Knowledge_Base_Over_Customer_Data/backend && pytest tests/ -q
cd D:/Knowledge_Base_Over_Customer_Data && python scripts/verify_backend_demo.py
```

Expected: unit suite passes; script reports real source/citation categories or a clear live-network failure.

**Step 5: Commit**

```bash
git add backend/tests scripts README.md
git commit -m "test: verify required backend demo flows"
```

---

## Backend Risks and Decisions

| Decision/Risk                            | Required handling                                                                                                                  |
| ---------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| Live docs can be unavailable             | Return an explicit missing-live-evidence response; do not silently fall back to stale static content.                              |
| Corpus Markdown layout may differ        | Inspect all five real files before locking parser logic; preserve raw excerpts even if optional metadata extraction is incomplete. |
| Embeddings introduce slow or flaky tests | Inject in-memory store and deterministic embedding fake in tests.                                                                  |
| Search service availability              | Keep discovery behind an adapter. Tests must mock it. Live result pages still need to be fetched from approved FlytBase domains.   |
| LLM hallucination                        | Prompt with retrieved sources only; no-evidence routes must avoid LLM generation altogether.                                       |

## Final Backend Definition of Done

- [ ] `pytest backend/tests/ -q` passes.
- [ ] API returns typed grounded answers and citations.
- [ ] Customer-only, docs-only, and cross-source flow tests pass.
- [ ] Live evidence sources are restricted to FlytBase docs/releases domains.
- [ ] No-evidence behavior is deterministic and non-hallucinatory.
- [ ] Dataset sync handles additions, edits, and removals incrementally.
