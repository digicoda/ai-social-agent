from datetime import datetime, timezone

from app.profiles import due_profiles, next_profile_run, save_profile, set_profile_enabled


def test_manual_profile_is_not_due(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    db = "sqlite:///./data/master.db"
    profile = save_profile(db, "Manual Brand", {"automation_mode": "manual"})
    assert profile["next_run"] is None
    assert due_profiles(db, datetime(2026, 9, 13, 12, tzinfo=timezone.utc)) == []


def test_auto_profile_gets_daily_next_run_and_is_due(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    db = "sqlite:///./data/master.db"
    profile = save_profile(db, "Auto Brand", {"automation_mode": "auto", "daily_time": "09:30", "timezone": "Asia/Karachi"})
    assert profile["next_run"] is not None
    due = due_profiles(db, datetime(2026, 9, 13, 4, 31, tzinfo=timezone.utc))
    assert [p["id"] for p in due] == [profile["id"]]
    assert due[0]["config"]["daily_time"] == "09:30"


def test_automation_toggle_clears_and_restores_schedule(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    db = "sqlite:///./data/master.db"
    profile = save_profile(db, "Toggle Brand", {"automation_mode": "auto", "daily_time": "10:00", "timezone": "UTC"})
    disabled = set_profile_enabled(db, profile["id"], False)
    assert disabled["enabled"] is False
    assert disabled["next_run"] is None
    assert due_profiles(db, datetime(2026, 9, 13, 23, tzinfo=timezone.utc)) == []
    enabled = set_profile_enabled(db, profile["id"], True)
    assert enabled["enabled"] is True
    assert enabled["next_run"] is not None


def test_daily_schedule_uses_profile_timezone(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    profile = {"config": {"daily_time": "09:00", "timezone": "Asia/Karachi"}}
    run_at = next_profile_run(profile, datetime(2026, 9, 13, 2, 0, tzinfo=timezone.utc))
    assert run_at.startswith("2026-09-13T04:00:00")
