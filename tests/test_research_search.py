from datetime import datetime, timezone, timedelta

from app.research.search import _classify, _within_date, search_options
from app.schemas import Problem


def test_classify_problem_and_category():
    category, intent = _classify("WordPress update causes a fatal error and the site is broken")
    assert category == "wordpress"
    assert intent == "bug"


def test_classify_question():
    category, intent = _classify("How do I connect an API to my ecommerce store?")
    assert category in {"development", "ecommerce"}
    assert intent == "question"


def test_time_filter():
    recent = Problem(source="test", external_id="1", title="x", url="", published_at=datetime.now(timezone.utc) - timedelta(days=2))
    old = Problem(source="test", external_id="2", title="x", url="", published_at=datetime.now(timezone.utc) - timedelta(days=40))
    assert _within_date(recent, 30)
    assert not _within_date(old, 30)


def test_search_options_are_explicit():
    data = search_options()
    assert {x["id"] for x in data["sources"]} >= {"github", "reddit", "stackoverflow", "rss"}
    assert "web" in {x["id"] for x in data["sources"]}
    assert data["modes"] == ["quick", "standard", "deep"]
