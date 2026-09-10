import json
import sqlite3

import httpx
import pytest

from app.ai import GeminiClient, GeminiError
from app.analysis import decision_for_score
from app.clustering import cluster_problems
from app.database import connect, save_problem
from app.dedup import find_cross_source_duplicate, similarity
from app.schemas import Problem


def test_decision_thresholds() -> None:
    assert decision_for_score(85) == "auto_publish_candidate"
    assert decision_for_score(70) == "approval_queue"
    assert decision_for_score(69) == "discard"


def test_gemini_client_requires_key() -> None:
    with pytest.raises(GeminiError):
        GeminiClient("")


def test_gemini_client_parses_structured_json(monkeypatch: pytest.MonkeyPatch) -> None:
    response = httpx.Response(
        200,
        json={
            "candidates": [{
                "content": {
                    "parts": [{"text": json.dumps({
                        "pain_point": "A failing integration",
                        "audience": "Developers",
                        "root_cause": "Bad credentials",
                        "solution_angle": "Show a safe debugging workflow",
                        "hooks": ["Why did it fail?", "Check this first", "A safer fix"],
                        "risks": ["Do not expose secrets"],
                        "confidence": 92,
                    })}]
                }
            }]
        },
        request=httpx.Request("POST", "https://example.test"),
    )

    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: response)
    analysis = GeminiClient("test-key").analyze(
        Problem(source="github", external_id="1", title="Integration fails", url="https://example.test")
    )
    assert analysis.confidence == 92
    assert len(analysis.hooks) == 3


def test_similarity_detects_same_problem_across_sources() -> None:
    left = Problem(
        source="github",
        external_id="1",
        title="WooCommerce checkout fails after plugin update",
        url="https://github.example/1",
        body="Checkout returns an error after updating the plugin.",
    )
    right = Problem(
        source="reddit",
        external_id="2",
        title="Checkout error after WooCommerce plugin update",
        url="https://reddit.example/2",
        body="My WooCommerce checkout started failing after a plugin update.",
    )
    assert similarity(left, right) >= 0.55


def test_cross_source_duplicate_lookup(tmp_path) -> None:
    connection = connect(f"sqlite:///{tmp_path / 'test.db'}")
    try:
        original = Problem(
            source="github",
            external_id="1",
            title="WooCommerce checkout fails after plugin update",
            url="https://github.example/1",
            body="Checkout returns an error after updating the plugin.",
        )
        incoming = Problem(
            source="reddit",
            external_id="2",
            title="Checkout error after WooCommerce plugin update",
            url="https://reddit.example/2",
            body="My WooCommerce checkout started failing after a plugin update.",
        )
        save_problem(connection, original)
        match = find_cross_source_duplicate(connection, incoming, threshold=0.55)
        assert match is not None
        assert match[0] == 1
    finally:
        connection.close()


def test_clustering_groups_related_problems(tmp_path) -> None:
    connection = connect(f"sqlite:///{tmp_path / 'test.db'}")
    try:
        save_problem(connection, Problem(
            source="github", external_id="1",
            title="WooCommerce checkout fails after plugin update",
            url="https://example.test/1",
            body="Checkout returns an error after updating the plugin.", score=90,
        ))
        save_problem(connection, Problem(
            source="reddit", external_id="2",
            title="Checkout error after WooCommerce plugin update",
            url="https://example.test/2",
            body="My WooCommerce checkout started failing after a plugin update.", score=80,
        ))
        save_problem(connection, Problem(
            source="stackoverflow", external_id="3",
            title="PHP array merge returns unexpected values",
            url="https://example.test/3", score=70,
        ))
        result = cluster_problems(connection, threshold=0.55)
        assert result.assignments == 3
        assert result.clusters == 2
        assert connection.execute("SELECT COUNT(*) FROM problem_cluster_members").fetchone()[0] == 3
    finally:
        connection.close()
