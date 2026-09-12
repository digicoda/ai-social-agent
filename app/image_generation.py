from __future__ import annotations

import base64
import json
import mimetypes
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from .config import Settings
from .database import connect

IMAGE_SHORTCODES: dict[str, dict[str, str]] = {
    "auto": {"label": "Auto", "description": "Let AI select the visual treatment from the post."},
    "explainer": {"label": "Explainer", "description": "Clear educational visual explaining a concept or workflow."},
    "advertisement": {"label": "Advertisement", "description": "Polished promotional creative with a strong visual hierarchy."},
    "promotion": {"label": "Promotion", "description": "Marketing-focused visual highlighting an offer, feature or benefit."},
    "marketing": {"label": "Marketing", "description": "Professional brand/marketing creative for audience engagement."},
    "problem": {"label": "Problem", "description": "Visualize the pain point or before-state described in the post."},
    "solution": {"label": "Solution", "description": "Show the practical solution, workflow or improved outcome."},
    "article": {"label": "Article", "description": "Editorial feature image suitable for a technical or thought-leadership post."},
    "infographic": {"label": "Infographic", "description": "Structured information graphic with restrained readable labels."},
    "social": {"label": "Social", "description": "Native-looking professional social-media creative."},
    "case-study": {"label": "Case Study", "description": "Professional case-study visual showing context, process and outcome."},
}


@dataclass(slots=True)
class ImageAsset:
    path: str
    prompt: str
    shortcode: str
    model: str
    aspect_ratio: str


def select_shortcode(title: str, body: str, category: str = "", intent: str = "") -> str:
    text = f"{title} {body} {category} {intent}".lower()
    if any(x in text for x in ("advertis", "ad creative", "campaign", "offer", "discount")):
        return "advertisement"
    if any(x in text for x in ("promot", "marketing", "brand", "conversion", "cta")):
        return "promotion"
    if any(x in text for x in ("how to", "tutorial", "guide", "explain", "workflow", "step-by-step", "steps")):
        return "explainer"
    if any(x in text for x in ("problem", "issue", "pain point", "broken", "error", "challenge")):
        return "problem"
    if any(x in text for x in ("solution", "fix", "resolve", "improve", "before and after")):
        return "solution"
    if any(x in text for x in ("case study", "results", "customer story", "outcome")):
        return "case-study"
    if any(x in text for x in ("stats", "statistics", "comparison", "data", "metrics")):
        return "infographic"
    if any(x in text for x in ("article", "research", "analysis", "thought leadership")):
        return "article"
    return "social"


def build_prompt(title: str, body: str, shortcode: str, custom_prompt: str = "", aspect_ratio: str = "1:1") -> str:
    preset = IMAGE_SHORTCODES.get(shortcode, IMAGE_SHORTCODES["social"])
    instruction = preset["description"]
    return f"""Create a high-quality professional social-media image for this post.\nCreative mode: {preset['label']} ({shortcode}).\nVisual direction: {instruction}\nAspect ratio: {aspect_ratio}.\nUse strong composition, realistic or polished editorial quality, clear subject hierarchy, natural lighting, and a modern professional aesthetic. Avoid generic stock-photo appearance, visual clutter, fake logos, watermarks, and invented factual claims. If text is necessary, keep it short, accurate, legible, and subordinate to the main visual.\nPost title: {title}\nPost body: {body[:12000]}\nAdditional user prompt: {custom_prompt[:4000]}\n"""


def _reference_part(path: str) -> dict[str, Any] | None:
    if not path:
        return None
    file_path = Path(path).expanduser().resolve()
    if not file_path.is_file() or file_path.stat().st_size > 12 * 1024 * 1024:
        raise ValueError("reference image does not exist or is too large")
    mime = mimetypes.guess_type(file_path.name)[0] or "image/png"
    if mime not in {"image/png", "image/jpeg", "image/webp"}:
        raise ValueError("reference image must be PNG, JPEG, or WebP")
    return {"inline_data": {"mime_type": mime, "data": base64.b64encode(file_path.read_bytes()).decode("ascii")}}


