from pathlib import Path


def _ui_polish() -> str:
    root = Path(__file__).resolve().parents[1]
    return (root / "app" / "dashboard" / "ui_polish.js").read_text(encoding="utf-8")


def test_ai_provider_connections_are_compact_four_column_cards_with_one_configure_action():
    js = _ui_polish()
    assert "grid-template-columns:repeat(4,minmax(0,1fr))" in js
    assert "AI Provider Connections" in js
    assert "Configure Provider" in js
    assert "Configure provider</button>" not in js
    assert "Manage AI provider connection status and configuration." in js


def test_research_sources_use_multi_checkbox_dropdown_and_keep_selected_values():
    js = _ui_polish()
    assert "source-multi-menu" in js
    assert "type='checkbox'" in js
    assert "select.classList.add('source-multi-native')" in js
    assert "selectedOptions" not in js
    assert "values.rs" in js


def test_research_results_are_persisted_across_dashboard_view_changes():
    js = _ui_polish()
    assert "__researchState" in js
    assert "sessionStorage.setItem('aiSocialResearchState'" in js
    assert "sessionStorage.getItem('aiSocialResearchState'" in js
    assert "Previous research results are preserved" in js
    assert "resultsHTML" in js


def test_research_results_are_constrained_to_the_parent_grid():
    js = _ui_polish()
    for rule in (
        ".research-results{min-width:0;max-width:100%;overflow:hidden}",
        ".research-results>.panel{min-width:0;max-width:100%;overflow:hidden}",
        ".research-results .item-title{min-width:0;overflow-wrap:anywhere;word-break:break-word}",
    ):
        assert rule in js
