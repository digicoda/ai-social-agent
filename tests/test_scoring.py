from datetime import datetime, timedelta, timezone

from app.schemas import Problem
from app.scoring import score_problem


def test_score_rewards_relevant_technical_problem():
    problem = Problem(
        source="stackoverflow",
        external_id="1",
        title="WooCommerce checkout PHP error after plugin update",
        url="https://example.com/q/1",
        body="My WordPress checkout is broken and throws an API error.",
        tags=["php", "wordpress", "woocommerce"],
        score=12,
        comments=5,
    )
    assert score_problem(problem) >= 50


def test_score_rewards_recent_problem_more_than_old_problem():
    recent = Problem(
        source="github",
        external_id="1",
        title="WordPress API error",
        url="https://example.com/1",
        published_at=datetime.now(timezone.utc) - timedelta(hours=12),
    )
    old = Problem(
        source="github",
        external_id="2",
        title="WordPress API error",
        url="https://example.com/2",
        published_at=datetime.now(timezone.utc) - timedelta(days=120),
    )
    assert score_problem(recent) > score_problem(old)
