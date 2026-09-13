from app.version import APP_NAME, APP_VERSION, FEATURES, RELEASE_TAG


def test_runtime_version_metadata_is_consistent():
    assert APP_NAME == "AI Social Agent"
    assert APP_VERSION == "1.3.2"
    assert RELEASE_TAG == "v1.3.2"
    assert FEATURES
