from __future__ import annotations


def _install_runtime_hooks() -> None:
    from fastapi import FastAPI, HTTPException, Request
    from . import profiles

    def active_profile_settings(base):
        pid = profiles._ACTIVE_PROFILE.get()
        if not pid: return None
        try: return profiles.settings_for_profile(base, profiles.get_profile(base, pid))
        except Exception: return None

    profiles.active_profile_settings = active_profile_settings
    original_init = FastAPI.__init__
    if getattr(FastAPI, "_ai_social_agent_patched", False): return

    def patched_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        profiles.install(self)
        try:
            from .research import search as research_search
            from .websearch import fetch_web
            import sys, json, re
            original_search = research_search.search_research
            supported = tuple(research_search.SUPPORTED_SOURCES)
            if "web" not in supported: research_search.SUPPORTED_SOURCES = supported + ("web",)

            def wrapped_search(settings, **kwargs):
                selected=list(kwargs.get("sources") or research_search.SUPPORTED_SOURCES); use_web="web" in selected; kwargs["sources"]=[x for x in selected if x!="web"]
                result=original_search(settings,**kwargs); result["sources"]=selected; result.setdefault("source_counts",{}).setdefault("web",0)
                if use_web:
                    try:
                        from .database import connect, save_problem
                        from .scoring import score_problem
                        from .research.search import _within_date,_text,_classify,_severity,_score,_sentiment,_dedup_key
                        query=kwargs.get("query",""); days=research_search.TIME_RANGES.get(kwargs.get("time_range","30d")); db=connect(settings.database_url); seen=set()
                        try:
                            for problem in fetch_web(query,limit=settings.research_limit_per_source,timeout=settings.research_timeout_seconds):
                                if not _within_date(problem,days): continue
                                text=_text(problem); terms=re.findall(r"[a-z0-9][a-z0-9_-]{2,}",query.lower())
                                if query.strip() and terms and not any(t in text for t in terms): continue
                                category,intent=_classify(text)
                                if kwargs.get("category","all")!="all" and category!=kwargs["category"]: continue
                                if kwargs.get("intent","all")!="all" and intent!=kwargs["intent"]: continue
                                key=_dedup_key(problem)
                                if key in seen: continue
                                seen.add(key); problem.score=score_problem(problem); save_problem(db,problem); sentiment=_sentiment(text); severity=_severity(text,intent); rel,opp,trend=_score(problem,research_search._relevance(problem,query),intent,severity)
                                result["items"].append({"source":"web","external_id":problem.external_id,"title":problem.title,"url":problem.url,"body":problem.body,"tags":problem.tags,"score":problem.score,"comments":problem.comments,"published_at":problem.published_at.isoformat() if problem.published_at else None,"category":category,"intent":intent,"relevance":rel,"opportunity":opp,"trend":trend,"sentiment":sentiment,"severity":severity}); result["source_counts"]["web"]+=1
                        finally: db.close()
                        result["items"].sort(key=lambda x:(x.get("opportunity",0),x.get("relevance",0),x.get("trend",0),x.get("severity",0)),reverse=True); result["items"]=result["items"][:kwargs.get("limit",50)]; result["total"]=len(result["items"])
                    except Exception: result.setdefault("failed_sources",[]).append("web")
                return result

            research_search.search_research=wrapped_search
            research_search.search_options=lambda:{"sources":[{"id":"github","name":"GitHub Issues","enabled":True},{"id":"reddit","name":"Reddit","enabled":True},{"id":"stackoverflow","name":"Stack Overflow","enabled":True},{"id":"rss","name":"RSS / News","enabled":True},{"id":"web","name":"Web Search","enabled":True}],"categories":list(research_search.CATEGORIES),"intents":list(research_search.INTENTS),"time_ranges":list(research_search.TIME_RANGES),"modes":["quick","standard","deep"]}
            api=sys.modules.get("app.research.search_api")
            if api is not None: api.SUPPORTED_SOURCES=research_search.SUPPORTED_SOURCES; api.search_research=wrapped_search; api.search_options=research_search.search_options

            from .content import generate_content_for_problem
            from .database import connect
            from .ai import create_ai_client
            from .schemas import Problem
            from datetime import datetime
            from .intelligence import _save_analysis, opportunity_score
            @self.post("/content/generate-by-title")
            def generate_by_title(request: Request, payload: dict):
                if request.session.get("authenticated") is not True: raise HTTPException(status_code=401,detail="dashboard login required")
                title=str(payload.get("title","")).strip()
                if not title: raise HTTPException(status_code=400,detail="title is required")
                settings=__import__("app.config",fromlist=["get_settings"]).get_settings(); db=connect(settings.database_url)
                try:
                    row=db.execute("SELECT * FROM problems WHERE title=? ORDER BY discovered_at DESC LIMIT 1",(title,)).fetchone()
                    if row is None: raise HTTPException(status_code=404,detail="research result not found")
                    existing=db.execute("SELECT 1 FROM ai_intelligence WHERE problem_id=?",(int(row["id"]),)).fetchone()
                finally: db.close()
                if not existing:
                    problem=Problem(source=row["source"],external_id=row["external_id"],title=row["title"],url=row["url"],summary=row["summary"],body=row["body"],tags=json.loads(row["tags"]),score=int(row["score"]),comments=int(row["comments"]),published_at=datetime.fromisoformat(row["published_at"]) if row["published_at"] else None,discovered_at=datetime.fromisoformat(row["discovered_at"]),metadata=json.loads(row["metadata"]))
                    analysis=create_ai_client(settings).analyze(problem); db=connect(settings.database_url)
                    try: _save_analysis(db,int(row["id"]),analysis,opportunity_score(problem,analysis,1),None,None); db.commit()
                    finally: db.close()
                return generate_content_for_problem(settings,int(row["id"]))
        except Exception:
            pass

    FastAPI.__init__=patched_init; FastAPI._ai_social_agent_patched=True


_install_runtime_hooks()
