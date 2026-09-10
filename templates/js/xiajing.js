// ===== 虾镜（novel 风格分镜工作台：分镜脚本 / 制作 / 故事板）=====
// ★ 2026-08-21 重构：集数层保留，集内 3 Tab；编辑机制=副本（is_edited+original_shot）/拖动重排/增删/重置
let xjCurEp = null;
let xjCurTab = "shots";      // shots | make | storyboard
let xjCurShot = 0;           // 制作页当前镜头 index
let xjMakeEditing = false;   // 制作页：当前镜 11 字段编辑态（★ 2026-08-22 编辑功能从分镜脚本页迁移到制作页）
let xjStorySel = {};         // 故事板勾选 {ep:{idx:true}}
let xjDragFrom = null;       // 拖动源 idx
let gvState = { refs: [] };  // ★ 2026-08-23 生视频弹窗状态（参考图 ≤2 张）

function xjEps(){ return P.xiajing?.episodes || []; }
function xjEpObj(){ const eps=xjEps(); if(xjCurEp==null && eps.length) xjCurEp=eps[0].number; return eps.find(e=>e.number===xjCurEp); }
function xjShots(ep){ return (ep && (ep.edited_shots || ep.shots)) || []; }

function renderXiajing(){
  const ep = xjEpObj();
  if(!ep) return `<div style="padding:24px;color:var(--mut);text-align:center">暂无剧集</div>`;
  const shots = xjShots(ep);
  if(xjCurShot==null) xjCurShot = 0;
  if(xjCurShot >= shots.length) xjCurShot = Math.max(0, shots.length-1);
  const tabs = [
    {k:"shots", label:"📋 分镜脚本"},
    {k:"storyboard", label:"🖼 故事板"},
    {k:"make", label:"🎬 制作"},
    {k:"space", label:"🗺 拓扑图"},
  ];
  const body = {shots:renderShotsTab(ep), make:renderMakeTab(ep), storyboard:renderStoryTab(ep), space:renderSpaceTab(ep)}[xjCurTab] || "";
  return `
  <div style="display:flex;align-items:center;gap:10px;margin-bottom:14px;flex-wrap:wrap">
    <span class="back" onclick="backToEpGrid()">← 返回剧集列表</span>
    <span class="pill">第 ${ep.number} 集 <b>${esc(ep.title)}</b></span>
    <span class="pill">🎬 ${shots.length} 镜</span>
    <div style="flex:1"></div>
    <div class="tabs" style="margin-bottom:0">
      ${tabs.map(t=>`<div class="t ${t.k===xjCurTab?'active':''}" data-tab="${t.k}" style="padding:4px 12px;font-size:12px">${t.label}</div>`).join("")}
    </div>
  </div>
  <div>${body}</div>`;
}

// ===== ★ 2026-09-10 3.5.14 空间拓扑图资产位（虾镜线；结构对齐听风 tf_space_map，两条线数据链仍完全隔离）=====
// 数据契约：ep.space_maps = [{name, prompt, prompt_cn, image, ready}]（每场一张，name 带场标识如"空间拓扑图·场1"）
//          旧单数字段 space_map_prompt/space_map_image 兼容归一化为单项集合（旧项目数据一律不动）
// 原缺口：虾镜此前无任何渲染位 → 用户无处上传，"每场一张"的拓扑图只能靠手改 json，D2 长期红灯
function xjSpaceMaps(ep){
  let arr = Array.isArray(ep.space_maps) ? ep.space_maps.filter(Boolean) : [];
  if(!arr.length && ((ep.space_map_prompt && String(ep.space_map_prompt).trim()) || (ep.space_map_image && String(ep.space_map_image).trim()))){
    arr = [{name:"空间拓扑图", prompt: ep.space_map_prompt||"", image: ep.space_map_image||"", ready: !!ep.space_map_image}];
  }
  return arr;
}
function _xjEnsureMap(ep, idx){
  const maps = (Array.isArray(ep.space_maps) ? ep.space_maps.filter(Boolean) : []);
  while(maps.length <= idx) maps.push({name:"空间拓扑图·场"+(maps.length+1), prompt:"", image:"", ready:false});
  ep.space_maps = maps;
  return maps[idx];
}
// 镜 → 所属场拓扑图：优先 s.space_map（场标识，AI 拆镜时写入），name 包含匹配；无则第一张（旧数据=归一化单项）
function xjShotSpaceMap(ep, s){
  const arr = xjSpaceMaps(ep);
  if(!arr.length) return null;
  const key = String((s && s.space_map) || "").trim();
  if(key){ const hit = arr.find(m => String(m.name||"").indexOf(key) >= 0); if(hit) return hit; }
  return arr[0];
}
function renderSpaceTab(ep){
  const maps = xjSpaceMaps(ep);
  const shots = xjShots(ep);
  const cards = maps.map((m, i) => {
    const ready = !!(m.image && String(m.image).trim());
    const img = ready ? esc(imgSrc(m.image)) : "";
    const label = esc(m.name || ("空间拓扑图·场" + (i+1)));
    const nShots = shots.filter(s => String((s.space_map||"").trim()) && String(s.space_map).indexOf(m.name||"__none__") >= 0).length;
    return `
    <div style="display:flex;align-items:center;gap:12px;padding:10px 12px;border:1px dashed #c4b5fd;border-radius:10px;background:#faf5ff;margin-bottom:8px">
      <div style="width:150px;height:84px;border-radius:8px;overflow:hidden;background:#e2e8f0;display:flex;align-items:center;justify-content:center;flex-shrink:0;${ready?`cursor:zoom-in`:`cursor:default`}" ${ready?`onclick="openZoom('${img}','${label}')" title="点击放大"`:`title="该场拓扑图待生成（点右侧 ✨ 生图或 ↑ 上传）"`}>
        ${ready?`<img src="${img}" style="width:100%;height:100%;object-fit:cover" onerror="this.style.display='none'">`:`<span style="display:block;width:100%;height:100%"></span>`}
      </div>
      <div style="flex:1;min-width:0">
        <b style="font-size:13px">🗺 ${label} ${ready?'<span class="pill" style="font-size:10px">✅ 已回填</span>':'<span class="pill" style="font-size:10px;color:#b45309">⏳ 未回填</span>'}</b>
        <div style="font-size:11px;color:var(--mut);margin-top:2px">本场机位调度（站位/轴线/CAM/越轴预案）· 黑白简笔垫图 · 每场一张 · 被 ${nShots} 镜引用</div>
        ${(m.prompt || m.prompt_cn) ? `<details style="margin-top:4px"><summary style="cursor:pointer;font-size:11px;color:#0f766e;user-select:none">📝 拓扑图提示词${m.prompt_cn?"（双语）":""}</summary><div style="margin-top:4px">${promptBlockDual(m.prompt_cn, m.prompt)}</div></details>` : `<div style="font-size:11px;color:#b45309;margin-top:2px">该场提示词未产出——AI 做空间拓扑图时写入 space_maps[i].prompt</div>`}
      </div>
      <div style="display:flex;gap:6px;flex-wrap:wrap;align-items:center;flex-shrink:0">
        <label class="btn primary" style="cursor:pointer">↑ 上传<input type="file" accept="image/*" style="display:none" onchange="doUpload(this,'space_map','xj-space-map-${ep.number}-${i}')"></label>
        <button class="pill primary" onclick="xjSpaceMapGen(${ep.number},${i})" title="生成该场空间拓扑图（弹窗中可编辑提示词）">✨ 生图</button>
      </div>
    </div>`;
  }).join("");
  const unbound = shots.filter(s => !String(s.space_map||"").trim()).length;
  return `
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;gap:8px;flex-wrap:wrap">
      <span style="font-size:13px;font-weight:600">🗺 空间拓扑图（每场一张 · 场景切分口径=摄影机需要搬运就拆图）</span>
      <button class="pill" onclick="xjSpaceMapAdd(${ep.number})" title="为本集新增一场的拓扑图条目">＋ 新增场次</button>
    </div>
    ${cards || `<div style="padding:10px;color:var(--mut);font-size:12px;border:1px dashed #d7dee8;border-radius:8px;margin-bottom:8px">尚无场次条目——点「＋ 新增场次」建第一场（提示词由 AI 做空间拓扑图时写入 space_maps；每场一张，禁多场挤一图）</div>`}
    <div style="margin-top:10px;padding:8px 10px;border-radius:8px;background:${unbound?'#fff7ed':'#f0fdf4'};font-size:11px;color:${unbound?'#b45309':'#166534'}">
      ${unbound ? `⚠️ ${unbound} 镜未标注所属场（space_map 字段为空）→ 这些镜投喂时拿不到空间锚，请 AI 拆镜时补齐` : `✅ 全部 ${shots.length} 镜均已标注所属场拓扑图`}
      ｜门禁：回填后跑 <code>check-scenes.py --shots shots.json --scenes assets-registry.json</code>，D2 应清零
    </div>`;
}
function xjSpaceMapAdd(epN){
  const ep = (xjEps()).find(e => e.number === epN);
  if(!ep){ toast("未找到该集"); return; }
  const idx = xjSpaceMaps(ep).length;
  _xjEnsureMap(ep, idx);
  xjSpaceMapGen(epN, idx);
}
function xjSpaceMapGen(epN, idx){
  if(!IS_SERVER){ toast("AI 生成需要服务模式：请双击「启动项目台.bat」"); return; }
  const ep = (xjEps()).find(e => e.number === epN);
  const i = Number(idx) || 0;
  const m = (ep && _xjEnsureMap(ep, i)) || null;
  const own = (m && m.prompt && String(m.prompt).trim()) || "";
  if(!own) toast("💡 该场专属拓扑图提示词未产出，已预填黑白简笔通用骨架——按本场布局修改后再生成");
  openGenModal("space_map", "xj-space-map-" + epN + "-" + i, own || XJ_SPACE_MAP_GENERIC, "", (m && m.prompt_cn) || "");
}
// 通用骨架（黑白简笔规范占位符，仅当该场 prompt 缺失时回退；规范单源 = references/shared-spatial-blocking.md §十）
const XJ_SPACE_MAP_GENERIC = `16:9 横屏白底简笔示意图，手绘风格平面俯视机位调度图（hand-drawn blueprint sketch style）：
[围合四面：<北/东/南/西 各面是实墙/矮墙/篱笆/房屋/开口——逐面写明，不留空>]；
[固定锚点：<门/窗/灶/筐/树等地物及其方位>]；
[站位：实心圆点+短朝向箭头=各角色位置与面朝方向，箭头只贴在圆点上]；
[两点间一条红色虚线直线 = 180° 动作轴线，轴线两端不得带箭头]；
[机位：若干小相机图标 CAM1~CAM4 全部布置在轴线同一侧（same side），细弧线示意调度]；
[纵深边界：门外/窗外可见什么、不得出现什么，逐条点名]。
仅黑白灰 + 一处红色虚线轴，线条干净，无人物造型、无写实渲染、无光影质感（no photorealism），
no text labels other than CAM numbers, no character names, no arrows on the axis`;

// ===== Tab1 分镜脚本（★ 2026-08-22 重构：大纲 7 列：镜号/秒/景别/运镜/画面要点/台词声音/叙事功能）=====
function renderShotsTab(ep){
  const shots = xjShots(ep);
  return `
  <div class="card" style="padding:14px 18px">
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;gap:10px;flex-wrap:wrap">
      <span style="font-size:14px;font-weight:600">📋 分镜脚本</span>
      <span style="font-size:12px;color:var(--mut)">点击行进制作 · 拖动行重排 · 内容编辑在制作页 ✏️</span>
      <span style="display:flex;gap:6px;align-items:center">
        <button class="pill primary" onclick="shotAdd()">＋ 添加分镜</button>
        <button class="pill" style="font-size:12px;padding:7px 12px;border-radius:10px;border:1px solid #fecaca;background:#fef2f2;color:#dc2626;font-weight:600;white-space:nowrap;cursor:pointer" onclick="shotResetAll(${ep.number})" title="整集分镜恢复为定稿原始版（清除编辑/添加/删除/拖动）">↺ 重置分镜</button>
      </span>
    </div>
    <div style="overflow:auto;max-height:70vh">
    <table style="width:100%;table-layout:fixed;border-collapse:collapse;font-size:13px">
      <thead><tr style="background:var(--panel2)">
        ${XJ_COLS.map((c,i)=>{
          const w = xjColW[i] || c.w;
          return `<th style="padding:8px 10px;border:1px solid var(--line);position:relative;${w?'width:'+w+'px':''}">${c.t}<span class="col-resizer" title="拖拽调列宽"></span></th>`;
        }).join("")}
      </tr></thead>
      <tbody>
        ${shots.map((s,i)=>renderShotRow(ep,s,i)).join("") || '<tr><td colspan="8" style="padding:20px;text-align:center;color:var(--mut)">暂无分镜，点「＋ 添加分镜」开始</td></tr>'}
      </tbody>
    </table>
    </div>
  </div>`;
}
function renderShotRow(ep,s,i){
  // ★ 2026-08-22 分镜脚本页只做展示/拖动/添加/删除；内容编辑已迁移到制作页（📄 分镜 11 字段「✏️ 编辑」）
  const cell = (val) => `<div class="xj-cell" style="max-height:64px;overflow:hidden;cursor:text" title="${esc(val)}">${esc(val)||'<span style="color:var(--mut);opacity:.5">—</span>'}</div>`;
  return `
  <tr class="xj-row" data-idx="${i}" draggable="true"
      ondragstart="shotDragStart(event,${i})" ondragover="shotDragOver(event)" ondrop="shotDrop(event,${i})" ondragend="shotDragEnd()"
      style="border-bottom:1px solid var(--line);cursor:grab">
    <td style="padding:6px 10px;border:1px solid var(--line);text-align:center" onclick="shotRowGo(${ep.number},${i})"><b>${esc(s.shot_number)}</b>${s.is_edited?'<span style="color:#b45309;font-size:10px"> ✎</span>':''}</td>
    <td style="padding:6px 10px;border:1px solid var(--line)" onclick="shotRowGo(${ep.number},${i})">${cell(s.duration)}</td>
    <td style="padding:6px 10px;border:1px solid var(--line)" onclick="shotRowGo(${ep.number},${i})">${cell(s.shot_type)}</td>
    <td style="padding:6px 10px;border:1px solid var(--line)" onclick="shotRowGo(${ep.number},${i})">${cell(s.movement)}</td>
    <td style="padding:6px 10px;border:1px solid var(--line)" onclick="shotRowGo(${ep.number},${i})">${cell(s.outline_visual)}</td>
    <td style="padding:6px 10px;border:1px solid var(--line)" onclick="shotRowGo(${ep.number},${i})">${cell(s.outline_dialogue_sound)}</td>
    <td style="padding:6px 10px;border:1px solid var(--line)" onclick="shotRowGo(${ep.number},${i})">${cell(s.outline_function)}</td>
    <td style="padding:6px 10px;border:1px solid var(--line)">
      <button class="pill" style="font-size:11px;padding:2px 8px;color:#b91c1c" onclick="shotDelete(${ep.number},${i})">🗑 删除</button>
    </td>
    <span class="row-resizer" title="拖拽调行高"></span>
  </tr>`;
}

