# Customer Intelligence Copilot

Retrieval-augmented assistant that answers questions about FlytBase by combining a
private **customer corpus** (Qdrant vector store) with **live FlytBase documentation**
retrieval, returning grounded answers with citations and evidence insufficiencies.

See [`instruction.md`](./instruction.md) for the full architecture (Mermaid diagram),
local run steps, and Hugging Face Space deployment.

## Problem Statement

Ship a customer-intelligence copilot that:

1. Runs as a backend **on Hugging Face** (free tier only — the Docker SDK is paid).
2. Answers from both a private customer corpus **and** live FlytBase docs/release notes.
3. Connects to a TanStack Start frontend without CORS or port conflicts.
4. Stays responsive — no multi-minute hangs while the model or vector store is slow.

## Solutions Applied

| # | Problem | Fix |
|---|---------|-----|
| 1 | HF free Spaces only allow the **Gradio** SDK, but the backend is FastAPI. | Mount the FastAPI API onto Gradio's underlying app (`demo.app.include_router`) so `/api/chat` and `/api/corpus/sync` serve from a free Gradio Space. See `backend/app.py`. |
| 2 | **Docker Desktop** was holding port `8000`, so uvicorn couldn't bind and the frontend hit Docker (404s) → "not connected". | Free port `8000` before starting the backend; the frontend (`:8080`) then reaches the API. |
| 3 | Queries returned **"No matching customer-record evidence"**. | The corpus is indexed into Qdrant at startup via Cloud Inference, which is slow. The startup `corpus_sync.sync` was **blocking** the server. Made indexing run in a **background thread** so the API is available immediately (existing chunks stay queryable). |
| 4 | Documentation questions returned **"No live FlytBase documentation or release-note evidence"**. | `FlytBaseWebRetriever` was built with an empty `search_urls`, so it never fetched anything. It now resolves URLs from FlytBase's official **`llms.txt`** index and fetches the matching `docs.flytbase.com` / `releases.flytbase.com` pages. |
| 5 | `/api/chat` **hung for ~5 minutes** on some questions. | The LLM client had no timeout (OpenAI SDK default 600s). Added `timeout=60, max_retries=1` so a stalled model call fails fast with a graceful message. |
| 6 | Stale backend processes squatted on `:8000` after edits/reloads. | Killed the orphaned processes; one clean instance bound successfully. |

## Backend

FastAPI service answering questions from the local `se-dataset/` corpus and **live**
FlytBase documentation/release notes, with source citations.

### Run

    cd backend
    python -m venv .venv && .venv\Scripts\activate
    pip install -r requirements.txt
    uvicorn app.main:app --host 0.0.0.0 --port 8000

### Endpoints

- `GET  /health` — liveness probe.
- `POST /api/chat` — `{question}` -> `ChatResponse` (answer, route, insufficiencies, citations).
- `POST /api/corpus/sync` — incremental sync of `se-dataset/` into the vector store -> `SyncSummary`.

### Demo verification

    cd backend && pytest tests/ -q
    python ../scripts/verify_backend_demo.py

The unit suite is network-free (injected fakes / MockTransport). The demo
script reports real citation categories or a clear live-network failure.
