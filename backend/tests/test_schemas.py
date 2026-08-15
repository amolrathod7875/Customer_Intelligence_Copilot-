import pytest
from pydantic import ValidationError

from app.models.schemas import Citation, SourceType


def test_documentation_citation_requires_allowed_https_url():
    with pytest.raises(ValidationError):
        Citation(
            id="web:1",
            source_type=SourceType.DOCUMENTATION,
            title="Mission Planning",
            excerpt="text",
            url=None,
        )


def test_customer_citation_allows_no_url():
    citation = Citation(
        id="customer:issues:ISS-1",
        source_type=SourceType.CUSTOMER_RECORD,
        title="ISS-1",
        excerpt="text",
        url=None,
    )

    assert citation.url is None