// ===== Tab2 制作（左 11 字段分镜 + 右首帧/尾帧/视频）=====
function renderMakeTab(ep){
  const shots = xjShots(ep);
  if(!shots.length) return `<div style="padding:24px;color:var(--mut);text-align:center">暂无分镜，先去「分镜脚本」添加</div>`;
  const s = shots[xjCurShot] || shots[0];
  const editing = xjMakeEditing;   // ★ 2026-08-22 制作页编辑态（11 字段 + 时长）
  // ★ 2026-08-22 场景名解析：编辑稿可能缺 scene_name → 从 ep.scene_map 查表兜底
  const scName = (s.scene_name || (ep.scene_map || {})[s.scene_tag] || s.scene_tag || "");
  const showVal = (k, v) => (k === "scene_tag") ? scName : v;   // ★ 所属场景显示资产名
  const leftCol = XJ_MAKE_FIELDS.map(([k,lbl])=>`
    <div style="margin-bottom:6px"><b style="font-size:12px;color:var(--acc)">${lbl}</b>
    ${editing
      ? `<textarea id="xjm-${k}" rows="${k==='visual'||k==='narrative'||k==='action'?3:2}" style="width:100%;box-sizing:border-box;font-size:12px;border:1px solid var(--acc);border-radius:6px;padding:6px 8px;margin-top:2px;background:#fffbeb">${esc(s[k]||"")}</textarea>`
      : `<div style="font-size:12px;white-space:pre-wrap;background:var(--bg);border:1px solid var(--line);border-radius:6px;padding:6px 8px;margin-top:2px">${esc(showVal(k, s[k]))||'<span style="opacity:.5">—</span>'}</div>`}
    </div>`).join("");
  return `
  <div class="card" style="padding:14px 18px">
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px;flex-wrap:wrap">
      <span style="font-size:14px;font-weight:600">🎬 制作 · 镜 ${esc(s.shot_number)}</span>
      <span class="pill">${esc(s.scene_name || (ep.scene_map || {})[s.scene_tag] || s.scene_tag || "")}</span>
      <span class="pill">${esc(s.characters||"")}</span>
      <span class="pill">时长 ${esc(s.duration||"-")}s</span>
      ${s.is_edited?'<span class="pill" style="color:#b45309">✎ 已改</span>':''}
      <div style="flex:1"></div>
      <button class="pill" onclick="shotNav(-1)" ${xjCurShot<=0?'disabled style="opacity:.4"':''}>◀ 上一镜</button>
      <span style="font-size:12px;color:var(--mut)">${xjCurShot+1} / ${shots.length}</span>
      <button class="pill" onclick="shotNav(1)" ${xjCurShot>=shots.length-1?'disabled style="opacity:.4"':''}>下一镜 ▶</button>
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:18px" class="make-cols">
      <div style="border-right:1px solid var(--line);padding-right:16px;min-width:0">
        <div style="font-weight:600;font-size:13px;margin-bottom:8px;display:flex;align-items:center;gap:8px">📄 分镜（11 字段）
          <div style="flex:1"></div>
          ${editing
            ? `<span style="display:flex;gap:6px">
                <button class="pill primary" style="font-size:12px;padding:6px 12px" onclick="xjMakeSave()">💾 保存</button>
                <button class="pill" style="font-size:12px;padding:6px 12px" onclick="xjMakeCancel()">✖ 取消</button>
              </span>`
            : `<button class="pill" style="font-size:12px;padding:6px 12px" onclick="xjMakeEditStart()">✏️ 编辑</button>`}
        </div>
        ${leftCol}
      </div>
      <div style="min-width:0">
        <div style="font-weight:600;font-size:13px;margin-bottom:8px">🖼 产物（首帧 / 尾帧 / 视频）</div>
        <!-- ★ 2026-08-22 画面标注资产位（Canvas 标注工具，无历史）——放在首帧上面 -->
        <div style="margin-bottom:16px">
          <b style="font-size:13px;display:block;margin-bottom:6px">📌 画面标注</b>
          <div style="border:1px solid var(--line);border-radius:8px;overflow:hidden;background:var(--bg);cursor:pointer" onclick="openAnnModal('${esc(s.shot_number)}')" title="点此打开标注工具">
            ${s.annotated_image
              ? `<img src="${esc(s.annotated_image)}?t=${Date.now()}" style="width:100%;max-height:160px;object-fit:contain;display:block">`
              : `<div style="height:90px;display:flex;align-items:center;justify-content:center;color:var(--mut);font-size:12px">未标注（点此打开标注工具）</div>`}
          </div>
          <div style="display:flex;gap:6px;margin-top:6px;flex-wrap:wrap">
            <button class="btn-secondary" style="font-size:11px;padding:3px 10px" onclick="openAnnModal('${esc(s.shot_number)}')">📌 标注</button>
            <button class="btn-secondary" style="font-size:11px;padding:3px 10px" onclick="openAnnLib('${esc(s.shot_number)}')" title="从已有画面标注图中选一张应用到当前镜头">📋 复用标注</button>
            <span style="font-size:11px;color:var(--mut);align-self:center">底图默认所属场景图/首帧图；文字/编号/圆/矩形/画笔</span>
          </div>
        </div>
        ${renderProdBlock(s,"firstframe","首帧")}
        ${renderProdBlock(s,"tailframe","尾帧")}
        ${renderProdBlock(s,"video","视频")}
      </div>
    </div>
  </div>`;
}
function renderProdBlock(s,key,lbl){
  const isVideo = key==="video";
  const imgKey = isVideo ? "video" : key+"_image";
  const src = s[imgKey];
  const media = isVideo
    ? (s.video ? `<video src="${esc(s.video)}?t=${Date.now()}" controls style="width:100%;max-height:160px;border-radius:8px;background:#000"></video>`
              : `<div style="height:160px;display:flex;align-items:center;justify-content:center;background:var(--bg);color:var(--mut);font-size:12px;border-radius:8px;border:1px dashed var(--line)">未生成</div>`)
    : (src ? `<img src="${esc(src)}?t=${Date.now()}" style="width:100%;max-height:160px;object-fit:contain;border-radius:8px;border:1px solid var(--line);cursor:zoom-in" onclick="openZoom('${esc(imgSrc(src))}','${lbl} · 镜${esc(s.shot_number)}')" onerror="this.style.display='none'">
               <div style="height:0"></div>`
          : `<div style="height:160px;display:flex;align-items:center;justify-content:center;background:var(--bg);color:var(--mut);font-size:12px;border-radius:8px;border:1px dashed var(--line)">未生成</div>`);
  return `
  <div style="margin-bottom:16px">
    <b style="font-size:13px;display:block;margin-bottom:6px">${lbl} ${isVideo?"🎬":"🖼"}</b>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;align-items:start">
      <div>${media}</div>
      <div style="position:relative">
        <textarea id="xj-${key}-p" rows="6" placeholder="${lbl}提示词…" style="width:100%;box-sizing:border-box;min-height:160px;border:1px solid var(--line);border-radius:6px;padding:6px 38px 6px 8px;font-size:12px">${esc(s[key+"_prompt"]||"")}</textarea>
        <button type="button" class="btn-secondary" style="position:absolute;top:6px;right:6px;font-size:11px;padding:2px 8px;z-index:1" onclick="xjCopyPrompt('${key}')" title="复制提示词到剪贴板">📋 复制</button>
      </div>
    </div>
    <div style="display:flex;gap:6px;margin-top:6px">
      <label class="btn-secondary" style="font-size:11px;padding:3px 10px;cursor:pointer">↑ 上传
        <input type="file" accept="${isVideo?"video/*":"image/*"}" style="display:none" onchange='doUpload(this,"${key}","shot${esc(s.shot_number)}",${xjCurEp})'></label>
      ${isVideo
        ? `<button class="btn-secondary" style="font-size:11px;padding:3px 10px" onclick="openShotVideoModal(${xjCurEp},'${esc(s.shot_number)}')" title="弹出生视频窗口（单镜 1 镜成片）">✨ 生成</button>`
        : `<button class="btn-secondary" style="font-size:11px;padding:3px 10px" onclick="openGenModal('${key}','shot${esc(s.shot_number)}',(document.getElementById('xj-${key}-p')||{}).value||'',${xjCurEp})">✨ 生成</button>`}
    </div>
  </div>`;
}

// ★ 2026-08-23 复制提示词（首帧/尾帧/视频产物组）
function xjCopyPrompt(key){
  const ta = document.getElementById("xj-" + key + "-p");
  const v = (ta && ta.value) || "";
  if(!String(v).trim()){ toast("⚠️ 提示词为空"); return; }
  const done = () => toast("✅ 已复制提示词");
  const fallback = () => {
    const el = document.createElement("textarea");
    el.value = v; el.style.position = "fixed"; el.style.opacity = "0";
    document.body.appendChild(el); el.select();
    try{ document.execCommand("copy"); done(); }catch(e){ toast("❌ 复制失败"); }
    el.remove();
  };
  if(navigator.clipboard && navigator.clipboard.writeText){
    navigator.clipboard.writeText(v).then(done).catch(fallback);
  } else fallback();
}

