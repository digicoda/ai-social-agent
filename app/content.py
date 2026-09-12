import json
import sqlite3
from dataclasses import dataclass
import httpx
from .ai import ProblemAnalysis
from .config import Settings
from .database import connect, get_analysis, list_problems, save_draft
from .humanize import humanize_content
from .image_generation import generate_image, save_image_asset

@dataclass(slots=True)
class ContentDraft:
    title: str; body: str; hashtags: list[str]; call_to_action: str; confidence: int
class ContentGenerationError(RuntimeError): pass

def _generate(client: httpx.Client, settings: Settings, problem, analysis: ProblemAnalysis) -> ContentDraft:
    prompt=f"""Create one high-quality educational social media draft from this researched technical problem.
The draft must be useful first, never fabricate facts, never claim personal experience, and never sound like an advertisement.
Return ONLY JSON with exactly these keys: title (string), body (string), hashtags (array of 3-6 strings without #), call_to_action (string), confidence (integer 0-100).
Use a clear hook, explain the underlying problem briefly, provide practical steps or insight, and end with a natural discussion question. Keep the body concise enough for a general professional social post (roughly 150-280 words).
Problem title: {problem.title}\nSource: {problem.source}\nOriginal context: {problem.body[:10000]}\nPain point: {analysis.pain_point}\nAudience: {analysis.audience}\nRoot cause: {analysis.root_cause}\nSolution angle: {analysis.solution_angle}\nHooks: {json.dumps(analysis.hooks, ensure_ascii=False)}\nRisks: {json.dumps(analysis.risks, ensure_ascii=False)}"""
    url=f"https://generativelanguage.googleapis.com/v1beta/models/{settings.gemini_model}:generateContent"
    response=client.post(url,headers={"x-goog-api-key":settings.gemini_api_key,"Content-Type":"application/json"},json={"contents":[{"parts":[{"text":prompt}]}],"generationConfig":{"temperature":0.4,"responseMimeType":"application/json"}}); response.raise_for_status(); payload=response.json()
    try:
        data=json.loads(payload["candidates"][0]["content"]["parts"][0]["text"]); title=str(data["title"]).strip(); body=str(data["body"]).strip(); hashtags=[str(item).strip().lstrip("#") for item in data["hashtags"] if str(item).strip()]; cta=str(data["call_to_action"]).strip()
        if not title or not body or not hashtags or not cta: raise ValueError("incomplete content draft")
        return ContentDraft(title,body,hashtags[:6],cta,max(0,min(100,int(data["confidence"]))))
    except (KeyError,TypeError,ValueError,json.JSONDecodeError) as exc: raise ContentGenerationError("Gemini returned an invalid content payload") from exc

def _apply_human_quality(client,settings,draft):
    if not settings.humanize_content:return draft
    try:
        edited,_report=humanize_content(client,settings,draft); return edited
    except (httpx.HTTPError,ContentGenerationError,ValueError,KeyError,TypeError,json.JSONDecodeError): return draft

def _content_analysis(connection,problem_id):
    legacy=get_analysis(connection,problem_id)
    if legacy:return legacy
    try: row=connection.execute("SELECT category,intent,sentiment,severity,frequency_signal,trend_signal,content_gap,opportunity_score,trend_label,pain_point,audience,root_cause,solution_angle,hooks,risks,related_topics,recommended_formats,evidence,confidence FROM ai_intelligence WHERE problem_id=?",(problem_id,)).fetchone()
    except sqlite3.OperationalError as exc:
        if "no such table" in str(exc).lower() and "ai_intelligence" in str(exc).lower():return None
        raise
    if row is None:return None
    return (ProblemAnalysis(pain_point=row["pain_point"],audience=row["audience"],root_cause=row["root_cause"],solution_angle=row["solution_angle"],hooks=json.loads(row["hooks"]),risks=json.loads(row["risks"]),confidence=int(row["confidence"]),category=row["category"],intent=row["intent"],sentiment=row["sentiment"],severity=int(row["severity"]),frequency_signal=int(row["frequency_signal"]),trend_signal=int(row["trend_signal"]),content_gap=int(row["content_gap"]),opportunity_score=int(row["opportunity_score"]),trend_label=row["trend_label"],related_topics=json.loads(row["related_topics"]),recommended_formats=json.loads(row["recommended_formats"]),evidence=json.loads(row["evidence"])),"create")

def generate_image_for_draft(settings: Settings, draft_id: int, title: str, body: str, analysis: ProblemAnalysis | None = None) -> dict | None:
    if not settings.image_enabled:return None
    try:
        category=getattr(analysis,"category","") if analysis else ""; intent=getattr(analysis,"intent","") if analysis else ""
        asset=generate_image(settings,title,body,category,intent,settings.image_shortcode,settings.image_prompt,settings.image_aspect_ratio,settings.image_reference_path)
        asset_id=save_image_asset(settings.database_url,draft_id,asset)
        return {"id":asset_id,"path":asset.path,"shortcode":asset.shortcode,"model":asset.model,"aspect_ratio":asset.aspect_ratio}
    except (httpx.HTTPError,ValueError,TypeError): return None

def generate_content(settings: Settings, limit: int=10) -> dict[str,int]:
    if not settings.gemini_api_key:raise ContentGenerationError("GEMINI_API_KEY is not configured")
    generated=skipped=failed=images=0
    with httpx.Client(timeout=settings.gemini_timeout_seconds) as client:
        connection=connect(settings.database_url)
        try:
            for problem_id,problem in list_problems(connection,limit=limit):
                if connection.execute("SELECT 1 FROM content_drafts WHERE problem_id=? AND status!='rejected' LIMIT 1",(problem_id,)).fetchone():skipped+=1;continue
                analyzed=_content_analysis(connection,problem_id)
                if analyzed is None or analyzed[1]=="discard":skipped+=1;continue
                analysis,_decision=analyzed
                try:
                    draft=_apply_human_quality(client,settings,_generate(client,settings,problem,analysis)); draft_id=save_draft(connection,problem_id,"generic",draft.title,draft.body,draft.hashtags,draft.call_to_action,draft.confidence); generated+=1
                    if generate_image_for_draft(settings,draft_id,draft.title,draft.body,analysis):images+=1
                except (httpx.HTTPError,ValueError,KeyError,TypeError,json.JSONDecodeError):failed+=1
        finally:connection.close()
    return {"generated":generated,"skipped":skipped,"failed":failed,"images":images}
