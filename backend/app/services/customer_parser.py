from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import re

from app.models.schemas import CustomerRecord


_RECORD_TYPES = {
    "accounts.md": "account",
    "issues.md": "issue",
    "feature_requests.md": "feature_request",
    "tasks.md": "task",
    "meeting_notes.md": "meeting_note",
}
_TABLE_SEPARATOR = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?\s*$")
_MEETING_HEADING = re.compile(
    r"^##\s+([A-Za-z]+-\d+)\s*:\s*(.+?)\s*$", re.MULTILINE
)


def parse_customer_file(path: Path) -> list[CustomerRecord]:
    """Parse one known corpus file into provenance-preserving records."""
    record_type = _RECORD_TYPES.get(path.name)
    if record_type is None:
        raise ValueError(f"unsupported customer corpus file: {path.name}")

    text = path.read_text(encoding="utf-8")
    if record_type == "meeting_note":
        return _parse_meetings(path.name, record_type, text)
    return _parse_table(path.name, record_type, text)


def parse_customer_directory(directory: Path) -> list[CustomerRecord]:
    records: list[CustomerRecord] = []
    for filename in _RECORD_TYPES:
        path = directory / filename
        if path.exists():
            records.extend(parse_customer_file(path))
    return records


def _parse_table(source_file: str, record_type: str, text: str) -> list[CustomerRecord]:
    lines = text.splitlines()
    header_index = next(
        (index for index, line in enumerate(lines[:-1]) if line.strip().startswith("|") and _TABLE_SEPARATOR.match(lines[index + 1])),
        None,
    )
    if header_index is None:
        return []

    headers = _cells(lines[header_index])
    records: list[CustomerRecord] = []
    for line in lines[header_index + 2 :]:
        if not line.strip().startswith("|"):
            continue
        cells = _cells(line)
        if len(cells) != len(headers) or not any(cells):
            continue
        metadata = dict(zip(headers, cells, strict=True))
        raw = line.strip()
        explicit_id = metadata.get("ID")
        record_id = explicit_id or _stable_hash(raw)
        records.append(
            CustomerRecord(
                id=f"{Path(source_file).stem}:{record_id}",
                record_type=record_type,
                source_file=source_file,
                text=raw,
                metadata=metadata,
            )
        )
    return records


def _parse_meetings(source_file: str, record_type: str, text: str) -> list[CustomerRecord]:
    matches = list(_MEETING_HEADING.finditer(text))
    records: list[CustomerRecord] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        raw = text[match.start() : end].strip()
        if not raw:
            continue
        meeting_id, account = match.groups()
        records.append(
            CustomerRecord(
                id=f"{Path(source_file).stem}:{meeting_id}",
                record_type=record_type,
                source_file=source_file,
                text=raw,
                metadata={"ID": meeting_id, "Account": account},
            )
        )
    return records


def _cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _stable_hash(text: str) -> str:
    normalized = " ".join(text.split())
    return sha256(normalized.encode("utf-8")).hexdigest()
