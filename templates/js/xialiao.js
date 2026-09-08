// ===== 虾料 =====
function renderXialiao(){
  const x = P.xialiao || {};
  const fc = x.format_check || {};
  const m = fc.metrics || {};
  const nodes = x.knowledge_graph?.nodes || [];
  return `
    <div class="resume-box"><b>续集指引</b>：换工具/电脑后，加载 xia-boss skill + 项目根目录即恢复。读取 SQLite(xiaji.db) 与 pipeline-state.json 定位断点（current=<b>${esc(P.pipeline?.current||"")}</b>）。</div>
    <div class="stat-row">
      <div class="stat-card"><div class="n" style="color:${fc.level==="ok"?"#0e8a5f":"#b45309"}">${esc(fc.level||"-").toUpperCase()}</div><div class="l">格式检查</div></div>
      <div class="stat-card"><div class="n">${x.billable_chars||0}</div><div class="l">计费字数</div></div>
      <div class="stat-card"><div class="n">${(x.scene_blocks||[]).length}</div><div class="l">场景块</div></div>
      <div class="stat-card"><div class="n">${m.scene_headers||0}</div><div class="l">场景头</div></div>
      <div class="stat-card"><div class="n">${m.dialogue_lines||0}</div><div class="l">对白行</div></div>
      <div class="stat-card"><div class="n">${nodes.length}</div><div class="l">图谱节点</div></div>
    </div>
    <h2 style="font-size:15px;margin:18px 0 10px">知识图谱</h2>
    ${renderKnowledgeGraph()}
    <h2 style="font-size:15px;margin:18px 0 10px">世界观</h2>
    ${renderWorldView()}
    <h2 style="font-size:15px;margin:18px 0 10px">章节与场景块</h2>
    <div class="sc-list">
      ${(x.scene_blocks||[]).map(s => `
        <div class="sc-item">
          <span class="h">${s.episode}-${s.scene}</span>
          <div style="flex:1">
            <div class="lbl">${esc(s.location)} · ${esc(s.time_of_day)} · ${esc(s.interior_exterior)}</div>
            <div style="font-size:12px;color:var(--mut);margin-top:2px">${esc(s.header_line)} ｜ 对白 ${s.dialogue_lines} 行 ｜ 动作 ${s.action_lines} 行</div>
            <div style="margin-top:4px">${(s.characters||[]).map(c=>`<span class="pill" style="padding:1px 7px">${esc(c)}</span>`).join(" ")}</div>
          </div>
        </div>`).join("")}
    </div>`;
}

