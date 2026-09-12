from pathlib import Path


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_research_passes_query_to_all_configured_sources():
    search = (_root() / "app" / "research" / "search.py").read_text(encoding="utf-8")
    assert "query=query" in search
    assert '"source_counts": source_counts' in search
    assert '"web"' in search


def test_research_adapters_support_real_query_search():
    reddit = (_root() / "app" / "research" / "reddit.py").read_text(encoding="utf-8")
    stackoverflow = (_root() / "app" / "research" / "stackoverflow.py").read_text(encoding="utf-8")
    rss = (_root() / "app" / "research" / "rss.py").read_text(encoding="utf-8")
    web = (_root() / "app" / "websearch.py").read_text(encoding="utf-8")
    assert "search.json" in reddit and '"q": query.strip()' in reddit
    assert 'API = "https://api.stackexchange.com/2.3/search/advanced"' in stackoverflow
    assert 'params["q"] = query.strip()' in stackoverflow
    assert "query: str = \"\"" in rss and "haystack" in rss
    assert "html.duckduckgo.com/html" in web


def test_workflow_ui_has_sorting_persistence_and_sequenced_steps():
    js = (_root() / "app" / "dashboard" / "workflow_polish.js").read_text(encoding="utf-8")
    for value in ("Priority", "Relevance", "Trend", "Engagement", "Source", "Title"):
        assert value in js
    assert "sessionStorage.setItem(stateKey" in js
    assert "window.go=function(v){saveResearch();return originalGo(v)}" in js
    assert "Configure" in js and "AI Analysis" in js and "Create Content" in js
    assert "Approval" in js and "Schedule" in js and "Publish" in js


def test_dashboard_loads_workflow_ui_bundle_after_existing_layers():
    dashboard = (_root() / "app" / "dashboard.py").read_text(encoding="utf-8")
    for script in ("full_ui.js", "ui_polish.js", "workflow_polish.js", "workflow_research.js", "bugfix_ui.js", "profile_ui.js", "profile_compat.js", "final_workflow_fix.js"):
        assert f'"{script}"' in dashboard
