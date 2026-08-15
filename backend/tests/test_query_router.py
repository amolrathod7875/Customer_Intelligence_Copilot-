from app.services.query_router import EvidenceRoute, route_question


def test_account_bug_question_routes_to_customer_only():
    assert route_question("What open bugs does Acme have?") == EvidenceRoute.CUSTOMER


def test_feature_support_question_routes_to_both_sources():
    assert route_question("Which customers requested geofencing and is it supported?") == EvidenceRoute.BOTH


def test_docs_question_routes_to_documentation_only():
    assert route_question("How does mission planning work in the docs?") == EvidenceRoute.DOCUMENTATION
