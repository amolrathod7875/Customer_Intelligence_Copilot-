from enum import Enum


class EvidenceRoute(str, Enum):
    CUSTOMER = "customer"
    DOCUMENTATION = "documentation"
    BOTH = "both"


_CUSTOMER_TERMS = {"account", "accounts", "issue", "issues", "bug", "bugs", "task", "tasks", "meeting", "meetings", "request", "requested", "ticket", "tickets", "customer", "customers"}
_WEB_TERMS = {"docs", "documentation", "release", "released", "shipped", "supported", "support", "capability", "capabilities", "how does", "how do"}


def route_question(question: str) -> EvidenceRoute:
    lowered = question.lower()
    customer = any(term in lowered for term in _CUSTOMER_TERMS)
    web = any(term in lowered for term in _WEB_TERMS)
    if customer and web:
        return EvidenceRoute.BOTH
    if web:
        return EvidenceRoute.DOCUMENTATION
    return EvidenceRoute.CUSTOMER
