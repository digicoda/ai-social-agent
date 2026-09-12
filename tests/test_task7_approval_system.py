from pathlib import Path

import pytest

from app.approval import history, queue, set_decision
from app.config import Settings
from app.database import connect, save_draft
from app.publish_service import publish_draft
from app.publishing import PublishingError


def settings(tmp_path: Path) -> Settings:
    return Settings(database_url=f"sqlite:///{tmp_path / 'approval.db'}")


def draft(s: Settings) -> int:
    db = connect(s.database_url)
    try:
        db.execute("INSERT INTO problems (source, external_id, title, url, discovered_at, fingerprint) VALUES (?, ?, ?, ?, ?, ?)", ("test", "task7", "Approval test", "https://example.com/task7", "2026-01-01T00:00:00+00:00", "task7-fingerprint"))
        problem_id = int(db.execute("SELECT last_insert_rowid()").fetchone()[0])
        return save_draft(db, problem_id, "generic", "Draft", "Body", ["test"], "Discuss?", 90)
    finally:
        db.close()


def test_human_approval_stays_pending_until_decision(tmp_path: Path):
    s = settings(tmp_path); draft_id = draft(s)
    assert queue(s)[0]["status"] == "pending_approval"
    assert history(s, draft_id) == []
    with pytest.raises(ValueError, match="rejection reason"):
        set_decision(s, draft_id, "rejected")
    assert queue(s)[0]["status"] == "pending_approval"


def test_approval_is_atomic_audited_and_terminal(tmp_path: Path):
    s = settings(tmp_path); draft_id = draft(s)
    assert set_decision(s, draft_id, "approved") is True
    assert queue(s, status="approved")[0]["id"] == draft_id
    audit = history(s, draft_id)
    assert audit[0]["from_status"] == "pending_approval"
    assert audit[0]["to_status"] == "approved"
    with pytest.raises(ValueError, match="only pending_approval"):
        set_decision(s, draft_id, "rejected", "Too risky")
    assert len(history(s, draft_id)) == 1


def test_rejection_reason_is_persisted(tmp_path: Path):
    s = settings(tmp_path); draft_id = draft(s)
    assert set_decision(s, draft_id, "rejected", "Needs factual review") is True
    assert queue(s, status="rejected")[0]["rejection_reason"] == "Needs factual review"
    assert history(s, draft_id)[0]["reason"] == "Needs factual review"


def test_pending_draft_cannot_publish(tmp_path: Path):
    s = settings(tmp_path); draft_id = draft(s)
    with pytest.raises(PublishingError, match="only approved drafts"):
        publish_draft(s, draft_id, "linkedin")
    assert queue(s)[0]["status"] == "pending_approval"