// ===== 世界观展示（数据源：data.js xialiao.world，取自 docs/02-world.md 08-bible.md）=====
function renderWorldView(){
  const w = P.xialiao?.world;
  if(!w) return `<div class="card" style="color:var(--mut);font-size:12px">暂无世界观设定（待虾料梳理）</div>`;
  const escW = (s) => esc(s||"");
  const env = w.environment || {};
  // 通用环境字段标签（不硬编码世界观；未知字段直接用键名）
  const envLabels = {tagline:"总述", current_year:"当前年份", era:"时代", human_population:"人类人口",
                     civilization:"文明形态", territory:"领地范围", day:"白昼", night:"夜晚",
                     sky:"天穹", land:"地貌", flora:"植被"};   // ★ 2026-09-02 自检清理：移除旧项目残留字段 moqi（未知字段回退键名显示，行71兜底仍在）
  const envStr = Object.entries(env).filter(([k,v]) => v!=null && typeof v === "string" && String(v).trim());
  const envArr = Object.entries(env).filter(([k,v]) => Array.isArray(v) && v.length);
  const hasEnv = envStr.length || envArr.length;
  const ps = w.power_system || {};
  const psRows = Object.entries(ps).filter(([k,v]) => v!=null && k!=="desc");
  const sm = w.system_mechanics || {};
  const smRows = Object.entries(sm).filter(([k,v]) => v!=null && k!=="desc");
  return `
    <div class="world-grid">
      <div class="world-card">
        <div class="wc-head">🌍 世界格局</div>
        <div class="wc-body">
          ${(w.realms||[]).map(r => `
            <div class="realm-row">
              <span class="realm-dot" style="background:${r.color||"#888"}"></span>
              <b>${escW(r.name)}</b>
              <span class="realm-pos">${escW(r.position||"")}</span>
              <div class="realm-feat">${escW(r.feature||r.desc||"")}</div>
              <span class="pill" style="padding:1px 8px">${escW(r.status||"")}</span>
            </div>`).join("")}
        </div>
      </div>
      <div class="world-card">
        <div class="wc-head">🏞 环境设定</div>
        <div class="wc-body">
          ${hasEnv ? `
            ${envStr.map(([k,v]) => `<div class="env-li"><b>${escW(envLabels[k]||k)}</b>：${escW(v)}</div>`).join("")}
            ${envArr.map(([k,arr]) => `<div class="env-sec"><b>${escW(envLabels[k]||k)}</b>${arr.map(x => `<div class="env-li">· ${escW(typeof x==="string"?x:(x.name||x.desc||JSON.stringify(x)))}</div>`).join("")}</div>`).join("")}
          ` : `<div class="env-empty">暂无环境设定</div>`}
        </div>
      </div>
      ${env.city ? `
      <div class="world-card world-card-wide">
        <div class="wc-head">🏙 聚落布局</div>
        <div class="wc-body">
          <div class="env-sec"><b>布局</b><div class="env-li">${escW(env.city.layout||"")}</div></div>
          <div class="city-grid">
            ${Object.entries(env.city).filter(([k,v]) => v!=null && k!=="layout" && typeof v==="string" && String(v).trim())
              .map(([k,v]) => `<div class="city-cell"><div class="city-lbl">${escW(k)}</div><div class="city-txt">${escW(v)}</div></div>`).join("")}
          </div>
          ${env.mood ? `<div class="env-quote" style="margin-top:6px">${escW(env.mood)}</div>` : ""}
        </div>
      </div>` : ""}
      <div class="world-card">
        <div class="wc-head">📜 关键时间线</div>
        <div class="wc-body">
          ${(w.timeline||[]).map(t => `
            <div class="tl-row">
              <span class="tl-era">${escW(t.era||t.year||t.time||"")}</span>
              <div class="tl-event">${escW(t.event||t.desc||"")}</div>
            </div>`).join("")}
        </div>
      </div>
      <div class="world-card">
        <div class="wc-head">⚔ 力量体系</div>
        <div class="wc-body">
          ${ps.desc ? `<div class="wc-desc">${escW(ps.desc)}</div>` : ""}
          ${psRows.map(([k,v]) => Array.isArray(v)
            ? `<div class="pw-row"><b>${escW(k)}</b><span class="pw-chips">${v.map(x=>`<span class="chip chip-blue">${escW(x)}</span>`).join("")}</span></div>`
            : (typeof v === "object"
              ? Object.entries(v).map(([k2,v2]) => `<div class="pw-row"><b>${escW(k)} · ${escW(k2)}</b><span class="pw-chips">${Array.isArray(v2)?v2.map(x=>`<span class="chip chip-blue">${escW(x)}</span>`).join(""):escW(v2)}</span></div>`).join("")
              : `<div class="pw-row"><b>${escW(k)}</b><span>${escW(v)}</span></div>`)).join("")}
          ${!ps.desc && !psRows.length ? `<div class="env-empty">暂无力量体系</div>` : ""}
        </div>
      </div>
      <div class="world-card">
        <div class="wc-head">🏛 核心势力</div>
        <div class="wc-body">
          ${(w.factions||[]).map(f => `
            <div class="fac-row">
              <span class="realm-dot" style="background:${f.color||"#888"}"></span>
              <div style="flex:1 1 0;min-width:110px">
                <b>${escW(f.name)}</b>
                <div class="fac-meta">掌权：${escW(f.leader||"")} · 地盘：${escW(f.domain||"")}</div>
              </div>
              <div style="flex:0 1 auto;max-width:52%;text-align:right">
                <div class="fac-goal">${escW(f.goal||"")}</div>
                <div class="fac-rel">${escW(f.rel||"")}</div>
              </div>
            </div>`).join("")}
        </div>
      </div>
      ${(w.crops||[]).length ? `
      <div class="world-card">
        <div class="wc-head">🌾 物产体系</div>
        <div class="wc-body">
          ${(w.crops||[]).map(c => `
            <div class="crop-row">
              <span class="crop-tier" style="color:${c.color||"#888"};border-color:${c.color||"#888"}">${escW(c.tier||"")}</span>
              <div class="crop-info">
                <div class="crop-names">${escW(c.crops||c.name||"")}</div>
                <div class="crop-effect">${escW((c.effect||"") + (c.stage?" · "+c.stage:""))}</div>
              </div>
            </div>`).join("")}
        </div>
      </div>` : ""}
      ${(w.conflicts||[]).length ? `
      <div class="world-card">
        <div class="wc-head">🔥 核心矛盾</div>
        <div class="wc-body">
          ${(w.conflicts||[]).map(c => `
            <div class="conf-row">
              <b>${escW(c.name||"")}</b>
              <div class="conf-desc">${escW(c.desc||"")}</div>
            </div>`).join("")}
        </div>
      </div>` : ""}
      ${smRows.length || sm.desc ? `
      <div class="world-card">
        <div class="wc-head">⚙ 系统机制</div>
        <div class="wc-body">
          ${sm.desc ? `<div class="wc-desc">${escW(sm.desc)}</div>` : ""}
          ${smRows.map(([k,v]) => `<div class="sys-row"><b>${escW(k)}</b><span>${escW(Array.isArray(v)?v.join(" / "):v)}</span></div>`).join("")}
        </div>
      </div>` : ""}
      ${(w.golden_rules||[]).length ? `
      <div class="world-card world-card-wide">
        <div class="wc-head">🔒 关键设定锁定（L3 约束）</div>
        <div class="wc-body">
          ${(w.golden_rules||[]).map((g,i) => `
            <div class="rule-row"><span class="rule-no">${i+1}</span><span>${escW(typeof g==="string"?g:(g.name||g.desc||JSON.stringify(g)))}</span></div>`).join("")}
        </div>
      </div>` : ""}
    </div>`;
}

