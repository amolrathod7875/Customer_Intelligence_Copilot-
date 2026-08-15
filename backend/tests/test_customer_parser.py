from pathlib import Path

from app.services.customer_parser import parse_customer_file


FIXTURE = Path("tests/fixtures/customer/feature_requests.md")


def test_parser_keeps_record_provenance_and_deterministic_id():
    records = parse_customer_file(FIXTURE)

    assert len(records) == 1
    assert records[0].source_file == "feature_requests.md"
    assert records[0].record_type == "feature_request"
    assert records[0].id.startswith("feature_requests:")
    assert "Acme Robotics" in records[0].text


def test_parser_ignores_headers_and_blank_rows():
    records = parse_customer_file(FIXTURE)

    assert all(record.text.strip() for record in records)
    assert not any("---" in record.text for record in records)


def test_parser_splits_meeting_headings_into_provenanced_records():
    records = parse_customer_file(Path("tests/fixtures/customer/meeting_notes.md"))

    assert len(records) == 1
    assert records[0].id == "meeting_notes:MTG-0001"
    assert records[0].metadata["Account"] == "Acme Robotics"
