async function loadJson(path){ const r = await fetch(path); if(!r.ok) throw new Error(path); return r.json(); }
function badge(txt){ return `<span class="badge b-${txt}">${txt}</span>`; }
function card(c){
  const m = Object.entries(c.metrics||{}).slice(0,3)
    .map(([k,v])=>`${k}: <strong>${v}</strong>`).join(" · ");
  return `<div class="card"><h3>${c.title||c.claim_id}</h3>
    ${badge(c.verification?.final||"PROVISIONAL")}<span class="badge">${c.mode}</span>
    <p class="mut">${c.world} · n=${c.n_decisions}</p><p>${m}</p>
    <p class="mut"><code>${c.claim_id.slice(0,18)}…</code></p></div>`;
}
(async()=>{
  try{
    const idx = await loadJson("data/claims.json");
    document.getElementById("claim-list").innerHTML =
      idx.map(card).join("") || "<p class='mut'>no claims yet</p>";
    const lb = idx.filter(c=>c.metrics).sort((a,b)=>(b.metrics.objective??0)-(a.metrics.objective??0));
    document.querySelector("#lb tbody").innerHTML = lb.map((c,i)=>
      `<tr><td>${i+1}</td><td><code>${(c.candidate?.config?.strategy||c.candidate?.config?.policy||c.candidate?.kind||"?")}</code></td>
       <td>${c.world}</td><td>${c.metrics.objective??"—"}</td><td>${c.mode}</td>
       <td class="mut">${c.claim_id.slice(0,14)}…</td></tr>`).join("");
  }catch(e){ document.getElementById("claim-list").textContent = "claims index unavailable"; }
  try{
    const packs = await loadJson("data/worldpacks.json");
    document.getElementById("pack-list").innerHTML = packs.map(p=>
      `<div class="card"><h3>${p.kind}</h3><p>${p.description||""}</p>
       <p class="mut">version ${p.version} · hash <code>${String(p.content_hash).slice(0,14)}…</code></p></div>`).join("")
      || "<p class='mut'>no worldpacks published</p>";
  }catch(e){ document.getElementById("pack-list").textContent = "worldpack index unavailable"; }
})();
