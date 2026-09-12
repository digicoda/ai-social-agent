<style>
.research-result-toolbar{padding:0!important;margin:0!important;border:0!important}.research-result-toolbar .research-sort-group{display:flex!important;align-items:center;gap:7px}.research-result-toolbar .research-sort-group label{font-size:10px;font-weight:800;white-space:nowrap}.research-result-toolbar .research-sort{min-width:165px!important;width:auto!important}#researchResults .panel>.section-head{display:flex;align-items:center;justify-content:space-between;gap:12px}#researchResults .panel>.section-head .research-result-toolbar{display:block!important;flex:0 0 auto}#researchResults .research-source-summary{display:none}
</style>
<script>
(function(){
 const $=id=>document.getElementById(id);
 function enhance(){
   if($('title')?.textContent!=='Research')return;
   const panel=$('researchResults')?.querySelector('.panel'),head=panel?.querySelector('.section-head'),group=panel?.querySelector('.research-sort-group');
   if(head&&group){const bar=group.closest('.research-result-toolbar');if(bar&&bar.parentElement!==head)head.appendChild(bar);const label=group.querySelector('label');if(label)label.textContent='Search by Priority'}
   const root=$('researchResults');if(root&&!root.dataset.targetedBound){root.dataset.targetedBound='1';root.addEventListener('click',async e=>{const btn=e.target.closest('button');if(!btn||btn.textContent.trim()!=='Create content')return;const article=btn.closest('article.item'),title=article?.querySelector('.item-title')?.textContent?.trim();if(!title)return;e.preventDefault();e.stopPropagation();try{const r=await fetch('/content/generate-by-title',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({title})}),d=await r.json().catch(()=>({}));if(!r.ok)throw Error(d.detail||r.statusText);toast(d.generated?'Content draft generated.':d.needs_analysis?'Run AI analysis for this result first.':'This result already has a draft.');if(d.generated)go('content')}catch(err){toast(err.message)}} ,true)}}
 const root=$('content');if(root)new MutationObserver(()=>setTimeout(enhance,0)).observe(root,{childList:true,subtree:true});setTimeout(enhance,0);
})();
</script>
