from app.services.corpus_sync import CorpusSync
from app.services.vector_store import InMemoryVectorStore


def write_issues(path, rows):
    header = (
        "# Issues\n\n"
        "| ID | Account | Category | Status | Title |\n"
        "|---|---|---|---|---|\n"
    )
    path.write_text(header + "\n".join(rows) + "\n", encoding="utf-8")


def test_sync_upserts_changed_record_and_removes_deleted_record(tmp_path):
    source = tmp_path / "issues.md"
    write_issues(
        source,
        [
            "| ISS-1 | Acme | Bug | Open | First issue |",
            "| ISS-2 | Beta | Bug | Open | Removed issue |",
        ],
    )
    store = InMemoryVectorStore()
    sync = CorpusSync(store=store)

    first = sync.sync(tmp_path)

    assert (first.scanned, first.created, first.updated, first.deleted, first.unchanged) == (2, 2, 0, 0, 0)

    write_issues(source, ["| ISS-1 | Acme | Bug | Closed | First issue |"]) 
    second = sync.sync(tmp_path)

    assert (second.scanned, second.created, second.updated, second.deleted, second.unchanged) == (1, 0, 1, 1, 0)
    assert len(store.records()) == 1
