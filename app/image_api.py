from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, Field
from .config import get_settings
from .content import generate_image_for_draft
from .database import connect
from .image_generation import IMAGE_SHORTCODES, generate_image, list_image_assets, save_image_asset

router=APIRouter(prefix="/images",tags=["images"])
class ImageRequest(BaseModel):
    shortcode:str="auto"; prompt:str=""; aspect_ratio:str="1:1"; reference_path:str=""; draft_id:int|None=None; title:str=Field(default="",max_length=500); body:str=Field(default="",max_length=20000); category:str=""; intent:str=""
def _auth(request:Request,x_api_key:str|None):
    expected=get_settings().internal_api_key
    if expected and x_api_key==expected:return
    if request.session.get("authenticated") is not True and expected:raise HTTPException(status_code=401,detail="invalid API key or dashboard session")
@router.get("/presets")
def presets(request:Request,x_api_key:str|None=Header(default=None)):
    _auth(request,x_api_key); return {"items":IMAGE_SHORTCODES}
@router.get("/draft/{draft_id}")
def draft_images(draft_id:int,request:Request,x_api_key:str|None=Header(default=None)):
    _auth(request,x_api_key); return {"items":list_image_assets(get_settings().database_url,draft_id=draft_id)}
@router.post("/generate")
def image_generate(request:Request,payload:ImageRequest,x_api_key:str|None=Header(default=None)):
    _auth(request,x_api_key); settings=get_settings()
    if payload.draft_id:
        db=connect(settings.database_url)
        try:
            row=db.execute("SELECT d.title,d.body,p.category,p.metadata FROM content_drafts d JOIN problems p ON p.id=d.problem_id WHERE d.id=?",(payload.draft_id,)).fetchone()
        finally:db.close()
        if row is None:raise HTTPException(status_code=404,detail="draft not found")
        title=payload.title or row["title"]; body=payload.body or row["body"]
    else:title=payload.title; body=payload.body
    if not title or not body:raise HTTPException(status_code=400,detail="title and body are required")
    try:
        asset=generate_image(settings,title,body,payload.category,payload.intent,payload.shortcode,payload.prompt,payload.aspect_ratio,payload.reference_path)
        asset_id=save_image_asset(settings.database_url,payload.draft_id or 0,asset) if payload.draft_id else None
        return {"id":asset_id,"path":asset.path,"shortcode":asset.shortcode,"model":asset.model,"aspect_ratio":asset.aspect_ratio,"prompt":asset.prompt}
    except Exception as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
