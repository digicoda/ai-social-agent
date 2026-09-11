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
    if not _configured(): return False
    if not has_users(settings.database_url):
        if not create_admin(settings.database_url, username, password): return False
    elif not authenticate(settings.database_url, username, password): return False
    request.session.clear(); request.session["authenticated"] = True; request.session["role"] = "admin"
    return True


def dashboard_signup(request: Request, username: str, password: str) -> bool:
    if has_users(get_settings().database_url): return False
    return dashboard_login(request, username, password)


def dashboard_logout(request: Request) -> RedirectResponse:
    request.session.clear(); return RedirectResponse("/dashboard", status_code=303)


def dashboard_page(request: Request) -> HTMLResponse:
    path = DASHBOARD_DIR / "index.html"
    html = path.read_text(encoding="utf-8")
    settings = get_settings()
    account_exists = has_users(settings.database_url)
    html = html.replace("__AUTH_CONFIGURED__", "true" if _configured() else "false")
    html = html.replace("__HAS_ACCOUNT__", "true" if account_exists else "false")
    html = html.replace("__AUTHENTICATED__", "true" if request.session.get("authenticated") else "false")
    update_script = '''<script>
(function(){
  function installUpdatePanel(){
    const title=document.getElementById('title'), content=document.getElementById('content');
    if(!title||!content||title.textContent!=='System'||document.getElementById('softwareUpdatePanel')) return;
    const panel=document.createElement('div'); panel.id='softwareUpdatePanel'; panel.className='panel';
    panel.innerHTML='<div class="section-head"><div><h2>Software Update</h2><div class="muted">Windows Desktop updates stop the agent, install the verified release, preserve your data/configuration, restart the service and check health.</div></div><button id="updateAgentBtn" class="btn">Check &amp; Update</button></div><div id="updateAgentStatus" class="help">Use this only on the Windows Desktop edition.</div>';
    content.appendChild(panel);
    document.getElementById('updateAgentBtn').onclick=async function(){
      if(!confirm('Start the AI Social Agent update now? The service will restart during installation.')) return;
      const b=this, status=document.getElementById('updateAgentStatus'); b.disabled=true; b.textContent='Starting update…'; status.textContent='Preparing update. Keep this dashboard open; the service will restart automatically.';
      try{const r=await fetch('/system/update',{method:'POST'});const d=await r.json().catch(()=>({}));if(!r.ok)throw new Error(d.detail||'Update could not be started.');status.textContent=d.message||'Update started.';}
      catch(e){status.textContent=e.message;b.disabled=false;b.textContent='Check & Update';}
    };
  }
  new MutationObserver(installUpdatePanel).observe(document.documentElement,{subtree:true,childList:true});
  setTimeout(installUpdatePanel,300);
})();
</script>'''
    html = html.replace("</body>", update_script + "</body>")
    if not account_exists:
        html = html.replace("</body>", '''<script>
(function(){
 const form=document.getElementById('loginForm'); if(!form)return;
 form.onsubmit=async function(e){e.preventDefault();const p=document.getElementById('password').value;
  if(p!==document.getElementById('confirmPassword').value)return setAuthMode(true,'Passwords do not match.');
  if(p.length<8)return setAuthMode(true,'Password must be at least 8 characters.');
  const b=document.getElementById('authSubmit');b.disabled=true;
  try{const r=await fetch('/dashboard/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:document.getElementById('username').value,password:p})});
   if(r.ok){document.getElementById('password').value='';document.getElementById('confirmPassword').value='';setAuthMode(false,'Account created successfully. Please sign in.');}
   else{const d=await r.json().catch(()=>({}));setAuthMode(true,d.detail||'Account could not be created.');}
  }finally{b.disabled=false;}
 };
})();
</script></body>''')
    else:
        html = html.replace("</body>", '''<script>
(function(){const b=document.getElementById('signUpTab');if(b)b.style.display='none';})();
</script></body>''')
    return HTMLResponse(html)