def generate_image(settings: Settings, title: str, body: str, category: str = "", intent: str = "", shortcode: str = "auto", custom_prompt: str = "", aspect_ratio: str = "1:1", reference_path: str = "") -> ImageAsset:
    if not settings.gemini_api_key:
        raise ValueError("GEMINI_API_KEY is not configured")
    shortcode = shortcode.lower().strip() or "auto"
    if shortcode not in IMAGE_SHORTCODES:
        raise ValueError("invalid image shortcode")
    if shortcode == "auto":
        shortcode = select_shortcode(title, body, category, intent)
    if aspect_ratio not in {"1:1", "4:5", "16:9", "9:16"}:
        raise ValueError("unsupported aspect ratio")
    prompt = build_prompt(title, body, shortcode, custom_prompt, aspect_ratio)
    parts: list[dict[str, Any]] = [{"text": prompt}]
    reference = _reference_part(reference_path)
    if reference:
        parts.append(reference)
    model = settings.gemini_model or "gemini-2.5-flash-image"
    if "image" not in model.lower():
        model = "gemini-2.5-flash-image"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    payload = {"contents": [{"parts": parts}], "generationConfig": {"responseModalities": ["IMAGE"], "responseFormat": {"image": {"aspect_ratio": aspect_ratio}}}}
    with httpx.Client(timeout=max(settings.gemini_timeout_seconds, 90.0)) as client:
        response = client.post(url, headers={"x-goog-api-key": settings.gemini_api_key, "Content-Type": "application/json"}, json=payload)
        response.raise_for_status()
        data = response.json()
    image_b64 = None
    for candidate in data.get("candidates", []):
        for part in candidate.get("content", {}).get("parts", []):
            inline = part.get("inlineData") or part.get("inline_data")
            if inline and inline.get("data"):
                image_b64 = inline["data"]
                break
        if image_b64:
            break
    if not image_b64:
        raise ValueError("image provider returned no image")
    output_dir = Path("data") / "media" / "generated"
    output_dir.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:60] or "post"
    path = output_dir / f"{safe}-{__import__('secrets').token_hex(5)}.png"
    path.write_bytes(base64.b64decode(image_b64))
    return ImageAsset(str(path), prompt, shortcode, model, aspect_ratio)


def save_image_asset(database_url: str, draft_id: int, asset: ImageAsset) -> int:
    db = connect(database_url)
    try:
        db.execute("CREATE TABLE IF NOT EXISTS image_assets (id INTEGER PRIMARY KEY AUTOINCREMENT, draft_id INTEGER NOT NULL, path TEXT NOT NULL, prompt TEXT NOT NULL, shortcode TEXT NOT NULL, model TEXT NOT NULL, aspect_ratio TEXT NOT NULL, created_at TEXT NOT NULL, FOREIGN KEY(draft_id) REFERENCES content_drafts(id) ON DELETE CASCADE)")
        from datetime import datetime, timezone
        cur = db.execute("INSERT INTO image_assets (draft_id,path,prompt,shortcode,model,aspect_ratio,created_at) VALUES (?,?,?,?,?,?,?)", (draft_id, asset.path, asset.prompt, asset.shortcode, asset.model, asset.aspect_ratio, datetime.now(timezone.utc).isoformat()))
        db.commit()
        return int(cur.lastrowid)
    finally:
        db.close()


def list_image_assets(database_url: str, draft_id: int | None = None, limit: int = 50) -> list[dict[str, Any]]:
    db = connect(database_url)
    try:
        db.execute("CREATE TABLE IF NOT EXISTS image_assets (id INTEGER PRIMARY KEY AUTOINCREMENT, draft_id INTEGER NOT NULL, path TEXT NOT NULL, prompt TEXT NOT NULL, shortcode TEXT NOT NULL, model TEXT NOT NULL, aspect_ratio TEXT NOT NULL, created_at TEXT NOT NULL, FOREIGN KEY(draft_id) REFERENCES content_drafts(id) ON DELETE CASCADE)")
        if draft_id is None:
            rows = db.execute("SELECT * FROM image_assets ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        else:
            rows = db.execute("SELECT * FROM image_assets WHERE draft_id=? ORDER BY created_at DESC LIMIT ?", (draft_id, limit)).fetchall()
        return [dict(row) for row in rows]
    finally:
        db.close()
