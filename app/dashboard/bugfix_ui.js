<style>
.research-source-warning{margin:8px 0;padding:9px 11px;border:1px solid #d9d2ff;background:#f8f6ff;color:#5f46a8;border-radius:8px;font-size:10px;line-height:1.45}.content-generation-note{margin:0 0 12px;padding:10px 12px;border:1px solid #e4e0ff;background:#f8f6ff;color:#5f46a8;border-radius:9px;font-size:11px}.generation-status{display:inline-flex;align-items:center;margin-left:8px;font-size:10px;color:#737887}.generation-status.ok{color:#027a48}.generation-status.error{color:#b42318}
</style>
<script>
(function(){
  const $=id=>document.getElementById(id);
  const esc=v=>String(v??'').replace(/[&<>\\"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','\\':'&#92;','"':'&quot;',"'":'&#39;'}[m]));
  const normalizeError=value=>{if(value==null)return 'Request failed';if(typeof value==='string')return value;if(value instanceof Error)return value.message||'Request failed';try{return value.detail?normalizeError(value.detail):value.message?normalizeError(value.message):JSON.stringify(value)}catch(e){return String(value)}};
  const api=async(url,opts={})=>{const r=await fetch(url,opts);const d=await r.json().catch(()=>({}));if(r.status===401){showLogin('Your session expired.');throw Error('unauthorized')}if(!r.ok)throw Error(normalizeError(d));return d};

  function patchSourceSelector(){
    if($('title')?.textContent!=='Research')return;
    const select=$('rs');
    if(!select)return;
    const web=[...select.options].find(o=>o.value==='web');
    if(web){web.disabled=false;web.textContent='Web Search';}
    const wrap=$('sourceMulti');
    if(wrap){const row=[...wrap.querySelectorAll('.source-multi-option')].find(x=>x.querySelector('input')?.getAttribute('aria-label')==='Web Search');if(row){const cb=row.querySelector('input');if(cb){cb.disabled=false;}row.style.opacity='';row.style.cursor='';row.title='Web Search is available.';}}
    window.__updateResearchSourceLabel?.();
    const warning=$('researchSourceWarning');
    if(warning)warning.remove();
  }

  function saveSelectedResearch(article){
    const meta=article.querySelector('.tiny')?.textContent||'';
    const source=(meta.split('·')[0]||'').trim();
    const title=article.querySelector('.item-title')?.textContent||'';
    const body=article.querySelector('p')?.textContent||'';
    try{sessionStorage.setItem('aiSocialSelectedResearch',JSON.stringify({source,title,body,savedAt:Date.now()}))}catch(e){}
  }

  function patchCreateButtons(){
    if($('title')?.textContent!=='Research')return;
    document.querySelectorAll('#researchResults article.item').forEach(article=>{
      const button=[...article.querySelectorAll('button')].find(b=>/create content/i.test(b.textContent||''));
      if(!button||button.dataset.contentHandoff)return;
      button.dataset.contentHandoff='1';
      button.onclick=e=>{e.preventDefault();saveSelectedResearch(article);window.go('content');};
    });
  }

  async function generateContentFixed(){
    const buttons=[...document.querySelectorAll('#generateBtn,[data-generate-content]')];
    buttons.forEach(b=>{b.disabled=true;b.dataset.originalText=b.textContent;b.textContent='Analyzing & generating…'});
    let status=document.querySelector('.generation-status');
    if(!status){status=document.createElement('span');status.className='generation-status';const target=$('generateBtn')?.parentElement;if(target)target.appendChild(status)}
    status.textContent='Running AI analysis first so research has usable content context…';status.className='generation-status';
    try{
      const selected=sessionStorage.getItem('aiSocialSelectedResearch');
      const analysis=await api('/intelligence/run?limit=100',{method:'POST',headers:{'Content-Type':'application/json'}});
      const result=await api('/content/generate?limit=10',{method:'POST'});
      const generated=Number(result.generated||result.created||0);
      const skipped=Number(result.skipped||0);
      const failed=Number(result.failed||0);
      if(generated===0){status.textContent=`No new draft was created (skipped ${skipped}, failed ${failed}).`;status.className='generation-status error';toast(`AI analyzed ${Number(analysis.analyzed||0)} item(s), but generated 0 new drafts. Check provider/API configuration or approval history.`);return;}
      status.textContent=`Generated ${generated} draft(s) successfully.`;status.className='generation-status ok';
      if(selected){try{sessionStorage.removeItem('aiSocialSelectedResearch')}catch(e){}}
      toast(`Generated ${generated} draft(s).`);
      setTimeout(()=>window.go('content'),350);
    }catch(e){status.textContent=normalizeError(e);status.className='generation-status error';toast(normalizeError(e))}
    finally{buttons.forEach(b=>{b.disabled=false;b.textContent=b.dataset.originalText||'Generate content'})}
  }

  function patchContent(){
    if($('title')?.textContent!=='Content')return;
    const selected=sessionStorage.getItem('aiSocialSelectedResearch');
    if(selected&&!$('contentGenerationNote')){
      let data={};try{data=JSON.parse(selected)||{}}catch(e){}
      const note=document.createElement('div');note.id='contentGenerationNote';note.className='content-generation-note';note.innerHTML=`<strong>Research handoff:</strong> ${esc(data.title||'Selected research signal')} · ${esc(data.source||'source')}<br><span>Generate Content will analyze the research set first, then create a draft from available intelligence.</span>`;
      $('content')?.querySelector('.page-intro')?.after(note);
    }
    const b=$('generateBtn');if(b&&!b.dataset.fixedGenerator){b.dataset.fixedGenerator='1';b.onclick=generateContentFixed}
  }

  function enhance(){patchSourceSelector();patchCreateButtons();patchContent()}
  const root=$('content');if(root){new MutationObserver(()=>{clearTimeout(window.__bugfixTimer);window.__bugfixTimer=setTimeout(enhance,0)}).observe(root,{childList:true,subtree:true})}
  setTimeout(enhance,100);
})();
</script>
