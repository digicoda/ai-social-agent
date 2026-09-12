from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, Field, field_validator

from ..config import get_settings
from .search import CATEGORIES, INTENTS, SUPPORTED_SOURCES, TIME_RANGES, search_options, search_research

router = APIRouter(prefix="/research", tags=["research"])


class SearchRequest(BaseModel):
    query: str = Field(default="", max_length=500)
    sources: list[str] = Field(default_factory=list, max_length=10)
    category: str = Field(default="all", max_length=50)
    intent: str = Field(default="all", max_length=50)
    time_range: str = Field(default="30d", max_length=20)
    mode: str = Field(default="standard", pattern="^(quick|standard|deep)$")
    limit: int = Field(default=50, ge=1, le=100)

    @field_validator("sources")
    @classmethod
    def validate_sources(cls, value: list[str]) -> list[str]:
        invalid = sorted(set(value) - set(SUPPORTED_SOURCES))
        if invalid:
            raise ValueError(f"unsupported research sources: {', '.join(invalid)}")
        return list(dict.fromkeys(value))

    @field_validator("category")
    @classmethod
    def validate_category(cls, value: str) -> str:
        if value not in {"all", *CATEGORIES}:
            raise ValueError("unsupported research category")
        return value

    @field_validator("intent")
    @classmethod
    def validate_intent(cls, value: str) -> str:
        if value not in {"all", *INTENTS}:
            raise ValueError("unsupported research intent")
        return value

    @field_validator("time_range")
    @classmethod
    def validate_time_range(cls, value: str) -> str:
        if value not in TIME_RANGES:
            raise ValueError("unsupported research time range")
        return value


def _authorize(request: Request, x_api_key: str | None) -> None:
    expected = get_settings().internal_api_key
    if expected and x_api_key == expected:
        return
    if request.session.get("authenticated") is True:
        return
    if expected:
        raise HTTPException(status_code=401, detail="invalid API key or dashboard session")


@router.get("/options")
def options(request: Request, x_api_key: str | None = Header(default=None)) -> dict:
    _authorize(request, x_api_key)
    return search_options()


@router.post("/search")
def search(payload: SearchRequest, request: Request, x_api_key: str | None = Header(default=None)) -> dict:
    _authorize(request, x_api_key)
    if payload.mode == "quick":
        payload.limit = min(payload.limit, 20)
    elif payload.mode == "deep":
        payload.limit = min(payload.limit, 100)
    return search_research(
        get_settings(),
        query=payload.query,
        sources=payload.sources or None,
        category=payload.category,
        intent=payload.intent,
        time_range=payload.time_range,
        limit=payload.limit,
    )
