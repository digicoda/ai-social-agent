"""Lightweight profile-aware research search and result storage."""
from __future__ import annotations
import hashlib, json, re
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlsplit, urlunsplit
from ..config import Settings
from ..database import connect
from ..schemas import Problem
from .github import fetch_github_issues
from .reddit import fetch_reddit
from .rss import fetch_rss
from .stackoverflow import fetch_stackoverflow
SCHEMA="""CREATE TABLE IF NOT EXISTS research_runs (id INTEGER PRIMARY KEY AUTOINCREMENT, profile_id INTEGER, query TEXT NOT NULL DEFAULT '', mode TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'running', discovered INTEGER NOT NULL DEFAULT 0, returned INTEGER NOT NULL DEFAULT 0, started_at TEXT NOT NULL, finished_at TEXT, error TEXT NOT NULL DEFAULT ''); CREATE INDEX IF NOT EXISTS idx_research_runs_profile ON research_runs(profile_id,started_at); CREATE TABLE IF NOT EXISTS research_results (id INTEGER PRIMARY KEY AUTOINCREMENT,run_id INTEGER NOT NULL,profile_id INTEGER,cluster_key TEXT NOT NULL,source TEXT NOT NULL,external_id TEXT NOT NULL,title TEXT NOT NULL,url TEXT NOT NULL,summary TEXT NOT NULL DEFAULT '',tags TEXT NOT NULL DEFAULT '[]',score INTEGER NOT NULL DEFAULT 0,comments INTEGER NOT NULL DEFAULT 0,published_at TEXT,opportunity_score INTEGER NOT NULL DEFAULT 0,labels TEXT NOT NULL DEFAULT '[]',fingerprint TEXT NOT NULL,created_at TEXT NOT NULL,UNIQUE(run_id,fingerprint),FOREIGN KEY(run_id) REFERENCES research_runs(id) ON DELETE CASCADE); CREATE INDEX IF NOT EXISTS idx_research_results_run ON research_results(run_id,opportunity_score DESC); CREATE INDEX IF NOT EXISTS idx_research_results_cluster ON research_results(cluster_key);"""
@dataclass(slots=True)
class SearchRequest:
    profile_id:int|None=None; topic:str=""; mode:str="standard"; category:str=""; intents:list[str]|None=None; sources:list[str]|None=None; time_range:str="30d"; limit:int=30
@dataclass(slots=True)
class SearchResult:
    source:str; external_id:str; title:str; url:str; summary:str; tags:list[str]; score:int; comments:int; published_at:str|None; opportunity_score:int; labels:list[str]; cluster_key:str
def _tokenize(text:str)->set[str]: return {x for x in re.findall(r"[a-z0-9]{3,}",text.lower()) if x not in {"the","and","for","with","from","this","that","how"}}
def _canonical_url(url:str)->str:
    try:
        p=urlsplit(url.strip()); return urlunsplit((p.scheme.lower(),p.netloc.lower(),p.path.rstrip("/"),"",""))
    except ValueError:return url.strip().lower()
def _fingerprint(problem:Problem)->str:
    text=" ".join(sorted(_tokenize(problem.title))) or problem.title.lower().strip(); return hashlib.sha256(text.encode()).hexdigest()
def _cluster_key(problem:Problem)->str:
    raw=" ".join(sorted(_tokenize(problem.title))[:12]) or _canonical_url(problem.url); return hashlib.sha1(raw.encode()).hexdigest()[:16]
def _matches(problem:Problem,terms:list[str])->bool:
    if not terms:return True
    hay=f"{problem.title} {problem.summary} {problem.body} {' '.join(problem.tags)}".lower(); return any(term.lower() in hay for term in terms if term.strip())
def _opportunity(problem:Problem,cross_source:int=1)->int:
    age=30.0
    if problem.published_at: age=max(0.0,(datetime.now(timezone.utc)-problem.published_at.astimezone(timezone.utc)).total_seconds()/86400)
    recency=max(0.0,30.0-min(age,30.0))/30.0*25; engagement=min(25.0,max(problem.score,0)*1.5+max(problem.comments,0)); repetition=min(20.0,cross_source*7.0); text=f"{problem.title} {problem.body}".lower(); severity=15.0 if any(x in text for x in ("broken","bug","error","fails","issue","problem","can't","cannot")) else 5.0
    return max(0,min(100,round(recency+engagement+repetition+severity+10)))
def _terms(request:SearchRequest,profile:dict[str,Any]|None)->list[str]:
    values=[request.topic,request.category]
    if profile: values.extend(profile.get("topics",[])); values.extend(profile.get("keywords",[])); values.append(profile.get("main_category",""))
    values.extend(request.intents or []); return [str(x).strip() for x in values if str(x).strip()]
def _query_for_github(terms:list[str])->str:
    keywords=[x for x in terms if len(x)>2][:5]; return "is:issue is:open "+(" ".join(f'"{x}"' for x in keywords) if keywords else "(bug OR error OR broken OR fails OR problem)")
