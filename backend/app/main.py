from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import build_container, router
from app.core.config import Settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Only build the container if one was not injected (e.g. by tests).
    if getattr(app.state, "container", None) is None:
        settings = Settings.from_environment()
        container = build_container(settings)
        container.corpus_sync.sync(settings.corpus_dir)
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
