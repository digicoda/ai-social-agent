from __future__ import annotations
import asyncio,json,re,uuid
from contextvars import ContextVar
from datetime import datetime,timedelta,timezone
from pathlib import Path
from typing import Any
from fastapi import HTTPException,Request
from pydantic import BaseModel,Field
from starlette.responses import JSONResponse
from .config import Settings
_ACTIVE_PROFILE: ContextVar[str|None]=ContextVar("ai_social_active_profile",default=None)
def _base()->Settings:return Settings()
def _db(settings):
 from .database import connect
 return connect(settings.database_url)
def _ensure(settings):
 db=_db(settings)
 try:
  db.execute("""CREATE TABLE IF NOT EXISTS profiles (id TEXT PRIMARY KEY,name TEXT NOT NULL UNIQUE,database_url TEXT NOT NULL,config TEXT NOT NULL DEFAULT '{}',automation_enabled INTEGER NOT NULL DEFAULT 0,daily_time TEXT NOT NULL DEFAULT '09:00',auto_approval INTEGER NOT NULL DEFAULT 0,categories TEXT NOT NULL DEFAULT '[]',research_query TEXT NOT NULL DEFAULT '',research_sources TEXT NOT NULL DEFAULT '[\"github\",\"reddit\",\"stackoverflow\",\"rss\",\"web\"]',posts_per_run INTEGER NOT NULL DEFAULT 5,last_run_date TEXT,last_run_status TEXT NOT NULL DEFAULT 'never',created_at TEXT NOT NULL,updated_at TEXT NOT NULL)""")
  if db.execute("SELECT 1 FROM profiles LIMIT 1").fetchone() is None:
   now=datetime.now(timezone.utc).isoformat();db.execute("INSERT INTO profiles (id,name,database_url,created_at,updated_at) VALUES (?,?,?,?,?)",("default","Default Profile",settings.database_url,now,now))
  db.commit()
 finally:db.close()
def _decode(row):
 d=dict(row)
 for key in ("config","categories","research_sources"):d[key]=json.loads(d.get(key) or ("{}" if key=="config" else "[]"))
 d["automation_enabled"]=bool(d["automation_enabled"]);d["auto_approval"]=bool(d["auto_approval"]);return d
def list_profiles(settings):
 _ensure(settings);db=_db(settings)
 try:return [_decode(r) for r in db.execute("SELECT * FROM profiles ORDER BY name COLLATE NOCASE").fetchall()]
 finally:db.close()
def get_profile(settings,profile_id=None):
 _ensure(settings);pid=profile_id or _ACTIVE_PROFILE.get();db=_db(settings)
 try:
  row=db.execute("SELECT * FROM profiles WHERE id=?",(pid,)).fetchone() if pid else db.execute("SELECT * FROM profiles ORDER BY created_at LIMIT 1").fetchone()
  if row is None:raise ValueError("profile not found")
  return _decode(row)
 finally:db.close()
def settings_for_profile(base,profile):
 values=base.model_dump();values.update(profile.get("config") or {});values["database_url"]=profile["database_url"];return Settings(**values)
def create_profile(base,data):
 name=str(data["name"]).strip()
 if not name:raise ValueError("profile name is required")
 pid=uuid.uuid4().hex[:16];safe=re.sub(r"[^a-z0-9_-]+","-",name.lower()).strip("-")[:40] or "profile";base_path=Path(base.database_url.replace("sqlite:///","",1)) if base.database_url.startswith("sqlite:///") else Path("data/ai_social_agent.db");db_path=base_path.parent/"profiles"/f"{safe}-{pid[:8]}.db";db_path.parent.mkdir(parents=True,exist_ok=True);now=datetime.now(timezone.utc).isoformat();db=_db(base)
 try:db.execute("INSERT INTO profiles (id,name,database_url,config,automation_enabled,daily_time,auto_approval,categories,research_query,research_sources,posts_per_run,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",(pid,name,f"sqlite:///{db_path.as_posix()}",json.dumps(data.get("config") or {}),int(bool(data.get("automation_enabled"))),data.get("daily_time") or "09:00",int(bool(data.get("auto_approval"))),json.dumps(data.get("categories") or []),data.get("research_query") or "",json.dumps(data.get("research_sources") or ["github","reddit","stackoverflow","rss","web"]),int(data.get("posts_per_run") or 5),now,now));db.commit()
 finally:db.close()
 return get_profile(base,pid)
