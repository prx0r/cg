async function loadJson(path){ const r = await fetch(path); if(!r.ok) throw new Error(path); return r.json(); }
function badge(txt){ return `<span class="badge b-${txt}">${txt}</span>`; }
function esc(s){return String(s??"").replace(/[&<>"]/g,x=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[x]));}
function card(c){
  const m = Object.entries(c.metrics||{}).slice(0,3)
    .map(([k,v])=>`${esc(k)}: <strong>${v}</strong>`).join(" · ");
  const r = c.reproducibility||{};
  const run = r.run_command ? `<p class="mut">re-run: <code>${esc(r.run_command)}</code></p>` : "";
  const repo = r.git_repo ? `<p class="mut"><a href="${esc(r.git_repo)}@${esc(r.git_commit)}" rel="noopener">${esc(r.git_repo.split("/").pop())}@${esc(String(r.git_commit).slice(0,8))}</a> · transcripts sha256-logged</p>` : "";
  return `<div class="card"><h3>${esc(c.title||c.claim_id)}</h3>
    ${badge(c.verification?.final||"PROVISIONAL")}<span class="badge">${esc(c.mode)}</span>
    <p class="mut">${esc(c.world)} · n=${c.n_decisions}</p><p>${m}</p>${run}${repo}
    <p class="mut"><code>${esc(c.claim_id.slice(0,18))}…</code></p></div>`;
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
    document.getElementById("pack-list").innerHTML = packs.map(p=>{
      const steps = (p.replay||[]).map(s2=>`<li><code>${esc(s2)}</code></li>`).join("");
      return `<div class="card"><h3>${esc(p.kind)}</h3><p>${esc(p.description||"")}</p>
       <p class="mut">hash <code>${esc(String(p.content_hash).slice(0,19))}…</code> @ <code>${esc(String(p.git_commit||"").slice(0,8))}</code></p>
       <ol class="mut">${steps}</ol></div>`;}).join("")
      || "<p class='mut'>no worldpacks published</p>";
  }catch(e){ document.getElementById("pack-list").textContent = "worldpack index unavailable"; }
})();