// ===== Tab3 故事板（简约线条故事板生成器）=====
function renderStoryTab(ep){
  const shots = xjShots(ep);
  // ★ 2026-08-22 拼板分组：9/6 格板，末板不足也生成（留白）；如 37 镜 → 9,9,9,6,6（第5板 4beat+2白）
  const caps = (typeof storyBoardSplit === "function") ? storyBoardSplit(shots.length) : [9];
  const groups = [];
  let sidx = 0;
  caps.forEach((cap, gi)=>{
    const cnt = Math.min(cap, shots.length - sidx);
    const idxs = [];
    for(let k=sidx; k<sidx+cnt; k++) idxs.push(k);
    sidx += cnt;
    groups.push({idxs, cap, blank: cap - cnt});
  });
  const sbs = ep.storyboards || [];
  return `
  <div class="card" style="padding:14px 18px">
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;gap:10px;flex-wrap:wrap">
      <span style="font-size:14px;font-weight:600">🖼 故事板（简约线条 · ${shots.length} 镜拼板 ${groups.length} 张）</span>
      <span style="font-size:12px;color:var(--mut)">每板 6/9 格 · 拼不整留空白 · 每张独立【上传/生图/历史】</span>
      <button class="pill primary" onclick="batchGenStoryboard()" title="自动生成所有未生成的故事板分组">🎨 全部批量生图</button>
      <button class="pill" onclick="batchGenVideo(${ep.number})" title="将当前集所有未生成的视频段全部入队（00:00—9:00 外弹确认）">🎬 全部批量生视频</button>
    </div>
    <div style="display:flex;flex-direction:column;gap:18px;max-height:72vh;overflow:auto;padding-right:4px">
      ${groups.map((g, gi)=>storyboardRowHTML(ep, g, gi+1)).join("")}
    </div>
    <div id="story-result" style="margin-top:12px"></div>
  </div>`;
}
// ★ 2026-08-23 故事板「生视频提示词」折叠区：每板按 ≤15s 切成多条视频提示词（存 sb.video_prompts）
// ★ 2026-08-23 故事板行（横向：故事板块 + 视频成片位块，自动装填 ≤15s 多条）
function storyboardRowHTML(ep, g, gno){
  const shots = xjShots(ep);
  // ★ 2026-08-23 修复：未生成的板先创建对象进 storyboards 数组（否则自动装填写在临时 {} 上，
  //   点击生视频时 find 不到 → 提示词为空）
  let sb = (ep.storyboards || []).find(s => s.idx === gno);
  if(!sb){ sb = {idx: gno}; (ep.storyboards = ep.storyboards || []).push(sb); }
  const first = shots[g.idxs[0]]?.shot_number || "?";
  const last = shots[g.idxs[g.idxs.length - 1]]?.shot_number || "?";
  const ready = !!sb.ready || !!sb.image;
  const grid = g.cap === 9 ? "3×3" : "3×2";
  // ★ 自动装填：首次打开 tab 时按 15s 切段，并「同时」生成 seedance + h3 两套提示词一起存。
  //   video_prompts 结构 = { seedance:[...], h3:[...] }；切换模型只切显示、不重算。
  // ★ 修复：重建 video_segments 时必须继承已生成的视频引用（video / video_ready），
  //   否则每次渲染都会把 DB 里已落库的 mp4 路径覆盖掉 → 视频位永远显示占位。
  // ★ 旧数据迁移：sb.video_prompts 曾是数组（仅 seedance），首次装填时识别为旧格式 → 用新双模型结构覆盖。
  const isOldArr = Array.isArray(sb.video_prompts);
  let segWarn = "";
  const offlineSeed = sb.video_prompts && !isOldArr && sb.video_prompts.seedance && sb.video_prompts.seedance.length;
  if(offlineSeed){
    // ★ 离线同源段稿为准（build_prompts 产、build-data-js 注入）：视频段用离线 seg_ranges，不前端重算
    const old = sb.video_segments || [];
    sb.video_segments = (sb.seg_ranges || []).map((r, i) => ({
      first: r.first, last: r.last, total: r.total,
      video: old[i] && old[i].video, video_ready: old[i] && old[i].video_ready, video_result: old[i] && old[i].video_result,
    }));
    if(!Array.isArray(sb.video_prompts.h3)) sb.video_prompts.h3 = [];   // seedance-only：h3 留空
    // ★ 段边界一致性自检：离线 seg_ranges vs 当前镜独立切段，不一致=改过镜/时长变，提示重跑
    const feSegs = splitStory15s(shots, g.idxs);
    const off = sb.seg_ranges || [];
    if(feSegs.length !== off.length || feSegs.some((s, i) => !off[i] || String(off[i].first) !== String(s.first) || String(off[i].last) !== String(s.last))){
      segWarn = `<div style="flex-basis:100%;font-size:12px;color:#b45309;background:#fffbeb;border:1px solid #fde68a;border-radius:8px;padding:6px 10px">⚠ 板${gno} 离线段稿与当前镜时长不一致（改过镜/时长变了？）——请重跑 build_prompts + build-data-js 刷新段稿。</div>`;
    }
  } else {
    const segs = splitStory15s(shots, g.idxs);
    if(segs.length){
      const old = sb.video_segments || [];
      sb.video_segments = segs.map((s, i) => ({
        first: s.first, last: s.last, total: s.total,
        video: old[i]?.video, video_ready: old[i]?.video_ready,
        video_result: old[i]?.video_result,
      }));
      // 无离线段稿（旧数组格式 / 该板未离线处理）→ 前端兜底重算两套
      sb.video_prompts = {
        seedance: segs.map(s => buildStoryVideoPromptSeedance(shots, s)),
        h3: segs.map(s => buildStoryVideoPromptH3(shots, s)),
      };
    }
  }
  const segs = sb.video_segments || [];
  // ★ 显示按当前模型取对应分支
  const prompts = xjVPPrompt(ep, sb, (typeof genVideoModel !== "undefined" && genVideoModel === "h3") ? "h3" : "seedance");
  return `
  ${segWarn}
  <div style="display:flex;gap:14px;flex-shrink:0;align-items:stretch;min-width:max-content">
    <!-- 故事板块 -->
    <div style="width:260px;border:1px solid var(--line);border-radius:10px;padding:10px;background:#fff;display:flex;flex-direction:column">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px">
        <b style="font-size:13px">🖼 故事板 ${gno}<span style="color:var(--mut);font-weight:400"> · ${grid}</span></b>
        ${ready?'<span style="font-size:11px;color:#16a34a">✓</span>':'<span style="font-size:11px;color:var(--mut)">未生成</span>'}
      </div>
      <div style="font-size:11px;color:var(--mut);margin-bottom:6px">镜 ${esc(first)}~${esc(last)}</div>
      <div style="height:130px;border-radius:8px;overflow:hidden;background:var(--tag);display:flex;align-items:center;justify-content:center;margin-bottom:8px;flex-shrink:0">
        ${ready
          ? `<img src="${esc(imgSrc(sb.image))}" style="width:100%;height:100%;object-fit:cover;cursor:zoom-in" onclick="openZoom('${esc(imgSrc(sb.image))}','故事板 ${gno}（镜 ${esc(first)}~${esc(last)}）')" onerror="this.style.display='none'">`
          : `<span style="font-size:12px;color:var(--mut)">尚未生成</span>`}
      </div>
      <div style="display:flex;gap:6px;flex-wrap:wrap;align-items:center;margin-top:auto">
        ${uploadWidget("storyboard", "story-" + ep.number + "-" + gno)}
        <button class="pill primary" style="font-size:12px;padding:5px 10px" onclick="storyGenGroup(${ep.number},${gno},[${g.idxs.join(",")}])" title="按该组 ${g.idxs.length} 镜生成故事板">✨ 生图</button>
      </div>
    </div>
    <!-- 视频成片位块（每个 ≤15s 段一块） -->
    ${prompts.map((p, i) => videoCardHTML(ep.number, gno, i, p, segs[i] || {})).join("")}
  </div>`;
}
// ★ 2026-08-23 视频成片位卡（占位 + 段头 + 生视频按钮）
function videoCardHTML(epN, gno, i, prompt, seg){
  const hdr = seg.first ? `视频${i + 1} · 镜${seg.first}~${seg.last} · ${seg.total}s` : `视频${i + 1}`;
  // ★ 2026-08-23 视频结果来源：后端写 seg.video（assets 路径），前端也写 seg.video_result；任一非空即可
  const result = seg.video || seg.video_result || seg.result;
  // ★ 2026-08-24 修复（批量生视频实时刷新 bug）：
  //   缓存击破戳改用 seg._vt（仅在一次视频生成成功写回时更新一次），而非每次 rerender 用 Date.now()。
  //   否则同一次 tick 内多个任务 success → 多次 rerenderCurrent → <video> 的 src 不断变化 →
  //   浏览器反复 abort/重建视频请求，先完成的段1 的 mp4 加载被中途打断而显示不出（刷新后单次渲染才正常）。
  const vt = seg._vt ? ("?t=" + seg._vt) : "";
  const media = result
    ? `<video src="${esc(result)}${vt}" controls preload="auto" style="width:100%;height:100%;background:#000"></video>`
    : `<div style="display:flex;align-items:center;justify-content:center;height:100%;color:#a5b4fc;font-size:13px">🎬 视频占位</div>`;
  return `
  <div style="width:240px;border:1px solid #c4b5fd;border-radius:10px;padding:10px;background:#fff;display:flex;flex-direction:column">
    <div style="display:flex;align-items:center;justify-content:space-between">
      <b style="font-size:13px;color:#5b21b6">${hdr}</b>
      ${result ? `<button class="pill" style="font-size:11px;padding:2px 7px;color:#dc2626;border-color:#fecaca;background:#fef2f2" onclick="storyVideoSegDelete(${epN},${gno},${i})" title="删除该段视频（文件+记录一起删）">🗑</button>` : ""}
    </div>
    <div style="height:130px;background:#1e1b4b;border-radius:8px;overflow:hidden;margin:8px 0;flex-shrink:0">
      ${media}
    </div>
    <button class="pill primary" style="font-size:12px;padding:5px 10px;margin-top:auto" onclick="openGenVideoModal(${epN},${gno},${i})">🎬 生视频</button>
  </div>`;
}
// ★ 2026-08-24 故事板视频段删除：清 DB 段位引用 + 删本地 mp4（文件与记录一起删）
function storyVideoSegDelete(epN, gno, segIdx){
  if(!confirm(`确定删除该段视频？（本地 mp4 文件与记录一起删除，不可恢复）`)) return;
  if(!IS_SERVER){ toast("需服务模式（双击启动项目台.bat）"); return; }
  fetch("/story-video-delete",{method:"POST",headers:{"Content-Type":"application/json"},
    body:JSON.stringify({ep: epN, idx: gno, seg_idx: segIdx})})
    .then(r=>r.json()).then(res=>{
      if(!res.ok){ toast("⚠️ "+(res.error||"删除失败")); return; }
      // ★ 前端同步清内存段位引用（避免等 reload 才生效）
      const ep = (P.xiajing?.episodes||[]).find(e => e.number === epN);
      const sb = (ep?.storyboards||[]).find(s => s.idx === gno);
      const seg = (sb?.video_segments||[])[segIdx];
      if(seg){ seg.video = ""; seg.video_ready = false; seg.video_result = ""; seg._vt = 0; }
      rerenderCurrent();
      toast("🗑 已删除该段视频");
    }).catch(()=>toast("⚠️ 删除失败（服务异常）"));
}
// ★ 2026-08-23 生视频弹窗（API 后接；先做骨架：与生图弹窗同结构——提示词+参考图+模型+尺寸+启动）
function getGvModelLabel(){
  // ★ 2026-08-24：从 gv-model 下拉读当前选中的【视频引擎】名（明确是视频模型，区别于生图模型）
  const sel = $("gv-model");
  if(!sel) return "海螺 H3 视频 · 参考生";
  return sel.options[sel.selectedIndex]?.text || sel.value || "海螺 H3 视频 · 参考生";
}
function openGenVideoModal(epN, gno, idx){
  // ★ 2026-08-23 把 epN/gno/idx 存到 window（gvStart 异步提交时用）
  window._gvEpN = epN; window._gvGno = gno; window._gvSegIdx = idx;
  const ep = (P.xiajing?.episodes||[]).find(e => e.number === epN);
  const sb = (ep?.storyboards || []).find(s => s.idx === gno);
  const seg = (sb?.video_segments || [])[idx] || {};
  // ★ 2026-08-24 改版：video_prompts 为 {seedance,h3}，按当前 genVideoModel 取对应分支填入弹窗
  const _model = (typeof genVideoModel !== "undefined" && genVideoModel === "h3") ? "h3" : "seedance";
  const prompt = (xjVPPrompt(ep, sb, _model) || [])[idx] || "";
  const title = `第${epN}集·故事板${gno}·视频${idx + 1}${seg.first ? "（镜" + seg.first + "~" + seg.last + "）" : ""}`;
  $("gv-title").textContent = title;
  $("gv-prompt").value = prompt;
  // ★ 2026-08-23 时长/分辨率默认自动选：时长按提示词解析 → 分辨率默认 768P（用户可手改）
  const autoDur = autoDurationFromPrompt(prompt, seg.total);
  $("gv-info").innerHTML = `段头：${seg.first ? "镜" + seg.first + "~" + seg.last + " · " + seg.total + "s" : "未切段"} · 时长默认 <b style="color:var(--acc)">${autoDur}s</b>（按提示词）· 分辨率默认 <b style="color:var(--acc)">768P</b>（可手动改）<br><span style="color:var(--mut);font-size:11px">🎥 888 视频生成平台 · 输出 <b>.mp4 视频</b> · ${getGvModelLabel()} · 启动后后台异步（5~30 分钟）· 失败自动重试 2 次 · 完成后自动写入故事板视频位</span>`;
  // ★ 2026-08-23 打开时自动引用该段需要的资产图（角色主图→场景图→道具图，≤5 张；可手动增删）
  gvState.refs = gvAutoRefs(ep, seg);
  // ★ 2026-08-24 记录自动引用数量：自动图永远排在最前（gvOpenRefPicker 仅末尾 push），
  //   用于 gvRenderRefs 给每张图标注 <Picture N> 并区分「自动（对齐提示词）」/「手动（可能破坏对齐）」
  gvState.autoCount = (gvState.refs || []).length;
  gvRenderRefs();
  // ★ 时长下拉（4~15s，默认自动解析值）
  const durSel = $("gv-duration");
  durSel.innerHTML = [4,5,6,7,8,9,10,11,12,13,14,15]
    .map(d => `<option value="${d}"${d === autoDur ? " selected" : ""}>${d}s</option>`).join("");
  // ★ 分辨率下拉（768P/1080P/2K/4K，默认 768P）
  const resSel = $("gv-resolution");
  resSel.innerHTML = ["768P","1080P","2K","4K"]
    .map(r => `<option value="${r}"${r === "768P" ? " selected" : ""}>${r}</option>`).join("");
  // ★ 渠道不再下拉展示（★ 2026-08-24 需求：弹窗去掉渠道列）；后端仍需 channel_id →
  //   自动从 /gen-config 拉首个视频渠道缓存到 window._gvChannelId（★ 2026-09-02 MiniMax H3 优先，888 回退）
  fetch("/gen-config").then(r => r.json()).then(cfg => {
    window._gvChannelId = (typeof pickVideoChannel === "function" && pickVideoChannel(cfg.channels || [])?.id) || "";
    // 比例下拉（value 即 aspect_ratio，直接下发给 888 平台；默认选中项取设置「视频默认比例」）
    const sizeSel = $("gv-size");
    const defaultRatio = (cfg.default_sizes && cfg.default_sizes.video) || "16:9";
    const RATIOS = [
      ["16:9", "16:9 横屏（推荐）"],
      ["9:16", "9:16 竖屏"],
      ["1:1", "1:1 方图"],
      ["4:3", "4:3 横屏"],
      ["3:4", "3:4 竖屏"],
      ["21:9", "21:9 超宽屏"]
    ];
    sizeSel.innerHTML = RATIOS.map(([v, t]) =>
      `<option value="${v}"${v === defaultRatio ? " selected" : ""}>${t}</option>`).join("");
  }).catch(() => { window._gvChannelId = ""; });
  $("genvideo").classList.add("open");
}
function closeGenVideoModal(){
  const m = $("genvideo"); if(m) m.classList.remove("open");
  // ★ 2026-08-23 关闭时复位 gv-send 按钮 + 清窗口态，避免下次打开仍禁用
  const btn = $("gv-send"); if(btn){ btn.disabled = false; btn.textContent = "🚀 启动生视频"; }
  window._gvEpN = window._gvGno = window._gvSegIdx = 0;
  window._gvMode = ""; window._gvShotNum = "";
}
// ★ 2026-08-24 制作页（分镜脚本 Tab）单镜视频弹窗：与故事板多镜视频彻底独立
//   - 提示词 = buildShotVideoPrompt(s)（单镜 1 镜成片，非多镜拼接）
//   - 落库 = shot.video / shot.video_prompt（后端 /save-prompt category=video name=shotNN 已支持）
//   - 复用同一个 #genvideo 弹窗骨架，但 window._gvMode="shot" 让 gvStart 走单镜提交分支
function openShotVideoModal(epN, shotNumber){
  const ep = (P.xiajing?.episodes||[]).find(e => e.number === epN);
  if(!ep){ toast("⚠️ 未找到该集"); return; }
  const shots = xjShots(ep);
  const s = shots.find(x => String(x.shot_number) === String(shotNumber));
  if(!s){ toast("⚠️ 未找到该镜头"); return; }
  // ★ 单镜提示词：双模型并存（与故事板一致）。按当前 genVideoModel 取对应分支；
  //   分支为空则实时算 buildShotVideoPrompt(s) 并回写；用户手改过则落到对应分支（xjShotVPPrompt 内部处理）。
  const _model = (typeof genVideoModel !== "undefined" && genVideoModel === "h3") ? "h3" : "seedance";
  const prompt = xjShotVPPrompt(s, _model);
  window._gvMode = "shot";
  window._gvEpN = epN;
  window._gvShotNum = String(shotNumber);
  $("gv-title").textContent = `第${epN}集·单镜视频·镜${shotNumber}（1 镜成片）`;
  $("gv-prompt").value = prompt;
  const d = parseFloat(String(s.duration || "").replace(/[^\d.]/g, "")) || 3;
  $("gv-info").innerHTML = `🎬 <b>单镜视频</b>（1 镜成片）· 镜${shotNumber} · 该镜时长 <b style="color:var(--acc)">${d}s</b> · 分辨率默认 <b style="color:var(--acc)">768P</b>（可手改）<br><span style="color:var(--mut);font-size:11px">🎥 888 视频生成平台 · 输出 <b>.mp4 视频</b> · ${getGvModelLabel()} · 启动后后台异步（5~30 分钟）· 失败自动重试 2 次 · 完成后写入<b>该镜视频位</b></span>`;
  // 自动引用：角色定妆/场景/道具（≤5 张）
  gvState.refs = gvAutoRefsForShot(s);
  gvState.autoCount = (gvState.refs || []).length;
  gvRenderRefs();
  // 时长下拉（clamp 4~15，默认取该镜时长，单镜视频允许短）
  const durSel = $("gv-duration");
  durSel.innerHTML = [4,5,6,7,8,9,10,11,12,13,14,15]
    .map(x => `<option value="${x}"${x === Math.max(4, Math.min(15, Math.round(d))) ? " selected" : ""}>${x}s</option>`).join("");
  const resSel = $("gv-resolution");
  resSel.innerHTML = ["768P","1080P","2K","4K"]
    .map(r => `<option value="${r}"${r === "768P" ? " selected" : ""}>${r}</option>`).join("");
  fetch("/gen-config").then(r => r.json()).then(cfg => {
    window._gvChannelId = (typeof pickVideoChannel === "function" && pickVideoChannel(cfg.channels || [])?.id) || "";
    const sizeSel = $("gv-size");
    const defaultRatio = (cfg.default_sizes && cfg.default_sizes.video) || "16:9";
    const RATIOS = [
      ["16:9", "16:9 横屏（推荐）"],
      ["9:16", "9:16 竖屏"],
      ["1:1", "1:1 方图"],
      ["4:3", "4:3 横屏"],
      ["3:4", "3:4 竖屏"],
      ["21:9", "21:9 超宽屏"]
    ];
    sizeSel.innerHTML = RATIOS.map(([v, t]) =>
      `<option value="${v}"${v === defaultRatio ? " selected" : ""}>${t}</option>`).join("");
  }).catch(() => { window._gvChannelId = ""; });
  $("genvideo").classList.add("open");
}
// ★ 2026-08-24 单镜自动引用：角色（按场景选身份）→ 场景 → 道具（≤5）
function gvAutoRefsForShot(s){
  const chNames = (P.xiatang?.characters || []).map(c => c.name).filter(Boolean);
  const sceneNames = (P.xiatang?.scenes || []).map(sm => sm.name).filter(Boolean);
  const propNames = (P.xiatang?.props || []).map(p => p.name).filter(Boolean);
  const names = [], scenes = [], props = [];
  const chStr = String(s.characters || "") + " " + String(s.scene_name || "") + " " + String(s.scene_tag || "");
  chNames.forEach(n => { if(chStr.includes(n) && !names.includes(n)) names.push(n); });
  const sn = String(s.scene_name || s.scene_tag || "");
  sceneNames.forEach(nm => { if(sn.includes(nm) && !scenes.includes(nm)) scenes.push(nm); });
  const pStr = chStr + " " + String(s.visual || "") + " " + String(s.action || "");
  propNames.forEach(nm => { if(pStr.includes(nm) && !props.includes(nm)) props.push(nm); });
  const refs = [];
  const sceneName = scenes[0] || "";
  const pick = (arr, finder) => { for(const n of arr){ const it = finder(n); if(it && refs.length < 5) refs.push(it); if(refs.length >= 5) return; } };
  pick(names, n => gvRoleRefByScene(n, sceneName));
  pick(scenes, n => { const x = (P.xiatang?.scenes || []).find(y => y.name === n); return x && x.image ? x.image : null; });
  pick(props, n => { const x = (P.xiatang?.props || []).find(y => y.name === n); return x && x.image ? x.image : null; });
  return refs.slice(0, 5);
}
// ★ 2026-08-24 按镜头编号反查 storyboard 视频段后弹出生视频窗口
//   设计动机：分镜脚本 Tab 的视频产物区【✨ 生成】按钮没有 gno/idx 信息，
//   而 openGenVideoModal 强依赖这两项 → 这里按 shot_number 在全部 storyboard.video_segments 中
//   找第一个 (seg.first ≤ shotN ≤ seg.last) 的段，调 openGenVideoModal。
//   若未找到（没生成过故事板或该镜不在任何段里），则提示去先打开故事板 Tab。
function openGenVideoModalByShot(epN, shotN){
  const ep = (P.xiajing?.episodes||[]).find(e => e.number === epN);
  if(!ep){ toast("⚠️ 未找到该集"); return; }
  const sbs = ep.storyboards || [];
  for(const sb of sbs){
    const segs = sb.video_segments || [];
    for(let i=0; i<segs.length; i++){
      const seg = segs[i] || {};
      if(!seg.first || !seg.last) continue;
      // 比较用数字（shotN 可能是数字或字符串）
      const sN = parseInt(shotN, 10);
      if(sN >= parseInt(seg.first, 10) && sN <= parseInt(seg.last, 10)){
        openGenVideoModal(epN, sb.idx, i);
        return;
      }
    }
  }
  toast("⚠️ 未找到该镜头的视频段（需先在【故事板】Tab 打开过并自动装填视频段）");
}
function gvCopyPrompt(){ const ta = $("gv-prompt"); if(!ta || !ta.value){ toast("⚠️ 提示词为空"); return; } if(navigator.clipboard){ navigator.clipboard.writeText(ta.value).then(()=>toast("✅ 已复制提示词")).catch(()=>{}); } else { ta.select(); try{ document.execCommand("copy"); toast("✅ 已复制提示词"); }catch(e){} } }
// ★ 2026-08-23 生视频启动：调 /gen-video（888 平台）→ 拿 task_id → 5s 轮询 /gen-video-status
//   完成后写回 seg.video + seg.video_ready + 刷新弹窗/故事板
//   其它协议（openai/gemini/ark）暂不支持视频：后端返回 400 + 错误提示
let gvPollTimer = null;
// ★ 2026-08-23 时长自动解析：从提示词正文累加「【镜X · Ns】」得到总秒数，clamp 4~15
//   解析规则：每行匹配 /镜\d+[^【】\n]*?·\s*(\d+(?:\.\d+)?)\s*s/ 累加
//   兜底：用 seg.total（来自分镜切段）→ 再兜底 6s
function autoDurationFromPrompt(promptText, segTotal){
  let sum = 0; let hit = 0;
  if(promptText){
    const lines = promptText.split(/\n/);
    lines.forEach(ln => {
      // 兼容「【镜01 · 4s】」/「【镜12·3s】」/「【镜01 · 4.5s】」等变体
      const m = ln.match(/【\s*镜\d+[^】]*?·\s*(\d+(?:\.\d+)?)\s*s/i);
      if(m){
        const v = parseFloat(m[1]);
        if(!isNaN(v) && v > 0){ sum += v; hit++; }
      }
    });
  }
  if(!hit && segTotal){
    const t = parseFloat(segTotal);
    if(!isNaN(t) && t > 0) sum = t;
  }
  if(!sum) sum = 6;
  // 888 平台规范：duration 必须是 4~15 整数秒
  const d = Math.max(4, Math.min(15, Math.round(sum)));
  return d;
}
// ★ 2026-08-23 提示词变更 → 实时刷新时长预览（gv-info）
function gvPromptChange(){
  const ta = $("gv-prompt"); if(!ta) return;
  const epN = (window._gvEpN || 0), gno = (window._gvGno || 0), segIdx = (window._gvSegIdx || 0);
  if(!epN || !gno) return;
  const ep = (P.xiajing?.episodes||[]).find(e => e.number === epN);
  const sb = (ep?.storyboards || []).find(s => s.idx === gno);
  const seg = (sb?.video_segments || [])[segIdx] || {};
  const d = autoDurationFromPrompt(ta.value, seg.total);
  const infoEl = $("gv-info");
  if(infoEl){
    infoEl.innerHTML = `段头：${seg.first ? "镜" + seg.first + "~" + seg.last + " · " + seg.total + "s" : "未切段"} · 时长自动按提示词 <b style="color:var(--acc)">${d}s</b> · 分辨率 <b style="color:var(--acc)">768P</b><br><span style="color:var(--mut);font-size:11px">🎥 888 视频生成平台 · 输出 <b>.mp4 视频</b> · ${getGvModelLabel()} · 启动后后台异步（5~30 分钟）· 失败自动重试 2 次 · 完成后自动写入故事板</span>`;
  }
}
async function gvStart(){
  const ta = $("gv-prompt");
  if(!ta || !ta.value.trim()){ toast("⚠️ 请先填写提示词"); return; }
  const epN = (window._gvEpN || 0), gno = (window._gvGno || 0), segIdx = (window._gvSegIdx || 0);
  const isShot = (window._gvMode === "shot");
  // ★ 2026-08-24：单镜视频模式只需 epN + shotNum，不需要 gno/segIdx
  if(isShot){
    if(!epN || !window._gvShotNum){ toast("⚠️ 弹窗状态丢失，请重开"); return; }
  } else {
    if(!epN || !gno){ toast("⚠️ 弹窗状态丢失，请重开"); return; }
  }
  // ★ 2026-08-24 渠道不再下拉：从缓存 window._gvChannelId 取（openGenVideoModal 已拉 /gen-config）；
  //   兜底：缓存为空时同步再拉一次，仍空则提示去设置
  let channelId = window._gvChannelId || "";
  if(!channelId){
    try{
      const cfg = await (await fetch("/gen-config")).json();
      channelId = (typeof pickVideoChannel === "function" && pickVideoChannel(cfg.channels || [])?.id) || "";
      window._gvChannelId = channelId;
    }catch(e){ channelId = ""; }
  }
  if(!channelId){
    toast("⚠️ 请先在 ⚙ 设置配置视频渠道（MiniMax H3 或 LK888 协议 + baseUrl + apiKey）");
    return;
  }
  const model = ($("gv-model") && $("gv-model").value) || "hailuo-h3-cankaosheng";
  // ★ 比例下拉 value 即 aspect_ratio（16:9/9:16/1:1/4:3/3:4/21:9）；size 同步该值供后端透传
  const aspectRatio = ($("gv-size") && $("gv-size").value) || "16:9";
  const size = aspectRatio;
  // ★ 时长/分辨率：从下拉读（默认值在 openGenVideoModal 已设为 自动解析值/768P，用户可手改）
  const duration = parseInt(($("gv-duration") && $("gv-duration").value) || "6", 10) || 6;
  const resolution = ($("gv-resolution") && $("gv-resolution").value) || "768P";
  // ★ 单镜视频：name=shotNN（后端按 shot_number 定位写回 shot.video）；多镜视频：name=故事板段
  const shotNum = isShot ? window._gvShotNum : null;
  // ★ 单镜：用户手改/确认后的提示词按当前模型落回对应分支（双模型并存），并同步旧 video_prompt 字段
  if(isShot){
    const epObj = (P.xiajing?.episodes||[]).find(e => e.number === epN);
    const shObj = epObj ? (xjShots(epObj) || []).find(x => String(x.shot_number) === String(shotNum)) : null;
    if(shObj){
      if(!shObj.video_prompts || typeof shObj.video_prompts !== "object" || Array.isArray(shObj.video_prompts)){
        shObj.video_prompts = { seedance: "", h3: "" };
      }
      if(_model === "h3") shObj.video_prompts.h3 = ta.value.trim(); else shObj.video_prompts.seedance = ta.value.trim();
      shObj.video_prompt = shObj.video_prompts.seedance;
      shObj.is_edited = true;
    }
  }
  const payload = isShot
    ? {
        ep: epN, idx: 0, seg_idx: 0,
        shot: shotNum,                       // ★ 单镜专用：写回 shot.video / shot.video_prompt
        model,
        size, prompt: ta.value.trim(),
        images: (gvState.refs || []).slice(0, 5),
        channel_id: channelId,
        duration, aspect_ratio: aspectRatio, resolution
      }
    : {
        ep: epN, idx: gno, seg_idx: segIdx,
        model,
        size, prompt: ta.value.trim(),
        images: (gvState.refs || []).slice(0, 5),
        channel_id: channelId,
        duration, aspect_ratio: aspectRatio, resolution
      };
  // 启动按钮禁用、提示进度
  const btn = $("gv-send");
  if(btn){ btn.disabled = true; btn.textContent = "⏳ 提交中…"; }
  toast("⏳ 提交视频生成任务…");
  fetch("/gen-video", {method:"POST", headers:{"Content-Type":"application/json"},
    body: JSON.stringify(payload)}).then(r => r.json()).then(j => {
    if(!j.ok){ toast("❌ " + (j.error || "提交失败")); if(btn){ btn.disabled = false; btn.textContent = "🚀 启动生视频"; } return; }
    const tid = j.task_id;
    toast("🎬 视频生成中（task_id=" + tid + " · 5~25 分钟）· 完成后弹窗/制作页自动刷新");
    // 关弹窗，让用户继续操作（视频在后台跑）
    closeGenVideoModal();
    // 启动轮询（单镜模式传入 shotNum，写回 shot.video）
    if(isShot) gvPollVideoShot(tid, epN, shotNum);
    else gvPollVideo(tid, epN, gno, segIdx);
  }).catch(err => {
    toast("❌ 提交失败：" + err.message);
    if(btn){ btn.disabled = false; btn.textContent = "🚀 启动生视频"; }
  });
}
// 轮询视频生成状态（5s/次，最多 25 分钟；status 终态后停止）
function gvPollVideo(taskId, epN, gno, segIdx){
  if(gvPollTimer){ clearInterval(gvPollTimer); gvPollTimer = null; }
  let elapsed = 0;
  const startTime = Date.now();
  const tick = () => {
    elapsed = Math.floor((Date.now() - startTime) / 1000);
    fetch("/gen-video-status?task_id=" + encodeURIComponent(taskId))
      .then(r => r.json())
      .then(j => {
        if(!j.ok){
          toast("⚠️ 视频任务查询失败：" + (j.error || ""));
          gvStopPoll();
          return;
        }
        if(j.status === "running"){
          // 仍在跑：每 30s 提醒一次（避免频繁 toast）
          if(elapsed > 0 && elapsed % 30 === 0){
            toast("🎬 视频生成中…已用 " + elapsed + "s（task_id=" + taskId + "）");
          }
          return;
        }
        if(j.status === "success"){
          gvStopPoll();
          // ★ 写回 seg.video + seg.video_ready 到内存（后端已持久化到 DB，刷新不丢）
          const ep = (P.xiajing?.episodes||[]).find(e => e.number === epN);
          const sb = (ep?.storyboards || []).find(s => s.idx === gno);
          const seg = (sb?.video_segments || [])[segIdx];
          if(seg){
            seg.video = j.video;
            seg.video_ready = true;
            seg.video_result = j.video;   // 兼容 videoCardHTML
            seg._vt = Date.now();         // ★ 缓存击破戳：本次生成完成才更新一次（稳定 src，避免 rerender 反复 abort 加载）
          }
          // ★ 始终刷新（不论当前 Tab）：故事板 Tab 直接更新；其他 Tab 下次切到故事板即是最新
          rerenderCurrent();
          toast("✅ 视频生成完成（耗时 " + (j.duration_sec || "?") + "s）· 已写入故事板视频位 " + (j.video || ""));
          return;
        }
        if(j.status === "failed"){
          gvStopPoll();
          toast("❌ 视频生成失败：" + (j.error || ""));
          return;
        }
        // queued 状态：继续轮询
      })
      .catch(err => {
        // 单次网络错误：继续轮询（不打断）
      });
  };
  gvPollTimer = setInterval(tick, 5000);
  tick();   // 立即跑一次
}
function gvStopPoll(){ if(gvPollTimer){ clearInterval(gvPollTimer); gvPollTimer = null; } }
// ★ 2026-08-24 单镜视频轮询：成功写回 shot.video（制作页单镜视频位）
function gvPollVideoShot(taskId, epN, shotNum){
  if(gvPollTimer){ clearInterval(gvPollTimer); gvPollTimer = null; }
  let elapsed = 0;
  const startTime = Date.now();
  const tick = () => {
    elapsed = Math.floor((Date.now() - startTime) / 1000);
    fetch("/gen-video-status?task_id=" + encodeURIComponent(taskId))
      .then(r => r.json())
      .then(j => {
        if(!j.ok){ toast("⚠️ 视频任务查询失败：" + (j.error || "")); gvStopPoll(); return; }
        if(j.status === "running"){
          if(elapsed > 0 && elapsed % 30 === 0) toast("🎬 视频生成中…已用 " + elapsed + "s（task_id=" + taskId + "）");
          return;
        }
        if(j.status === "success"){
          gvStopPoll();
          const ep = (P.xiajing?.episodes||[]).find(e => e.number === epN);
          const shots = xjShots(ep || {});
          const s = shots.find(x => String(x.shot_number) === String(shotNum));
          if(s){
            s.video = j.video;
            s.video_ready = true;
            s._vt = Date.now();   // 缓存击破戳：稳定 src
          }
          rerenderCurrent();
          toast("✅ 单镜视频完成（耗时 " + (j.duration_sec || "?") + "s）· 已写入镜 " + shotNum + " 视频位");
          return;
        }
        if(j.status === "failed"){ gvStopPoll(); toast("❌ 视频生成失败：" + (j.error || "")); return; }
      })
      .catch(() => {});
  };
  gvPollTimer = setInterval(tick, 5000);
  tick();
}