def update_profile(base,pid,data):
 current=get_profile(base,pid);name=str(data.get("name",current["name"])).strip();daily=str(data.get("daily_time",current["daily_time"]))
 if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d",daily):raise ValueError("daily_time must be HH:MM")
 posts=max(1,min(50,int(data.get("posts_per_run",current["posts_per_run"]))));db=_db(base)
 try:db.execute("UPDATE profiles SET name=?,config=?,automation_enabled=?,daily_time=?,auto_approval=?,categories=?,research_query=?,research_sources=?,posts_per_run=?,updated_at=? WHERE id=?",(name,json.dumps(data.get("config",current["config"])),int(bool(data.get("automation_enabled",current["automation_enabled"]))),daily,int(bool(data.get("auto_approval",current["auto_approval"]))),json.dumps(data.get("categories",current["categories"])),data.get("research_query",current["research_query"]),json.dumps(data.get("research_sources",current["research_sources"])),posts,datetime.now(timezone.utc).isoformat(),pid));db.commit()
 finally:db.close()
 return get_profile(base,pid)
def delete_profile(base,pid):
 if len(list_profiles(base))<=1:raise ValueError("at least one profile must remain")
 db=_db(base)
 try:cur=db.execute("DELETE FROM profiles WHERE id=?",(pid,));db.commit();return cur.rowcount==1
 finally:db.close()
def run_profile_automation(base,profile):
 from .research.search import search_research
 from .intelligence import run_intelligence
 from .content import generate_content
 from .database import connect,list_drafts,update_draft_status,create_schedule
 settings=settings_for_profile(base,profile);sources=profile["research_sources"] or ["github","reddit","stackoverflow","rss","web"];categories=profile["categories"] or ["all"];research_total=0
 for category in categories:
  query=(profile["research_query"] or "").strip();query=(query+" "+category).strip() if category!="all" else query;result=search_research(settings,query=query,sources=sources,category="all",intent="all",time_range="7d",limit=min(100,max(20,settings.research_limit_per_source*2)));research_total+=int(result.get("total",0))
 analysis=run_intelligence(settings,limit=min(500,max(25,profile["posts_per_run"]*8)));generation=generate_content(settings,limit=profile["posts_per_run"]);approved=scheduled=0
 if profile["auto_approval"]:
  db=connect(settings.database_url)
  try:
   rows=list_drafts(db,status="pending_approval",limit=profile["posts_per_run"]);provider=str(profile.get("config",{}).get("publish_provider") or "linkedin");now=datetime.now(timezone.utc);hh,mm=map(int,profile["daily_time"].split(":"));target=now.replace(hour=hh,minute=mm,second=0,microsecond=0)
   if target<now:target+=timedelta(days=1)
   for row in rows:update_draft_status(db,int(row["id"]),"approved");approved+=1;create_schedule(db,int(row["id"]),provider,target.isoformat(),3);scheduled+=1
  finally:db.close()
 return {"research_results":research_total,"analyzed":analysis.analyzed,"generated":generation.get("generated",0),"skipped":generation.get("skipped",0),"failed":generation.get("failed",0),"auto_approved":approved,"scheduled":scheduled}
