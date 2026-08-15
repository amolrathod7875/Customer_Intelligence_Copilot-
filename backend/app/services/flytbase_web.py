from __future__ import annotations

from collections.abc import Callable
from hashlib import sha256
import re
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from app.models.schemas import Citation, SourceType

_ALLOWED_HOSTS = {"docs.flytbase.com", "releases.flytbase.com"}

# Official, LLM-oriented documentation indexes published by FlytBase. Each lists
# every doc/release page as `[title](url)` markdown links we can match on.
_CATALOG_URLS = (
    "https://docs.flytbase.com/llms.txt",
    "https://releases.flytbase.com/llms.txt",
)
_LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)")
_STOPWORDS = {
    "how", "does", "flytbase", "the", "a", "an", "is", "are", "what",
    "to", "of", "for", "and", "or", "on", "in", "do", "did", "with", "from",
}


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
        self._search_urls = search_urls or self._default_search_urls
        self._max_response_bytes = max_response_bytes
        self._catalog: list[tuple[str, str]] | None = None

    # ---- URL discovery via the official llms.txt index -------------------
    def _load_catalog(self) -> list[tuple[str, str]]:
        if self._catalog is None:
            links: list[tuple[str, str]] = []
            for catalog_url in _CATALOG_URLS:
                try:
                    resp = self._client.get(catalog_url)
                    resp.raise_for_status()
                except Exception:
                    continue
                for match in _LINK_RE.finditer(resp.text):
                    text, url = match.group(1), match.group(2)
                    if urlparse(url).hostname in _ALLOWED_HOSTS:
                        links.append((text, url))
            self._catalog = links
        return self._catalog

    def _default_search_urls(self, query: str) -> list[str]:
        links = self._load_catalog()
        if not links:
            return []
        terms = {
            t for t in re.findall(r"[a-z0-9]+", query.lower())
            if t not in _STOPWORDS and len(t) > 2
        }
        if not terms:
            return []
        scored: list[tuple[int, str]] = []
        for text, url in links:
            hay = f"{text} {urlparse(url).path}".lower()
            score = sum(1 for t in terms if t in hay)
            if score > 0:
                scored.append((score, url))
        scored.sort(key=lambda item: -item[0])
        if not scored:
            return [u for _, u in links if "planning" in u.lower()][:5]
        # Prefer the rendered HTML page over the raw `.md` source.
        return [u[:-3] if u.endswith(".md") else u for _, u in scored[:8]]

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
