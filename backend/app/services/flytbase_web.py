from __future__ import annotations

from collections.abc import Callable
from hashlib import sha256
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from app.models.schemas import Citation, SourceType

_ALLOWED_HOSTS = {"docs.flytbase.com", "releases.flytbase.com"}


class FlytBaseWebRetriever:
    def __init__(
        self,
        client: httpx.Client | None = None,
        search_urls: Callable[[str], list[str]] | None = None,
        max_response_bytes: int = 1_000_000,
    ) -> None:
        self._client = client or httpx.Client(
            timeout=10.0,
            follow_redirects=True,
            headers={"User-Agent": "Customer-Intelligence-Copilot/0.1"},
        )
        self._search_urls = search_urls or (lambda _: [])
        self._max_response_bytes = max_response_bytes

    def fetch(self, url: str) -> Citation | None:
        if not _is_allowed(url):
            return None
        try:
            response = self._client.get(url)
            response.raise_for_status()
        except httpx.HTTPError:
            return None
        if len(response.content) > self._max_response_bytes:
            return None
        soup = BeautifulSoup(response.text, "html.parser")
        title = (soup.title.string if soup.title and soup.title.string else "FlytBase documentation").strip()
        content = soup.find("main") or soup.find("article") or soup.body
        excerpt = content.get_text(" ", strip=True) if content else ""
        if not excerpt:
            return None
        source_type = SourceType.DOCUMENTATION if urlparse(url).hostname == "docs.flytbase.com" else SourceType.RELEASE_NOTE
        return Citation(
            id=f"web:{sha256(url.encode()).hexdigest()}",
            source_type=source_type,
            title=title,
            excerpt=excerpt[:4_000],
            url=url,
        )

    def search(self, query: str, limit: int = 5) -> list[Citation]:
        evidence: list[Citation] = []
        for url in self._search_urls(query):
            citation = self.fetch(url)
            if citation is not None:
                evidence.append(citation)
            if len(evidence) >= limit:
                break
        return evidence


def _is_allowed(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme == "https" and parsed.hostname in _ALLOWED_HOSTS