def run_due_automations(base):
 now=datetime.now(timezone.utc);today=now.date().isoformat();results=[]
 for profile in list_profiles(base):
  if not profile["automation_enabled"]:continue
  hh,mm=map(int,profile["daily_time"].split(":"))
  if (now.hour,now.minute)<(hh,mm) or profile.get("last_run_date")==today:continue
  db=_db(base)
  try:
   cur=db.execute("UPDATE profiles SET last_run_date=?,last_run_status='running',updated_at=? WHERE id=? AND automation_enabled=1 AND (last_run_date IS NULL OR last_run_date!=?)",(today,now.isoformat(),profile["id"],today));db.commit()
   if cur.rowcount!=1:continue
  finally:db.close()
  try:status=run_profile_automation(base,profile);encoded=json.dumps(status)
  except Exception as exc:status={"error":str(exc)};encoded=json.dumps(status)
  db=_db(base)
  try:db.execute("UPDATE profiles SET last_run_status=?,updated_at=? WHERE id=?",(encoded,datetime.now(timezone.utc).isoformat(),profile["id"]));db.commit()
  finally:db.close()
  results.append({"profile_id":profile["id"],"profile":profile["name"],"status":status})
 return results
class ProfileMiddleware:
 def __init__(self,app):self.app=app
 async def __call__(self,scope,receive,send):
  if scope.get("type")!="http":return await self.app(scope,receive,send)
  request=Request(scope,receive=receive);token=None
  try:token=_ACTIVE_PROFILE.set(get_profile(_base(),request.cookies.get("ai_social_profile"))["id"])
  except Exception:pass
  try:return await self.app(scope,receive,send)
  finally:
   if token is not None:_ACTIVE_PROFILE.reset(token)
def install(app):
 app.add_middleware(ProfileMiddleware)
 class ProfilePayload(BaseModel):
  name:str=Field(min_length=1,max_length=80);config:dict[str,Any]=Field(default_factory=dict);automation_enabled:bool=False;daily_time:str="09:00";auto_approval:bool=False;categories:list[str]=Field(default_factory=list,max_length=30);research_query:str=Field(default="",max_length=500);research_sources:list[str]=Field(default_factory=lambda:["github","reddit","stackoverflow","rss","web"],max_length=10);posts_per_run:int=Field(default=5,ge=1,le=50)
 def auth(request):
  if request.session.get("authenticated") is not True:raise HTTPException(status_code=401,detail="dashboard login required")
 @app.get("/profiles")
 def profiles(request:Request):auth(request);base=_base();return {"profiles":list_profiles(base),"active":get_profile(base)["id"]}
 @app.post("/profiles")
 def create(request:Request,payload:ProfilePayload):auth(request);return create_profile(_base(),payload.model_dump())
 @app.put("/profiles/{pid}")
 def update(pid:str,request:Request,payload:ProfilePayload):auth(request);return update_profile(_base(),pid,payload.model_dump())
 @app.delete("/profiles/{pid}")
 def delete(pid:str,request:Request):auth(request);return {"deleted":delete_profile(_base(),pid)}
 @app.post("/profiles/{pid}/activate")
 def activate(pid:str,request:Request):
  auth(request);p=get_profile(_base(),pid);r=JSONResponse({"active":p["id"],"profile":p});r.set_cookie("ai_social_profile",p["id"],max_age=31536000,samesite="lax");return r
 @app.post("/profiles/automation/run")
 def automation_run(request:Request):auth(request);return {"runs":run_due_automations(_base())}
 @app.get("/profiles/automation/status")
 def automation_status(request:Request):auth(request);return {"profiles":[{k:p[k] for k in ("id","name","automation_enabled","daily_time","auto_approval","categories","research_query","research_sources","posts_per_run","last_run_date","last_run_status")} for p in list_profiles(_base())]}
 @app.post("/content/generate-selected")
 def generate_selected(request:Request,problem_id:int):
  auth(request)
  from .content import generate_content_for_problem
  try:return generate_content_for_problem(_base(),problem_id)
  except Exception as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
 async def loop():
  while True:
   try:await asyncio.to_thread(run_due_automations,_base())
   except Exception:pass
   await asyncio.sleep(30)
 task_holder=[None]
 async def startup():task_holder[0]=asyncio.create_task(loop())
 async def shutdown():
  if task_holder[0] is not None:task_holder[0].cancel()
 app.router.on_startup.append(startup);app.router.on_shutdown.append(shutdown)
