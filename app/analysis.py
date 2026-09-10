from dataclasses import dataclass

from .ai import GeminiClient, ProblemAnalysis
from .config import Settings
from .database import connect, list_problems, save_analysis


@dataclass(slots=True)
class AnalysisResult:
    analyzed: int = 0
    auto_publish_candidates: int = 0
    approval_queue: int = 0
    discarded: int = 0
    failed: int = 0


def decision_for_score(score: int) -> str:
    if score >= 85:
        return "auto_publish_candidate"
    if score >= 70:
        return "approval_queue"
    return "discard"


def run_analysis(settings: Settings, limit: int = 25) -> AnalysisResult:
    result = AnalysisResult()
    client = GeminiClient(
        settings.gemini_api_key,
        model=settings.gemini_model,
        timeout=settings.gemini_timeout_seconds,
    )
    connection = connect(settings.database_url)
    try:
        for problem_id, problem in list_problems(connection, limit=limit):
            try:
                analysis: ProblemAnalysis = client.analyze(problem)
                decision = decision_for_score(problem.score)
                save_analysis(connection, problem_id, analysis, decision)
                result.analyzed += 1
                if decision == "auto_publish_candidate":
                    result.auto_publish_candidates += 1
                elif decision == "approval_queue":
                    result.approval_queue += 1
                else:
                    result.discarded += 1
            except Exception:
                result.failed += 1
    finally:
        connection.close()
    return result