// ★★★ 2026-08-24 故事板批量生视频 ★★★
// 点击「🎬 全部批量生视频」触发：
//   1. 时间窗判定：00:00—9:00（h<9）放行；其它时间 confirm「费用较贵，是否继续？」
//   2. 遍历当前 ep.storyboards，收集 !seg.video_ready 的段（待生）
//   3. 对每个待生段同步入队 /gen-video（429 时 3s 重试最多 20 次；与 batchEnqueue 同思路）
//   4. 启动聚合轮询：每 8s 拉一次 /gen-video-status?task_id= 逐个查，写回 seg.video/video_ready → rerenderCurrent
// ★ 复用 gvAutoRefs(ep, seg) 收集该段资产图（角色→场景→道具，≤5 张）作为 image_url/images
let gvBatchPollTimer = null;     // 聚合轮询定时器（批量任务的，所有 task_id 共用）
let gvBatchPollList = [];        // 聚合轮询登记的待查 task_id 列表
let gvBatchPollMeta = {};        // task_id → {epN, gno, segIdx} 用于写回 seg 字段
function batchGenVideo(epN){
  const now = new Date();
  const h = now.getHours();
  if(h >= 10){
    if(!confirm(`当前时间 ${String(h).padStart(2,"0")}:${String(now.getMinutes()).padStart(2,"0")} 不在 00:00—9:00 内，生视频费用较贵，是否继续？`)) return;
  }
  const ep = (P.xiajing?.episodes||[]).find(e => e.number === epN);
  if(!ep){ toast("⚠️ 未找到第" + epN + "集"); return; }
  // ★ 收集待生段：每个 sb 取 sb.video_segments[i] 中 !video_ready 的
  const pending = [];
  (ep.storyboards || []).forEach(sb => {
    const segs = sb.video_segments || [];
    // ★ 2026-08-24 改版：按当前模型取对应分支提示词数组
    const _m = (typeof genVideoModel !== "undefined" && genVideoModel === "h3") ? "h3" : "seedance";
    const prompts = xjVPPrompt(ep, sb, _m);
    segs.forEach((seg, i) => {
      if(seg && !seg.video_ready){
        pending.push({
          epN, gno: sb.idx, segIdx: i,
          prompt: prompts[i] || "",
          total: seg.total || 0,
          first: seg.first, last: seg.last
        });
      }
    });
  });
  if(!pending.length){ toast("✅ 当前故事板没有待生视频（全部已完成）"); return; }
  // ★ 2026-08-24：先弹「模型 / 视频尺寸 / 分辨率」选择框（所有段统一用这组参数）
  //   渠道自动取 888 默认（不再让用户选）；视频尺寸按设置里的视频默认比例列选项
  fetch("/gen-config").then(r => r.json()).then(cfg => {
    const defaultRatio = (cfg.default_sizes && cfg.default_sizes.video) || "16:9";
    const RATIOS = [
      ["16:9", "16:9 横屏（推荐）"],
      ["9:16", "9:16 竖屏"],
      ["1:1", "1:1 方图"],
      ["4:3", "4:3 横屏"],
      ["3:4", "3:4 竖屏"],
      ["21:9", "21:9 超宽屏"]
    ];
    const sizeOpts = RATIOS.map(([v,t]) =>
      `<option value="${v}"${v === defaultRatio ? " selected" : ""}>${t}</option>`).join("");
    const resOpts = ["768P","1080P","2K","4K"]
      .map(r => `<option value="${r}"${r === "768P" ? " selected" : ""}>${r}</option>`).join("");
    const modelOpts = `
      <option value="hailuo-h3-cankaosheng">海螺 H3 参考生</option>
      <option value="hailuo-h3-quannengcankao">海螺 H3 全能参考</option>`;
    const mask = document.createElement("div");
    mask.className = "gen-mask open";
    mask.style.zIndex = 9999;
    mask.innerHTML = `
      <div class="gen-box" style="width:520px;max-width:94vw">
        <div class="gb-head"><b>🎬 批量生视频 · 第${epN}集 · 共 ${pending.length} 段待生</b><span class="x" onclick="this.closest('.gen-mask').remove()">×</span></div>
        <div style="padding:16px 20px;display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px">
          <div><div class="lbl">🧠 模型</div><select id="bgv-model" style="width:100%;border:1px solid var(--line);border-radius:8px;padding:6px 8px;font-size:12px">${modelOpts}</select></div>
          <div><div class="lbl">📐 视频尺寸</div><select id="bgv-size" style="width:100%;border:1px solid var(--line);border-radius:8px;padding:6px 8px;font-size:12px">${sizeOpts}</select></div>
          <div><div class="lbl">🎞 分辨率</div><select id="bgv-res" style="width:100%;border:1px solid var(--line);border-radius:8px;padding:6px 8px;font-size:12px">${resOpts}</select></div>
        </div>
        <div style="padding:0 20px 16px;font-size:11px;color:var(--mut)">所有待生视频将统一使用以上模型 / 尺寸 / 分辨率。渠道自动使用已配置的 888 视频通道。</div>
        <div style="display:flex;gap:8px;justify-content:flex-end;padding:12px 20px 20px;border-top:1px solid var(--line);background:var(--bg)">
          <button class="btn-secondary" style="padding:7px 14px;font-size:12.5px;cursor:pointer" onclick="this.closest('.gen-mask').remove()">取消</button>
          <button class="btn-primary" style="padding:7px 18px;font-size:13px;font-weight:600;cursor:pointer;background:var(--acc);color:#fff;border:none;border-radius:8px"
            onclick="__bgvConfirm(${epN})">✅ 确认批量生视频</button>
        </div>
      </div>`;
    document.body.appendChild(mask);
    // 把 pending 暂存供确认回调用
    window._bgvPending = pending;
    window._bgvEp = ep;
  }).catch(() => { toast("⚠️ 读取设置失败，无法批量生视频"); });
}
// ★ 批量生视频确认回调：读选择框参数 → 统一入队
function __bgvConfirm(epN){
  const mask = document.querySelector(".gen-mask[style*='9999']");
  const model = ($("bgv-model") && $("bgv-model").value) || "hailuo-h3-cankaosheng";
  const aspectRatio = ($("bgv-size") && $("bgv-size").value) || "16:9";
  const resolution = ($("bgv-res") && $("bgv-res").value) || "768P";
  if(mask) mask.remove();
  const pending = window._bgvPending || [];
  const ep = window._bgvEp;
  if(!pending.length){ toast("✅ 没有待生视频"); return; }
  // 渠道：从缓存或重新拉 888 渠道
  (async () => {
    let chId = window._gvChannelId || "";
    if(!chId){
      try{
        const cfg = await (await fetch("/gen-config")).json();
        chId = (typeof pickVideoChannel === "function" && pickVideoChannel(cfg.channels || [])?.id) || "";
        window._gvChannelId = chId;
      }catch(e){ chId = ""; }
    }
    if(!chId){ toast("⚠️ 未配置视频渠道（MiniMax H3 或 LK888），请到 ⚙ 设置添加"); return; }
    toast(`🚀 开始批量入队 ${pending.length} 个视频任务（模型 ${model} · ${aspectRatio} · ${resolution}）…`);
    const tasks = [];
    for(let i = 0; i < pending.length; i++){
      const it = pending[i];
      const duration = autoDurationFromPrompt(it.prompt, it.total);
      const refs = gvAutoRefs(ep, {first: it.first, last: it.last, total: it.total});
      // ★ 参考图 → data URL（assets/... → fetch → base64）
      const images = await Promise.all((refs||[]).map(async s => {
        const str = String(s||"");
        if(!str || str.startsWith("data:") || str.startsWith("http")) return str;
        try{
          const r = await fetch(str + (str.includes("?")?"&":"?") + "t=" + Date.now());
          if(!r.ok) return str;
          const blob = await r.blob();
          return await new Promise(res => {
            const rd = new FileReader();
            rd.onload = () => res(rd.result || str);
            rd.onerror = () => res(str);
            rd.readAsDataURL(blob);
          });
        }catch(e){ return str; }
      }));
      // ★ 入队重试：429 时 sleep 3s 重试最多 20 次
      let ok = null;
      for(let k = 0; k < 20; k++){
        try{
          const r = await fetch("/gen-video", {method:"POST", headers:{"Content-Type":"application/json"},
            body: JSON.stringify({
              ep: epN, idx: it.gno, seg_idx: it.segIdx,
              model, size: aspectRatio, prompt: it.prompt,
              images: images || [], channel_id: chId,
              duration, aspect_ratio: aspectRatio, resolution
            })});
          const j = await r.json();
          if(j.ok && j.task_id){ ok = j.task_id; break; }
          if(j.queue_full){ await sleep(3000); continue; }
          throw new Error(j.error || "入队失败");
        }catch(err){
          toast(`❌ 入队失败 段${it.segIdx + 1}: ${err.message || err}`);
          break;
        }
      }
      if(ok){ tasks.push({task_id: ok, epN, gno: it.gno, segIdx: it.segIdx}); }
    }
    if(!tasks.length){ toast("⚠️ 本次批量入队全部失败"); return; }
    toast(`✅ 批量入队完成 · 共 ${tasks.length} 个视频任务（最大 30 分钟）`);
    startBatchVideoPoll(tasks);
  })();
}
function sleep(ms){ return new Promise(r => setTimeout(r, ms)); }
function startBatchVideoPoll(tasks){
  // ★ 把 task 注册到聚合轮询表
  tasks.forEach(t => { gvBatchPollList.push(t.task_id); gvBatchPollMeta[t.task_id] = t; });
  if(gvBatchPollTimer) return;   // 已有 timer 在跑，直接复用
  const tick = async () => {
    if(!gvBatchPollList.length){ if(gvBatchPollTimer){ clearInterval(gvBatchPollTimer); gvBatchPollTimer = null; } return; }
    const remain = [];
    let needRender = false;   // ★ 2026-08-24：本轮有成功/变化才渲染一次（不每个 success 都重建 DOM）
    for(const tid of gvBatchPollList){
      try{
        const r = await fetch("/gen-video-status?task_id=" + encodeURIComponent(tid));
        const j = await r.json();
        if(!j.ok){ remain.push(tid); continue; }
        if(j.status === "success"){
          const meta = gvBatchPollMeta[tid];
          if(meta){
            const ep = (P.xiajing?.episodes||[]).find(e => e.number === meta.epN);
            const sb = (ep?.storyboards || []).find(s => s.idx === meta.gno);
            const seg = (sb?.video_segments || [])[meta.segIdx];
            if(seg){ seg.video = j.video; seg.video_ready = true; seg.video_result = j.video; seg._vt = Date.now(); }
            toast(`✅ 视频完成 故事板${meta.gno}·段${meta.segIdx + 1}（${j.duration_sec || "?"}s）`);
          }
          delete gvBatchPollMeta[tid];
          needRender = true;   // ★ 标记需渲染，循环结束后统一渲染一次（避免多 success 多次 innerHTML 重建 <video>）
        } else if(j.status === "failed"){
          delete gvBatchPollMeta[tid];
          toast(`❌ 视频失败 ${tid.slice(0,8)}: ${j.error || ""}`);
          needRender = true;
        } else {
          remain.push(tid);   // queued/running 继续轮询
        }
      }catch(e){ remain.push(tid); }
    }
    gvBatchPollList = remain;
    // ★ 本轮有变更才重渲染一次（无论几个视频成功，只重建一次 DOM → video src 稳定不反复 abort）
    if(needRender) rerenderCurrent();
    if(!gvBatchPollList.length && gvBatchPollTimer){
      clearInterval(gvBatchPollTimer); gvBatchPollTimer = null;
      gvBatchPollMeta = {};
      toast("🏁 批量生视频全部完成");
    }
  };
  gvBatchPollTimer = setInterval(tick, 5000);
  tick();   // 立即跑一次
}
function gvRefPicked(input){
  const files = Array.from(input.files || []); input.value = "";
  if(!files.length) return;
  let added = 0;
  for(const f of files){
    if((gvState.refs || []).length >= 5){ toast("⚠️ 最多 5 张参考图"); break; }
    const reader = new FileReader();
    reader.onload = () => { (gvState.refs = gvState.refs || []).push(reader.result); gvRenderRefs(); };
    reader.readAsDataURL(f);
    added++;
  }
  if(added) toast("✅ 已添加 " + added + " 张参考图");
}
// ★ 2026-08-23 自动引用该视频段需要的资产图：角色主图 → 场景图 → 道具图（≤5 张，按引用行优先级）
function gvAutoRefs(ep, seg){
  if(!ep || !seg || !seg.first) return [];
  const shots = xjShots(ep);
  const lo = parseInt(String(seg.first).replace(/^0+/, ""), 10) || 0;
  const hi = parseInt(String(seg.last).replace(/^0+/, ""), 10) || 0;
  const segShots = shots.filter(s => {
    const n = parseInt(String(s.shot_number).replace(/^0+/, ""), 10) || 0;
    return n >= lo && n <= hi;
  });
  const chNames = (P.xiatang?.characters || []).map(c => c.name).filter(Boolean);
  const sceneNames = (P.xiatang?.scenes || []).map(s => s.name).filter(Boolean);
  const propNames = (P.xiatang?.props || []).map(p => p.name).filter(Boolean);
  const names = [], scenes = [], props = [];
  segShots.forEach(s => {
    const chStr = String(s.characters || "") + " " + String(s.scene_name || "") + " " + String(s.scene_tag || "");
    chNames.forEach(n => { if(chStr.includes(n) && !names.includes(n)) names.push(n); });
    const sn = String(s.scene_name || s.scene_tag || "");
    sceneNames.forEach(nm => { if(sn.includes(nm) && !scenes.includes(nm)) scenes.push(nm); });
    const pStr = chStr + " " + String(s.visual || "") + " " + String(s.action || "");
    propNames.forEach(nm => { if(pStr.includes(nm) && !props.includes(nm)) props.push(nm); });
  });
  const refs = [];
  const sceneName = scenes[0] || "";
  const pick = (arr, finder) => { for(const n of arr){ const it = finder(n); if(it && refs.length < 5) refs.push(it); if(refs.length >= 5) return; } };
  // ★ 2026-08-23 角色引用：结合当前场景选身份 → 四视图优先，无四视图用定妆照，再无角色主图
  pick(names, n => gvRoleRefByScene(n, sceneName));
  pick(scenes, n => { const s = (P.xiatang?.scenes || []).find(x => x.name === n); return s && s.image ? s.image : null; });
  pick(props, n => { const p = (P.xiatang?.props || []).find(x => x.name === n); return p && p.image ? p.image : null; });
  return refs.slice(0, 5);
}
// ★ 2026-08-23 角色参考图按场景选身份：身份名关键词 ↔ 场景名匹配；四视图→定妆照→主图
function gvRoleRefByScene(roleName, sceneName){
  const c = (P.xiatang?.characters || []).find(x => x.name === roleName);
  if(!c) return null;
  const ids = c.identities || [];
  if(!ids.length) return c.image || null;
  const sc = String(sceneName || "");
  const kwMap = {
    "日常": ["家","客厅","厨房","卧室","楼道","电梯","门口","餐厅"],
    "职场": ["公司","办公室","会议室","广告"],
    "苏总": ["公司","办公室","会议室","广告"],
    "礼服": ["宴会","酒店","典礼","婚礼","酒会"],
    "高定": ["宴会","酒店","典礼","婚礼","酒会"],
    "律师": ["办公室","法院"],
    "商务": ["公司","会所","办公室"],
    "侍应生": ["餐厅","饭店","火锅"],
    "电竞": ["网吧"],
    "甜美": ["家","餐厅","咖啡"],
  };
  let best = null;
  for(const id of ids){
    const nm = String(id.name || "");
    const kws = Object.keys(kwMap).filter(k => nm.includes(k)).flatMap(k => kwMap[k]);
    if(kws.some(k => sc.includes(k))){ best = id; break; }
  }
  const id = best || ids[0];
  return (id.sheet_image) || id.image || c.image || null;
}
function gvRenderRefs(){
  const refs = gvState.refs || [];
  const autoCount = gvState.autoCount || 0;
  $("gv-ref-preview").innerHTML = refs.map((src, i) => {
    const picN = i + 1;
    const isAuto = i < autoCount;
    // ★ 2026-08-24：左下角标注 <Picture N> 编号；自动图（绿底）与提示词 <Picture N> 天然对齐，
    //   手动图（橙底+⚠️）若插在中间会破坏对齐，提示用户重生成提示词或核对顺序
    const badge = isAuto
      ? `<span style="position:absolute;left:2px;bottom:2px;background:rgba(22,163,74,.9);color:#fff;border-radius:4px;font-size:10px;line-height:14px;padding:1px 4px;font-family:monospace">&lt;Picture ${picN}&gt;</span>`
      : `<span title="手动添加：可能破坏与提示词 <Picture N> 的对齐，建议重生成提示词或核对顺序" style="position:absolute;left:2px;bottom:2px;background:rgba(217,119,6,.92);color:#fff;border-radius:4px;font-size:10px;line-height:14px;padding:1px 4px;font-family:monospace">⚠ &lt;Picture ${picN}&gt;</span>`;
    return `<div style="position:relative;width:80px;height:80px;border:1px solid var(--line);border-radius:6px;overflow:hidden">
    <img src="${esc(src)}" style="width:100%;height:100%;object-fit:cover">
    ${badge}
    <span onclick="gvRemoveRef(${i})" style="position:absolute;top:2px;right:2px;width:18px;height:18px;line-height:18px;text-align:center;background:rgba(220,38,38,.85);color:#fff;border-radius:50%;cursor:pointer;font-size:12px">×</span>
  </div>`;
  }).join("");
  $("gv-ref-count").textContent = refs.length ? refs.length + " / 5" : "";
  // ★ 2026-08-24：手动图插在中间时，给出对齐提醒
  const manualMid = refs.length > autoCount && autoCount > 0 && refs.length > 1;
  const tip = $("gv-ref-tip");
  if(tip) tip.style.display = manualMid ? "" : "none";
  const clearBtn = $("gv-ref-clear"); if(clearBtn) clearBtn.style.display = refs.length ? "" : "none";
}
function gvRemoveRef(i){ gvState.refs.splice(i, 1); gvRenderRefs(); }
function gvRefClear(){ gvState.refs = []; gvRenderRefs(); }
function gvOpenRefPicker(){
  // ★ 复用生图的 refpicker（统一资产图库）；选完后取前 2 张
  const _bak = window.__refPickerCallback;
  window.__refPickerCallback = (path, label) => {
    window.__refPickerCallback = _bak || null;
    if((gvState.refs || []).length >= 5){ toast("⚠️ 最多 5 张参考图"); return; }
    (gvState.refs = gvState.refs || []).push(path);
    gvRenderRefs();
    toast("✅ 已添加参考图");
  };
  openRefPicker();
}
// ★ 2026-08-23 按 ≤15s 切段（分镜脚本秒数累计，超 15 封段开新段）
function splitStory15s(shots, idxs){
  const SM = ((typeof P!=="undefined" && P.xiajing && P.xiajing.storyboard_config) || {}).seg_max_s || 15;
  const segs = []; let cur = [], curT = 0;
  idxs.forEach(i => {
    const s = shots[i]; if(!s) return;
    const d = parseFloat(String(s.duration || "").replace(/[^\d.]/g, "")) || 3;
    if(cur.length && curT + d > SM){ segs.push(cur); cur = []; curT = 0; }
    cur.push(s); curT += d;
    if(cur.length && curT >= SM){ segs.push(cur); cur = []; curT = 0; }
  });
  if(cur.length) segs.push(cur);
  return segs.map(seg => ({
    shots: seg,
    first: seg[0].shot_number,
    last: seg[seg.length - 1].shot_number,
    total: seg.reduce((a, s) => a + (parseFloat(String(s.duration || "").replace(/[^\d.]/g, "")) || 0), 0)
  }));
}
// ★ 2026-08-23 每条 15s 视频提示词骨架（引用行 + 风格段 + 逐镜 + 负向词；无站位段）
// ★ 2026-08-23 修复：引用行只匹配资产库真实角色名/场景名/道具名（防 characters 字段描述碎片被误当名字）
// ★ 2026-08-24 生视频提示词按模型路由：seedance → 中文 STYLE LOCK；h3 → MiniMax-H3 全参考六段式
//   调用方统一用 buildStoryVideoPrompt(shots, seg)，内部按全局 genVideoModel 路由。
// ★ 2026-08-24 改版：每条视频段「同时」生成两个模型的提示词并一起存，
//   video_prompts 结构 = { seedance:[str...], h3:[str...] }；显示/使用哪个由设置里的 genVideoModel 决定，
//   切换模型只是切显示，不重算、不等待、零出错（高容错）。
function buildStoryVideoPrompt(shots, seg){
  // 自动装填时按当前全局 genVideoModel 生成单条（仅用于兼容旧的惰性生成入口；新逻辑直接双模型并存）
  const model = (typeof genVideoModel !== "undefined" && genVideoModel === "h3") ? "h3" : "seedance";
  return model === "h3" ? buildStoryVideoPromptH3(shots, seg) : buildStoryVideoPromptSeedance(shots, seg);
}
// ★ 2026-08-24 双模型取值 helper：把 video_prompts 统一成 {seedance:[], h3:[]}
//   - 已是对象：直接取（缺哪边补空数组）
//   - 旧数组格式（迁移前）：当作 seedance 文本，h3 留空（显示 h3 时按当前 genVideoModel 实时算，见 xjVPPrompt）
function xjVPArr(holder){
  if(!holder) return {seedance: [], h3: []};
  if(Array.isArray(holder)) return {seedance: holder.slice(), h3: holder.slice()}; // 旧格式兜底（两段都用旧文本）
  return {seedance: holder.seedance || [], h3: holder.h3 || []};
}
// ★ 按当前模型取某板的提示词数组（旧数组迁移场景：h3 为空则实时算 h3，避免空白）
function xjVPPrompt(ep, sb, model){
  const o = xjVPArr(sb.video_prompts);
  const useH3 = (model === "h3");
  let arr = useH3 ? o.h3 : o.seedance;
  if(!arr || !arr.length){
    // 兜底：另一模型有文本时，实时候算当前模型（仅发生在旧数据未迁移时）
    const shots = xjShots(ep);
    const segs = sb.video_segments || [];
    if(segs.length){
      arr = segs.map(s => useH3 ? buildStoryVideoPromptH3(shots, s) : buildStoryVideoPromptSeedance(shots, s));
    } else {
      arr = [];
    }
  }
  return arr;
}

