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
