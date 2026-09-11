from __future__ import annotations

from pathlib import Path

from fastapi import HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from .auth import authenticate, create_admin, has_users
from .config import get_settings

DASHBOARD_DIR = Path(__file__).with_name("dashboard")


def _configured() -> bool:
    return bool(get_settings().session_secret)


def require_dashboard_session(request: Request) -> None:
    if not request.session.get("authenticated"):
        raise HTTPException(status_code=401, detail="dashboard login required")


def dashboard_login(request: Request, username: str, password: str) -> bool:
    settings = get_settings()
    if not _configured():
        return False
    if not has_users(settings.database_url):
        if not create_admin(settings.database_url, username, password):
            return False
    elif not authenticate(settings.database_url, username, password):
        return False
    request.session.clear()
    request.session["authenticated"] = True
    request.session["role"] = "admin"
    return True


def dashboard_signup(request: Request, username: str, password: str) -> bool:
    return dashboard_login(request, username, password)


def dashboard_logout(request: Request) -> RedirectResponse:
    request.session.clear()
    return RedirectResponse("/dashboard", status_code=303)


def dashboard_page(request: Request) -> HTMLResponse:
    path = DASHBOARD_DIR / "index.html"
    html = path.read_text(encoding="utf-8")
    settings = get_settings()
    html = html.replace("__AUTH_CONFIGURED__", "true" if _configured() else "false")
    html = html.replace("__HAS_ACCOUNT__", "true" if has_users(settings.database_url) else "false")
    html = html.replace("__AUTHENTICATED__", "true" if request.session.get("authenticated") else "false")
    setup_script = r'''<script>
(function(){
 const hasAccount=__HAS_ACCOUNT__, box=document.getElementById('login'), form=document.getElementById('loginForm');
 if(!box||!form)return; const h=box.querySelector('h1'), sub=box.querySelector('p.muted'), btn=form.querySelector('button'), notice=document.getElementById('loginNotice');
 const tabs=document.createElement('div'); tabs.style.cssText='display:flex;gap:8px;margin:18px 0 4px';
 tabs.innerHTML='<button type="button" id="signInTab" class="btn secondary" style="flex:1">Sign in</button><button type="button" id="signUpTab" class="btn" style="flex:1">Create admin</button>';
 form.parentNode.insertBefore(tabs,form);
 const confirmLabel=document.createElement('label'), confirm=document.createElement('input');
 confirmLabel.textContent='Confirm password'; confirmLabel.style.cssText='display:block;font-size:13px;font-weight:600;margin:14px 0 6px'; confirm.type='password'; confirm.id='confirmPassword'; confirm.style.width='100%'; form.append(confirmLabel,confirm);
 let signup=!hasAccount;
 function mode(v,msg){signup=v;h.textContent=v?'Create admin account':'Welcome back';sub.textContent=v?'First-time setup — create your administrator login.':'Sign in to your admin dashboard.';btn.textContent=v?'Create account':'Sign in';document.getElementById('signInTab').className=v?'btn secondary':'btn';document.getElementById('signUpTab').className=v?'btn':'btn secondary';confirmLabel.classList.toggle('hidden',!v);confirm.classList.toggle('hidden',!v);confirm.required=v;if(msg){notice.textContent=msg;notice.classList.remove('hidden')}else notice.classList.add('hidden')}
 document.getElementById('signInTab').onclick=()=>mode(false,''); document.getElementById('signUpTab').onclick=()=>mode(true,'Create your first admin account.');
 form.onsubmit=async e=>{e.preventDefault();const password=document.getElementById('password').value;if(signup&&password!==confirm.value)return mode(true,'Passwords do not match.');if(signup&&password.length<8)return mode(true,'Password must be at least 8 characters.');btn.disabled=true;try{const r=await fetch('/dashboard/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:document.getElementById('username').value,password})});if(r.ok){showApp();refresh()}else{const d=await r.json().catch(()=>({}));mode(signup,d.detail||(signup?'Account could not be created.':'Invalid credentials.'))}}finally{btn.disabled=false}};
 mode(signup,signup?'Welcome! Create your admin username and password to begin.':'');
})();
</script>'''
    html = html.replace('</body>', setup_script + '</body>')
    return HTMLResponse(html)
