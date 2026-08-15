from enum import Enum
from typing import Any
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator, model_validator


class SourceType(str, Enum):
    CUSTOMER_RECORD = "customer_record"
    DOCUMENTATION = "documentation"
    RELEASE_NOTE = "release_note"


class Citation(BaseModel):
    id: str = Field(min_length=1)
    source_type: SourceType
    title: str = Field(min_length=1)
    excerpt: str = Field(min_length=1)
    url: str | None = None

    @field_validator("url")
    @classmethod
    def url_must_be_allowed_https_url(cls, value: str | None) -> str | None:
        if value is None:
            return value
        parsed = urlparse(value)
        if parsed.scheme != "https" or parsed.hostname not in {
            "docs.flytbase.com",
            "releases.flytbase.com",
        }:
            raise ValueError("citation URL must use HTTPS on an allowed FlytBase host")
        return value

    @model_validator(mode="after")
    def web_citations_require_a_url(self) -> "Citation":
        if self.source_type is not SourceType.CUSTOMER_RECORD and self.url is None:
            raise ValueError("web citations require an HTTPS FlytBase URL")
        return self


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4_000)


class ChatResponse(BaseModel):
    answer: str
    route: str
    insufficiencies: list[str] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)


class SyncSummary(BaseModel):
    scanned: int = Field(ge=0)
    created: int = Field(ge=0)
    updated: int = Field(ge=0)
    deleted: int = Field(ge=0)
    unchanged: int = Field(ge=0)
    synced_at: str


class CustomerRecord(BaseModel):
    id: str = Field(min_length=1)
    record_type: str = Field(min_length=1)
    source_file: str = Field(min_length=1)
    text: str = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)
