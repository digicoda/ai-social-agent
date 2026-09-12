"""AI Social Agent application package."""


def _install_profile_context():
    from fastapi import FastAPI
    from .profile_context import install_profile_context
    if getattr(FastAPI, "_ai_social_profile_patch", False):
        return
    original_init = FastAPI.__init__

    def patched_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        install_profile_context(self)

    FastAPI.__init__ = patched_init
    FastAPI._ai_social_profile_patch = True


try:
    _install_profile_context()
except ImportError:
    # Keeps lightweight imports/tests that do not install FastAPI functional.
    pass
