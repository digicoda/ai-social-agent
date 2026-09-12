<style>
/* Desktop-first UI polish: compact controls, balanced forms, and clearer hierarchy. */
.content{padding-top:22px}.panel{padding:18px}.card{padding:14px}.action-card,.action-box,.social-box,.content-card,.side-card{padding:14px}.field{margin-bottom:10px}.field input,.field textarea,.field select{max-width:100%;min-height:38px}.field textarea{min-height:96px}.btn{width:auto!important;display:inline-flex;align-items:center;justify-content:center;white-space:nowrap}.toolbar .btn,.table-actions .btn{flex:0 0 auto}.config-footer{padding-top:12px}.provider-grid{grid-template-columns:repeat(2,minmax(0,1fr));align-items:start}.provider{padding:14px}.provider-form{padding:13px}.model-row{align-items:end}.model-row .btn{min-height:38px}.research-controls{grid-template-columns:minmax(280px,2fr) minmax(150px,1fr) minmax(150px,1fr)}.research-results{margin-top:12px}.research-results .panel{padding:14px}.research-results .item{padding:12px}.approval-preview{align-items:start}.chart{padding-top:10px}.analytics-line-card{margin-top:14px}.analytics-line{width:100%;height:220px;display:block}.analytics-line-grid{stroke:#e7e9ef;stroke-width:1}.analytics-line-path{fill:none;stroke:#7c5cff;stroke-width:3;stroke-linecap:round;stroke-linejoin:round}.analytics-line-point{fill:#fff;stroke:#7c5cff;stroke-width:2}.analytics-axis{font-size:10px;fill:#858a95}.integration-provider-grid,.integration-social-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.integration-provider-card,.integration-social-card{border:1px solid var(--line);border-radius:11px;background:#fff;padding:14px}.integration-provider-card .toolbar,.integration-social-card .toolbar{margin-top:12px}.integration-provider-card .statusline,.integration-social-card .statusline{align-items:flex-start}.integration-section{margin-top:14px}.integration-section:first-child{margin-top:0}.integration-section .panel{padding:16px}.connection-meta{display:flex;align-items:center;gap:7px;flex-wrap:wrap;margin-top:7px}.connection-action{margin-left:auto}.calendar-form{display:grid;grid-template-columns:minmax(240px,1.35fr) minmax(150px,.7fr) minmax(210px,.9fr);gap:12px;align-items:end}.calendar-form .field{margin:0}.calendar-toolbar{display:flex;align-items:center;gap:8px;flex-wrap:wrap}.calendar-jobs{margin-top:14px}.calendar-jobs table th,.calendar-jobs table td{vertical-align:middle}.settings-layout{max-width:1120px}.settings-layout .panel{padding:16px}.settings-layout .action-grid{align-items:start}.settings-layout .field:last-child{margin-bottom:0}.settings-layout .config-pane{padding:2px 0}.inline-fields{display:flex;gap:10px;align-items:end;flex-wrap:wrap}.inline-fields .field{flex:1 1 180px;margin:0}.compact-note{font-size:11px;color:var(--muted);line-height:1.5}.integration-provider-card .btn,.integration-social-card .btn{font-size:11px;padding:8px 11px}
@media(max-width:1000px){.calendar-form{grid-template-columns:1fr 1fr}.integration-provider-grid,.integration-social-grid{grid-template-columns:1fr}.research-controls{grid-template-columns:1fr 1fr}.settings-layout{max-width:none}}
@media(max-width:700px){.panel{padding:14px}.page-intro{margin-bottom:14px}.research-controls,.calendar-form{grid-template-columns:1fr}.inline-fields{display:grid;grid-template-columns:1fr}.model-row{display:grid;grid-template-columns:1fr}.model-row .btn{width:max-content!important}.config-footer{align-items:flex-start;flex-direction:column}.integration-provider-grid,.integration-social-grid{grid-template-columns:1fr}}
</style>
<script>
(function(){
  const $=id=>document.getElementById(id);
  const esc=v=>String(v??'').replace(/[&<>\\"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','\\':'&#92;','"':'&quot;',"'":'&#39;'}[m]));
  const wait=ms=>new Promise(r=>setTimeout(r,ms));

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
    const form=root.querySelector('.panel:nth-of-type(2) .grid.grid3');
    if(form)form.className='calendar-form';
    const save=$('saveSchedule');
    if(save){save.parentElement?.classList.add('calendar-toolbar');}
    const panels=root.querySelectorAll('.panel');
    if(panels[panels.length-1])panels[panels.length-1].classList.add('calendar-jobs');
  }

  function patchIntegrations(){
    const root=$('content');
    if(!root||$('title')?.textContent!=='Integrations'||$('integrationPolished'))return;
    const panels=[...root.querySelectorAll(':scope > .grid > .panel')];
    if(panels.length<2)return;
    const publishing=panels[0];
    const ai=panels[1];
    const aiItems=[...ai.querySelectorAll('.list > .item')];
    const socialItems=[...publishing.querySelectorAll('.social-box')];
    const socialWrap=document.createElement('div');
    socialWrap.className='integration-section';
    socialWrap.innerHTML='<div class="panel"><div class="section-head"><div><h3>Social & Publishing Accounts</h3><span>Manage publishing destinations independently from AI providers.</span></div></div><div class="integration-social-grid" id="integrationSocialGrid"></div></div>';
    const socialGrid=socialWrap.querySelector('#integrationSocialGrid');
    socialItems.forEach(box=>{box.classList.add('integration-social-card');socialGrid.appendChild(box)});
    const aiWrap=document.createElement('div');
    aiWrap.id='integrationPolished';
    aiWrap.className='integration-section';
    aiWrap.innerHTML='<div class="panel"><div class="section-head"><div><h3>AI Provider Connections</h3><span>Each provider shows its current connection state and a direct configuration action.</span></div></div><div class="integration-provider-grid" id="integrationProviderGrid"></div></div>';
    const aiGrid=aiWrap.querySelector('#integrationProviderGrid');
    aiItems.forEach(item=>{
      const name=item.querySelector('strong')?.textContent||'AI Provider';
      const status=item.querySelector('.chip')?.outerHTML||'<span class="chip">Not configured</span>';
      const card=document.createElement('div');
      card.className='integration-provider-card';
      card.innerHTML=`<div class="statusline"><div><strong>${esc(name)}</strong><div class="connection-meta"><span class="tiny muted">AI model connection</span>${status}</div></div></div><div class="toolbar"><button class="btn secondary" type="button">Configure provider</button></div>`;
      card.querySelector('button').onclick=()=>window.go('settings');
      aiGrid.appendChild(card);
    });
    const outer=root.querySelector(':scope > .grid');
    if(outer){outer.replaceWith(aiWrap,socialWrap)}
  }

  function addAnalyticsLine(){
    const root=$('content');
    if(!root||$('title')?.textContent!=='Analytics'||$('analyticsLineCard'))return;
    const table=root.querySelector('table');
    if(!table)return;
    const rows=[...table.querySelectorAll('tbody tr')];
    const counts={};
    rows.forEach(row=>{const cells=row.querySelectorAll('td');const date=(cells[4]?.textContent||'').trim();if(!date)return;const key=date.slice(0,10);counts[key]=(counts[key]||0)+1});
    const keys=Object.keys(counts).sort();
    const values=keys.map(k=>counts[k]);
    const max=Math.max(1,...values);
    const width=760,height=210,left=42,right=16,top=18,bottom=34;
    const pts=values.map((v,i)=>{const x=keys.length===1?(width-left-right)/2+left:left+i*((width-left-right)/Math.max(1,keys.length-1));const y=top+(height-top-bottom)*(1-v/max);return [x,y]});
    const path=pts.map((p,i)=>(i?'L':'M')+p[0].toFixed(1)+' '+p[1].toFixed(1)).join(' ')||`M ${left} ${height-bottom}`;
    const labels=keys.length?keys: ['No data'];
    const grid=[0,.5,1].map(f=>{const y=top+(height-top-bottom)*f;return `<line class="analytics-line-grid" x1="${left}" y1="${y}" x2="${width-right}" y2="${y}"/>`}).join('');
    const points=pts.map(p=>`<circle class="analytics-line-point" cx="${p[0]}" cy="${p[1]}" r="4"/>`).join('');
    const xlabels=labels.map((k,i)=>{const x=pts[i]?.[0]||left;return `<text class="analytics-axis" x="${x}" y="${height-10}" text-anchor="middle">${esc(k.slice(5)||k)}</text>`}).join('');
    const card=document.createElement('div');card.id='analyticsLineCard';card.className='panel analytics-line-card';
    card.innerHTML=`<div class="section-head"><div><h3>Publishing activity trend</h3><span>Attempts grouped by day from the publishing history.</span></div><span class="badge">${values.reduce((a,b)=>a+b,0)} attempts</span></div><svg class="analytics-line" viewBox="0 0 ${width} ${height}" role="img" aria-label="Publishing attempts by day">${grid}<path class="analytics-line-path" d="${path}"/>${points}${xlabels}</svg>`;
    root.appendChild(card);
  }

  function patch(){
    patchSettings();patchCalendar();patchIntegrations();addAnalyticsLine();
  }
  new MutationObserver(()=>setTimeout(patch,0)).observe(document.documentElement,{subtree:true,childList:true});
  [100,350,900].forEach(t=>setTimeout(patch,t));
})();
</script>