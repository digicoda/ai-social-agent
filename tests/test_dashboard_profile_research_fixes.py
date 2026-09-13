from app.profiles import DEFAULT_PROFILE, _merged
from app.research.search import search_options


def test_profile_supports_website_auto_resources_and_multiple_publishers():
    cfg = _merged({
        "website_url": "https://example.com",
        "source_mode": "auto",
        "categories": ["marketing"],
        "publish_providers": ["linkedin", "linkedin"],
        "daily_time": "13:45",
    })
    assert cfg["website_url"] == "https://example.com"
    assert cfg["source_mode"] == "auto"
    assert cfg["publish_providers"] == ["linkedin"]
    assert cfg["daily_time"] == "13:45"


def test_profile_defaults_include_all_first_class_research_sources():
    assert set(DEFAULT_PROFILE["sources"]) == {"github", "reddit", "stackoverflow", "rss", "web"}


def test_research_options_expose_all_sources():
    ids = {item["id"] for item in search_options()["sources"]}
    assert ids == {"github", "reddit", "stackoverflow", "rss", "web"}
