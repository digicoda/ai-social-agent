from pathlib import Path

import pytest

from app.approval import history, queue, set_decision
from app.config import Settings
from app.database import connect, save_draft


def _settings(tmp_path: Path) -> Settings:
    return Settings(database_url=f"sqlite:///{tmp_path / 'approval.db'}")


def _draft(settings: Settings) -> int:
    connection = connect(settings.database_url)
    try:
        connection.execute(
            "INSERT INTO problems (source, external_id, title, url, discovered_at, fingerprint) VALUES (?, ?, ?, ?, ?, ?)",
            ("test", "task7", "Approval test", "https://example.com/task7", "2026-01-01T00:00:00+00:00", "task7-fingerprint"),
        )
        problem_id = int(connection.execute("SELECT last_insert_rowid()").fetchone()[0])
        return save_draft(connection, problem_id, "generic", "Draft", "Body", ["test"], "Discuss?", 90)
    finally:
        connection.close()


def test_human_approval_requires_explicit_decision(tmp_path: Path):
    settings = _settings(tmp_path)
    draft_id = _draft(settings)
    assert queue(settings)[0]["status"] == "pending_approval"
    assert history(settings, draft_id) == []
    with pytest.raises(ValueError, match="rejection reason"):
        set_decision(settings, draft_id, "rejected")


def test_approval_is_terminal_and_audited(tmp_path: Path):
    settings = _settings(tmp_path)
    draft_id = _draft(settings)
    assert set_decision(settings, draft_id, "approved") is True
    assert queue(settings, status="approved")[0]["id"] == draft_id
    audit = history(settings, draft_id)
    assert len(audit) == 1
    assert audit[0]["from_status"] == "pending_approval"
    assert audit[0]["to_status"] == "approved"
    with pytest.raises(ValueError, match="only pending_approval"):
        set_decision(settings, draft_id, "rejected", "Too risky")
    assert len(history(settings, draft_id)) == 1


def test_rejection_reason_is_persisted(tmp_path: Path):
    settings = _settings(tmp_path)
    draft_id = _draft(settings)
    assert set_decision(settings, draft_id, "rejected", "Needs factual review") is True
    item = queue(settings, status="rejected")[0]
    assert item["rejection_reason"] == "Needs factual review"
    audit = history(settings, draft_id)[0]
    assert audit["action"] == "rejected"
    assert audit["reason"] == "Needs factual review"
