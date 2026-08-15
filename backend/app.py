"""HF Spaces entrypoint (Gradio SDK).

Hugging Face free Spaces only support the Gradio SDK, but Gradio is built on
FastAPI. We create a minimal `gr.Blocks` (required by the SDK runner) and mount
our existing FastAPI API onto Gradio's underlying FastAPI app, so every
`/api/*` endpoint keeps working without a paid Docker Space.
"""

import os
import gradio as gr

from app.api.routes import build_container, router
from app.core.config import Settings


def _resolve_corpus_dir() -> None:
    """Pick a corpus path that exists: prefer the Space-secret CORPUS_DIR,
    then a repo-local ``se-dataset`` directory, then the dev default."""
    if os.getenv("CORPUS_DIR"):
        return
    for candidate in ("se-dataset", "../se-dataset"):
        if os.path.isdir(candidate):
            os.environ["CORPUS_DIR"] = candidate
            return


def _bootstrap() -> object:
    """Build the service container and index the corpus (best effort)."""
    _resolve_corpus_dir()
    settings = Settings.from_environment()
    container = build_container(settings)
    try:
        container.corpus_sync.sync(settings.corpus_dir)
    except Exception as exc:  # Don't hard-crash the Space if the corpus is absent.
        print(f"[startup] corpus sync skipped: {exc}")
    return container


container = _bootstrap()

demo = gr.Blocks(title="Customer Intelligence Copilot")
demo.app.state.container = container
demo.app.include_router(router)


@demo.app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


# CORS. Gradio already allows all origins, but we make the frontend origin
# explicit and configurable via the FRONTEND_ORIGIN Space secret.
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

_frontend = os.getenv("FRONTEND_ORIGIN", "*")
_origins = ["*"] if _frontend == "*" else [o.strip() for o in _frontend.split(",")]
demo.app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=int(os.getenv("PORT", "7860")))
