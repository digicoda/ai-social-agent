<style>
/* Desktop-first UI polish: compact controls, balanced forms, clearer hierarchy. */
.content{padding-top:22px}.panel{padding:18px}.card{padding:14px}.action-card,.action-box,.social-box,.content-card,.side-card{padding:14px}.field{margin-bottom:10px}.field input,.field textarea,.field select{max-width:100%;min-height:38px}.field textarea{min-height:96px}.btn{width:auto!important;display:inline-flex;align-items:center;justify-content:center;white-space:nowrap}.toolbar .btn,.table-actions .btn{flex:0 0 auto}.config-footer{padding-top:12px}.provider-grid{grid-template-columns:repeat(2,minmax(0,1fr));align-items:start}.provider{padding:14px}.provider-form{padding:13px}.model-row{align-items:end}.model-row .btn{min-height:38px}.research-controls{grid-template-columns:minmax(280px,2fr) minmax(150px,1fr) minmax(150px,1fr)}.research-results{margin-top:12px}.research-results .panel{padding:14px}.research-results .item{padding:12px}.approval-preview{align-items:start}.chart{padding-top:10px}.analytics-line-card{margin-top:14px}.analytics-line{width:100%;height:220px;display:block}.analytics-line-grid{stroke:#e7e9ef;stroke-width:1}.analytics-line-path{fill:none;stroke:#7c5cff;stroke-width:3;stroke-linecap:round;stroke-linejoin:round}.analytics-line-point{fill:#fff;stroke:#7c5cff;stroke-width:2}.analytics-axis{font-size:10px;fill:#858a95}.integration-provider-grid,.integration-social-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px}.integration-social-grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.integration-provider-card,.integration-social-card{border:1px solid var(--line);border-radius:11px;background:#fff;padding:14px}.integration-social-card .toolbar{margin-top:12px}.integration-provider-card .statusline,.integration-social-card .statusline{align-items:flex-start}.integration-section{margin-top:14px}.integration-section:first-child{margin-top:0}.integration-section .panel{padding:16px}.connection-meta{display:flex;align-items:center;gap:7px;flex-wrap:wrap;margin-top:7px}.connection-action{margin-left:auto}.integration-provider-grid .integration-provider-card{min-width:0}.integration-provider-card strong{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.integration-provider-card .connection-meta{margin-top:5px}.calendar-form{display:grid;grid-template-columns:minmax(240px,1.35fr) minmax(150px,.7fr) minmax(210px,.9fr);gap:12px;align-items:end}.calendar-form .field{margin:0}.calendar-toolbar{display:flex;align-items:center;gap:8px;flex-wrap:wrap}.calendar-jobs{margin-top:14px}.calendar-jobs table th,.calendar-jobs table td{vertical-align:middle}.settings-layout{max-width:1120px}.settings-layout .panel{padding:16px}.settings-layout .action-grid{align-items:start}.settings-layout .field:last-child{margin-bottom:0}.settings-layout .config-pane{padding:2px 0}.inline-fields{display:flex;gap:10px;align-items:end;flex-wrap:wrap}.inline-fields .field{flex:1 1 180px;margin:0}.compact-note{font-size:11px;color:var(--muted);line-height:1.5}.integration-social-card .btn{font-size:11px;padding:8px 11px}
.source-multi-native{display:none!important}.source-multi{position:relative}.source-multi-trigger{width:100%;min-height:38px;padding:8px 34px 8px 10px;border:1px solid #d9dce4;border-radius:8px;background:#fff;color:#242833;text-align:left;font-size:12px;cursor:pointer;position:relative}.source-multi-trigger:after{content:'▾';position:absolute;right:11px;top:9px;color:#737887}.source-multi-menu{position:absolute;left:0;right:0;top:calc(100% + 5px);z-index:70;display:none;max-height:240px;overflow:auto;background:#fff;border:1px solid #dfe2e9;border-radius:9px;box-shadow:0 12px 30px rgba(20,24,35,.14);padding:6px}.source-multi.open .source-multi-menu{display:block}.source-multi-option{display:flex;align-items:center;gap:8px;padding:8px 7px;border-radius:6px;font-size:11px;color:#333843;cursor:pointer}.source-multi-option:hover{background:#f5f6f9}.source-multi-option input{width:15px;height:15px;min-height:15px;margin:0}.research-results{min-width:0;max-width:100%;overflow:hidden}.research-results>.panel{min-width:0;max-width:100%;overflow:hidden}.research-results .list,.research-results .item{min-width:0;max-width:100%;overflow:hidden}.research-results .item p{overflow-wrap:anywhere;word-break:break-word}.research-results .item-title{min-width:0;overflow-wrap:anywhere;word-break:break-word}.research-results .statusline{min-width:0}.research-results .statusline>div{min-width:0;max-width:100%}.research-results .table-actions{max-width:100%}.research-results .btn{max-width:100%;overflow:hidden;text-overflow:ellipsis}.research-persist-note{margin-bottom:10px;padding:8px 10px;border:1px solid #e4e0ff;background:#f8f6ff;border-radius:8px;font-size:10px;color:#6655a8}
@media(max-width:1100px){.integration-provider-grid{grid-template-columns:repeat(3,minmax(0,1fr))}.calendar-form{grid-template-columns:1fr 1fr}.research-controls{grid-template-columns:1fr 1fr}.settings-layout{max-width:none}}
@media(max-width:900px){.integration-provider-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.integration-social-grid{grid-template-columns:1fr}.provider-grid,.social-grid,.action-grid,.approval-layout{grid-template-columns:1fr}}
@media(max-width:700px){.panel{padding:14px}.page-intro{margin-bottom:14px}.research-controls,.calendar-form{grid-template-columns:1fr}.inline-fields{display:grid;grid-template-columns:1fr}.model-row{display:grid;grid-template-columns:1fr}.model-row .btn{width:max-content!important}.config-footer{align-items:flex-start;flex-direction:column}.integration-provider-grid,.integration-social-grid{grid-template-columns:1fr}}
</style>
<script>
(function(){
  const $=id=>document.getElementById(id);
  const esc=v=>String(v??'').replace(/[&<>\\"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','\\':'&#92;','"':'&quot;',"'":'&#39;'}[m]));

  function patchSettings(){
    const root=$('content');
    if(!root||$('title')?.textContent!=='Settings')return;
    root.classList.add('settings-layout');
    root.querySelectorAll('.action-grid').forEach(g=>g.classList.add('settings-action-grid'));
    root.querySelectorAll('.provider-form').forEach(f=>f.querySelectorAll('.toolbar').forEach(t=>t.classList.add('provider-actions')));
  }

  function patchCalendar(){
    const root=$('content');
    if(!root||$('title')?.textContent!=='Calendar')return;
    const schedulePanel=[...root.querySelectorAll('.panel')].find(p=>p.querySelector('#scheduleDraft'));
    const form=schedulePanel?.querySelector('.grid.grid3');
    if(form)form.className='calendar-form';
    const save=$('saveSchedule');
    if(save&&schedulePanel&&!save.dataset.polished){
      save.dataset.polished='1';
      const row=document.createElement('div');row.className='calendar-toolbar';save.parentElement?.insertBefore(row,save);row.appendChild(save);const status=$('scheduleStatus');if(status)row.appendChild(status);
    }
    const panels=root.querySelectorAll('.panel');
    if(panels[panels.length-1])panels[panels.length-1].classList.add('calendar-jobs');
  }

  function patchIntegrations(){
    const root=$('content');
    if(!root||$('title')?.textContent!=='Integrations'||$('integrationPolished'))return;
    const outer=root.querySelector(':scope > .grid');
    if(!outer)return;
    const panels=[...outer.querySelectorAll(':scope > .panel')];
    if(panels.length<2)return;
    const publishing=panels[0],ai=panels[1];
    const aiItems=[...ai.querySelectorAll('.list > .item')];
    const socialItems=[...publishing.querySelectorAll('.social-box')];

    const aiWrap=document.createElement('div');aiWrap.id='integrationPolished';aiWrap.className='integration-section';
    aiWrap.innerHTML='<div class="panel"><div class="section-head"><div><h3>AI Provider Connections</h3><span>Manage AI provider connection status and configuration.</span></div><div class="toolbar"><button class="btn" id="configureProvidersBtn" type="button">Configure Provider</button></div></div><div class="integration-provider-grid" id="integrationProviderGrid"></div></div>';
    const aiGrid=aiWrap.querySelector('#integrationProviderGrid');
    aiItems.forEach(item=>{
      const name=item.querySelector('strong')?.textContent||'AI Provider';
      const status=item.querySelector('.chip')?.outerHTML||'<span class="chip">Not configured</span>';
      const card=document.createElement('div');card.className='integration-provider-card';
      card.innerHTML=`<div class="statusline"><div><strong>${esc(name)}</strong><div class="connection-meta">${status}</div></div></div>`;
      aiGrid.appendChild(card);
    });
    aiWrap.querySelector('#configureProvidersBtn').onclick=()=>{
      window.go('settings');
      setTimeout(()=>{
        const tabs=[...document.querySelectorAll('.config-tab')];
        const aiTab=tabs.find(t=>/ai|provider/i.test(t.textContent||''));
        if(aiTab)aiTab.click();
      },80);
    };

    const socialWrap=document.createElement('div');socialWrap.className='integration-section';
    socialWrap.innerHTML='<div class="panel"><div class="section-head"><div><h3>Social & Publishing Accounts</h3><span>Manage publishing destinations independently from AI providers.</span></div></div><div class="integration-social-grid" id="integrationSocialGrid"></div></div>';
    const socialGrid=socialWrap.querySelector('#integrationSocialGrid');socialItems.forEach(box=>{box.classList.add('integration-social-card');socialGrid.appendChild(box)});
    outer.replaceWith(aiWrap,socialWrap);
  }

  function sourceMultiSelect(){
    const root=$('content');
    if(!root||$('title')?.textContent!=='Research')return;
    const select=$('rs');
    if(!select||select.dataset.multiPolished)return;
    select.dataset.multiPolished='1';select.classList.add('source-multi-native');
    const wrap=document.createElement('div');wrap.className='source-multi';wrap.id='sourceMulti';
    const trigger=document.createElement('button');trigger.type='button';trigger.className='source-multi-trigger';trigger.setAttribute('aria-haspopup','listbox');
    const menu=document.createElement('div');menu.className='source-multi-menu';menu.setAttribute('role','listbox');menu.setAttribute('aria-multiselectable','true');
    [...select.options].forEach((opt,i)=>{
      const label=document.createElement('label');label.className='source-multi-option';
      const cb=document.createElement('input');cb.type='checkbox';cb.checked=opt.selected;cb.dataset.index=String(i);cb.setAttribute('aria-label',opt.textContent||opt.value);
      cb.onchange=()=>{opt.selected=cb.checked;updateSourceLabel();saveResearchState()};
      label.append(cb,document.createTextNode(opt.textContent||opt.value));menu.appendChild(label);
    });
    trigger.onclick=()=>wrap.classList.toggle('open');
    wrap.append(trigger,menu);select.parentElement?.insertBefore(wrap,select);
    const updateSourceLabel=()=>{const chosen=[...select.options].filter(o=>o.selected).map(o=>o.textContent.trim());trigger.textContent=chosen.length===select.options.length?'All sources':chosen.length?`${chosen.length} source${chosen.length===1?'':'s'} selected`:'No sources selected';trigger.setAttribute('aria-label',chosen.join(', ')||'No sources selected')};
    window.__updateResearchSourceLabel=updateSourceLabel;updateSourceLabel();
    if(!window.__sourceMultiDocBound){window.__sourceMultiDocBound=true;document.addEventListener('click',e=>{const active=document.querySelector('.source-multi.open');if(active&&!active.contains(e.target))active.classList.remove('open')});}
  }

  function saveResearchState(){
    const r=$('researchResults');
    if(!$('content')||$('title')?.textContent!=='Research'||!r)return;
    const hasResults=!!r.innerHTML.trim();
    const state=window.__researchState||{};
    const values={};['rq','rc','ri','rt','rm'].forEach(id=>{const el=$(id);if(el)values[id]=el.value});
    const rs=$('rs');if(rs)values.rs=[...rs.options].filter(o=>o.selected).map(o=>o.value);
    state.values=values;
    if(hasResults){state.resultsHTML=r.innerHTML;state.status=$('researchStatus')?.textContent||'';state.savedAt=Date.now()}
    window.__researchState=state;
    try{sessionStorage.setItem('aiSocialResearchState',JSON.stringify(state))}catch(e){}
  }

  function loadResearchState(){
    if(!window.__researchState){try{window.__researchState=JSON.parse(sessionStorage.getItem('aiSocialResearchState')||'null')||{}}catch(e){window.__researchState={}}}
    const state=window.__researchState||{};const r=$('researchResults');
    if(!r||!state.resultsHTML||r.dataset.restored)return;
    r.dataset.restored='1';
    r.innerHTML='<div class="research-persist-note">Previous research results are preserved while you move between dashboard pages.</div>'+state.resultsHTML;
    if($('researchStatus')&&state.status)$('researchStatus').textContent=state.status;
    const values=state.values||{};['rq','rc','ri','rt','rm'].forEach(id=>{const el=$(id);if(el&&values[id]!==undefined)el.value=values[id]});
    const rs=$('rs');if(rs&&Array.isArray(values.rs)){const selected=new Set(values.rs);[...rs.options].forEach(o=>o.selected=selected.has(o.value));const wrap=$('sourceMulti');if(wrap){wrap.querySelectorAll('input[type=checkbox]').forEach(cb=>{const o=rs.options[Number(cb.dataset.index)];if(o)cb.checked=o.selected});window.__updateResearchSourceLabel?.()}}
  }

  function bindResearchPersistence(){
    const root=$('content');
    if(!root||$('title')?.textContent!=='Research')return;
    sourceMultiSelect();
    loadResearchState();
    if(root.dataset.researchPersistenceBound)return;
    root.dataset.researchPersistenceBound='1';
    ['rq','rc','ri','rt','rm','rs'].forEach(id=>$(id)?.addEventListener('input',saveResearchState));
    ['rc','ri','rt','rm','rs'].forEach(id=>$(id)?.addEventListener('change',saveResearchState));
    const rr=$('researchResults');if(rr)new MutationObserver(()=>saveResearchState()).observe(rr,{childList:true,subtree:true});
  }

  function addAnalyticsLine(){
    const root=$('content');
    if(!root||$('title')?.textContent!=='Analytics'||$('analyticsLineCard'))return;
    const table=root.querySelector('table');if(!table)return;
    const rows=[...table.querySelectorAll('tbody tr')],counts={};
    rows.forEach(row=>{const cells=row.querySelectorAll('td');const date=(cells[4]?.textContent||'').trim();if(!date)return;const key=date.slice(0,10);counts[key]=(counts[key]||0)+1});
    const keys=Object.keys(counts).sort(),values=keys.map(k=>counts[k]),max=Math.max(1,...values);
    const width=760,height=210,left=42,right=16,top=18,bottom=34;
    const pts=values.map((v,i)=>{const x=keys.length===1?(width-left-right)/2+left:left+i*((width-left-right)/Math.max(1,keys.length-1));const y=top+(height-top-bottom)*(1-v/max);return [x,y]});
    const path=pts.map((p,i)=>(i?'L':'M')+p[0].toFixed(1)+' '+p[1].toFixed(1)).join(' ')||`M ${left} ${height-bottom}`;
    const labels=keys.length?keys:['No data'];
    const grid=[0,.5,1].map(f=>{const y=top+(height-top-bottom)*f;return `<line class="analytics-line-grid" x1="${left}" y1="${y}" x2="${width-right}" y2="${y}"/>`}).join('');
    const points=pts.map(p=>`<circle class="analytics-line-point" cx="${p[0]}" cy="${p[1]}" r="4"/>`).join('');
    const xlabels=labels.map((k,i)=>{const x=pts[i]?.[0]||left;return `<text class="analytics-axis" x="${x}" y="${height-10}" text-anchor="middle">${esc(k.slice(5)||k)}</text>`}).join('');
    const card=document.createElement('div');card.id='analyticsLineCard';card.className='panel analytics-line-card';
    card.innerHTML=`<div class="section-head"><div><h3>Publishing activity trend</h3><span>Attempts grouped by day from the publishing history.</span></div><span class="badge">${values.reduce((a,b)=>a+b,0)} attempts</span></div><svg class="analytics-line" viewBox="0 0 ${width} ${height}" role="img" aria-label="Publishing attempts by day">${grid}<path class="analytics-line-path" d="${path}"/>${points}${xlabels}</svg>`;root.appendChild(card);
  }

  function patch(){patchSettings();patchCalendar();patchIntegrations();bindResearchPersistence();addAnalyticsLine()}
  new MutationObserver(()=>setTimeout(patch,0)).observe(document.documentElement,{subtree:true,childList:true});
  [100,350,900].forEach(t=>setTimeout(patch,t));
})();
</script>
