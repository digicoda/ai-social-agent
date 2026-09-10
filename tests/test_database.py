from app.database import connect, save_problem
from app.schemas import Problem


def test_duplicate_fingerprint_is_ignored(tmp_path):
    db = tmp_path / "test.db"
    connection = connect(f"sqlite:///{db}")
    first = Problem(source="rss", external_id="a", title="Same technical problem", url="https://a.test")
    second = Problem(source="reddit", external_id="b", title="Same technical problem", url="https://b.test")
    assert save_problem(connection, first) is True
    assert save_problem(connection, second) is False
    assert connection.execute("SELECT COUNT(*) FROM problems").fetchone()[0] == 1
    connection.close()
