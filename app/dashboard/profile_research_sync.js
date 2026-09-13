<style>
/* Profile/research polish: compact controls without changing the dashboard layout. */
#profileResearchNote{margin:0 0 10px;padding:8px 10px;border:1px solid #e4e0ff;border-radius:8px;background:#f8f6ff;color:#6655a8;font-size:10px;line-height:1.45;display:none}
.profile-time-select{height:38px;min-height:38px!important;font-variant-numeric:tabular-nums}
.check-row input[type=checkbox]{width:14px!important;height:14px!important;min-width:14px!important;min-height:14px!important;margin:0!important}
.profile-check-grid{gap:3px!important}
#pfSourcesBox .check-row{padding:3px 6px!important;margin:0!important}
.profile-multi-publish{display:flex;flex-wrap:wrap;gap:4px}
.update-version-card{display:flex;align-items:center;justify-content:space-between;gap:14px;padding:13px 14px;border:1px solid var(--line);border-radius:10px;background:#fafbfc;margin-bottom:12px}
.update-version-card strong{font-size:13px}.update-version-card small{display:block;color:var(--muted);font-size:10px;margin-top:3px}.update-version-badge{font-weight:800;font-size:11px;padding:5px 8px;border-radius:999px;background:#ece9ff;color:#5d43c7;white-space:nowrap}
@media(max-width:700px){.update-version-card{align-items:flex-start;flex-direction:column}}
</style>
<script>
(function(){
const APP_VERSION='1.2.3';
const $=id=>document.getElementById(id);
const api=async(url,opts={})=>{const r=await fetch(url,opts);const d=await r.json().catch(()=>({}));if(!r.ok)throw Error(typeof d.detail==='string'?d.detail:JSON.stringify(d.detail||d));return d};
const SOURCES=['github','reddit','stackoverflow','rss','web'];
const SOURCE_NAMES={github:'GitHub',reddit:'Reddit',stackoverflow:'Stack Overflow',rss:'RSS / News',web:'Web Search'};
function cookieProfile(){const m=document.cookie.match('(?:^|; )ai_social_profile=([^;]*)');return m?decodeURIComponent(m[1]):''}
function autoSources(categories){const c=new Set((categories||[]).map(x=>String(x).toLowerCase()));const out=new Set(['web','reddit','rss']);if([...c].some(x=>['technology','ai','development','security','wordpress','ecommerce'].includes(x)))['github','stackoverflow'].forEach(x=>out.add(x));return [...out]}
async function currentProfile(){const id=cookieProfile();const d=await api('/profiles');if(id){const p=d.items.find(x=>String(x.id)===String(id));if(p)return p}return null}
function setSelect(id,value){const el=$(id);if(el&&value!==undefined)el.value=value}
function applyProfileToResearch(p){
 const note=$('profileResearchNote');
 if(!note)return;
 if(!p){note.style.display='block';note.innerHTML='<strong>Default / Shared research</strong> — choose a profile above to automatically use its website, keywords, categories, intent and resource policy.';return}
 const c=p.config||{};const cats=Array.isArray(c.categories)?c.categories:[];const sources=c.source_mode==='manual'?(c.sources||[]):autoSources(cats);
 setSelect('rq',c.query||'');setSelect('rc',cats[0]||'all');setSelect('ri',c.intent||'all');setSelect('rt',c.time_range||'7d');
 const rs=$('rs');if(rs){const selected=new Set(sources);[...rs.options].forEach(o=>o.selected=selected.has(o.value));document.querySelectorAll('#sourceMulti input[type=checkbox]').forEach(cb=>{const o=rs.options[Number(cb.dataset.index)];if(o)cb.checked=o.selected});window.__updateResearchSourceLabel?.()}
 note.style.display='block';note.innerHTML=`<strong>Profile: ${String(p.name).replace(/[&<>"']/g,'')}</strong> — research controls are synced from this profile. Website context: ${String(c.website_url||'not set').replace(/[&<>"']/g,'')}. Resources: ${(sources||[]).map(x=>SOURCE_NAMES[x]||x).join(', ')}.`;
 try{window.__researchState=window.__researchState||{};window.__researchState.values={...(window.__researchState.values||{}),rq:c.query||'',rc:cats[0]||'all',ri:c.intent||'all',rt:c.time_range||'7d',rs:sources};sessionStorage.setItem('aiSocialResearchState',JSON.stringify(window.__researchState))}catch(e){}
}
async function syncProfile(){try{applyProfileToResearch(await currentProfile())}catch(e){const n=$('profileResearchNote');if(n){n.style.display='block';n.textContent='Profile settings could not be loaded. Research remains available manually.'}}}
function patchPriority(){
 const root=$('content');if(!root||$('title')?.textContent!=='Research')return;
 const selects=[...root.querySelectorAll('select')];const sort=selects.find(x=>/sort|priority|relevance/i.test(x.id+' '+x.getAttribute('aria-label')+' '+x.previousElementSibling?.textContent));if(!sort)return;
 const head=sort.closest('.field')?.previousElementSibling||sort.parentElement?.previousElementSibling;const container=sort.closest('.panel')?.querySelector('.section-head');if(!container||container.querySelector('.research-priority-inline'))return;
 const wrap=document.createElement('div');wrap.className='toolbar research-priority-inline';wrap.style.marginLeft='auto';const label=document.createElement('span');label.className='muted tiny';label.textContent='Priority';wrap.append(label,sort.closest('.field')||sort);container.appendChild(wrap);
}
function patchSettingsVersion(){
 const root=$('content');if(!root||$('title')?.textContent!=='Settings'||root.querySelector('.update-version-card'))return;
 const card=document.createElement('div');card.className='update-version-card';card.innerHTML=`<div><strong>AI Social Agent</strong><small>Current installed application version</small></div><span class="update-version-badge">v${APP_VERSION}</span>`;
 root.prepend(card);
 const tabs=[...root.querySelectorAll('.tab,.config-tab,button')];const update=tabs.find(x=>/software update|updates?|update/i.test(x.textContent||''));if(update){update.title=`Software Updates — current v${APP_VERSION}`;}
}
function install(){
 const root=$('content');if(!root)return;
 if($('title')?.textContent==='Research'){
  if(!$('profileResearchNote')){$('researchResults')?.parentElement?.insertAdjacentHTML('beforebegin','<div id="profileResearchNote"></div>')}
  syncProfile();patchPriority();
 }
 if($('title')?.textContent==='Settings')patchSettingsVersion();
}
window.addEventListener('profile:refresh',syncProfile);
setTimeout(install,350);new MutationObserver(()=>install()).observe(document.body,{childList:true,subtree:true});
})();
</script>