// ===== 知识图谱（DramaClaw 风格：深色科技 + 拖拽/缩放/点击）=====
function renderKnowledgeGraph(){
  const kg = P.xialiao?.knowledge_graph || {nodes:[],edges:[]};
  const nodes = kg.nodes || [];
  const edges = kg.edges || [];
  if(!nodes.length) return `<div style="padding:20px;text-align:center;color:var(--mut);background:#0a0a0f;border-radius:12px;font-size:12px">暂无知识图谱</div>`;
  return `
    <div class="kg-wrap" id="kg-wrap">
      <div class="kg-header">
        <div class="kg-title">
          <span class="kg-icon">🕸️</span>
          <b>知识图谱</b>
          <span class="kg-stat">${nodes.length} 个节点 · ${edges.length} 条关系</span>
        </div>
        <div class="kg-tools">
          <button onclick="kgZoom(-0.2)" title="缩小">−</button>
          <button onclick="kgZoom(0.2)" title="放大">+</button>
          <button onclick="kgReset()" title="重置视图">↺</button>
          <button onclick="kgFullscreen()" title="全屏">⛶</button>
        </div>
      </div>
      <div class="kg-canvas">
        <svg class="kg-svg" id="kg-svg" viewBox="0 0 1200 720" preserveAspectRatio="xMidYMid meet">
          <defs>
            <radialGradient id="kg-glow-cyan" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stop-color="#22d3ee" stop-opacity="0.6"/>
              <stop offset="100%" stop-color="#22d3ee" stop-opacity="0"/>
            </radialGradient>
            <radialGradient id="kg-glow-purple" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stop-color="#a855f7" stop-opacity="0.5"/>
              <stop offset="100%" stop-color="#a855f7" stop-opacity="0"/>
            </radialGradient>
            <radialGradient id="kg-glow-pink" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stop-color="#ec4899" stop-opacity="0.5"/>
              <stop offset="100%" stop-color="#ec4899" stop-opacity="0"/>
            </radialGradient>
            <radialGradient id="kg-glow-amber" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stop-color="#fbbf24" stop-opacity="0.5"/>
              <stop offset="100%" stop-color="#fbbf24" stop-opacity="0"/>
            </radialGradient>
          </defs>
          <g class="kg-root" id="kg-root">
            <g class="kg-edges">${edges.map(e => `
              <line class="kg-edge" data-from="${esc(e.from)}" data-to="${esc(e.to)}" data-type="${esc(e.type||"")}" stroke="#22d3ee" stroke-width="0.8" stroke-dasharray="4,4" opacity="0.35"/>`).join("")}
            </g>
            <g class="kg-nodes">${nodes.map((n,i) => `
              <g class="kg-node kg-type-${esc(n.type)}" data-id="${esc(n.id)}" data-type="${esc(n.type)}" transform="translate(${kgNodePos(n,i,nodes.length)})">
                <circle class="kg-glow" r="26" fill="url(#kg-glow-${typeGlow(n.type)})"/>
                <circle class="kg-ring" r="14" fill="#0a0a0f"/>
                <circle class="kg-ring2" r="6" fill="${typeColor(n.type)}"/>
                <text class="kg-label" y="38" text-anchor="middle">${esc(n.label)}</text>
              </g>`).join("")}
            </g>
          </g>
        </svg>
        <div class="kg-detail" id="kg-detail"></div>
      </div>
      <div class="kg-foot">拖动节点 · 滚轮缩放 · 点击节点查看详情 · 双击空白处重置</div>
    </div>`;
}

