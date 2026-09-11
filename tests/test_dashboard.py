def test_dashboard_module_imports():
    from app.dashboard import dashboard_page, require_dashboard_session
    assert callable(dashboard_page)
    assert callable(require_dashboard_session)
