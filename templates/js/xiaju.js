// ===== 📜 虾剧（剧本输出工作台，★ 2026-09-05 新增）=====
// 展示/编辑/复制分集剧本（90s 情绪循环 + 颗粒度段结构，规范见 skill references/shared-script-writing.md）
// 数据：P.xiaju.episodes = [{number, title, body, updated_at}]；保存 POST /xiaju/save 全量写 SQLite xiaju 模块
let xjuCurEp = null;    // 当前集 number
let xjuMode = "view";   // view=渲染视图 / edit=编辑视图

function xjuEps(){
  return (P.xiaju?.episodes || []).slice().sort((a, b) => (a.number||0) - (b.number||0));
}
function xjuCur(){
  return xjuEps().find(e => e.number === xjuCurEp) || null;
}

// --- 正文结构化渲染：#/##/###/△/台词/普通行 ---
function xjuRenderBody(body){
  const lines = String(body || "").split("\n");
  let html = "", inCycle = false, cycleKey = "";
  const escLine = s => esc(s);
  const closeCycle = () => { if(inCycle){ html += `</div></div>`; inCycle = false; } };
  for(const raw of lines){
    const line = raw.replace(/\s+$/, "");
    if(/^#\s/.test(line)){ closeCycle(); html += `<div style="font-size:17px;font-weight:600;margin:10px 0 6px">${escLine(line)}</div>`; }
    else if(/^##\s/.test(line)){
      closeCycle();
      if(/^##\s*循环/.test(line)){
        inCycle = true; cycleKey = escLine(line);
        html += `<div style="border:1px solid #d7dee8;border-radius:10px;margin:10px 0;background:#fafbff">` +
                `<div style="padding:8px 12px;background:linear-gradient(135deg,#f5f3ff,#ede9fe);border-radius:10px 10px 0 0;display:flex;justify-content:space-between;align-items:center;gap:8px">` +
                `<b style="color:#5b21b6;font-size:13px">${escLine(line)}</b>` +
                `<button class="pill" style="cursor:pointer" onclick="xjuCopyCycle(this)" data-key="${escLine(line)}">📋 复制本循环</button></div>` +
                `<div style="padding:6px 12px 10px">`;
      } else {
        html += `<div style="font-size:14px;font-weight:600;margin:12px 0 4px;color:#0f766e">${escLine(line)}</div>`;
      }
    }
    else if(/^###\s/.test(line)){
      html += `<div style="font-size:12.5px;font-weight:600;color:#4338ca;margin:10px 0 4px;padding:3px 8px;background:#eef2ff;border-radius:6px;display:inline-block">${escLine(line)}</div>`;
    }
    else if(/^△/.test(line)){
      html += `<div style="display:flex;gap:6px;margin:3px 0"><span style="color:#94a3b8;flex-shrink:0">△</span><span style="color:#334155">${escLine(line.slice(1).trim())}</span></div>`;
    }
    else if(/^\s*-\s*\*\*【(.+?)】\*\*\s*(.*)$/.test(line)){
      const mm = line.match(/^\s*-\s*\*\*【(.+?)】\*\*\s*(.*)$/);
      html += `<div style="margin:3px 0;padding:5px 10px;background:#fbfcfe;border:1px solid #eef0f5;border-radius:8px;font-size:12.5px"><b style="color:#6d28d9">【${escLine(mm[1])}】</b> ${escLine(mm[2])}</div>`;
    }
    else if(/^[^\s＄*\-][^：]{1,10}：/.test(line) && !/^VFX|^SFX|^画风|^场景|^武器|^道具|^出场人物|^人物|^剧情功能|^情绪目标|^情绪递增线|^循环结尾爆点|^本集|^【|^△/.test(line)){
      const i = line.indexOf("：");
      html += `<div style="margin:4px 0;padding:6px 10px;background:#f8fafc;border-left:3px solid #818cf8;border-radius:0 6px 6px 0"><b style="color:#3730a3">${escLine(line.slice(0, i))}</b><span style="color:#64748b">${escLine(line.slice(i, i+1))}</span>${escLine(line.slice(i+1))}</div>`;
    }
    else if(/^(VFX|SFX)\s*[：:]/.test(line)){
      const i = line.indexOf("：") >= 0 ? line.indexOf("：") : line.indexOf(":");
      html += `<div style="font-size:11.5px;color:#0f766e;margin:2px 0 2px 14px"><b>${escLine(line.slice(0, i))}</b>${escLine(line.slice(i))}</div>`;
    }
    else if(line.trim() === ""){ html += `<div style="height:4px"></div>`; }
    else { html += `<div style="color:#475569;margin:3px 0">${escLine(line)}</div>`; }
  }
  closeCycle();
  return html;
}

// --- 主渲染 ---
function renderXiaju(){
  const eps = xjuEps();
  const cur = xjuCur();
  const listHtml = eps.length ? eps.map(e => `
    <div class="role-list-item" data-num="${e.number}" style="padding:8px 10px;border-radius:8px;cursor:pointer;${e.number===xjuCurEp?"background:#ede9fe;font-weight:600":""}">
      <div style="display:flex;justify-content:space-between;align-items:center;gap:6px">
        <span>第${e.number}集 ${esc(e.title || "")}</span>
        <span style="color:var(--mut);font-size:11px">${(e.body||"").length}字</span>
      </div>
    </div>`).join("")
    : `<div style="color:var(--mut);font-size:12px;padding:8px">暂无剧本——点「＋ 新增集」粘贴分集剧本（规范：90s 情绪循环×颗粒度段，见 shared-script-writing.md）</div>`;
  let mainHtml = "";
  if(!cur){
    mainHtml = `<div style="padding:40px;color:var(--mut);text-align:center">左侧选择或新增一集剧本</div>`;
  } else if(xjuMode === "edit"){
    mainHtml = `
      <div style="display:flex;gap:8px;margin-bottom:8px;flex-wrap:wrap">
        <button class="pill primary" onclick="xjuSave()">💾 保存</button>
        <button class="pill" onclick="xjuCancelEdit()">✖ 取消</button>
        <span style="color:var(--mut);font-size:12px;align-self:center">第${cur.number}集 · 编辑模式（可直接粘贴整集 markdown）</span>
      </div>
      <textarea id="xju-editor" style="width:100%;min-height:62vh;font-family:var(--font-mono,monospace);font-size:12.5px;line-height:1.7;padding:12px;border:1px solid #d7dee8;border-radius:10px">${esc(cur.body || "")}</textarea>`;
  } else {
    mainHtml = `
      <div style="display:flex;gap:8px;margin-bottom:8px;flex-wrap:wrap">
        <button class="pill primary" onclick="xjuEdit()">✏️ 编辑</button>
        <button class="pill" onclick="xjuCopyAll()">📋 复制整集</button>
        <button class="pill" onclick="xjuDownload()">⬇ 下载 .md</button>
        <button class="pill" style="color:#b91c1c" onclick="xjuDel()">🗑 删除本集</button>
        <span style="color:var(--mut);font-size:12px;align-self:center">${(cur.body||"").length} 字 · ${esc(cur.updated_at || "")}</span>
      </div>
      <div style="border:1px solid #d7dee8;border-radius:10px;padding:14px 16px;max-height:72vh;overflow:auto;background:#fff">${xjuRenderBody(cur.body || "")}</div>`;
  }
  return `
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;gap:10px;flex-wrap:wrap">
      <span style="font-size:15px;font-weight:600">📜 虾剧 · 分集剧本</span>
      <button class="pill primary" onclick="xjuAdd()">＋ 新增集</button>
    </div>
    <div style="display:flex;gap:14px;align-items:flex-start">
      <div style="width:230px;flex-shrink:0;display:flex;flex-direction:column;gap:2px;max-height:76vh;overflow:auto">${listHtml}</div>
      <div style="flex:1;min-width:0">${mainHtml}</div>
    </div>`;
}

// --- 交互 ---
function bindXiaju(){
  document.querySelectorAll("#content .role-list-item[data-num]").forEach(el => {
    el.addEventListener("click", () => {
      xjuCurEp = Number(el.dataset.num); xjuMode = "view";
      const c = $("content"); c.innerHTML = renderXiaju(); bindXiaju();
    });
  });
}
function xjuAdd(){
  const n = Number(prompt("新增第几集？（集号数字）", (xjuEps().slice(-1)[0]?.number || 0) + 1));
  if(!n) return;
  if(xjuEps().some(e => e.number === n)){ toast("⚠️ 已存在第" + n + "集"); return; }
  P.xiaju = P.xiaju || {}; P.xiaju.episodes = P.xiaju.episodes || [];
  P.xiaju.episodes.push({number: n, title: "", body: `# 第${n}集《标题》\n\n## 本集结构\n循环1：〔事件〕→ 结尾爆点\n\n## 本集核心情绪\n\n## 循环1 · <地点> / 日 / 内景\n场景：<纯地点名> 日 内\n**人物：**\n**剧情功能：**\n**情绪目标：**\n**循环结尾爆点：**\n### 循环1·0—3秒\n- **【场景】** <地点> › <分区>（内·日）｜空间证据：\n- **【出场角色】** 。\n- **【画面】** \n- **【台词】** \n- **【情绪功能】** \n- **【可拍性】** \n### 循环1·3—12秒\n- **【场景】** \n- **【画面】** \n- **【台词】** \n`, updated_at: new Date().toISOString().slice(0,16).replace("T"," ")});
  xjuCurEp = n; xjuMode = "edit";
  const c = $("content"); c.innerHTML = renderXiaju(); bindXiaju();
  xjuSave(true);
}
function xjuEdit(){ xjuMode = "edit"; const c = $("content"); c.innerHTML = renderXiaju(); bindXiaju(); }
function xjuCancelEdit(){ xjuMode = "view"; const c = $("content"); c.innerHTML = renderXiaju(); bindXiaju(); }
function xjuSave(silent){
  const ta = $("xju-editor");
  const cur = xjuCur();
  if(!cur) return;
  if(ta){
    cur.body = ta.value;
    const tm = cur.body.match(/^#\s*第\s*\d+\s*集[《\s]*([^《\n]*)/);
    if(tm) cur.title = tm[1].trim().replace(/》$/, "");
  }
  cur.updated_at = new Date().toISOString().slice(0,16).replace("T"," ");
  fetch("/xiaju/save", {method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify({episodes: xjuEps()})})
    .then(r => r.json()).then(j => {
      if(j.ok){ if(!silent) toast("💾 已保存（" + xjuEps().length + " 集）"); }
      else toast("❌ 保存失败：" + (j.error || ""));
    }).catch(e => toast("❌ 保存失败：" + e));
  xjuMode = "view"; const c = $("content"); c.innerHTML = renderXiaju(); bindXiaju();
}
function xjuDel(){
  const cur = xjuCur();
  if(!cur) return;
  if(!confirm("确认删除第" + cur.number + "集？此操作不可撤销。")) return;
  P.xiaju.episodes = P.xiaju.episodes.filter(e => e.number !== cur.number);
  xjuCurEp = null;
  fetch("/xiaju/save", {method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify({episodes: xjuEps()})});
  const c = $("content"); c.innerHTML = renderXiaju(); bindXiaju();
  toast("🗑 已删除");
}
function xjuCopyAll(){
  const cur = xjuCur(); if(!cur) return;
  navigator.clipboard.writeText(cur.body || "").then(() => toast("📋 已复制整集"));
}
function xjuDownload(){
  const cur = xjuCur(); if(!cur) return;
  const blob = new Blob([cur.body || ""], {type: "text/markdown;charset=utf-8"});
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `ep${String(cur.number).padStart(3,"0")}.md`;
  a.click(); URL.revokeObjectURL(a.href);
}
function xjuCopyCycle(btn){
  const cur = xjuCur(); if(!cur) return;
  const key = btn.dataset.key || "";
  const lines = String(cur.body || "").split("\n");
  const out = [];
  let on = false;
  for(const line of lines){
    if(line.startsWith("## ")){
      if(on) break;
      on = line.trim() === key || line.trim() === key.replace(/\s+/g, " ");
    }
    if(on) out.push(line);
  }
  if(out.length) navigator.clipboard.writeText(out.join("\n")).then(() => toast("📋 已复制本循环"));
  else toast("⚠️ 未找到该循环内容");
}
