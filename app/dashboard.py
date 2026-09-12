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
    if has_users(get_settings().database_url):
        return False
    return dashboard_login(request, username, password)


def dashboard_logout(request: Request) -> RedirectResponse:
    request.session.clear()
    return RedirectResponse("/dashboard", status_code=303)


def dashboard_page(request: Request) -> HTMLResponse:
    path = DASHBOARD_DIR / "index.html"
    html = path.read_text(encoding="utf-8")
    settings = get_settings()
    account_exists = has_users(settings.database_url)
    html = html.replace("__AUTH_CONFIGURED__", "true" if _configured() else "false")
    html = html.replace("__HAS_ACCOUNT__", "true" if account_exists else "false")
    html = html.replace("__AUTHENTICATED__", "true" if request.session.get("authenticated") else "false")

    intelligence_script = '''<script>
(function(){
  function installAI(){
    const nav=document.querySelector('.nav'), content=document.getElementById('content');
    if(!nav||!content||document.getElementById('aiResultsNav')) return;
    const btn=document.createElement('button'); btn.id='aiResultsNav'; btn.dataset.view='ai-results'; btn.textContent='AI Analysis Results';
    const research=nav.querySelector('[data-view="research"]'); research ? research.insertAdjacentElement('afterend',btn) : nav.insertBefore(btn,nav.firstChild);
    btn.addEventListener('click',function(){window.current='ai-results'; if(typeof window.refresh==='function')window.refresh();});
  }
  async function renderAIResults(){
    const content=document.getElementById('content'); if(!content)return;
    content.innerHTML='<div class="panel"><div class="section-head"><div><h2>AI Analysis Results</h2><div class="muted">Clean, deduplicated and scored research insights.</div></div><div class="row"><button class="btn" id="runAI">Analyze research</button><button class="btn secondary" id="refreshAI">Refresh</button></div></div><div id="aiSummary" class="cards"></div><div id="aiClusters" class="list" style="margin-top:16px"></div><div id="aiItems" class="list" style="margin-top:16px"></div></div>';
    async function load(){
      const r=await fetch('/intelligence/results'); if(!r.ok)throw new Error('Could not load AI analysis results.'); const d=await r.json();
      const items=d.items||[], clusters=d.clusters||[];
      const avg=items.length?Math.round(items.reduce((a,x)=>a+Number(x.opportunity_score||0),0)/items.length):0;
      document.getElementById('aiSummary').innerHTML='<div class="card"><div class="muted">Analyzed</div><div class="metric">'+items.filter(x=>!x.duplicate_of).length+'</div></div><div class="card"><div class="muted">Clusters</div><div class="metric">'+clusters.length+'</div></div><div class="card"><div class="muted">Avg opportunity</div><div class="metric">'+avg+'</div></div><div class="card"><div class="muted">Top opportunity</div><div class="metric">'+(items[0]?.opportunity_score||0)+'</div></div>';
      document.getElementById('aiClusters').innerHTML=clusters.length?'<div class="panel"><h2>Research clusters</h2>'+clusters.slice(0,12).map(c=>'<div class="item"><strong>'+escAI(c.label)+'</strong><div class="muted">'+Number(c.member_count||0)+' items · opportunity '+Number(c.opportunity_score||0)+' · '+escAI(c.trend_label)+'</div><p>'+escAI(c.content_angle)+'</p></div>').join('')+'</div>':'<div class="item muted">No clusters yet. Run analysis after collecting research.</div>';
      document.getElementById('aiItems').innerHTML=items.length?'<div class="panel"><h2>Ranked insights</h2>'+items.slice(0,50).map(x=>'<div class="item"><strong>'+escAI(x.title)+'</strong><div class="muted">'+escAI(x.source)+' · '+escAI(x.category)+' · '+escAI(x.intent)+' · opportunity '+Number(x.opportunity_score||0)+' · trend '+escAI(x.trend_label)+'</div><p><b>Pain:</b> '+escAI(x.pain_point)+'</p><p><b>Angle:</b> '+escAI(x.solution_angle)+'</p><div class="row"><a class="btn secondary" target="_blank" rel="noopener noreferrer" href="'+safeHrefAI(x.url)+'">Open source</a></div></div>').join('')+'</div>':'<div class="item muted">No AI results yet.</div>';
    }
    document.getElementById('runAI').onclick=async function(){this.disabled=true;this.textContent='Analyzing…';try{const r=await fetch('/intelligence/run',{method:'POST'});if(!r.ok)throw new Error((await r.json().catch(()=>({}))).detail||'AI analysis failed.');const d=await r.json();toastAI('Analyzed '+Number(d.analyzed||0)+' items · '+Number(d.duplicates||0)+' duplicates · '+Number(d.clusters||0)+' clusters.');await load();}catch(e){toastAI(e.message)}finally{this.disabled=false;this.textContent='Analyze research'}};
    document.getElementById('refreshAI').onclick=load; await load();
  }
  function escAI(v){return String(v??'').replace(/[&<>\\"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','\\':'&#92;','"':'&quot;',"'":'&#39;'}[m]))}
  function safeHrefAI(v){try{const u=new URL(String(v||''),window.location.origin);return ['http:','https:'].includes(u.protocol)?escAI(u.href):'#'}catch(e){return '#'}}
  function toastAI(msg){const t=document.getElementById('toast');if(t){t.textContent=msg;t.classList.add('show');setTimeout(()=>t.classList.remove('show'),3500)}}
  const original=window.refresh;
  window.refresh=async function(){if(window.current==='ai-results')return renderAIResults();return original?original.apply(this,arguments):undefined};
  const observer=new MutationObserver(installAI); observer.observe(document.documentElement,{subtree:true,childList:true}); setTimeout(installAI,300);
  window.renderAIResults=renderAIResults;
})();
</script>'''

    provider_script = '''<script>
(function(){
  function installProviderControls(){
    const title=document.getElementById('title'), content=document.getElementById('content');
    if(!title||!content||title.textContent!=='System'||document.getElementById('aiProviderPanel')) return;
    const panel=document.createElement('div'); panel.id='aiProviderPanel'; panel.className='panel';
    panel.innerHTML='<div class="section-head"><div><h2>AI Providers</h2><div class="muted">Choose the analysis engine. No extra Python AI SDK is required.</div></div><button id="saveAIProviders" class="btn">Save AI settings</button></div><div class="grid2"><div><div class="field"><label>Active provider</label><select id="ai_provider"><option value="gemini">Google Gemini</option><option value="openai">OpenAI</option><option value="huggingface">Hugging Face</option></select></div><div class="field"><label>Gemini API key</label><input id="gemini_api_key2" type="password" autocomplete="new-password" placeholder="Leave blank to keep existing key"></div><div class="field"><label>OpenAI API key</label><input id="openai_api_key2" type="password" autocomplete="new-password" placeholder="Leave blank to keep existing key"></div><div class="field"><label>Hugging Face token</label><input id="huggingface_api_key2" type="password" autocomplete="new-password" placeholder="Leave blank to keep existing token"></div></div><div><div class="field"><label>Gemini model</label><input id="gemini_model2" value="gemini-2.5-flash"></div><div class="field"><label>OpenAI model</label><input id="openai_model2" value="gpt-4o-mini"></div><div class="field"><label>Hugging Face model</label><input id="huggingface_model2" value="deepseek-ai/DeepSeek-V3-0324"></div></div></div><div id="aiProviderStatus" class="help">Loading provider settings…</div>';
    content.appendChild(panel);
    (async function(){try{const r=await fetch('/system/settings');if(!r.ok)return;const d=await r.json(),s=d.settings;document.getElementById('ai_provider').value=s.ai_provider||'gemini';document.getElementById('gemini_model2').value=s.gemini_model||'gemini-2.5-flash';document.getElementById('openai_model2').value=s.openai_model||'gpt-4o-mini';document.getElementById('huggingface_model2').value=s.huggingface_model||'deepseek-ai/DeepSeek-V3-0324';document.getElementById('aiProviderStatus').textContent=(d.providers||[]).filter(x=>['gemini','openai','huggingface'].includes(x.id)).map(x=>x.name+': '+x.status).join(' · ');}catch(e){}})();
    document.getElementById('saveAIProviders').onclick=async function(){const values={ai_provider:document.getElementById('ai_provider').value,gemini_model:document.getElementById('gemini_model2').value,openai_model:document.getElementById('openai_model2').value,huggingface_model:document.getElementById('huggingface_model2').value};[['gemini_api_key2','gemini_api_key'],['openai_api_key2','openai_api_key'],['huggingface_api_key2','huggingface_api_key']].forEach(([a,b])=>{const v=document.getElementById(a).value;if(v)values[b]=v});const r=await fetch('/system/settings',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({values})});const d=await r.json().catch(()=>({}));document.getElementById('aiProviderStatus').textContent=r.ok?'AI provider settings saved.':(d.detail||'Could not save settings.');};
  }
  new MutationObserver(installProviderControls).observe(document.documentElement,{subtree:true,childList:true}); setTimeout(installProviderControls,500);
})();
</script>'''

    update_script = '''<script>
(function(){function installUpdatePanel(){const title=document.getElementById('title'),content=document.getElementById('content');if(!title||!content||title.textContent!=='System'||document.getElementById('softwareUpdatePanel'))return;const panel=document.createElement('div');panel.id='softwareUpdatePanel';panel.className='panel';panel.innerHTML='<div class="section-head"><div><h2>Software Update</h2><div class="muted">Windows Desktop updates preserve the database and configuration.</div></div><button id="updateAgentBtn" class="btn">Check &amp; Update</button></div><div id="updateAgentStatus" class="help">Use this on the Windows Desktop edition.</div>';content.appendChild(panel);document.getElementById('updateAgentBtn').onclick=async function(){if(!confirm('Start the AI Social Agent update now?'))return;const b=this,s=document.getElementById('updateAgentStatus');b.disabled=true;b.textContent='Starting update…';try{const r=await fetch('/system/update',{method:'POST'}),d=await r.json().catch(()=>({}));if(!r.ok)throw new Error(d.detail||'Update could not be started.');s.textContent=d.message||'Update started.'}catch(e){s.textContent=e.message;b.disabled=false;b.textContent='Check & Update'}}}new MutationObserver(installUpdatePanel).observe(document.documentElement,{subtree:true,childList:true});setTimeout(installUpdatePanel,300)})();
</script>'''

    security_script = '''<script>
(function(){
  window.esc=function(v){return String(v??'').replace(/[&<>\\"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','\\':'&#92;','"':'&quot;',"'":'&#39;'}[m]))};
  window.safeHref=function(v){try{const u=new URL(String(v||''),window.location.origin);return ['http:','https:'].includes(u.protocol)?window.esc(u.href):'#'}catch(e){return '#'}};
})();
</script>'''

    search_script = (DASHBOARD_DIR / "search_ui.js").read_text(encoding="utf-8")
    html = html.replace("</body>", intelligence_script + provider_script + update_script + security_script + search_script + "</body>")
    if not account_exists:
        html = html.replace("</body>", '''<script>(function(){const form=document.getElementById('loginForm');if(!form)return;form.onsubmit=async function(e){e.preventDefault();const p=document.getElementById('password').value;if(p!==document.getElementById('confirmPassword').value)return setAuthMode(true,'Passwords do not match.');if(p.length<8)return setAuthMode(true,'Password must be at least 8 characters.');const b=document.getElementById('authSubmit');b.disabled=true;try{const r=await fetch('/dashboard/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:document.getElementById('username').value,password:p})});if(r.ok){document.getElementById('password').value='';document.getElementById('confirmPassword').value='';setAuthMode(false,'Account created successfully. Please sign in.')}else{const d=await r.json().catch(()=>({}));setAuthMode(true,d.detail||'Account could not be created.')}}finally{b.disabled=false}}})();</script></body>''')
    else:
        html = html.replace("</body>", '''<script>(function(){const b=document.getElementById('signUpTab');if(b)b.style.display='none'})();</script></body>''')
    return HTMLResponse(html)
