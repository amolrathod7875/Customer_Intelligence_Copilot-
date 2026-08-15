import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import build_container, router
from app.core.config import Settings


def _index_corpus(container, corpus_dir) -> None:
    # Run indexing off the startup path: Qdrant Cloud Inference makes the first
    # sync slow, and blocking the lifespan keeps the port closed (health down).
    try:
        container.corpus_sync.sync(corpus_dir)
    except Exception as exc:  # never crash the server over indexing
        print(f"[startup] corpus sync failed: {exc}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Only build the container if one was not injected (e.g. by tests).
    if getattr(app.state, "container", None) is None:
        settings = Settings.from_environment()
        container = build_container(settings)
        threading.Thread(
            target=_index_corpus, args=(container, settings.corpus_dir), daemon=True
        ).start()
        app.state.container = container
    yield


def create_app() -> FastAPI:
    settings = Settings.from_environment()
    app = FastAPI(title="Customer Intelligence Copilot", lifespan=lifespan)

    # CORS restricted to local dev origins (localhost / 127.0.0.1, any port).
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
