SEARCH_UI_SCRIPT = r'''<script>
(function(){
  const esc=v=>String(v??'').replace(/[&<>\\"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','\\':'&#92;','"':'&quot;',"'":'&#39;'}[m]));
  const safeHref=v=>{try{const u=new URL(String(v||''),window.location.origin);return ['http:','https:'].includes(u.protocol)?esc(u.href):'#'}catch(e){return '#'}};
  const title=document.getElementById('title'), content=document.getElementById('content');
  let options=null, rendering=false;
  async function loadOptions(){if(options)return options;const r=await fetch('/research/options');if(!r.ok)throw new Error('Could not load research options.');options=await r.json();return options;}
  async function renderSearch(){
    if(!title||!content||title.textContent!=='Research'||rendering)return; rendering=true;
    try{
      const o=await loadOptions();
      content.innerHTML=`<div class="panel search-hero"><div class="section-head"><div><span class="status next">Research Intelligence</span><h2 style="margin:10px 0 4px">Find high-value problems and opportunities</h2><div class="muted">Discover, classify, score and rank signals across configured sources.</div></div><span class="status ok">Live pipeline</span></div><div class="search-box"><div class="field"><label>Topic, keyword or question</label><input id="researchQuery" maxlength="500" placeholder="e.g. problems website owners face after updates" autofocus></div><div class="grid2"><div class="field"><label>Category</label><select id="researchCategory"><option value="all">All categories</option>${o.categories.map(x=>`<option value="${esc(x)}">${esc(x.replace(/_/g,' '))}</option>`).join('')}</select></div><div class="field"><label>Intent</label><select id="researchIntent"><option value="all">All intents</option>${o.intents.map(x=>`<option value="${esc(x)}">${esc(x.replace(/_/g,' '))}</option>`).join('')}</select></div></div><div class="field"><label>Sources</label><div class="provider-grid source-grid">${o.sources.map(x=>`<label class="provider source-option ${x.enabled?'':'disabled'}"><span><input type="checkbox" class="researchSource" value="${esc(x.id)}" ${x.enabled?'checked':''} ${x.enabled?'':'disabled'}><strong>${esc(x.name)}</strong></span><small>${esc(x.note||'Configured research source')}</small></label>`).join('')}</div></div><div class="grid2"><div class="field"><label>Time range</label><select id="researchTime">${o.time_ranges.map(x=>`<option value="${esc(x)}" ${x==='30d'?'selected':''}>${esc(x)}</option>`).join('')}</select></div><div class="field"><label>Research depth</label><select id="researchMode"><option value="quick">Quick · fastest scan</option><option value="standard" selected>Standard · balanced</option><option value="deep">Deep · maximum result set</option></select></div></div><div class="search-actions"><button class="btn" id="runResearchSearch">Run research</button><button class="btn secondary" id="clearResearch">Clear</button><span id="researchStatus" class="help" role="status" aria-live="polite"></span></div></div></div><div class="panel hidden" id="researchResults"><div class="section-head"><div><h2>Research Results</h2><div class="muted" id="researchSummary"></div></div><span id="resultState" class="status next"></span></div><div id="researchResultList" class="list"></div></div>`;
      document.getElementById('runResearchSearch').onclick=runSearch;
      document.getElementById('clearResearch').onclick=()=>{document.getElementById('researchQuery').value='';document.getElementById('researchResults').classList.add('hidden');document.getElementById('researchStatus').textContent='';document.getElementById('researchQuery').focus()};
      document.getElementById('researchQuery').addEventListener('keydown',e=>{if(e.key==='Enter')runSearch()});
    }catch(e){content.innerHTML=`<div class="panel"><div class="notice">${esc(e.message)}</div></div>`}
    finally{rendering=false}
  }
  async function runSearch(){
    const b=document.getElementById('runResearchSearch'),status=document.getElementById('researchStatus'); if(!b)return;
    b.disabled=true;b.textContent='Searching…';status.textContent='Collecting, filtering, classifying and scoring results…';
    try{
      const mode=document.getElementById('researchMode').value;
      const sources=[...document.querySelectorAll('.researchSource:checked')].map(x=>x.value);
      const payload={query:document.getElementById('researchQuery').value,sources,category:document.getElementById('researchCategory').value,intent:document.getElementById('researchIntent').value,time_range:document.getElementById('researchTime').value,mode,limit:mode==='deep'?100:mode==='quick'?20:50};
      const r=await fetch('/research/search',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});const d=await r.json().catch(()=>({}));if(!r.ok)throw new Error(d.detail||'Research search failed.');renderResults(d);status.textContent=d.failed_sources?.length?`Completed with source issues: ${d.failed_sources.join(', ')}`:'Research completed successfully.';
    }catch(e){status.textContent=e.message;document.getElementById('resultState').textContent='Search failed'}finally{b.disabled=false;b.textContent='Run research'}
  }
  function renderResults(d){
    const box=document.getElementById('researchResults'),list=document.getElementById('researchResultList');box.classList.remove('hidden');const items=d.items||[];
    document.getElementById('researchSummary').textContent=`${Number(d.total||items.length)} unique results · ranked by relevance, opportunity and trend`;document.getElementById('resultState').textContent=items.length?'Results ready':'No matches';
    list.innerHTML=items.length?items.map(x=>`<article class="item result-card"><div class="section-head"><div><strong>${esc(x.title)}</strong><div class="muted result-meta">${esc(x.source)} · ${esc(x.category)} · ${esc(x.intent)}</div></div><span class="status ${Number(x.opportunity)>=70?'ok':Number(x.opportunity)>=45?'next':''}">Opportunity ${Number(x.opportunity)||0}</span></div><div class="score-row"><span class="status">Relevance ${Number(x.relevance)||0}</span><span class="status">Trend ${Number(x.trend)||0}</span><span class="status">Score ${Number(x.score)||0}</span><span class="status">${Number(x.comments)||0} comments</span></div><p>${esc(String(x.body||'').slice(0,650))}</p><div class="result-actions"><a class="btn secondary" href="${safeHref(x.url)}" target="_blank" rel="noopener noreferrer">View source</a><button class="btn secondary" data-copy="${esc((x.title||'')+' — '+(x.url||''))}">Copy</button><button class="btn" data-analyze="${Number(x.id||0)}">Analyze</button></div></article>`).join(''):'<div class="empty-state"><strong>No matching research signals</strong><div class="muted">Try a broader topic, another category or a longer time range.</div></div>';
    list.querySelectorAll('[data-copy]').forEach(b=>b.onclick=async()=>{try{await navigator.clipboard.writeText(b.dataset.copy||'');b.textContent='Copied';setTimeout(()=>b.textContent='Copy',1200)}catch(e){}});
    list.querySelectorAll('[data-analyze]').forEach(b=>b.onclick=()=>{window.current='ai-results';if(typeof window.refresh==='function')window.refresh()});
  }
  const original=window.refresh;window.refresh=async function(){if(window.current==='research')return renderSearch();return original?original.apply(this,arguments):undefined};
  new MutationObserver(()=>{if(title&&title.textContent==='Research')renderSearch()}).observe(document.documentElement,{subtree:true,childList:true,characterData:true});setTimeout(()=>{if(title&&title.textContent==='Research')renderSearch()},400);
})();
</script>'''
