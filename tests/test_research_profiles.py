from pathlib import Path

import pytest

from app.research.profiles import delete_profile, get_profile, list_profiles, save_profile


def db_url(tmp_path: Path) -> str:
    return f"sqlite:///{tmp_path / 'profiles.db'}"


def test_only_name_and_main_category_are_required(tmp_path: Path):
    url = db_url(tmp_path)
    item = save_profile(url, {"name": "Morning Tech", "main_category": "Technology"})
    assert item["name"] == "Morning Tech"
    assert item["main_category"] == "Technology"
    assert item["posting_times"] == ["09:00", "18:00"]
    assert item["sources"]


def test_multiple_profiles_have_independent_schedules(tmp_path: Path):
    url = db_url(tmp_path)
    first = save_profile(url, {"name": "Morning", "main_category": "Education", "posting_times": ["08:00"]})
    second = save_profile(url, {"name": "Dinner", "main_category": "Food", "posting_times": ["19:30", "21:00"]})
    assert first["id"] != second["id"]
    assert get_profile(url, first["id"])["posting_times"] == ["08:00"]
    assert get_profile(url, second["id"])["posting_times"] == ["19:30", "21:00"]
    assert len(list_profiles(url)) == 2


def test_missing_required_fields_rejected(tmp_path: Path):
    with pytest.raises(ValueError):
        save_profile(db_url(tmp_path), {"name": "No Category"})


def test_delete_profile(tmp_path: Path):
    url = db_url(tmp_path)
    item = save_profile(url, {"name": "Temp", "main_category": "Business"})
    assert delete_profile(url, item["id"])
    assert get_profile(url, item["id"]) is None