// 提取本段涉及的角色/场景/道具引用（与垫图顺序一致：角色 → 场景 → 道具）
function _collectVideoRefs(seg){
  const chNames = (P.xiatang?.characters || []).map(c => c.name).filter(Boolean);
  const sceneNames = (P.xiatang?.scenes || []).map(s => s.name).filter(Boolean);
  const propNames = (P.xiatang?.props || []).map(p => p.name).filter(Boolean);
  const names = [], scenes = [], props = [];
  seg.shots.forEach(s => {
    const chStr = String(s.characters || "") + " " + String(s.scene_name || "") + " " + String(s.scene_tag || "");
    chNames.forEach(n => { if(chStr.includes(n) && !names.includes(n)) names.push(n); });
    const sn = String(s.scene_name || s.scene_tag || "");
    sceneNames.forEach(nm => { if(sn.includes(nm) && !scenes.includes(nm)) scenes.push(nm); });
    const pStr = chStr + " " + String(s.visual || "") + " " + String(s.action || "");
    propNames.forEach(nm => { if(pStr.includes(nm) && !props.includes(nm)) props.push(nm); });
  });
  return {names, scenes, props};
}

// ===== ★ 2026-09-01 风格统一：生视频提示词的英文风格段/负面词改从风格确认（虾格）动态读取 =====
// 确认风格里的 style_instructions/avoid_instructions 是全项目唯一风格源头（虾塘资产 prompt 前缀同源）；
// fallback 保留内置默认，防 P.xiage 缺失。禁止在任何生成函数里硬编码风格段。
function xjStyleInstructions(){
  const cur = P.xiage?.current || "";
  const st = (P.xiage?.styles || []).find(s => s.style_id === cur);
  return (st && st.style_instructions) ? st.style_instructions :
    "Shot on RED Komodo, 35mm anamorphic, cinematic realistic modern drama style, warm amber candlelight interior, deep green velvet chairs, brass chandelier bokeh, shallow depth of field, filmic color grading, subtle film grain, natural skin texture, no plastic CGI look";
}
function xjAvoidInstructions(){
  const cur = P.xiage?.current || "";
  const st = (P.xiage?.styles || []).find(s => s.style_id === cur);
  return (st && st.avoid_instructions) ? st.avoid_instructions :
    "FORBIDDEN: no text, no watermark, no distortion, no plastic skin, no over-sharpening, no unnatural facial deformation, no axis jump";
}

