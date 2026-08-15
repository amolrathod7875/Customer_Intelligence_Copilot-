from dataclasses import dataclass
from os import getenv
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    llm_base_url: str | None
    llm_api_key: str | None
    llm_model: str | None
    corpus_dir: Path
    chroma_dir: Path
    frontend_origin: str

    @classmethod
    def from_environment(cls) -> "Settings":
        return cls(
            llm_base_url=getenv("LLM_BASE_URL") or None,
            llm_api_key=getenv("LLM_API_KEY") or None,
            llm_model=getenv("LLM_MODEL") or None,
            corpus_dir=Path(getenv("CORPUS_DIR", "../se-dataset")),
            chroma_dir=Path(getenv("CHROMA_DIR", ".data/chroma")),
            frontend_origin=getenv("FRONTEND_ORIGIN", "http://localhost:5173"),
        )