// 知识图谱节点初始位置：数据含 x/y 则用数据；★ 兜底算法（2026-08-21 修复）：无坐标时按 index 环形分布，禁止 n.x||600 全堆中心
function kgNodePos(n, i, total){
  if (n.x != null && n.y != null) return `${n.x},${n.y}`;
  const ang = 2 * Math.PI * i / Math.max(1, total) - Math.PI / 2;  // 12 点钟方向起
  const r = 260;
  return `${Math.round(600 + r * Math.cos(ang))},${Math.round(360 + r * Math.sin(ang))}`;
}

function typeColor(t){
  return {character:"#22d3ee", place:"#a855f7", organization:"#06b6d4", item:"#fbbf24", concept:"#ec4899", system:"#0e8a5f"}[t] || "#22d3ee";
}
function typeGlow(t){
  return {character:"cyan", place:"purple", organization:"cyan", item:"amber", concept:"pink", system:"cyan"}[t] || "cyan";
}

// 知识图谱交互
const kgState = {scale:1, tx:0, ty:0};
function kgApply(){
  const root = document.getElementById("kg-root");
  if(root) root.setAttribute("transform", `translate(${kgState.tx},${kgState.ty}) scale(${kgState.scale})`);
}
function kgZoom(d){
  kgState.scale = Math.max(0.3, Math.min(2.5, kgState.scale + d));
  kgApply();
}
function kgReset(){
  kgState.scale = 1; kgState.tx = 0; kgState.ty = 0;
  kgApply();
}
function kgFullscreen(){
  document.getElementById("kg-wrap")?.requestFullscreen?.();
}
function kgInit(){
  const svg = document.getElementById("kg-svg");
  if(!svg || svg.dataset.kgInited) return;
  svg.dataset.kgInited = "1";
  // 滚轮缩放
  svg.addEventListener("wheel", e => {
    e.preventDefault();
    kgZoom(e.deltaY > 0 ? -0.1 : 0.1);
  }, {passive:false});
  // 空白处平移
  let pan = null;
  svg.addEventListener("mousedown", e => {
    if(e.target.closest(".kg-node")) return;
    pan = {x:e.clientX, y:e.clientY};
    svg.classList.add("dragging");
    kgClearHighlight();
  });
  document.addEventListener("mousemove", e => {
    if(!pan) return;
    kgState.tx += (e.clientX - pan.x);
    kgState.ty += (e.clientY - pan.y);
    pan = {x:e.clientX, y:e.clientY};
    kgApply();
  });
  document.addEventListener("mouseup", () => { pan = null; svg.classList.remove("dragging"); });
  svg.addEventListener("dblclick", e => {
    if(!e.target.closest(".kg-node")){ kgReset(); kgClearHighlight(); }
  });
  // 节点拖动 + 边跟随 + 点击
  svg.querySelectorAll(".kg-node").forEach(node => {
    let drag = null;
    node.addEventListener("mousedown", e => {
      e.stopPropagation();
      const tr = node.getAttribute("transform")?.match(/translate\(([\d.-]+),([\d.-]+)\)/);
      if(tr) drag = {x:e.clientX, y:e.clientY, nx:parseFloat(tr[1]), ny:parseFloat(tr[2])};
    });
    document.addEventListener("mousemove", e => {
      if(!drag) return;
      const dx = (e.clientX - drag.x) / kgState.scale;
      const dy = (e.clientY - drag.y) / kgState.scale;
      node.setAttribute("transform", `translate(${drag.nx+dx},${drag.ny+dy})`);
      kgUpdateEdges();
    });
    document.addEventListener("mouseup", () => { drag = null; });
    node.addEventListener("click", e => {
      e.stopPropagation();
      kgShowDetail(node.dataset.id);
    });
  });
  kgUpdateEdges();
}
function kgUpdateEdges(){
  const svg = document.getElementById("kg-svg");
  if(!svg) return;
  const nodes = new Map();
  svg.querySelectorAll(".kg-node").forEach(n => {
    const tr = n.getAttribute("transform")?.match(/translate\(([\d.-]+),([\d.-]+)\)/);
    if(tr) nodes.set(n.dataset.id, {x:parseFloat(tr[1]), y:parseFloat(tr[2])});
  });
  svg.querySelectorAll(".kg-edge").forEach(line => {
    const a = nodes.get(line.dataset.from);
    const b = nodes.get(line.dataset.to);
    if(a && b){
      line.setAttribute("x1", a.x); line.setAttribute("y1", a.y);
      line.setAttribute("x2", b.x); line.setAttribute("y2", b.y);
    }
  });
}
function kgShowDetail(id){
  const node = (P.xialiao?.knowledge_graph?.nodes||[]).find(n => n.id === id);
  const deg = (P.xialiao?.knowledge_graph?.edges||[]).filter(e => e.from===id || e.to===id);
  const d = document.getElementById("kg-detail");
  if(!node || !d) return;
  d.innerHTML = `
    <div class="kg-d-head">
      <span class="kg-d-icon">${nodeIcon(node.type)}</span>
      <b>${esc(node.label)}</b>
      <button onclick="kgCloseDetail()">×</button>
    </div>
    <div class="kg-d-type">${esc(node.type)} · 权重 ${node.weight||1}</div>
    <div class="kg-d-desc">${esc(node.desc||"暂无描述")}</div>
    <div class="kg-d-rel">${deg.length} 条关系</div>
    <div class="kg-d-list">${deg.map(e => `<div class="kg-d-rel-item"><span class="kg-rel-${e.from===id?'out':'in'}">${e.from===id?'→':'←'} ${esc(e.label||e.type||"关联")}</span> <b>${esc(e.from===id?e.to:e.from)}</b></div>`).join("")}</div>
  `;
  d.classList.add("open");
  kgHighlight(id);
}
function kgCloseDetail(){
  const d = document.getElementById("kg-detail");
  if(d) d.classList.remove("open");
  kgClearHighlight();
}
// 高亮：与选中节点直接相连的边/节点亮起，其余弱化
function kgHighlight(id){
  const svg = document.getElementById("kg-svg");
  if(!svg) return;
  const linkedIds = new Set([id]);
  svg.querySelectorAll(".kg-edge").forEach(line => {
    const isLink = line.dataset.from === id || line.dataset.to === id;
    if(isLink) linkedIds.add(line.dataset.from === id ? line.dataset.to : line.dataset.from);
  });
  svg.querySelectorAll(".kg-edge").forEach(line => {
    const isLink = line.dataset.from === id || line.dataset.to === id;
    line.classList.remove("active","dim");
    if(isLink) line.classList.add("active");
    else line.classList.add("dim");
  });
  svg.querySelectorAll(".kg-node").forEach(n => {
    n.classList.remove("dim","linked","selected");
    if(n.dataset.id === id) n.classList.add("selected");
    else if(linkedIds.has(n.dataset.id)) n.classList.add("linked");
    else n.classList.add("dim");
  });
}
function kgClearHighlight(){
  const svg = document.getElementById("kg-svg");
  if(!svg) return;
  svg.querySelectorAll(".kg-edge").forEach(line => line.classList.remove("active","dim"));
  svg.querySelectorAll(".kg-node").forEach(n => n.classList.remove("dim","linked","selected"));
}
function nodeIcon(t){
  return {character:"👤", place:"📍", organization:"🏛", item:"🧰", concept:"💡", system:"⚙"}[t] || "●";
}

