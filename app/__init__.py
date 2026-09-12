from __future__ import annotations


def _install_runtime_hooks() -> None:
    from fastapi import FastAPI
    from . import profiles

    def active_profile_settings(base):
        pid = profiles._ACTIVE_PROFILE.get()
        if not pid:
            return None
        try:
            return profiles.settings_for_profile(base, profiles.get_profile(base, pid))
        except Exception:
            return None

    profiles.active_profile_settings = active_profile_settings
    original_init = FastAPI.__init__

    if getattr(FastAPI, "_ai_social_agent_patched", False):
        return

    def patched_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        profiles.install(self)
        try:
            from .research import search as research_search
            from .websearch import fetch_web
            original_search = research_search.search_research
            original_supported = tuple(research_search.SUPPORTED_SOURCES)
            if "web" not in original_supported:
                research_search.SUPPORTED_SOURCES = original_supported + ("web",)

            def wrapped_search(settings, **kwargs):
                selected = kwargs.get("sources")
                selected = list(selected) if selected else list(research_search.SUPPORTED_SOURCES)
                use_web = "web" in selected
                kwargs["sources"] = [x for x in selected if x != "web"]
                result = original_search(settings, **kwargs)
                result["sources"] = selected
                result.setdefault("source_counts", {}).setdefault("web", 0)
                if use_web:
                    try:
                        from .database import connect, save_problem
                        from .dedup import find_cross_source_duplicate
                        from .scoring import score_problem
                        from .research.search import _within_date, _text, _classify, _severity, _score, _sentiment, SearchItem, _dedup_key
                        import re
                        query = kwargs.get("query", "")
                        days = research_search.TIME_RANGES.get(kwargs.get("time_range", "30d"))
                        db = connect(settings.database_url); seen = set()
                        try:
                            for problem in fetch_web(query, limit=settings.research_limit_per_source, timeout=settings.research_timeout_seconds):
                                if not _within_date(problem, days): continue
                                text = _text(problem); terms = re.findall(r"[a-z0-9][a-z0-9_-]{2,}", query.lower())
                                if query.strip() and terms and not any(t in text for t in terms): continue
                                category, intent = _classify(text)
                                if kwargs.get("category", "all") != "all" and category != kwargs["category"]: continue
                                if kwargs.get("intent", "all") != "all" and intent != kwargs["intent"]: continue
                                key = _dedup_key(problem)
                                if key in seen: continue
                                seen.add(key); problem.score = score_problem(problem); save_problem(db, problem)
                                sentiment = _sentiment(text); severity = _severity(text, intent); rel, opp, trend = _score(problem, research_search._relevance(problem, query), intent, severity)
                                result["items"].append({"source":"web","external_id":problem.external_id,"title":problem.title,"url":problem.url,"body":problem.body,"tags":problem.tags,"score":problem.score,"comments":problem.comments,"published_at":problem.published_at.isoformat() if problem.published_at else None,"category":category,"intent":intent,"relevance":rel,"opportunity":opp,"trend":trend,"sentiment":sentiment,"severity":severity})
                                result["source_counts"]["web"] += 1
                        finally: db.close()
                        result["items"].sort(key=lambda x:(x.get("opportunity",0),x.get("relevance",0),x.get("trend",0),x.get("severity",0)), reverse=True)
                        result["items"] = result["items"][:kwargs.get("limit",50)]
                        result["total"] = len(result["items"])
                    except Exception:
                        result.setdefault("failed_sources", []).append("web")
                return result

            research_search.search_research = wrapped_search
            research_search.search_options = lambda: {"sources":[{"id":"github","name":"GitHub Issues","enabled":True},{"id":"reddit","name":"Reddit","enabled":True},{"id":"stackoverflow","name":"Stack Overflow","enabled":True},{"id":"rss","name":"RSS / News","enabled":True},{"id":"web","name":"Web Search","enabled":True}],"categories":list(research_search.CATEGORIES),"intents":list(research_search.INTENTS),"time_ranges":list(research_search.TIME_RANGES),"modes":["quick","standard","deep"]}
        except Exception:
            pass

    FastAPI.__init__ = patched_init
    FastAPI._ai_social_agent_patched = True


_install_runtime_hooks()
