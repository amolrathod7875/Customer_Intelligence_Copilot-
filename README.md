# Customer_Intelligence_Copilot-

## Backend

FastAPI service answering questions from the local `se-dataset/` corpus and
**live** FlytBase documentation/release notes, with source citations.

### Run

    cd backend
    python -m venv .venv && .venv\Scripts\activate
    pip install -r requirements.txt
    uvicorn app.main:app --reload

### Endpoints

- `GET  /health` — liveness probe.
- `POST /api/chat` — `{question}` -> `ChatResponse` (answer, route, insufficiencies, citations).
- `POST /api/corpus/sync` — incremental sync of `se-dataset/` into the vector store -> `SyncSummary`.

### Demo verification

    cd backend && pytest tests/ -q
    python ../scripts/verify_backend_demo.py

The unit suite is network-free (injected fakes / MockTransport). The demo
script reports real citation categories or a clear live-network failure.