def _fetch(settings:Settings,source:str,terms:list[str],profile:dict[str,Any]|None,limit:int)->list[Problem]:
    timeout=settings.research_timeout_seconds
    if source=="github": return fetch_github_issues(_query_for_github(terms),limit=limit,timeout=timeout)
    if source=="stackoverflow":
        tags=[x for x in (profile or {}).get("keywords",[]) if re.fullmatch(r"[A-Za-z0-9+#.-]{2,35}",str(x))][:5]; return fetch_stackoverflow(tags=tags or None,limit=limit,timeout=timeout)
    if source=="reddit": return fetch_reddit(limit=limit,user_agent=settings.reddit_user_agent,timeout=timeout)
    if source=="rss": return fetch_rss(settings.rss_feed_list,limit=limit)
    return []
def _cutoff(value:str)->datetime:
    now=datetime.now(timezone.utc); days={"24h":1/24,"7d":7,"30d":30,"90d":90,"year":365}[value]; return now-timedelta(days=days)
def search(settings:Settings,request:SearchRequest,profile:dict[str,Any]|None=None)->dict[str,Any]:
    modes={"quick":10,"standard":25,"deep":50,"monitoring":20}
    if request.mode not in modes: raise ValueError("mode must be quick, standard, deep, or monitoring")
    if request.time_range not in {"24h","7d","30d","90d","year","custom"}: raise ValueError("invalid time_range")
    limit=max(1,min(request.limit,100)); sources=request.sources or (profile or {}).get("sources") or ["github","reddit","stackoverflow","rss"]; sources=[s for s in sources if s in {"github","reddit","stackoverflow","rss"}]
    if not sources: raise ValueError("at least one supported source is required")
    if not request.topic.strip() and not profile and not request.category.strip(): raise ValueError("topic, category, or profile_id is required")
    db=connect(settings.database_url); db.executescript(SCHEMA); cur=db.execute("INSERT INTO research_runs(profile_id,query,mode,started_at) VALUES (?,?,?,?)",(request.profile_id,request.topic.strip(),request.mode,datetime.now(timezone.utc).isoformat())); run_id=int(cur.lastrowid); db.commit(); discovered=0; candidates=[]; failed=[]
    try:
        terms=_terms(request,profile); per_source=modes[request.mode]; cutoff=None if request.time_range=="custom" else _cutoff(request.time_range)
        for source in sources:
            try:
                items=_fetch(settings,source,terms,profile,per_source); discovered+=len(items)
                for item in items:
                    if cutoff and item.published_at and item.published_at.astimezone(timezone.utc)<cutoff: continue
                    if _matches(item,terms): candidates.append(item)
            except Exception: failed.append(source)
        unique={}
        for item in candidates:
            key=_fingerprint(item)
            if key not in unique or item.score+item.comments>unique[key].score+unique[key].comments: unique[key]=item
        cross={}
        for item in unique.values(): cross[_cluster_key(item)]=cross.get(_cluster_key(item),0)+1
        now=datetime.now(timezone.utc).isoformat(); results=[]
        for item in sorted(unique.values(),key=lambda x:_opportunity(x,cross.get(_cluster_key(x),1)),reverse=True)[:limit]:
            labels=["source:"+item.source]
            if item.comments>=5 or item.score>=10: labels.append("engaged")
            if any(w in f"{item.title} {item.body}".lower() for w in ("bug","error","broken","fails","problem")): labels.append("pain-point")
            result=SearchResult(item.source,item.external_id,item.title,item.url,item.summary,item.tags,item.score,item.comments,item.published_at.isoformat() if item.published_at else None,_opportunity(item,cross.get(_cluster_key(item),1)),labels,_cluster_key(item)); db.execute("INSERT OR IGNORE INTO research_results(run_id,profile_id,cluster_key,source,external_id,title,url,summary,tags,score,comments,published_at,opportunity_score,labels,fingerprint,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(run_id,request.profile_id,result.cluster_key,result.source,result.external_id,result.title,result.url,result.summary,json.dumps(result.tags),result.score,result.comments,result.published_at,result.opportunity_score,json.dumps(result.labels),_fingerprint(item),now)); results.append(result)
        status="completed" if not failed else "partial"; db.execute("UPDATE research_runs SET status=?,discovered=?,returned=?,finished_at=?,error=? WHERE id=?",(status,discovered,len(results),datetime.now(timezone.utc).isoformat(),",".join(failed),run_id)); db.commit(); return {"run_id":run_id,"status":status,"discovered":discovered,"returned":len(results),"failed_sources":failed,"items":[asdict(x) for x in results]}
    except Exception as exc:
        db.execute("UPDATE research_runs SET status='failed',finished_at=?,error=? WHERE id=?",(datetime.now(timezone.utc).isoformat(),str(exc),run_id)); db.commit(); raise
    finally: db.close()