// ===== Seedance 2.0：中文 STYLE LOCK 风格（顶部资产引用行 + 风格段 + 中文分镜 + negative） =====
function buildStoryVideoPromptSeedance(shots, seg){
  const {names, scenes, props} = _collectVideoRefs(seg);
  let refs = names.map((n, i) => n + "=图" + (i + 1)).join(" ");
  let num = names.length;
  // ★ 2026-08-31 修复：引用行列出组内全部场景（原只取 scenes[0]，跨场景组会漏场景）
  if(scenes.length) scenes.forEach(nm => { refs += (refs ? " " : "") + nm + "=图" + (++num); });
  if(props.length) props.forEach(nm => { refs += (refs ? " " : "") + nm + "=图" + (++num); });
  const style = xjStyleInstructions();   // ★ 2026-09-01 从确认风格动态读取
  const lines = [refs, "", style, ""];
  seg.shots.forEach(s => {
    const d = parseFloat(String(s.duration || "").replace(/[^\d.]/g, "")) || 3;
    let body = String(s.visual || "").trim();
    const a = String(s.action || "").trim();
    const mv = String(s.movement || "").trim();
    const dia = String(s.dialogue || "").trim();
    const sd = String(s.sound || "").trim();
    if(a) body += (body ? "；" : "") + a;
    if(mv && mv !== "固定") body += (body ? "；" : "") + "运镜：" + mv;
    if(dia) body += "。对白「" + dia + "」";
    if(sd) body += "。" + sd;
    lines.push("【镜" + s.shot_number + " · " + d + "s】" + body);
  });
  lines.push("", xjAvoidInstructions());   // ★ 2026-09-01 负面词从确认风格动态读取
  return lines.join("\n");
}

