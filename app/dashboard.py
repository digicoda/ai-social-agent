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
    search_script = '''<script>
(function(){
  const esc=v=>String(v??'').replace(/[&<>\"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}[m]));
  const title=document.getElementById('title'), content=document.getElementById('content');
  let options=null, lastSignature='';
  async function loadOptions(){if(options)return options;const r=await fetch('/research/options');if(!r.ok)throw new Error('Could not load research options.');options=await r.json();return options;}
  async function renderSearch(){
    if(!title||!content||title.textContent!=='Research')return;
    const sig=title.textContent+'|research'; if(lastSignature===sig&&document.getElementById('researchSearchPanel'))return; lastSignature=sig;
    try{const o=await loadOptions();content.innerHTML=`
      <div class="panel" id="researchSearchPanel"><div class="section-head"><div><h2>Research Intelligence</h2><div class="muted">Discover problems, questions, trends and opportunities across configured research sources.</div></div><span class="status next">Configurable</span></div>
      <div class="field"><label>Research topic, keyword or question</label><input id="researchQuery" maxlength="500" placeholder="e.g. problems website owners face after updates"></div>
      <div class="grid2"><div class="field"><label>Category</label><select id="researchCategory"><option value="all">All categories</option>${o.categories.map(x=>`<option value="${esc(x)}">${esc(x.replace(/_/g,' '))}</option>`).join('')}</select></div><div class="field"><label>Intent</label><select id="researchIntent"><option value="all">All intents</option>${o.intents.map(x=>`<option value="${esc(x)}">${esc(x.replace(/_/g,' '))}</option>`).join('')}</select></div></div>
      <div class="field"><label>Sources</label><div class="provider-grid">${o.sources.map(x=>`<label class="provider" style="cursor:pointer"><input type="checkbox" class="researchSource" value="${esc(x.id)}" ${x.enabled?'checked':''} ${x.enabled?'':'disabled'} style="width:auto;margin-right:8px"><strong>${esc(x.name)}</strong><div class="help">${esc(x.note||'Live source')}</div></label>`).join('')}</div></div>
      <div class="grid2"><div class="field"><label>Time range</label><select id="researchTime">${o.time_ranges.map(x=>`<option value="${x}" ${x==='30d'?'selected':''}>${esc(x)}</option>`).join('')}</select></div><div class="field"><label>Research depth</label><select id="researchMode"><option value="quick">Quick — fastest scan</option><option value="standard" selected>Standard — balanced</option><option value="deep">Deep — maximum result set</option></select></div></div>
      <div class="row"><button class="btn" id="runResearchSearch">Run research</button><button class="btn secondary" id="clearResearch">Clear</button></div><div id="researchStatus" class="help" style="margin-top:10px"></div></div>
      <div class="panel hidden" id="researchResults"><div class="section-head"><div><h2>Research Results</h2><div class="muted" id="researchSummary"></div></div></div><div id="researchResultList" class="list"></div></div>`;
      document.getElementById('runResearchSearch').onclick=runSearch;
      document.getElementById('clearResearch').onclick=()=>{document.getElementById('researchQuery').value='';document.getElementById('researchResults').classList.add('hidden');document.getElementById('researchStatus').textContent='';};
    }catch(e){content.innerHTML=`<div class="panel"><p>${esc(e.message)}</p></div>`}
  }
  async function runSearch(){
    const b=document.getElementById('runResearchSearch'), status=document.getElementById('researchStatus');b.disabled=true;b.textContent='Searching…';status.textContent='Collecting, filtering, classifying and scoring results…';
    try{const sources=[...document.querySelectorAll('.researchSource:checked')].map(x=>x.value);const payload={query:document.getElementById('researchQuery').value,sources,category:document.getElementById('researchCategory').value,intent:document.getElementById('researchIntent').value,time_range:document.getElementById('researchTime').value,mode:document.getElementById('researchMode').value,limit:document.getElementById('researchMode').value==='deep'?100:50};const r=await fetch('/research/search',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});const d=await r.json();if(!r.ok)throw new Error(d.detail||'Research search failed.');renderResults(d);status.textContent=d.failed_sources.length?`Completed with source issues: ${d.failed_sources.join(', ')}`:'Research completed successfully.';}catch(e){status.textContent=e.message}finally{b.disabled=false;b.textContent='Run research';}
  }
  function renderResults(d){const box=document.getElementById('researchResults'), list=document.getElementById('researchResultList');box.classList.remove('hidden');document.getElementById('researchSummary').textContent=`${d.total} unique results · ranked by relevance, opportunity and trend`;
    list.innerHTML=d.items.length?d.items.map(x=>`<div class="item"><div class="section-head"><strong>${esc(x.title)}</strong><span class="status ${x.opportunity>=70?'ok':x.opportunity>=45?'next':''}">Opportunity ${x.opportunity}</span></div><div class="row"><span class="status">${esc(x.source)}</span><span class="status">${esc(x.category)}</span><span class="status">${esc(x.intent)}</span><span class="status">Relevance ${x.relevance}</span><span class="status">Trend ${x.trend}</span><span class="status">${x.score} score · ${x.comments} comments</span></div><p>${esc((x.body||'').slice(0,500))}</p><div class="row"><a class="btn secondary" href="${esc(x.url)}" target="_blank" rel="noopener">View source</a><button class="btn secondary" onclick="navigator.clipboard?.writeText(${JSON.stringify(x.title+' — '+x.url)});this.textContent='Copied'">Copy</button></div></div>`).join(''):'<p class="muted">No matching results. Try a broader topic, category, intent or time range.</p>';
  }
  new MutationObserver(()=>{if(title&&title.textContent==='Research')renderSearch();}).observe(document.documentElement,{subtree:true,childList:true,characterData:true});
  setTimeout(()=>{if(title&&title.textContent==='Research')renderSearch();},500);
})();
</script>'''
    html = html.replace("</body>", update_script + search_script + "</body>")
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
