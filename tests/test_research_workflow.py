from pathlib import Path

def _root() -> Path: return Path(__file__).resolve().parents[1]
def test_research_passes_query_to_all_configured_sources():
    search=(_root()/"app/research/search.py").read_text(encoding="utf-8");assert "fetch_reddit(limit=settings.research_limit_per_source" in search;assert "query=query" in search;assert "fetch_stackoverflow(limit=settings.research_limit_per_source" in search;assert "fetch_rss(settings.rss_feed_list, limit=settings.research_limit_per_source, query=query)" in search;assert '"source_counts": source_counts' in search
def test_research_adapters_support_real_query_search():
    reddit=(_root()/"app/research/reddit.py").read_text(encoding="utf-8");stackoverflow=(_root()/"app/research/stackoverflow.py").read_text(encoding="utf-8");rss=(_root()/"app/research/rss.py").read_text(encoding="utf-8");assert "search.json" in reddit and '"q": query.strip()' in reddit;assert 'API = "https://api.stackexchange.com/2.3/search/advanced"' in stackoverflow;assert 'params["q"] = query.strip()' in stackoverflow;assert "query: str = \"\"" in rss;assert "haystack" in rss
def test_workflow_ui_has_sorting_persistence_and_sequenced_steps():
    js=(_root()/"app/dashboard/workflow_polish.js").read_text(encoding="utf-8")
    for value in ("Priority","Relevance","Trend","Engagement","Source","Title"):assert value in js
    assert "sessionStorage.setItem(stateKey" in js;assert "window.go=function(v){saveResearch();return originalGo(v)}" in js;assert "Configure" in js and "AI Analysis" in js and "Create Content" in js;assert "Approval" in js and "Schedule" in js and "Publish" in js
def test_dashboard_loads_workflow_ui_after_existing_dashboard_layers():
    dashboard=(_root()/"app/dashboard.py").read_text(encoding="utf-8")
    assert 'workflow_ui = (DASHBOARD_DIR / "workflow_polish.js").read_text' in dashboard
    assert "workflow_polish.js" in dashboard and "full_ui.js" in dashboard and "ui_polish.js" in dashboard
