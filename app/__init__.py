"""AI Social Agent application package."""


def _install_profile_context():
    from fastapi import FastAPI, Request
    from .profile_context import install_profile_context
    from .profiles import get_profile
    from .config import get_settings
    from .version import APP_NAME, APP_VERSION, FEATURES, RELEASE_TAG

    if getattr(FastAPI, "_ai_social_profile_patch", False):
        return
    original_init = FastAPI.__init__

    def patched_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        install_profile_context(self)

        if not getattr(self, "_ai_social_meta_routes", False):
            @self.get("/system/version")
            def system_version():
                return {"name": APP_NAME, "version": APP_VERSION, "release": RELEASE_TAG, "features": FEATURES, "platform": "windows" if __import__("os").name == "nt" else "server"}

            @self.get("/profiles/active")
            def active_profile(request: Request):
                raw = request.cookies.get("ai_social_profile", "")
                if not raw.isdigit():
                    return {"profile": None}
                profile = get_profile(get_settings().database_url, int(raw))
                if not profile:
                    return {"profile": None}
                return {"profile": profile}

            self._ai_social_meta_routes = True

    FastAPI.__init__ = patched_init
    FastAPI._ai_social_profile_patch = True


try:
    _install_profile_context()
except ImportError:
    # Keeps lightweight imports/tests that do not install FastAPI functional.
    pass
