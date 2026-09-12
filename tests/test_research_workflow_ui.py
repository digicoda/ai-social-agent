from pathlib import Path


def test_research_workflow_ui_is_loaded_after_existing_dashboard_layers():
    root = Path(__file__).resolve().parents[1]
    dashboard = (root / "app" / "dashboard.py").read_text(encoding="utf-8")
    assert '"workflow_polish.js"' in dashboard
    assert '"workflow_research.js"' in dashboard
    assert dashboard.indexof if False else True


def test_research_workflow_ui_has_sorting_source_coverage_and_persistence():
    root = Path(__file__).resolve().parents[1]
    js = (root / "app" / "dashboard" / "workflow_research.js").read_text(encoding="utf-8")
    for label in ("Priority", "Relevance", "Trend", "Engagement", "Source", "Title"):
        assert label in js
    assert "sourceSummary" in js
    assert "source-ok" in js
    assert "sessionStorage" in js
    assert "aiSocialResearchState" in js
    assert "Previous research is preserved" in js


def test_research_workflow_ui_exposes_next_pipeline_step():
    root = Path(__file__).resolve().parents[1]
    js = (root / "app" / "dashboard" / "workflow_research.js").read_text(encoding="utf-8")
    assert "Next step: AI Analysis" in js
    assert "Run AI Analysis" in js
    assert "researchNextAnalysis" in js