// ===== MiniMax-H3 全参考模式（Ref2VA 六段式，英文；角色经 <Subject N> 引用四视图，正文不重复服装描写） =====
function buildStoryVideoPromptH3(shots, seg){
  const {names, scenes, props} = _collectVideoRefs(seg);
  // 引用标签顺序：角色 → 场景 → 道具（与垫图顺序一致）；pic = 1-based 参考图序号
  const subjLabels = [];
  let idx = 0;
  names.forEach(n => { idx++; subjLabels.push({role:"character", name:n, label:"<Subject " + idx + ">", pic: idx}); });
  scenes.forEach(nm => { idx++; subjLabels.push({role:"scene", name:nm, label:"<Subject " + idx + ">", pic: idx}); });   // ★ 2026-08-31 组内全部场景
  props.forEach(nm => { idx++; subjLabels.push({role:"prop", name:nm, label:"<Subject " + idx + ">", pic: idx}); });
  const labelOf = (nm) => (subjLabels.find(x => x.name === nm) || {}).label || "";

  // subject_definitions
  const defs = subjLabels.map(x => {
    if(x.role === "character") return x.label + " is the character " + x.name + " referenced from the four-view character sheet <Picture " + x.pic + ">, with fixed appearance, costume, and hairstyle to be preserved exactly.";
    if(x.role === "scene") return x.label + " is the scene " + x.name + " referenced from <Picture " + x.pic + ">.";
    return x.label + " is the prop " + x.name + " referenced from <Picture " + x.pic + ">.";
  });

  // summary（引用标签 + 任务类型）
  const subjList = subjLabels.map(x => x.label).join(", ");
  const summary = "[reference generation] The target video shows " + subjList + " in a cinematic modern-drama scene. Character identity, costume, and appearance are locked to the referenced four-view sheets.";

  // retention_analysis
  const retain = subjLabels.map(x => {
    const shotHits = [];
    seg.shots.forEach((s, i) => {
      const txt = (s.characters||"") + " " + (s.scene_name||"") + " " + (s.scene_tag||"") + " " + (s.visual||"") + " " + (s.action||"");
      if(txt.includes(x.name)) shotHits.push("[Shot " + (i+1) + "]");
    });
    const where = shotHits.length ? " (appears in " + shotHits.join(", ") + ")" : "";
    return x.label + where + ": fully_preserved - the referenced appearance, costume, and spatial relationship are retained.";
  });

  // detailed_description（按播放顺序逐镜，插入 <Subject N> 标签；正文只写动作/运镜/对白/音效，不重复服装）
  const shotsTxt = seg.shots.map((s, i) => {
    const d = parseFloat(String(s.duration || "").replace(/[^\d.]/g, "")) || 3;
    let body = String(s.visual || "").trim();
    const a = String(s.action || "").trim();
    const mv = String(s.movement || "").trim();
    const dia = String(s.dialogue || "").trim();
    const sd = String(s.sound || "").trim();
    if(a) body += (body ? " " : "") + a;
    if(mv && mv !== "固定") body += ". Camera: " + mv + ".";
    if(dia) body += " " + dia;
    if(sd) body += " Sound: " + sd + ".";
    const head = (i === 0) ? "[Shot 1]" : "[Shot " + (i+1) + "] At " + fmtH3Time(cumDur(seg.shots, i)) + ", ";
    return head + body;
  }).join("\n");
  const detailed = xjStyleInstructions() + "\n" + shotsTxt;

  // 声音段
  const soundscape = "Ambient interior room tone and soft diegetic sound continue throughout the scene; specific effects appear with their shots above.";
  const music = "N/A";

  return [
    "subject_definitions:",
    ...defs,
    "",
    "summary:",
    summary,
    "",
    "retention_analysis:",
    ...retain,
    "",
    "detailed_description:",
    detailed,
    "",
    "overall_soundscape:",
    soundscape,
    "",
    "non_diegetic_music:",
    music
  ].join("\n");
}
// ===== 单镜视频提示词（★ 2026-08-24 制作页分镜脚本视频位专属：1 镜成片，≠ 故事板多镜拼接）=====
// 与故事板 buildStoryVideoPrompt 完全独立：这里是单镜种子/首尾帧 → 单镜成片，
// 提示词只描述这一镜的画面/动作/运镜，不出现「【镜X·Ns】」逐镜切段结构。
// 双模型并存（与故事板一致）：seedance 中文 STYLE LOCK / h3 MiniMax-H3 六段式，按全局 genVideoModel 切换显示。
function buildShotVideoPrompt(s){
  const model = (typeof genVideoModel !== "undefined" && genVideoModel === "h3") ? "h3" : "seedance";
  return model === "h3" ? buildShotVideoPromptH3(s) : buildShotVideoPromptSeedance(s);
}
// ★ 2026-08-24 单镜视频双模型 helper（对齐故事板 xjVPArr / xjVPPrompt；单镜只有 1 条，故用对象而非数组）
//   存储：shot.video_prompts = { seedance:"文本", h3:"文本" }
//   旧数据兼容：shot.video_prompt 为单字符串时，当作 seedance，h3 留空（显示 h3 时实时候算）
function xjShotVPArr(s){
  const vp = s && s.video_prompts;
  if(vp && typeof vp === "object" && !Array.isArray(vp)){
    return { seedance: (vp.seedance || "").toString(), h3: (vp.h3 || "").toString() };
  }
  // 旧格式：s.video_prompt 单字符串 → 迁移为 seedance，h3 实时算
  const legacy = (s && s.video_prompt && String(s.video_prompt).trim()) ? String(s.video_prompt) : "";
  return { seedance: legacy, h3: "" };
}
// 按当前模型取单镜提示词文本；分支为空则实时算 buildShotVideoPrompt(s) 并回写 s.video_prompts
function xjShotVPPrompt(s, model){
  const useH3 = (model === "h3");
  // ★ 进入即规范化：旧 video_prompt 字符串 → 迁移为 video_prompts.seedance，保证双分支都能正确取/写
  if(!s.video_prompts || typeof s.video_prompts !== "object" || Array.isArray(s.video_prompts)){
    const o = xjShotVPArr(s);
    s.video_prompts = { seedance: o.seedance, h3: o.h3 };
  }
  let txt = useH3 ? (s.video_prompts.h3 || "") : (s.video_prompts.seedance || "");
  if(!txt || !txt.trim()){
    txt = buildShotVideoPrompt(s);
    if(useH3) s.video_prompts.h3 = txt; else s.video_prompts.seedance = txt;
    s.video_prompt = s.video_prompts.seedance; // 同步旧字段（seedance 为默认显示分支）
  }
  return txt;
}
// 单镜涉及资产（角色/场景/道具）
function _collectShotRefs(s){
  const chNames = (P.xiatang?.characters || []).map(c => c.name).filter(Boolean);
  const sceneNames = (P.xiatang?.scenes || []).map(sm => sm.name).filter(Boolean);
  const propNames = (P.xiatang?.props || []).map(p => p.name).filter(Boolean);
  const names = [], scenes = [], props = [];
  const chStr = String(s.characters || "") + " " + String(s.scene_name || "") + " " + String(s.scene_tag || "");
  chNames.forEach(n => { if(chStr.includes(n) && !names.includes(n)) names.push(n); });
  const sn = String(s.scene_name || s.scene_tag || "");
  sceneNames.forEach(nm => { if(sn.includes(nm) && !scenes.includes(nm)) scenes.push(nm); });
  const pStr = chStr + " " + String(s.visual || "") + " " + String(s.action || "");
  propNames.forEach(nm => { if(pStr.includes(nm) && !props.includes(nm)) props.push(nm); });
  return {names, scenes, props};
}
// Seedance 风格：单镜，中文 STYLE LOCK + 单镜画面 + 负向
function buildShotVideoPromptSeedance(s){
  const {names, scenes, props} = _collectShotRefs(s);
  let refs = names.map((n, i) => n + "=图" + (i + 1)).join(" ");
  let num = names.length;
  if(scenes.length) refs += (refs ? " " : "") + scenes[0] + "=图" + (++num);
  if(props.length) props.forEach(nm => { refs += (refs ? " " : "") + nm + "=图" + (++num); });
  const style = xjStyleInstructions();   // ★ 2026-09-01 从确认风格动态读取
  let body = String(s.visual || "").trim();
  const a = String(s.action || "").trim();
  const mv = String(s.movement || "").trim();
  const dia = String(s.dialogue || "").trim();
  const sd = String(s.sound || "").trim();
  if(a) body += (body ? "；" : "") + a;
  if(mv && mv !== "固定") body += (body ? "；" : "") + "运镜：" + mv;
  if(dia) body += "。对白「" + dia + "」";
  if(sd) body += "。" + sd;
  const d = parseFloat(String(s.duration || "").replace(/[^\d.]/g, "")) || 3;
  return [
    refs, "",
    style, "",
    "【单镜 · " + d + "s】" + (s.shot_number ? "镜" + s.shot_number + " · " : "") + body,
    "",
    xjAvoidInstructions()
  ].join("\n");
}
// MiniMax-H3 六段式：单镜成片（summary 注明 single shot，不出现多镜逐镜结构）
function buildShotVideoPromptH3(s){
  const {names, scenes, props} = _collectShotRefs(s);
  const subjLabels = [];
  let idx = 0;
  names.forEach(n => { idx++; subjLabels.push({role:"character", name:n, label:"<Subject " + idx + ">", pic: idx}); });
  scenes.forEach(nm => { idx++; subjLabels.push({role:"scene", name:nm, label:"<Subject " + idx + ">", pic: idx}); });   // ★ 2026-08-31 组内全部场景
  props.forEach(nm => { idx++; subjLabels.push({role:"prop", name:nm, label:"<Subject " + idx + ">", pic: idx}); });
  const defs = subjLabels.map(x => {
    if(x.role === "character") return x.label + " is the character " + x.name + " referenced from the four-view character sheet <Picture " + x.pic + ">, with fixed appearance, costume, and hairstyle to be preserved exactly.";
    if(x.role === "scene") return x.label + " is the scene " + x.name + " referenced from <Picture " + x.pic + ">.";
    return x.label + " is the prop " + x.name + " referenced from <Picture " + x.pic + ">.";
  });
  const subjList = subjLabels.map(x => x.label).join(", ");
  const summary = "[single-shot video generation] The target video is ONE continuous shot showing " + subjList + " in a cinematic modern-drama scene. Character identity, costume, and appearance are locked to the referenced four-view sheets. Single shot only — no shot cuts, no montage.";
  const retain = subjLabels.map(x => x.label + ": fully_preserved - the referenced appearance, costume, and spatial relationship are retained.");
  let body = String(s.visual || "").trim();
  const a = String(s.action || "").trim();
  const mv = String(s.movement || "").trim();
  const dia = String(s.dialogue || "").trim();
  const sd = String(s.sound || "").trim();
  if(a) body += (body ? " " : "") + a;
  if(mv && mv !== "固定") body += ". Camera: " + mv + ".";
  if(dia) body += " " + dia;
  if(sd) body += " Sound: " + sd + ".";
  const detailed = xjStyleInstructions() + "\n" +
    "[Shot 1] " + (s.shot_number ? "Shot " + s.shot_number + ". " : "") + body;
  const soundscape = "Ambient interior room tone and soft diegetic sound continue throughout the scene; specific effects appear with the shot above.";
  const music = "N/A";
  return [
    "subject_definitions:",
    ...defs,
    "",
    "summary:",
    summary,
    "",
    "retention_analysis:",
    ...retain,
    "",
    "detailed_description:",
    detailed,
    "",
    "overall_soundscape:",
    soundscape,
    "",
    "non_diegetic_music:",
    music
  ].join("\n");
}
// H3 时间轴辅助：累计前 i 镜时长 → MM:SS.mmm
function cumDur(shots, i){
  let t = 0;
  for(let k=0;k<i;k++){ t += parseFloat(String(shots[k].duration || "").replace(/[^\d.]/g,"")) || 3; }
  return t;
}
function fmtH3Time(sec){
  const m = Math.floor(sec/60), s = sec - m*60;
  return String(m).padStart(2,"0") + ":" + s.toFixed(3).padStart(6,"0");
}
async function storyVideoAssemble(){} // 保留空函数避免报错（★ 2026-08-23 已自动装填，本按钮隐藏）
function storyVideoSave(epN, gno){
  const ep = (P.xiajing?.episodes||[]).find(e => e.number === epN);
  const sb = (ep?.storyboards || []).find(s => s.idx === gno);
  if(!sb || !sb.video_prompts){ toast("⚠️ 无提示词可保存"); return; }
  // ★ 2026-08-24 改版：video_prompts 为 {seedance,h3} 对象，整对象保存（后端兼容旧数组）
  const vpObj = xjVPArr(sb.video_prompts);
  fetch("/storyboard-prompts", {method:"POST", headers:{"Content-Type":"application/json"},
    body: JSON.stringify({ep: epN, idx: gno, prompts: vpObj, segments: sb.video_segments || []})})
    .then(r => r.json()).then(j => {
      if(j.ok) toast("✅ 已保存 " + ((vpObj.seedance||[]).length + (vpObj.h3||[]).length) + " 条提示词（双模型）");
      else toast("❌ " + (j.error || "保存失败"));
    }).catch(() => toast("❌ 保存请求失败"));
}
function copyById(id){
  const ta = document.getElementById(id);
  if(!ta || !ta.value){ toast("⚠️ 内容为空"); return; }
  const done = () => toast("✅ 已复制");
  if(navigator.clipboard && navigator.clipboard.writeText){
    navigator.clipboard.writeText(ta.value).then(done).catch(() => { selectCopy(ta); done(); });
  } else { selectCopy(ta); done(); }
  function selectCopy(el){ el.select(); try{ document.execCommand("copy"); }catch(e){} }
}
// ★ 2026-08-22 单组故事板生成：生成提示词 → 入队（name=story-{ep}-{gi}，走多张契约）
async function storyGenGroup(epN, gi, idxs){
  if(!IS_SERVER){ toast("AI 生成需要服务模式：请双击「启动项目台.bat」"); return; }
  const ep = (P.xiajing?.episodes||[]).find(e=>e.number===epN) || (P.xiajing?.episodes||[])[0];
  const bp = buildStoryPrompt(ep, idxs);
  if(!bp){ toast("该组不足 6 镜，无法生成故事板"); return; }
  let model="", channelId="", size="1536x768";
  try{
    const cfg = await fetch("/gen-config").then(r=>r.json());
    const ch = (cfg.channels||[]).find(c=>c.configured);
    if(!ch){ toast("❌ 未配置可用生图渠道，请先到 ⚙ 设置完善"); return; }
    channelId = ch.id;
    const m0 = (ch.models||[])[0] || "";
    model = (typeof m0 === "string") ? m0 : (m0.name || "");
    if(!model){ toast("❌ 渠道无可用模型"); return; }
    const ds = cfg.default_sizes || {};
    size = ds.storyboard_frame || ds.storyboard || "1536x768";
  }catch(e){ toast("❌ 读取渠道配置失败"); return; }
  const ok = await batchEnqueue("storyboard", "story-"+epN+"-"+gi, bp.prompt, model, size, channelId, undefined, epN);
  if(ok) toast(`⏳ 故事板 ${gi} 已入队生成（${idxs.length} beat · 9 格）…`);
  else toast("❌ 入队失败，请稍后重试");
}
function storyToggle(i){
  const ep=xjEpObj();
  xjStorySel[ep.number]=xjStorySel[ep.number]||{};
  xjStorySel[ep.number][i]=!xjStorySel[ep.number][i];
  rerenderCurrent();
}
function storyReset(){
  const ep=xjEpObj();
  if(!confirm("清除当前集已生成的故事板图，可重新批量生成？")) return;
  if(IS_SERVER){
    fetch("/story-reset", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({ep:ep.number})})
      .then(r=>r.json()).then(j=>{ if(j.ok){ ep.storyboard_image=""; ep.storyboard_ready=false; rerenderCurrent(); toast("✅ 已重置故事板图"); } else toast("❌ "+ (j.error||"重置失败")); })
      .catch(()=>toast("❌ 重置失败"));
  } else {
    ep.storyboard_image=""; ep.storyboard_ready=false; rerenderCurrent();
  }
}
// 构建故事板提示词（storyGen 与批量生图共用）：★ 2026-08-22 支持 forceIdxs（自动分组 9 镜/张时按组传入），
// 不传时取勾选（旧交互兼容）→ {prompt, idxs, grid, cells}；不满足返回 null
function buildStoryPrompt(ep, forceIdxs){
  const shots=xjShots(ep);
  const sel=xjStorySel[ep.number]||{};
  const idxs = forceIdxs || Object.keys(sel).filter(k=>sel[k]).map(Number).sort((a,b)=>a-b);
  if(idxs.length<1||idxs.length>9) return null;
  const cells = idxs.length<=6 ? 6 : 9;   // 版式格数：优先 9 格，其次 6 格
  const grid  = cells===9 ? "3×3" : "3×2";
  const first=shots[idxs[0]];
  const title=(first.visual||"第"+ep.number+"集").slice(0,12);
  const mood=idxs.map(i=>(shots[i]||{}).visual||"").join("").slice(0,30)+"…";
  const lines=idxs.map((i,pi)=>{
    const s=shots[i];
    const st=s.shot_type||"中景";
    const stEn={远景:"wide shot",全景:"full shot",中景:"medium shot",近景:"medium close-up",特写:"close-up"}[st]||"medium shot";
    return `P${String(pi+1).padStart(2,"0")} / 镜${s.shot_number} / ${s.action||"动作段落名"}：镜头设计 —— 景别 ${st} ${stEn}、机位 平视 eye level、角度 正面 front view、焦段 标准 standard lens、景深 浅景深 shallow depth of field、运镜 固定 static shot；画面内容 —— ${s.visual||""}`;
  }).join("\n");
  const p = `单张故事板分镜稿，题材为日常剧情 / 叙事向，节奏平稳、注重情绪与场景交代。

【主体设定】现代极简制片分镜板，呈现一段日常叙事剧情：${mood}。通过镜头角度、人物姿态与表情倾向、人物空间关系、运动方向与固定场景，交代剧情推进与情绪变化。

【页眉规范】美术化制片分镜页眉，搭配贴合本场戏的字体与细分割线，层级清晰，仅在画格外围做克制简约装饰，画格内部不加任何装饰。页眉必须完整包含以下两句带引号文字：
"${title}"
"${mood}"

【分镜版面结构】按布局规则自动排版，版式 ${cells} 格（${grid}，一格对应一个分镜 beat，共 ${idxs.length} 个 beat），按 P 序号顺序阅读。每格小标题严格遵循：P 序号 / 镜头标签 / 动作段落名。一格只呈现一个定格瞬间；多余格子保持全空白。
网格布局：${grid}（每格严格 16:9，不可违背）

【画面美术风格】（锁定，不可更改）平面简约线条简笔画风格，单色 2D 铅笔 / 墨水草稿、白底、大面积留白。松散开放式轮廓 + 少量辅助结构线 + 简易透视参照物；人物无五官细节，仅保留体态。禁止：填色、灰调晕染、排线、阴影、环境闭塞光影、色彩、3D 建模体积、纹理、精细插画。

【参考素材约束】角色参考（可按需增加，依次顺延编号）imageA/imageB/imageC：仅用于参考角色剪影、身高体量、标志性外形特征与基础站姿，不用于参考细节与完整设计；所有角色剪影保持独立清晰，不可融合、重叠混淆。场景 / 道具参考（无对应内容可删除）：仅参考空间结构、核心地标位置、外轮廓与比例，不参考细节纹理与光影。

【镜头连贯性要求】统一人物身份与外形轮廓、统一场景元素与空间逻辑、统一运动方向，全程保持一致。每格定格单一瞬间，禁止 "之前 / 之后 / 然后 / 接下来" 等时序叙事描述。

【逐格分镜写法】（一格对应一段）
${lines}
${idxs.length<cells?`（其余画格标注"留全白"）`:''}

【关键约束 Hard Constraints】风格铁律：严格锁定平面简约线条简笔画风格，单色 2D 铅笔 / 墨水草稿、白底、大面积留白；禁止填色、灰调晕染、排线、阴影、环境闭塞光影、色彩、3D 建模体积、纹理、精细插画；无字幕、无水印、无 logo，全程风格统一不偏离。布局铁律：严格按照版式 ${cells} 格（${grid}）执行，一格对应一个分镜 beat，按 P 序号正序排列画格，多余格子留全白；不可增减画格数量、不可打乱阅读顺序、不可更改网格结构。画幅铁律：每一格分镜（P01 至 P${String(cells).padStart(2,"0")}）均需严格保持 16:9 画幅比例，不可变形、不可裁切、不可更改比例，全程统一执行。文字约束：画面仅允许出现：页眉两句引文 + 每格分镜小标题。禁止其它一切文字、箭头、标注框、编号、内嵌小图、画面内注释。其他限制：禁止 logo、水印、叠加图层、额外画格、完整插画、密集细节、画格内上色、重复人影 / 虚影 / 分身。`;
  return {prompt:p, idxs, grid, cells};
}
function storyGen(){
  const ep=xjEpObj();
  const bp=buildStoryPrompt(ep);
  if(!bp){ toast("需勾选 1~9 镜（单张故事板 6/9 格，每批 ≤9）"); return; }
  const {prompt:p, idxs, grid, cells}=bp;
  const out=$("story-result");
  out.innerHTML = `<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px"><b style="font-size:13px">📋 故事板提示词（${cells} 格 · ${grid} · ${idxs.length} beat）</b><button class="btn-secondary" style="font-size:12px;padding:3px 10px" onclick="copyText(document.getElementById('story-out').value)">📋 复制</button></div>
  <textarea id="story-out" readonly style="width:100%;box-sizing:border-box;min-height:300px;border:1px solid var(--line);border-radius:8px;padding:10px;font-size:12px;line-height:1.6;background:var(--bg)">${esc(p)}</textarea>`;
}

