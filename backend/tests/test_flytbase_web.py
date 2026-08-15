import httpx

from app.services.flytbase_web import FlytBaseWebRetriever


def test_fetch_turns_live_documentation_html_into_citation():
    transport = httpx.MockTransport(
        lambda _: httpx.Response(200, text="<html><title>Mission Planning</title><main>Supports missions.</main></html>")
    )
    retriever = FlytBaseWebRetriever(client=httpx.Client(transport=transport))

    evidence = retriever.fetch("https://docs.flytbase.com/mission-planning")

    assert evidence is not None
    assert evidence.source_type.value == "documentation"
    assert evidence.title == "Mission Planning"
    assert evidence.url == "https://docs.flytbase.com/mission-planning"


def test_fetch_rejects_off_domain_urls_without_requesting_them():
    retriever = FlytBaseWebRetriever(client=httpx.Client(transport=httpx.MockTransport(lambda _: AssertionError())))

    assert retriever.fetch("https://example.com/not-allowed") is None


def test_fetch_classifies_release_notes():
    transport = httpx.MockTransport(
        lambda _: httpx.Response(200, text="<title>Release 1.0</title><article>Shipped feature.</article>")
    )
    evidence = FlytBaseWebRetriever(client=httpx.Client(transport=transport)).fetch(
        "https://releases.flytbase.com/release-1"
    )

    assert evidence is not None
    assert evidence.source_type.value == "release_note"
