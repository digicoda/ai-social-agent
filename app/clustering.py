import sqlite3
from dataclasses import dataclass

from .dedup import similarity
from .schemas import Problem


@dataclass(slots=True)
class ClusterResult:
    clusters: int = 0
    assignments: int = 0


def _problem_from_row(row: sqlite3.Row) -> Problem:
    return Problem(
        source=row["source"],
        external_id=row["external_id"],
        title=row["title"],
        url=row["url"],
        summary=row["summary"],
        body=row["body"],
        score=int(row["score"]),
        comments=int(row["comments"]),
    )


def cluster_problems(
    connection: sqlite3.Connection,
    *,
    limit: int = 250,
    threshold: float = 0.55,
) -> ClusterResult:
    """Group closely related problems into local SQLite clusters.

    Clusters are rebuilt from the highest-scoring recent problems. This keeps
    the operation deterministic, cheap, and easy to rerun without embeddings.
    """
    rows = connection.execute(
        "SELECT * FROM problems ORDER BY score DESC, discovered_at DESC LIMIT ?",
        (limit,),
    ).fetchall()

    connection.execute("DELETE FROM problem_cluster_members")
    connection.execute("DELETE FROM problem_clusters")

    representatives: list[tuple[int, Problem]] = []
    result = ClusterResult()

    for row in rows:
        problem_id = int(row["id"])
        problem = _problem_from_row(row)
        chosen_cluster: int | None = None
        best_similarity = 0.0

        for cluster_id, representative in representatives:
            score = similarity(problem, representative)
            if score >= threshold and score > best_similarity:
                chosen_cluster = cluster_id
                best_similarity = score

        if chosen_cluster is None:
            cursor = connection.execute(
                "INSERT INTO problem_clusters (representative_problem_id, label) VALUES (?, ?)",
                (problem_id, problem.title[:120]),
            )
            chosen_cluster = int(cursor.lastrowid)
            representatives.append((chosen_cluster, problem))
            result.clusters += 1

        connection.execute(
            "INSERT INTO problem_cluster_members (cluster_id, problem_id, similarity) VALUES (?, ?, ?)",
            (chosen_cluster, problem_id, best_similarity),
        )
        result.assignments += 1

    connection.commit()
    return result