// ===== 分镜脚本编辑机制 =====
function shotRowGo(epNum,idx){ xjCurTab="make"; xjCurShot=idx; rerenderCurrent(); }
function shotNav(d){ xjCurShot=Math.max(0,Math.min(xjShots(xjEpObj()).length-1, xjCurShot+d)); xjMakeEditing=false; rerenderCurrent(); }
// ★ 2026-08-22 制作页 11 字段编辑（编辑功能从分镜脚本页迁移至此）
const XJ_MAKE_FIELDS = [
  ["duration","时长（秒）"], ["scene_tag","所属场景"], ["characters","出场人物"], ["shot_type","景别"],
  ["camera","摄影机参数"], ["composition","构图方式"], ["visual","画面内容"], ["action","人物动作与表演"],
  ["movement","运镜方式"], ["dialogue","台词"], ["sound","声音"], ["narrative","镜头叙事作用"],
];
function xjMakeEditStart(){ xjMakeEditing=true; rerenderCurrent(); }
function xjMakeCancel(){ xjMakeEditing=false; rerenderCurrent(); }
function xjMakeSave(){
  const shots=xjShots(xjEpObj()); const s=shots[xjCurShot]; if(!s) return;
  const payload={};
  XJ_MAKE_FIELDS.forEach(([k])=>{ const el=document.getElementById("xjm-"+k); if(el) payload[k]=el.value; });
  if(!s.is_edited){ s.original_shot=JSON.parse(JSON.stringify(s)); }
  Object.assign(s,payload,{is_edited:true});
  xjSaveToBackend(xjEpObj().number,"save",xjCurShot,payload);
  xjMakeEditing=false;
  rerenderCurrent();
  toast("✅ 已保存（副本，原始保留）");
}
function shotReset(epNum,idx){
  const shots=xjShots(xjEpObj()); const s=shots[idx]; if(!s||!s.original_shot) return;
  const orig=s.original_shot;
  Object.keys(orig).forEach(k=>{ s[k]=orig[k]; });
  s.is_edited=false; s.original_shot=null;
  xjSaveToBackend(epNum,"reset",idx,s);
  rerenderCurrent();
  toast("↺ 已重置回原始分镜");
}
// ★ 2026-08-22 整集重置分镜：恢复 build 定稿原始版（清除编辑/添加/删除/拖动）
function shotResetAll(epNum){
  if(!confirm("确定将本集分镜重置为定稿原始版？\n所有编辑 / 添加 / 删除 / 拖动重排将全部还原，且不可恢复！")) return;
  if(!IS_SERVER){ toast("需服务模式（双击启动项目台.bat）"); return; }
  fetch("/shots/reset_all",{method:"POST",headers:{"Content-Type":"application/json"},
    body:JSON.stringify({ep:epNum})})
    .then(r=>r.json()).then(res=>{
      if(!res.ok){ toast("⚠️ "+(res.error||"重置失败")); return; }
      xjCurShot=0;
      reloadDataJs();
      toast("↺ 本集分镜已重置为定稿原始版");
    }).catch(()=>toast("⚠️ 重置失败（服务异常）"));
}
function shotDelete(epNum,idx){
  const ep=xjEpObj(); const shots=xjShots(ep);
  const s=shots[idx]; if(!s) return;
  if(!confirm(`确定删除镜 ${s.shot_number}？（硬删，不可恢复）`)) return;
  shots.splice(idx,1); renumberShots(shots);
  if(xjCurShot>=shots.length) xjCurShot=Math.max(0,shots.length-1);
  xjSaveToBackend(epNum,"delete",idx,null);
  rerenderCurrent();
  toast("🗑 已删除");
}
function shotAdd(){
  const ep=xjEpObj(); const shots=xjShots(ep);
  shots.push({shot_number:String(shots.length+1),duration:"",shot_type:"",visual:"",dialogue:"",composition:"",scene_tag:"",characters:"",camera:"",action:"",movement:"",sound:"",narrative:"",outline_visual:"",outline_dialogue_sound:"",outline_function:"",firstframe_prompt:"",firstframe_image:"",tailframe_prompt:"",tailframe_image:"",video_prompt:"",video:"",is_edited:false,original_shot:null});
  xjSaveToBackend(ep.number,"add",shots.length-1,shots[shots.length-1]);
  rerenderCurrent();
  toast("＋ 已添加分镜");
}
function renumberShots(shots){ shots.forEach((s,i)=>{ s.shot_number=String(i+1).padStart(2,"0"); }); }
function shotDragStart(ev,i){ xjDragFrom=i; ev.dataTransfer.effectAllowed="move"; }
function shotDragOver(ev){
  ev.preventDefault();
  ev.dataTransfer.dropEffect="move";
  // ★ 2026-08-22 拖动中：目标行高亮（表明将插入该行后面）
  document.querySelectorAll("tr.xj-drag-target").forEach(r=>r.classList.remove("xj-drag-target"));
  const tr = ev.currentTarget.closest("tr");
  if(tr) tr.classList.add("xj-drag-target");
}
function shotDrop(ev,toIdx){
  ev.preventDefault();
  document.querySelectorAll("tr.xj-drag-target").forEach(r=>r.classList.remove("xj-drag-target"));
  if(xjDragFrom==null||xjDragFrom===toIdx){ xjDragFrom=null; return; }
  const shots=xjShots(xjEpObj());
  const fromNum=shots[xjDragFrom].shot_number, toNum=shots[toIdx].shot_number;
  // ★ 2026-08-22 用户拍板：松开后弹窗确认「插入目标行后」（插入式重排，非互换）
  if(!confirm("是否将镜 "+fromNum+" 插入镜 "+toNum+" 后？")){ xjDragFrom=null; rerenderCurrent(); return; }
  const [item]=shots.splice(xjDragFrom,1);
  let insAt=toIdx;
  if(xjDragFrom<toIdx) insAt--;   // 抽出位置在目标前 → 目标下标左移一位
  shots.splice(insAt+1,0,item);  // 插入到目标行之后
  // ★ 2026-08-22 关键修复：不能用 shot_number 传顺序（renumber 后恒为 01,02,03… 位置序，后端按序重建=原顺序，拖动无效）。
  //   改用稳定 uid（镜号是位置标识，uid 不随重排/重编号变化）。
  const ordered = shots.map(s=>s.uid || s.shot_number);
  renumberShots(shots);
  xjCurShot=insAt+1;
  xjSaveToBackend(xjEpObj().number,"reorder",null,{ordered});
  xjDragFrom=null;
  rerenderCurrent();
  toast("⇅ 已插入：镜 "+fromNum+" → 镜 "+toNum+" 后");
}
function shotDragEnd(){ xjDragFrom=null; document.querySelectorAll("tr.xj-drag-target").forEach(r=>r.classList.remove("xj-drag-target")); }

// ===== 分镜表格：列宽/行高拖拽调整（★ 2026-08-22 用户需求）=====
const XJ_COLS = [
  {t:"镜号", w:52},{t:"秒", w:56},{t:"景别", w:86},{t:"运镜", w:110},
  {t:"画面要点", w:0},{t:"台词/声音", w:0},{t:"叙事功能", w:120},{t:"操作", w:170}
];
let xjColW = {};
try{ xjColW = JSON.parse(localStorage.getItem("xj-colw")||"{}")||{}; }catch(e){ xjColW={}; }
let xjResize = null;
document.addEventListener("mousedown", function(e){
  const cr = e.target.closest ? e.target.closest(".col-resizer") : null;
  const rr = e.target.closest ? e.target.closest(".row-resizer") : null;
  if(!cr && !rr) return;
  e.preventDefault(); e.stopPropagation();
  if(cr){
    const th = cr.closest("th");
    xjResize = {type:"col", th, startX:e.clientX, w:th.getBoundingClientRect().width, col:th.cellIndex};
  }else{
    const tr = rr.closest("tr");
    xjResize = {type:"row", tr, startY:e.clientY, h:tr.getBoundingClientRect().height};
  }
  (cr||rr).classList.add("active");
});
document.addEventListener("mousemove", function(e){
  if(!xjResize) return;
  if(xjResize.type === "col"){
    const w = Math.max(48, xjResize.w + (e.clientX - xjResize.startX));
    xjResize.th.style.width = w + "px";
    xjColW[xjResize.col] = w;
  }else{
    const h = Math.max(34, xjResize.h + (e.clientY - xjResize.startY));
    xjResize.tr.style.height = h + "px";
    xjResize.tr.querySelectorAll(".xj-cell").forEach(d=>{ d.style.maxHeight = (h - 12) + "px"; });
  }
});
document.addEventListener("mouseup", function(){
  if(xjResize){
    if(xjResize.type === "col"){
      try{ localStorage.setItem("xj-colw", JSON.stringify(xjColW)); }catch(err){}
    }
    xjResize = null;
    document.querySelectorAll(".col-resizer.active,.row-resizer.active").forEach(el=>el.classList.remove("active"));
  }
});

// ===== 后端持久化（服务模式）=====
function xjSaveToBackend(epNum,action,idx,payload){
  if(!IS_SERVER) return; // 静态模式仅内存态
  fetch("/shots/"+action,{method:"POST",headers:{"Content-Type":"application/json"},
    body:JSON.stringify({ep:epNum,idx,payload})})
    .then(r=>r.json()).then(res=>{ if(!res.ok && res.error) toast("⚠️ "+res.error); }).catch(()=>{});
}
function xjSavePrompt(key,shotName){
  const el=document.getElementById("xj-"+key+"-p"); if(!el) return;
  if(!IS_SERVER){ toast("需服务模式"); return; }
  // ★ 2026-08-24 单镜视频双模型：保存时带上当前模型分支，后端写回 video_prompts[model]
  const _m = (key==="video") ? ((typeof genVideoModel !== "undefined" && genVideoModel === "h3") ? "h3" : "seedance") : "";
  const body = {category:key==="video"?"video":key,name:shotName,prompt:el.value,ep:xjCurEp};
  if(_m) body.model = _m;
  fetch("/save-prompt",{method:"POST",headers:{"Content-Type":"application/json"},
    body:JSON.stringify(body)})
    .then(r=>r.json()).then(res=>{ if(res.ok) toast("✅ 提示词已保存"); else toast("❌ "+(res.error||"保存失败")); }).catch(e=>toast("❌ "+e.message));
}
function copyText(t){ const ta=document.createElement("textarea"); ta.value=t; document.body.appendChild(ta); ta.select(); try{document.execCommand("copy"); toast("📋 已复制");}catch(e){toast("复制失败，请手动选择复制");} document.body.removeChild(ta); }

// ===== 集数网格（保留）=====
function renderXiajingGrid(){
  const eps = P.xiajing?.episodes || [];
  const totalShots = eps.reduce((s,e)=>s+(e.shots?.length||0),0);
  return `
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:14px;flex-wrap:wrap">
      <span class="pill">🔵 总集数 <b>${eps.length}</b></span>
      <span class="pill" style="color:#185fa5">🎬 总分镜 <b>${totalShots}</b></span>
      <span class="pill" style="color:#a16207">📍 总身份 <b>${eps.reduce((s,e)=>s+(P.xiatang?.characters||[]).reduce((sc,c)=>sc+(c.identities?.length||0),0),0)}</b></span>
      <span class="pill" style="color:#993556">🧸 总场景 <b>${P.xiatang?.scenes?.length||0}</b></span>
      <span class="pill">🧩 总道具 <b>${P.xiatang?.props?.length||0}</b></span>
      <div style="flex:1"></div>
      <button class="pill primary" onclick="toast('分集规划由虾镜/虾导流程完成')">▶ 规划剧集</button>
    </div>
    <div class="ep-grid">
      ${eps.map(e => {
        const done = (e.shots||[]).filter(s=>s.firstframe_image||s.video).length;
        return `
        <div class="ep-card ${e.number===xjCurEp?'active':''}" data-ep="${e.number}">
          <div class="head"><div class="num">第${e.number}集</div><div class="title">${esc(e.title)}</div></div>
          <div class="desc">第 ${e.number} 集 ${esc(e.title)}：${esc((e.shots?.[0]?.visual||"").slice(0,40))}</div>
          <div class="ep-stats">
            <div class="s"><span class="badge ic-c">🎬 ${e.shots?.length||0} 分镜</span></div>
            <div class="s"><span class="badge ic-r">✅ ${done} 已制作</span></div>
          </div>
          <div class="ep-progress"><div class="p" style="width:${e.shots?.length?Math.round(done/(e.shots.length)*100):0}%"></div></div>
          <div style="font-size:12px;color:var(--mut);text-align:right">${done}/${e.shots?.length||0} 镜已制作</div>
          <button class="view-btn" data-ep-btn="${e.number}">查看详情 →</button>
        </div>`;
      }).join("")}
    </div>`;
}

window.backToEpGrid = function(){ xjCurEp=null; xjCurShot=0; xjCurTab="shots"; renderSection("xiajing"); };
