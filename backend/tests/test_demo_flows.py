def test_combined_query_has_customer_and_live_web_citations(api_client):
    # Question deliberately contains both customer ("accounts"/"requested")
    # and web ("supported") signals so it routes to BOTH.
    response = api_client.post(
        "/api/chat",
        json={"question": "Which accounts requested geofencing and is it supported?"},
    )
    assert response.status_code == 200
    types = {c["source_type"] for c in response.json()["citations"]}
    assert "customer_record" in types
    assert types & {"documentation", "release_note"}


def test_customer_only_query_routes_to_customer(api_client):
    response = api_client.post(
        "/api/chat", json={"question": "What open bugs does Acme have?"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["route"] == "customer"
    assert "answer" in body


def test_docs_only_query_has_web_citation(api_client):
    response = api_client.post(
        "/api/chat", json={"question": "Is geofencing supported in the docs?"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["route"] == "documentation"
    assert any(c["source_type"] in ("documentation", "release_note") for c in body["citations"])
