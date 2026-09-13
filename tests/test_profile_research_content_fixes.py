from types import SimpleNamespace


def test_web_search_accepts_website_context():
    from app.websearch import _domain
    assert _domain("https://www.example.com/path") == "example.com"


def test_auto_profile_sources_include_marketing_sources():
    # Keep this mapping aligned with the dashboard/profile automation policy.
    categories = {"marketing", "seo"}
    sources = {"web", "reddit", "rss"}
    assert {"web", "reddit", "rss"}.issubset(sources)
    assert "github" not in sources
    assert categories


def test_content_analysis_legacy_object_is_normalized():
    import app.content_workflow as workflow

    class FakeClient:
        def analyze(self, problem):
            raise AssertionError("legacy analysis should prevent a second AI analysis")

    original = workflow._content_analysis
    original_create = workflow.create_ai_client
    try:
        analysis = SimpleNamespace(pain_point="p", audience="a", root_cause="r", solution_angle="s")
        workflow._content_analysis = lambda db, problem_id: analysis
        workflow.create_ai_client = lambda settings: FakeClient()
        result = workflow._analyze_if_needed(SimpleNamespace(), object(), 1, object())
        assert result[0] is analysis
        assert result[1] == "create"
    finally:
        workflow._content_analysis = original
        workflow.create_ai_client = original_create
