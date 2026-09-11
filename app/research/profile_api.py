from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, Field

from ..config import get_settings
from .profiles import delete_profile, get_profile, list_profiles, save_profile

router = APIRouter(prefix="/research/profiles", tags=["research-profiles"])

class ProfileRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    main_category: str = Field(min_length=1, max_length=160)
    values: dict[str, object] = Field(default_factory=dict)


def _auth(request: Request, x_api_key: str | None) -> None:
    expected = get_settings().internal_api_key
    if expected and x_api_key == expected: return
    if request.session.get("authenticated") is True: return
    if expected: raise HTTPException(status_code=401, detail="invalid API key or dashboard session")

@router.get("")
def profiles(request: Request, enabled_only: bool = False, x_api_key: str | None = Header(default=None)) -> dict:
    _auth(request, x_api_key)
    return {"items": list_profiles(get_settings().database_url, enabled_only=enabled_only)}

@router.get("/{profile_id}")
def profile(profile_id: int, request: Request, x_api_key: str | None = Header(default=None)) -> dict:
    _auth(request, x_api_key)
    item = get_profile(get_settings().database_url, profile_id)
    if item is None: raise HTTPException(status_code=404, detail="profile not found")
    return item

@router.post("")
def create_profile(payload: ProfileRequest, request: Request, x_api_key: str | None = Header(default=None)) -> dict:
    _auth(request, x_api_key)
    values = dict(payload.values); values.update(name=payload.name, main_category=payload.main_category)
    try: return save_profile(get_settings().database_url, values)
    except (ValueError, TypeError) as exc: raise HTTPException(status_code=400, detail=str(exc)) from exc

@router.put("/{profile_id}")
def update_profile(profile_id: int, payload: ProfileRequest, request: Request, x_api_key: str | None = Header(default=None)) -> dict:
    _auth(request, x_api_key)
    values = dict(payload.values); values.update(name=payload.name, main_category=payload.main_category)
    try: return save_profile(get_settings().database_url, values, profile_id=profile_id)
    except (ValueError, TypeError) as exc: raise HTTPException(status_code=400, detail=str(exc)) from exc

@router.delete("/{profile_id}")
def remove_profile(profile_id: int, request: Request, x_api_key: str | None = Header(default=None)) -> dict[str, bool]:
    _auth(request, x_api_key)
    if not delete_profile(get_settings().database_url, profile_id): raise HTTPException(status_code=404, detail="profile not found")
    return {"deleted": True}
