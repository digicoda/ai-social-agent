<script>
(function(){
  const COOKIE='ai_social_profile';
  const getId=()=>{const m=document.cookie.match('(?:^|; )'+COOKIE+'=([^;]*)');return m?decodeURIComponent(m[1]):''};
  const api=async u=>{const r=await fetch(u);const d=await r.json();if(!r.ok)throw Error(d.detail||'Request failed');return d};
  function install(){
    if(document.getElementById('profileSwitcher'))return;
    const top=document.querySelector('.topbar')||document.querySelector('header'); if(!top)return;
    const wrap=document.createElement('div');wrap.id='profileSwitcher';wrap.className='profile-switcher';
    wrap.innerHTML='<label>Profile</label><select id="profileSelect"><option>Loading…</option></select>';
    top.prepend(wrap);
    const select=wrap.querySelector('select');
    api('/profiles').then(d=>{select.innerHTML='<option value="">Default / Shared</option>'+d.items.map(p=>`<option value="${p.id}">${String(p.name).replace(/[&<>\"']/g,'')}</option>`).join('');select.value=getId();});
    select.onchange=()=>{const id=select.value;if(id)document.cookie=COOKIE+'='+encodeURIComponent(id)+'; Path=/; SameSite=Lax';else document.cookie=COOKIE+'=; Max-Age=0; Path=/; SameSite=Lax';location.reload()};
  }
  const s=document.createElement('style');s.textContent='#profileSwitcher{display:flex;align-items:center;gap:6px;margin-right:8px}#profileSwitcher label{font-size:10px;color:#8f93a3;font-weight:700}#profileSwitcher select{width:auto;min-width:130px;padding:7px 28px 7px 9px;border-radius:8px}';document.head.appendChild(s);
  setTimeout(install,250);new MutationObserver(install).observe(document.body,{childList:true,subtree:true});
})();
</script>
