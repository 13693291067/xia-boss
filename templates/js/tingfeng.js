// ===== 听风电影（电影化分镜）=====
// ★ 数据隔离铁律：听风电影与虾镜完全独立——数据(tingfeng.json vs shots.json)、
//   前端模块(tingfeng.js vs xiajing.js)、资产目录(assets/tingfeng/ vs assets/epNNN/)、
//   后端 category(tingfeng vs storyboard) 全部独立，禁止任何数据污染。
// 数据：P.tingfeng = { episodes:[{number, title, segments:[
//   {id, duration, script_range, core_action, continuity_header, exit_hook, scene, shots:[{n,ts,frame,camera,scene,visual,dialogue,sound}], video_prompt}
// ], storyboards:[{idx,image,ready,segs_idx}]}] }
let tfCurEp = null;      // 当前选中集（null=集网格）
let tfCurTab = "shots";  // shots(分镜脚本) | make(制作)
let tfGridCap = 6;       // 故事板格数：9 | 6 | 4（默认 6）

// 景别完整名称映射
const TF_FRAME_MAP = {"ECU":"极近景","CU":"近景","MCU":"中近景","MS":"中景","WS":"全景","ELS":"大远景"};
function tfFrameName(f){
  if(!f) return "";
  return String(f).split("→").map(x => { x = x.trim(); return TF_FRAME_MAP[x] || x; }).join("→");
}

function renderTingFeng(){
  const eps = (P.tingfeng?.episodes) || [];
  if(!eps.length){
    return `
    <div class="card" style="padding:40px;text-align:center">
      <div style="font-size:40px;margin-bottom:12px">🎬</div>
      <h2 style="margin:0 0 8px">听风电影 · 电影化分镜</h2>
      <p style="color:var(--mut);font-size:13px;margin:0 0 20px">尚未生成听风版分镜。</p>
      <p style="color:var(--mut);font-size:12px;max-width:520px;margin:0 auto;line-height:1.8">
        在对话中让 AI 用「听风电影」skill 生成：<br>
        ① 听风分段表（戏剧弧切段 ≤15s）→ ② 每段五层分镜（含场景字段）→ ③ 每段视频提示词（保真全文）<br>
        生成后写入 <code>outputs/tingfeng/{集}/tingfeng.json</code>，重跑 build 后此处显示。
      </p>
    </div>`;
  }
  if(tfCurEp == null || !eps.find(e => e.number === tfCurEp)) return renderTingFengGrid(eps);
  return renderTingFengEp(eps.find(e => e.number === tfCurEp));
}

// ===== 集网格（虾镜式分集效果）=====
function renderTingFengGrid(eps){
  const totalSegs = eps.reduce((s,e)=>s+(e.segments?.length||0),0);
  const totalShots = eps.reduce((s,e)=>s+(e.segments||[]).reduce((a,x)=>a+(x.shots?.length||0),0),0);
  return `
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:14px;flex-wrap:wrap">
      <span class="pill">🎬 总集数 <b>${eps.length}</b></span>
      <span class="pill" style="color:#7c3aed">🎞 总分段 <b>${totalSegs}</b></span>
      <span class="pill" style="color:#a16207">🎥 总镜头 <b>${totalShots}</b></span>
      <div style="flex:1"></div>
      <span style="font-size:12px;color:var(--mut)">听风电影化分镜 · 与虾镜数据完全独立</span>
    </div>
    <div class="ep-grid">
      ${eps.map(e => {
        const segs = e.segments || [];
  const totalShots = segs.reduce((a,s)=>a+Math.max(1,(s.shots||[]).length),0);
        const done = (e.storyboards||[]).filter(sb => sb.ready).length;
        return `
        <div class="ep-card" onclick="tfOpenEp(${e.number})" style="cursor:pointer">
          <div class="head"><div class="num">第${e.number}集</div><div class="title">${esc(e.title||"")}</div></div>
          <div class="desc">听风分段 ${segs.length} 段 · 总时长 ${segs.reduce((s,x)=>s+(parseInt(x.duration)||0),0)}s</div>
          <div class="ep-stats">
            <div class="s"><span class="badge ic-c">🎞 ${segs.length} 分段</span></div>
            <div class="s"><span class="badge ic-r">🎬 ${segs.reduce((s,x)=>s+(x.shots?.length||0),0)} 镜头</span></div>
          </div>
          <div class="ep-progress"><div class="p" style="width:${totalShots?Math.round(done/Math.ceil(totalShots/tfGridCap)*100):0}%"></div></div>
          <div style="font-size:12px;color:var(--mut);text-align:right">${done}/${Math.ceil(totalShots/tfGridCap)} 板故事板</div>
          <button class="view-btn" style="cursor:pointer">查看详情 →</button>
        </div>`;
      }).join("")}
    </div>`;
}
function tfOpenEp(n){
  tfCurEp = n;
  const c = $("content"); c.innerHTML = renderTingFeng(); bindTingFeng();
}

// ===== 集内（双 Tab：分镜脚本 / 制作）=====
function renderTingFengEp(ep){
  const tabs = [
    {k:"shots", label:"📋 分镜脚本"},
    {k:"make", label:"🎬 制作"},
  ];
  const body = {shots:tfRenderShots(ep), make:tfRenderMake(ep)}[tfCurTab] || "";
  return `
  <div style="display:flex;align-items:center;gap:10px;margin-bottom:14px;flex-wrap:wrap">
    <span class="back" onclick="tfBackGrid()" style="cursor:pointer">← 返回剧集列表</span>
    <span class="pill">第 ${ep.number} 集 <b>${esc(ep.title||"")}</b></span>
  </div>
  <div class="tabs" id="tingfeng-tabs">
    ${tabs.map(t => `<div class="t ${t.k===tfCurTab?'active':''}" data-tf-tab="${t.k}" style="cursor:pointer">${t.label}</div>`).join("")}
  </div>
  <div id="tingfeng-body" style="margin-top:12px">${body}</div>`;
}
function tfBackGrid(){
  tfCurEp = null;
  const c = $("content"); c.innerHTML = renderTingFeng(); bindTingFeng();
}

// ===== Tab1 分镜脚本（扁平表格：镜号/时间段/景别/运镜/画面/音效，无表格线）=====
function tfRenderShots(ep){
  const segs = ep.segments || [];
  // 扁平化：所有段的所有镜 + 段间分隔标记（★ 2026-09-01 用户定稿 v2：6 列带横竖表格线；列宽优化——画面列压缩、音效列加宽）
  const rows = [];
  segs.forEach((seg, si) => {
    const segNo = String(seg.id || ("S" + String(si + 1).padStart(2, "0")));
    rows.push({type:"sep", seg, segNo});
    (seg.shots || []).forEach(s => rows.push({type:"shot", seg, segNo, shot:s, segIdx:si}));
  });
  const totalShots = rows.filter(r => r.type==="shot").length;
  const L = "border-right:1px solid #e8edf3";  // 竖线（每列右边线）
  return `
  <div style="margin-bottom:8px;font-size:12px;color:var(--mut)">听风分镜脚本 · 共 ${segs.length} 段 / ${totalShots} 镜 · 一行一镜</div>
  <div style="max-height:75vh;overflow:auto;border:1px solid #d7dee8;border-radius:10px;background:#fff">
    <div style="display:flex;align-items:stretch;font-size:11.5px;color:var(--mut);font-weight:600;background:#f4f6fa;position:sticky;top:0;z-index:1;border-bottom:1px solid #d7dee8">
      <span style="width:58px;flex-shrink:0;padding:8px 8px;${L}">镜号</span>
      <span style="width:96px;flex-shrink:0;padding:8px 8px;${L}">时间段</span>
      <span style="width:112px;flex-shrink:0;padding:8px 8px;${L}">景别</span>
      <span style="width:120px;flex-shrink:0;padding:8px 8px;${L}">运镜</span>
      <span style="flex:1 1 46%;min-width:260px;padding:8px 10px;${L}">画面</span>
      <span style="flex:0 0 30%;min-width:230px;padding:8px 10px">音效</span>
    </div>
    ${rows.map(r => r.type === "sep"
      ? `<div style="background:linear-gradient(135deg,#f5f3ff,#ede9fe);padding:6px 10px;font-size:12px;color:#5b21b6;font-weight:600;border-top:1px solid #d7dee8;border-bottom:1px solid #d7dee8">${esc(r.segNo)} · ${esc(r.seg.duration||"")}s${r.seg.route?` · <span style="color:#0f766e">${esc(r.seg.route)}</span>`:` · <span style="color:#b45309">未标路由</span>`} · ${esc(r.seg.core_action||"")} <span style="color:var(--mut);font-weight:400;font-size:11px">· ${esc(r.seg.scene||"")}</span></div>`
      : `<div style="display:flex;align-items:stretch;font-size:12px;border-bottom:1px solid #e8edf3">
          <span style="width:58px;flex-shrink:0;padding:8px;font-weight:600;color:#5b21b6;${L}">${esc(r.shot.n||"")}</span>
          <span style="width:96px;flex-shrink:0;padding:8px;color:var(--mut);${L}">${esc(r.shot.ts||"")}</span>
          <span style="width:112px;flex-shrink:0;padding:8px;${L}">${esc(tfFrameName(r.shot.frame))}${r.shot.frame&&r.shot.frame!==tfFrameName(r.shot.frame)?` <span style="color:var(--mut);font-size:10.5px">(${esc(r.shot.frame)})</span>`:""}</span>
          <span style="width:120px;flex-shrink:0;padding:8px;color:#334155;${L}">${esc(r.shot.camera||"")}</span>
          <span style="flex:1 1 46%;min-width:260px;padding:8px 10px;color:#475569;${L}">${esc(r.shot.visual||"")}</span>
          <span style="flex:0 0 30%;min-width:230px;padding:8px 10px;color:#0f766e">${esc([r.shot.dialogue ? "「"+r.shot.dialogue+"」" : "", r.shot.sound].filter(Boolean).join(" ") || "—")}</span>
        </div>`).join("")}
  </div>`;
}// ===== Tab2 制作：故事板（★ 2026-09-01 用户定稿：格=分镜头，按镜头拼 4/6/9 格；S 段整体性铁律——一段的所有镜头必须同板，禁止把一段拆到两块板）=====
// 分组：按镜头顺序累积 S 段，切板点只落在段边界（贪心：加段超容则封板；末板不足留白）
function tfGroupBoards(ep, cap){
  const segs = ep.segments || [];
  const boards = [];
  let cur = [], curShots = 0;
  segs.forEach((seg, si) => {
    const n = Math.max(1, (seg.shots || []).length);
    if(cur.length && curShots + n > cap){
      boards.push({segIdxs: cur.slice(), shots: curShots, blank: Math.max(0, cap - curShots)});
      cur = []; curShots = 0;
    }
    cur.push(si); curShots += n;
  });
  if(cur.length) boards.push({segIdxs: cur.slice(), shots: curShots, blank: Math.max(0, cap - curShots)});
  return boards;
}
function tfGridLabel(cells){
  return cells <= 4 ? "2×2" : (cells <= 6 ? "3×2" : "3×3");
}
// ★ 2026-09-04 空间拓扑图（每场一张；黑白简笔规范单源 = skill references/shared-spatial-blocking.md §十；独立 tf_space_map 链路，与虾镜完全隔离）
// 数据契约：ep.space_maps = [{name, prompt, image, ready}]（每场一项，name 带场标识如"空间拓扑图·场1"；AI 在 Stage 1 产出后写入 tingfeng.json）；
//          旧单数字段 space_map_prompt/space_map_image 兼容归一化为单项集合（旧项目数据不动）
function tfSpaceMaps(ep){
  let arr = Array.isArray(ep.space_maps) ? ep.space_maps.filter(Boolean) : [];
  if(!arr.length && ((ep.space_map_prompt && String(ep.space_map_prompt).trim()) || (ep.space_map_image && String(ep.space_map_image).trim()))){
    arr = [{name:"空间拓扑图", prompt: ep.space_map_prompt||"", image: ep.space_map_image||"", ready: !!ep.space_map_image}];
  }
  return arr;
}
// 段 → 所属场拓扑图：优先 seg.space_map（场名/场标识，AI 分镜产出时写入），集合内 name 包含匹配；无则第一张（旧数据=归一化单项）
function tfSegSpaceMap(ep, seg){
  const arr = tfSpaceMaps(ep);
  if(!arr.length) return null;
  const key = String((seg && seg.space_map) || "").trim();
  if(key){ const hit = arr.find(m => String(m.name||"").indexOf(key) >= 0); if(hit) return hit; }
  return arr[0];
}

function tfSpaceMapCardHTML(ep){
  const maps = tfSpaceMaps(ep);
  const cards = maps.map((m, i) => {
    const ready = !!(m.image && String(m.image).trim());
    const img = ready ? esc(imgSrc(m.image)) : "";
    const label = esc(m.name || ("空间拓扑图·场" + (i+1)));
    return `
    <div style="display:flex;align-items:center;gap:12px;padding:10px 12px;border:1px dashed #c4b5fd;border-radius:10px;background:#faf5ff;margin-bottom:8px">
      <div style="width:150px;height:84px;border-radius:8px;overflow:hidden;background:#e2e8f0;display:flex;align-items:center;justify-content:center;flex-shrink:0;${ready?`cursor:zoom-in`:`cursor:default`}" ${ready?`onclick="openZoom('${img}','${label}')" title="点击放大"`:`title="该场拓扑图待生成（点右侧 ✨ 生图）"`}>
        ${ready?`<img src="${img}" style="width:100%;height:100%;object-fit:cover" onerror="this.style.display='none'">`:`<span style="display:block;width:100%;height:100%"></span>`}
      </div>
      <div style="flex:1;min-width:0">
        <b style="font-size:13px">🗺 ${label}</b>
        <div style="font-size:11px;color:var(--mut);margin-top:2px">本场机位调度（站位/轴线/CAM/越轴预案）· 黑白简笔垫图 · 每场一张</div>
        ${(m.prompt || m.prompt_cn) ? `<details style="margin-top:4px"><summary style="cursor:pointer;font-size:11px;color:#0f766e;user-select:none">📝 拓扑图提示词${m.prompt_cn?"（双语）":""}</summary><div style="margin-top:4px">${promptBlockDual(m.prompt_cn, m.prompt)}</div></details>` : ""}
      </div>
      <div style="display:flex;gap:6px;flex-wrap:wrap;align-items:center;flex-shrink:0">
        <label class="btn primary" style="cursor:pointer">↑ 上传<input type="file" accept="image/*" style="display:none" onchange="doUpload(this,'tf_space_map','tf-space-map-${ep.number}-${i}')"></label>
        <button class="pill primary" onclick="tfSpaceMapGen(${ep.number},${i})" title="生成该场空间拓扑图（弹窗中可编辑提示词）">✨ 生图</button>
      </div>
    </div>`;
  }).join("");
  return `
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;gap:8px;flex-wrap:wrap">
      <span style="font-size:13px;font-weight:600">🗺 空间拓扑图（每场一张 · 场景切分口径=摄影机需要搬运就拆图）</span>
      <button class="pill" onclick="tfSpaceMapAdd(${ep.number})" title="为本集新增一场的拓扑图条目">＋ 新增场次</button>
    </div>
    ${cards || `<div style="padding:10px;color:var(--mut);font-size:12px;border:1px dashed #d7dee8;border-radius:8px;margin-bottom:8px">尚无场次条目——点「＋ 新增场次」建第一场拓扑图（提示词随 Stage 1 产出写入；每场一张，禁多场挤一图）</div>`}`;
}
function _tfEnsureMap(ep, idx){
  const maps = (Array.isArray(ep.space_maps) ? ep.space_maps.filter(Boolean) : []);
  while(maps.length <= idx){
    maps.push({name:"空间拓扑图·场"+(maps.length+1), prompt:"", image:"", ready:false});
  }
  ep.space_maps = maps;
  return maps[idx];
}
function tfSpaceMapAdd(epN){
  const ep = (P.tingfeng?.episodes||[]).find(e => e.number === epN);
  if(!ep){ toast("未找到该集"); return; }
  const idx = tfSpaceMaps(ep).length;
  _tfEnsureMap(ep, idx);
  tfSpaceMapGen(epN, idx);
}
function tfSpaceMapGen(epN, idx){
  if(!IS_SERVER){ toast("AI 生成需要服务模式：请双击「启动项目台.bat」"); return; }
  // ★ 2026-09-04 每场独立提示词：读 ep.space_maps[idx].prompt（AI 做 Stage 1 时按每场布局产出写入；
  //   弹窗手改后经 /save-prompt 落库）；无则回退黑白简笔通用骨架（占位符，用户手改）
  const ep = (P.tingfeng?.episodes||[]).find(e => e.number === epN);
  const i = Number(idx) || 0;
  const m = (ep && _tfEnsureMap(ep, i)) || null;
  const own = (m && m.prompt && String(m.prompt).trim()) || "";
  if(!own) toast("💡 该场专属拓扑图提示词未生成，已预填黑白简笔通用骨架——按本场布局修改后再生成");
  openGenModal("tf_space_map", "tf-space-map-" + epN + "-" + i, own || TF_SPACE_MAP_GENERIC, "", (m && m.prompt_cn) || "");
}
// 通用骨架（黑白简笔规范占位符，仅当该场 prompt 缺失时回退；规范单源 = references/shared-spatial-blocking.md §十）
const TF_SPACE_MAP_GENERIC = `16:9 横屏白底简笔示意图，手绘风格平面俯视机位调度图：以细黑线俯视平面绘制
[固定锚点带：<本场不动参照物：关墙/大帐/立柱/门洞…>（方块示意）]；
[站位：左侧圆点+长枪小图标=主角方，右侧圆点+标识=对手方（图标带可区分特征）]；
两点间一条红色虚线直线 = 180° 动作轴线；
轴线同侧布置四个小相机图标 CAM1~CAM4，细弧线示意调度弧；
[下方纵深边界：远景要素点线]。
仅黑白灰 + 一处红色轴线虚线，线条干净简洁，无写实渲染、无人物、无照片质感（blueprint sketch style），no photorealism, no text labels other than CAM1-CAM4 numbers`;

function tfRenderMake(ep){
  const segs = ep.segments || [];
  if(!segs.length) return `<div style="padding:24px;color:var(--mut);text-align:center">暂无分段</div>`;
  const boards = tfGroupBoards(ep, tfGridCap);
  const totalShots = segs.reduce((a,s)=>a+Math.max(1,(s.shots||[]).length),0);
  return `
    ${tfSpaceMapCardHTML(ep)}
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;gap:10px;flex-wrap:wrap">
      <span style="font-size:14px;font-weight:600">🖼 故事板（简约线条 · ${totalShots} 镜拼板 ${boards.length} 张）</span>
      <span style="font-size:12px;color:var(--mut)">格数：
        ${[9,6].map(g => `<button class="pill ${g===tfGridCap?'primary':''}" onclick="tfSetCap(${g})" style="cursor:pointer;margin-left:4px">${g}格</button>`).join("")}
        <span style="margin-left:8px">· 拼板以分镜头为单位，S 段整体不拆分</span>
      </span>
      <button class="pill primary" onclick="tfBatchGenStory()" title="批量生成所有未生成的故事板分组">🎨 全部批量生图</button>
      <button class="pill primary" onclick="tfBatchGenVideo()" title="将本集所有未生成的段视频全部入队">🎬 全部批量生视频</button>
    </div>
    <div style="display:flex;flex-direction:column;gap:18px;max-height:72vh;overflow:auto;padding-right:4px">
      ${boards.map((b, bi) => tfStoryRowHTML(ep, b, bi+1, tfGridCap)).join("")}
    </div>`;
}
function tfSetCap(g){
  tfGridCap = g;
  const c = $("content"); c.innerHTML = renderTingFeng(); bindTingFeng();
}

// 每板一行：故事板块 + 视频成片位块（与虾镜故事板页布局同构；board=按镜头拼好的段组）
function tfStoryRowHTML(ep, board, gno, cap){
  const idxs = board.segIdxs;
  const segs = idxs.map(i => (ep.segments||[])[i]);
  const first = segs[0]?.id || "?";
  const last = segs[segs.length-1]?.id || "?";
  let sb = (ep.storyboards || []).find(s => s.idx === gno);
  if(!sb){ sb = {idx: gno}; (ep.storyboards = ep.storyboards || []).push(sb); }
  const ready = !!sb.ready || !!sb.image;
  const grid = tfGridLabel(board.shots);
  return `
  <div style="display:flex;gap:14px;flex-shrink:0;align-items:stretch;min-width:max-content">
    <!-- 故事板块 -->
    <div style="width:260px;border:1px solid var(--line);border-radius:10px;padding:10px;background:#fff;display:flex;flex-direction:column">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px">
        <b style="font-size:13px">🖼 板${gno}<span style="color:var(--mut);font-weight:400"> · ${grid}</span></b>
        ${ready?'<span style="font-size:11px;color:#16a34a">✓</span>':'<span style="font-size:11px;color:var(--mut)">未生成</span>'}
      </div>
      <div style="font-size:11px;color:var(--mut);margin-bottom:6px">${esc(first)}~${esc(last)} · ${segs.length}段 ${board.shots}镜${board.blank?` · 留白${board.blank}格`:""}</div>
      <div style="height:130px;border-radius:8px;overflow:hidden;background:var(--tag);display:flex;align-items:center;justify-content:center;margin-bottom:8px;flex-shrink:0">
        ${ready
          ? `<img src="${esc(imgSrc(sb.image))}" style="width:100%;height:100%;object-fit:cover;cursor:zoom-in" onclick="openZoom('${esc(imgSrc(sb.image))}','听风板 ${gno}（${esc(first)}~${esc(last)}）')" onerror="this.style.display='none'">`
          : `<span style="font-size:12px;color:var(--mut)">尚未生成</span>`}
      </div>
      <div style="display:flex;gap:6px;flex-wrap:wrap;align-items:center;margin-top:auto">
        <label class="btn primary" style="cursor:pointer;font-size:12px;padding:6px 10px">↑ 上传<input type="file" accept="image/*" style="display:none" onchange="doUpload(this,'tingfeng','tingfeng-${ep.number}-${gno}')"></label>
        <button class="pill primary" style="font-size:12px;padding:5px 10px" onclick="tfStoryGen(${ep.number},${gno},${JSON.stringify(idxs)})" title="按该板 ${segs.length} 段 ${board.shots} 镜生成故事板（简约线条）">✨ 生图</button>
      </div>
    </div>
    <!-- 视频成片位块（每格=一段） -->
    ${segs.map((seg, i) => tfVideoCardHTML(ep, gno, idxs[i], seg)).join("")}
  </div>`;
}
// 视频成片位：段信息 + 播放器/占位 + 生视频/删除/复制（★ 2026-09-01 对齐虾镜故事板视频位能力）
function tfVideoCardHTML(ep, gno, segIdx, seg){
  const segNo = String(seg.id || "S" + String(segIdx+1).padStart(2,"0"));
  const result = seg.video || seg.video_result;
  const vt = seg._vt ? ("?t=" + seg._vt) : "";
  return `
  <div style="width:240px;border:1px solid #c4b5fd;border-radius:10px;padding:10px;background:#fff;display:flex;flex-direction:column">
    <div style="display:flex;align-items:center;justify-content:space-between">
      <b style="font-size:12.5px;color:#5b21b6">${esc(segNo)} · ${esc(seg.duration||"")}s${seg.route?` · <span style="color:#0f766e">${esc(seg.route)}</span>`:` · <span style="color:#b45309">未标路由</span>`}</b>
      ${result?`<button class="pill" style="font-size:10.5px;padding:2px 7px;color:#dc2626;border-color:#fecaca;background:#fef2f2;cursor:pointer" onclick="tfVideoDelete(${ep.number},${segIdx})" title="删除该段视频（文件+记录一起删）">🗑</button>`:`<span style="font-size:10.5px;color:var(--mut)">镜${esc((seg.shots||[])[0]?.n||"")}~${esc((seg.shots||[])[(seg.shots||[]).length-1]?.n||"")}</span>`}
    </div>
    <div style="height:130px;background:#1e1b4b;border-radius:8px;overflow:hidden;margin:8px 0;flex-shrink:0;display:flex;align-items:center;justify-content:center">
      ${result
        ? `<video src="${esc(result)}${vt}" controls preload="auto" style="width:100%;height:100%;background:#000"></video>`
        : `<span style="color:#a5b4fc;font-size:13px">🎬 视频占位</span>`}
    </div>
    <div style="font-size:11px;color:var(--mut);margin-bottom:6px;flex:1">${esc(seg.core_action||"")}</div>
    <button class="pill primary" style="font-size:11.5px;padding:5px 10px;margin-bottom:4px;cursor:pointer" onclick="openTfVideoModal(${ep.number},${segIdx})">🎬 生视频</button>
    <button class="pill" onclick="tfCopy(${segIdx})" style="font-size:11px;padding:4px 10px;cursor:pointer">📋 复制提示词</button>
  </div>`;
}

// ===== 段级双模型提示词（★ 2026-09-02 方案A：seedance=分镜全文保真；h3=为空时实时构建 MiniMax-H3 六段式，不再复制 Seedance 文本；弹窗手改后写回对应分支）=====
function tfEnsureVP(ep, seg){
  if(!seg.video_prompts || typeof seg.video_prompts !== "object" || Array.isArray(seg.video_prompts)){
    seg.video_prompts = { seedance: seg.video_prompt || "", h3: "" };
  }
  if(!seg.video_prompts.seedance) seg.video_prompts.seedance = seg.video_prompt || "";
  // ★ 2026-09-02 h3 槽位为空（或仍等于 seedance=旧懒装填复制的假 H3）→ 实时候算 buildTfVideoPromptH3 并回写
  if(!seg.video_prompts.h3 || seg.video_prompts.h3 === seg.video_prompts.seedance) seg.video_prompts.h3 = buildTfVideoPromptH3(ep, seg);
  return seg.video_prompts;
}
function tfCurModel(){ return (typeof genVideoModel !== "undefined" && genVideoModel === "h3") ? "h3" : "seedance"; }

// ===== MiniMax-H3 全参考六段式（★ 2026-09-02 兜底初稿 v2：按 quality-spec 修 6 处程序可做项——
//   ①去 Frame:/Camera: 字段标签→英文引导句+景别英译 ②台词四件套((Sx)/画外/<d>[Chinese]>/闭嘴声明)
//   ③拓扑图改 <Picture N> 规划参考立条(不占 Subject 编号) ④retention 按 role 分模板+Picture 规划行
//   ⑤NEGATIVE 不再并入(§6 负面清单非 H3 合法段)+STYLE 缺防污染句补标准句 ⑥soundscape 聚合汇总(禁指针式)
//   附修 v1 丢对白 bug：visual 混入的「- 对白/- 音效」尾巴提取复用而非丢弃。
//   ★ 定位=旧数据兜底初稿(正文中文不合规 §1)；正式 H3 以分镜同步双产(§1.9)为准 =====
const TF_FRAME_EN = {"ECU":"extreme close-up","CU":"close-up","MCU":"medium close-up","MS":"medium shot","WS":"wide shot","ELS":"extreme long shot"};
function tfH3TsStart(ts){
  const m = String(ts || "").match(/([\d.]+)\s*s/);
  return m ? parseFloat(m[1]) : null;
}
function tfH3FmtTime(sec){
  const m = Math.floor(sec / 60), s = sec - m * 60;
  return String(m).padStart(2, "0") + ":" + s.toFixed(3).padStart(6, "0");
}
function tfH3SplitTail(t){
  // visual 里混入的「- 对白…/- 音效…」尾巴：拆出 主画面/对白/音效（独立字段缺失时兜底用）
  t = String(t || "");
  let dia = "", snd = "";
  const diaM = t.match(/-\s*对白[^：]*：\s*([\s\S]*?)(?=\s*-\s*音效|$)/);
  if(diaM) dia = diaM[1].trim();
  const sndM = t.match(/-\s*音效[^：]*：\s*([\s\S]*?)(?=\s*-\s*对白|$)/);
  if(sndM) snd = sndM[1].trim();
  const main = t.split(/\s*-\s*(?:对白|音效)/)[0].trim();
  return { main, dia, snd };
}
function buildTfVideoPromptH3(ep, seg){
  const vp = String(seg.video_prompt || "");
  const lines = vp.split("\n");
  // 引用行（首部「名字=图N」，空格/逗号分隔；与 tfAutoRefs 垫图顺序同源）
  const refLine = lines.find(l => /=图\d+/.test(l)) || "";
  const refs = [...refLine.matchAll(/([^=\s，,]+)=图(\d+)/g)].map(m => ({ name: m[1], pic: Number(m[2]) }));
  // 【STYLE】风格段；★ 修正⑤：NEGATIVE 丢弃（quality-spec §6 负面清单不是 H3 合法段落）
  const styleM = vp.match(/【STYLE】([\s\S]*?)(?=\n## |【NEGATIVE】|$)/);
  let styleTxt = styleM ? styleM[1].trim() : "";
  // STYLE 缺防污染句 → 补规范标准句（§6 融进风格开场句）
  if(styleTxt && !/infer/i.test(styleTxt)) styleTxt += " This look applies only to the rendering medium, materials, lighting, and finish, and must never be used to infer or change faces, ages, genders, body proportions, clothing, accessories, props, or environments, which always follow the reference pictures and the on-script descriptions.";
  // ★ 修正③：拓扑图 = <Picture N> 规划参考单独立条（§3），不占 Subject 编号
  const spatial = refs.find(r => r.name === "空间拓扑图") || null;
  const subjRefs = refs.filter(r => r.name !== "空间拓扑图");
  const subj = subjRefs.map((r, i) => {
    let role = "prop";
    if((P.xiatang?.characters || []).find(x => x.name === r.name)) role = "character";
    else if((P.xiatang?.scenes || []).find(x => x.name === r.name)) role = "scene";
    return Object.assign({}, r, { role, label: "<Subject " + (i + 1) + ">" });
  });
  const shots = seg.shots || [];
  // ① subject_definitions（+ Picture 规划参考立条）
  const defs = subj.map(x => {
    if(x.role === "character") return x.label + " is the character " + x.name + " referenced from the character reference sheet <Picture " + x.pic + ">, with fixed appearance, costume, and hairstyle to be preserved exactly.";
    if(x.role === "scene") return x.label + " is the scene " + x.name + " referenced from <Picture " + x.pic + ">.";
    return x.label + " is the prop " + x.name + " referenced from <Picture " + x.pic + ">.";
  });
  if(spatial) defs.push("<Picture " + spatial.pic + "> is a spatial-planning reference (a top-down floor plan of the set) for [Shot 1] to [Shot " + Math.max(1, shots.length) + "], defining the relative positions of all areas, the movement directions, and all character blocking; on-screen spatial relationships must strictly follow this plan.");
  // ② summary
  const subjList = subj.map(x => x.label).join(", ");
  const summary = subj.length
    ? "[reference generation] The target video shows " + subjList + " in a cinematic scene. Character identity, costume, and appearance are locked to the referenced sheets" + (spatial ? "; spatial blocking follows the floor-plan reference <Picture " + spatial.pic + ">" : "") + "."
    : "[reference generation] The target video is a cinematic scene rendered from the attached reference images.";
  // ③ retention_analysis（★ 修正④：按 role 分模板禁复制；Picture 规划行写「被遵循的空间关系」）
  const retain = subj.map(x => {
    const hits = [];
    shots.forEach((s, i) => {
      const txt = (s.visual || "") + " " + (s.camera || "") + " " + (s.dialogue || "") + " " + (s.sound || "");
      if(txt.includes(x.name)) hits.push("[Shot " + (i + 1) + "]");
    });
    const where = hits.length ? " (appears in " + hits.join(", ") + ")" : "";
    if(x.role === "character") return x.label + where + ": fully_preserved - the referenced appearance, costume, and hairstyle are retained.";
    if(x.role === "scene") return x.label + where + ": fully_preserved - the referenced scene layout and set landmarks are retained.";
    return x.label + where + ": fully_preserved - the referenced prop appearance and placement are retained.";
  });
  if(spatial) retain.push("<Picture " + spatial.pic + ">: the spatial relationships, movement directions, and character blocking defined in the plan are followed in all shots above.");
  // ④ detailed_description（★ 修正①：去字段标签→英文引导句；★ 修正②：台词四件套）
  const per = (shots.length && seg.duration) ? (parseFloat(seg.duration) || shots.length * 3) / shots.length : 3;
  const speakerMap = {};
  let spkIdx = 0;
  const speakerOf = (nm) => { if(!speakerMap[nm]){ spkIdx++; speakerMap[nm] = "S" + spkIdx; } return speakerMap[nm]; };
  const shotsTxt = shots.map((s, i) => {
    const start = tfH3TsStart(s.ts);
    const at = (i === 0) ? "" : " At " + tfH3FmtTime(start != null ? start : i * per) + ",";
    const frame = String(s.frame || "");
    // 景别英文句：抽取 (ECU|CU|MCU|MS|WS|ELS) 缩写转英文
    const abbrs = [...frame.matchAll(/\((ECU|CU|MCU|MS|WS|ELS)\)/g)].map(m => m[1]);
    const frTxt = abbrs.length ? "The shot is framed as " + abbrs.map(a => TF_FRAME_EN[a] + " (" + a + ")").join(", then reframes to a ") + "." : "";
    const visAll = tfH3SplitTail(s.visual);
    const cam = String(s.camera || "").trim();
    const vis = visAll.main;
    // 对白/音效：独立字段优先，缺失时用 visual 混入尾巴兜底（v1 直接丢弃 bug 修正）
    const dia = String(s.dialogue || "").trim() || visAll.dia;
    const snd = String(s.sound || "").trim() || visAll.snd;
    // ★ 修正②：台词四件套——(Sx) 按发声顺序分配 + 画外声明 + <d>[Chinese] 原话> + 闭嘴声明
    let diaTxt = "";
    if(dia){
      const offsrc = /画外/.test(dia) || /画外/.test(String(s.visual || ""));
      const mm = dia.match(/^([^：:]{1,20})[：:]\s*「?([^」]*)」?\s*$/) || dia.match(/^([^：:]{1,20})[：:]\s*([\s\S]*)$/);
      let spkName = "", quote = "";
      if(mm){ spkName = mm[1].replace(/[（(][^)）]*[)）]/g, "").trim(); quote = (mm[2] || "").replace(/^[「」\s]+/, "").replace(/[「」\s]+$/, "").trim(); }
      else { const q = dia.match(/「([^」]+)」/); if(q) quote = q[1].trim(); }
      const sx = speakerOf(spkName || "_anon");
      const inFrameChars = subj.filter(x => x.role === "character" && vis.includes(x.name));
      const closer = (offsrc && inFrameChars.length && (!spkName || !inFrameChars.find(x => x.name === spkName))) ? " while " + inFrameChars[0].label + "'s lips remain completely closed" : "";
      diaTxt = (spkName ? spkName + " " : "") + "(" + sx + ") " + (offsrc ? "says in an off-screen voiceover" : "says") + (quote ? ": <d>[Chinese] " + quote + "</d>" : "") + closer + ".";
    }
    const bodyParts = [frTxt, cam ? "The camera: " + cam + "." : "", vis ? "On screen: " + vis + "." : "", diaTxt, snd ? "Diegetic sound: " + snd + "." : ""].filter(Boolean);
    // 拓扑图在正文实际生效处引用一次（§3：航拍/俯拍/大远景首镜）
    if(spatial && (i === 0 || /航拍|俯|掠过/.test(cam) || /\((ELS|WS)\)/.test(frame))) bodyParts.push("Spatial blocking follows the floor plan in <Picture " + spatial.pic + ">.");
    const head = (i === 0) ? "[Shot 1]" : "[Shot " + (i + 1) + "]";
    return head + at + " " + bodyParts.join(" ");
  }).join("\n");
  let detailed = (styleTxt ? styleTxt + "\n" : "");
  if(shotsTxt) detailed += shotsTxt;
  else {
    // 兜底：无 shots → 取 video_prompt 正文（## 起、NEGATIVE 前）整体作为正文
    const bodyM = vp.match(/## [\s\S]*?(?=【NEGATIVE】|$)/);
    detailed += bodyM ? bodyM[0].trim() : vp.trim();
  }
  // ⑤ overall_soundscape（★ 修正⑥：聚合各镜音效点名汇总，禁「见上文」指针式）
  const snds = [];
  shots.forEach(s => { const t = String(s.sound || "").trim() || tfH3SplitTail(s.visual).snd; if(t && !snds.includes(t)) snds.push(t); });
  const soundscape = snds.length
    ? "Diegetic ambience and effects throughout the scene include: " + snds.slice(0, 3).join("; ") + (snds.length > 3 ? "; and more" : "") + ". Dialogue appears with its shots above."
    : "Ambient diegetic sound continues throughout the scene.";
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

// ===== ★ 2026-09-01 自动垫图：拓扑图最前（图1）+ 按引用行名字顺序查资产图（角色四视图/定妆照/主图，场景主图）=====
function tfRoleRef(roleName, epN){
  const c = (P.xiatang?.characters || []).find(x => x.name === roleName);
  if(!c) return null;
  const ids = c.identities || [];
  if(!ids.length) return c.image || null;
  // 按 chapter_range 选覆盖本集的身份（epN 对应 chNNN；无匹配用第一个）
  const idn = ids.find(i => {
    const m = String(i.chapter_range || "").match(/ch(\d{3})-ch(\d{3})/);
    return m && Number(m[1]) <= epN && epN <= Number(m[2]);
  }) || ids[0];
  return idn.sheet_image || idn.image || c.image || null;
}
function tfAutoRefs(ep, seg){
  const refs = [];
  // ★ 2026-09-01 引用顺序规则：角色 → 场景 → 道具 → 空间拓扑图（最后），与引用行图号对齐
  const firstLine = String(seg.video_prompt || "").split("\n")[0];
  // ★ 2026-09-04 修复：名字捕获排除中英逗号——此前 [^=\s]+ 会把"，"吞进名字（如"甲=图1，乙=图2"第二个名字被捕获为"，乙"→精确匹配失败→场景/道具全部失联，只剩首名角色）
  const names = [...firstLine.matchAll(/([^=\s，,]+)=图\d+/g)].map(m => m[1]);
  const assetNames = names.filter(n => n !== "空间拓扑图");
  for(const n of assetNames){
    if(refs.length >= 4) break;   // 预留最后一位给拓扑图
    let img = null;
    const c = (P.xiatang?.characters || []).find(x => x.name === n);
    if(c){ img = tfRoleRef(n, ep.number); }
    else {
      const s = (P.xiatang?.scenes || []).find(x => x.name === n);
      if(s && s.image) img = s.image;
      else {
        // ★ 2026-09-04 补道具分支（对齐虾镜 gvAutoRefs：角色→场景→道具）
        const p = (P.xiatang?.props || []).find(x => x.name === n);
        if(p && p.image) img = p.image;
      }
    }
    if(img && !refs.includes(img)) refs.push(img);
  }
  // 空间拓扑图垫最后（与引用行末位对齐；★ 2026-09-04 按段所属场取图：seg.space_map → 集合匹配 → 兜底第一张）
  const _segMap = tfSegSpaceMap(ep, seg);
  if(_segMap && _segMap.image && refs.length < 5) refs.push(_segMap.image);
  return refs.slice(0, 5);
}

// ===== 生视频弹窗（复用公共 gv-* DOM；提示词=当前模型分支；提交 module=tingfeng）=====
function openTfVideoModal(epN, segIdx){
  window._tfEpN = epN; window._tfSegIdx = segIdx;
  const ep = (P.tingfeng?.episodes||[]).find(e => e.number === epN);
  const seg = (ep?.segments||[])[segIdx];
  if(!seg){ toast("未找到该段"); return; }
  const vps = tfEnsureVP(ep, seg);
  const prompt = vps[tfCurModel()] || "";
  $("gv-title").textContent = `第${epN}集 · ${seg.id||("S"+(segIdx+1))} · ${seg.duration||""}s`;
  $("gv-prompt").value = prompt;
  $("gv-info").innerHTML = `段：${esc(seg.id||"")} · ${seg.duration||""}s · 分辨率默认 <b style="color:var(--acc)">768P</b>（可改）<br><span style="color:var(--mut);font-size:11px">🎥 视频渠道：MiniMax H3 官方（优先）/ LK888（回退）· 输出 .mp4 · 启动后后台异步（5~25 分钟）· 失败自动重试 2 次 · 完成后自动写入本位</span>` + (tfCurModel()==="h3" ? `<br><span style="color:#b45309;font-size:11px">⚠️ 当前 H3 提示词若为函数兜底初稿（正文中文），仅供参考——正式 H3 以分镜同步双产交付的六段式终稿为准（quality-spec）</span>` : "");
  // ★ 2026-09-01 自动引用资产图（对齐虾镜 gvAutoRefs 模式：拓扑图最前 + 引用行名字顺序，≤5 张）
  if(typeof gvState !== "undefined"){
    gvState.refs = tfAutoRefs(ep, seg);
    gvState.autoCount = (gvState.refs || []).length;
    if(typeof gvRenderRefs === "function") gvRenderRefs();
  }
  const durSel = $("gv-duration");
  durSel.innerHTML = [4,5,6,7,8,9,10,11,12,13,14,15]
    .map(d => `<option value="${d}"${d === parseInt(seg.duration,10) ? " selected" : ""}>${d}s</option>`).join("");
  const resSel = $("gv-resolution");
  resSel.innerHTML = ["768P","1080P","2K","4K"].map(r => `<option value="${r}"${r==="768P"?" selected":""}>${r}</option>`).join("");
  // ★ 2026-09-03 补比例（gv-size）下拉渲染——此前缺失导致听风弹窗"视频尺寸没法选择"（只有虾镜弹窗渲染过它）
  fetch("/gen-config").then(r => r.json()).then(cfg => {
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
  }).catch(() => {});
  // ★ 启动按钮改绑听风提交（虾镜打开弹窗时会绑回 gvStart，互不干扰）
  $("gv-send").onclick = tfGvStart;
  // ★ 2026-09-01 修复"点了没反应"：弹窗 DOM id = genvideo，用 classList.add("open") 打开（与虾镜一致）
  $("genvideo").classList.add("open");
}
async function tfGvStart(){
  const ta = $("gv-prompt");
  if(!ta || !ta.value.trim()){ toast("⚠️ 请先填写提示词"); return; }
  const epN = window._tfEpN, segIdx = window._tfSegIdx;
  if(epN == null || segIdx == null){ toast("⚠️ 弹窗状态丢失，请重开"); return; }
  let channelId = window._gvChannelId || "";
  try{
    const cfg = await (await fetch("/gen-config")).json();
    // ★ 2026-09-02 MiniMax H3 官方渠道优先，888 中转回退（pickVideoChannel，见 gen.js）
    channelId = (typeof pickVideoChannel === "function" && pickVideoChannel(cfg.channels || [])?.id) || "";
    window._gvChannelId = channelId;
  }catch(e){ channelId = window._gvChannelId || ""; }
  if(!channelId){ toast("⚠️ 请先在 ⚙ 设置配置视频渠道（MiniMax H3 或 LK888）"); return; }
  const ep = (P.tingfeng?.episodes||[]).find(e => e.number === epN);
  const seg = (ep?.segments||[])[segIdx];
  if(seg){
    const vps = tfEnsureVP(ep, seg);
    if(tfCurModel() === "h3") vps.h3 = ta.value.trim(); else vps.seedance = ta.value.trim();
    seg.video_prompt = vps.seedance;
  }
  const payload = {
    module: "tingfeng", ep: epN, idx: 0, seg_idx: segIdx,
    model: ($("gv-model") && $("gv-model").value) || "hailuo-h3-cankaosheng",
    size: ($("gv-size") && $("gv-size").value) || "16:9",
    prompt: ta.value.trim(), images: (typeof gvState!=="undefined" ? (gvState.refs||[]).slice(0,5) : []),
    channel_id: channelId,
    duration: parseInt(($("gv-duration") && $("gv-duration").value) || "6", 10) || 6,
    aspect_ratio: ($("gv-size") && $("gv-size").value) || "16:9",
    resolution: ($("gv-resolution") && $("gv-resolution").value) || "768P"
  };
  const btn = $("gv-send");
  if(btn){ btn.disabled = true; btn.textContent = "⏳ 提交中…"; }
  // ★ 2026-09-01 拓扑图未生成时提醒；★ 2026-09-04 按段所属场检查（每场一张）
  {
    const _ep0 = (P.tingfeng?.episodes||[]).find(e => e.number === epN);
    const _seg0 = _ep0 ? (_ep0.segments||[])[segIdx] : null;
    const _m0 = _ep0 ? tfSegSpaceMap(_ep0, _seg0) : null;
    if(!(_m0 && _m0.image)) toast("💡 提示：该段所属场的空间拓扑图未生成（引用行末位），建议先在制作页顶部生成对应场次拓扑图，再垫图才与图号对齐");
  }
  toast("⏳ 提交听风视频任务…");
  fetch("/gen-video", {method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify(payload)})
    .then(r => r.json()).then(j => {
      if(!j.ok){ toast("❌ " + (j.error || "提交失败")); if(btn){ btn.disabled=false; btn.textContent="🚀 启动生视频"; } return; }
      toast("🎬 听风视频生成中（task_id=" + j.task_id + " · 5~25 分钟）· 完成后自动写入视频位");
      if(typeof closeGenVideoModal === "function") closeGenVideoModal();
      else { const m=$("gv-modal"); if(m) m.style.display="none"; if(btn){ btn.disabled=false; btn.textContent="🚀 启动生视频"; } }
      tfPollVideo(j.task_id, epN, segIdx);
    }).catch(err => {
      toast("❌ 提交失败：" + err.message);
      if(btn){ btn.disabled=false; btn.textContent="🚀 启动生视频"; }
    });
}
var tfPollTimer = null;
function tfPollStop(){ if(tfPollTimer){ clearInterval(tfPollTimer); tfPollTimer = null; } }
function tfPollVideo(taskId, epN, segIdx){
  tfPollStop();
  let elapsed = 0; const t0 = Date.now();
  tfPollTimer = setInterval(() => {
    elapsed = Math.floor((Date.now() - t0)/1000);
    fetch("/gen-video-status?task_id=" + encodeURIComponent(taskId)).then(r=>r.json()).then(j => {
      if(!j.ok){ toast("⚠️ 视频任务查询失败：" + (j.error||"")); tfPollStop(); return; }
      if(j.status === "running"){
        if(elapsed > 0 && elapsed % 30 === 0) toast("🎬 生成中…已用 " + elapsed + "s");
        return;
      }
      tfPollStop();
      const ep = (P.tingfeng?.episodes||[]).find(e => e.number === epN);
      const seg = (ep?.segments||[])[segIdx];
      if(seg && j.status === "success" && j.video){
        seg.video = j.video; seg.video_ready = true; seg.video_result = j.video; seg._vt = Date.now();
        toast("✅ 听风视频已写入视频位");
      } else {
        toast((j.status === "success" ? "✅ 视频完成" : "❌ 视频失败：" + (j.error || j.status)));
      }
      const c = $("content"); if(c && tfCurEp){ c.innerHTML = renderTingFeng(); bindTingFeng(); }
    }).catch(()=>{});
  }, 5000);
}
// 删除段视频（文件+记录一起删；后端 /story-video-delete 按 module 路由）
function tfVideoDelete(epN, segIdx){
  if(!confirm("确定删除该段视频？（本地 mp4 与记录一起删除，不可恢复）")) return;
  if(!IS_SERVER){ toast("需服务模式（双击启动项目台.bat）"); return; }
  fetch("/story-video-delete", {method:"POST", headers:{"Content-Type":"application/json"},
    body: JSON.stringify({module:"tingfeng", ep: epN, idx: 0, seg_idx: segIdx})})
    .then(r=>r.json()).then(res=>{
      if(!res.ok){ toast("⚠️ " + (res.error||"删除失败")); return; }
      const ep = (P.tingfeng?.episodes||[]).find(e => e.number === epN);
      const seg = (ep?.segments||[])[segIdx];
      if(seg){ seg.video=""; seg.video_ready=false; seg.video_result=""; seg._vt=0; }
      const c = $("content"); if(c && tfCurEp){ c.innerHTML = renderTingFeng(); bindTingFeng(); }
      toast("🗑 已删除该段视频");
    }).catch(()=>toast("⚠️ 删除失败（服务异常）"));
}
// 全部批量生视频（未生成的段逐一入队，默认参数：段时长/16:9/768P/分镜全文）
async function tfBatchGenVideo(){
  if(!IS_SERVER){ toast("AI 生成需要服务模式：请双击「启动项目台.bat」"); return; }
  const ep = (P.tingfeng?.episodes||[]).find(e => e.number === tfCurEp);
  if(!ep){ toast("请先进入一集"); return; }
  let channelId = "", model = "";
  try{
    const cfg = await fetch("/gen-config").then(r => r.json());
    // ★ 2026-09-02 MiniMax H3 官方渠道优先，888 中转回退
    const ch = pickVideoChannel(cfg.channels||[]);
    if(!ch){ toast("❌ 未配置视频渠道（MiniMax H3 或 LK888），请先到 ⚙ 设置完善"); return; }
    channelId = ch.id;
    model = (ch.apiFormat === "minimax_h3") ? "MiniMax-H3" : ((ch.models||[])[0] || "");
    model = (typeof model === "string") ? model : (model.name || "");
    if(!model){ toast("❌ 渠道无可用模型"); return; }    if(!model){ toast("❌ 渠道无可用模型"); return; }
  }catch(e){ toast("❌ 读取渠道配置失败"); return; }
  const segs = ep.segments || [];
  let cnt = 0;
  for(let i=0;i<segs.length;i++){
    const seg = segs[i];
    if(seg.video_ready || seg.video) continue;
    const vps = tfEnsureVP(ep, seg);
    const payload = {
      module: "tingfeng", ep: ep.number, idx: 0, seg_idx: i,
      model, size: "16:9", prompt: vps[tfCurModel()] || seg.video_prompt || "",
      images: [], channel_id: channelId,
      duration: parseInt(seg.duration,10) || 6, aspect_ratio: "16:9", resolution: "768P"
    };
    const r = await fetch("/gen-video", {method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify(payload)}).then(x=>x.json()).catch(()=>({ok:false}));
    if(r.ok){ cnt++; tfPollVideo(r.task_id, ep.number, i); }
  }
  toast(cnt ? `🎬 已入队 ${cnt} 段听风视频（后台生成，完成后自动写入视频位）` : "✅ 所有段视频已生成");
}

// ===== 故事板生图提示词（简约线条，与虾镜同风格；★ 2026-09-01 用户定稿：每格 = 一个分镜头，S 段不拆板，全部镜头进故事板）=====
function buildTfStoryPrompt(ep, idxs){
  const segs = idxs.map(i => (ep.segments||[])[i]).filter(Boolean);
  if(!segs.length) return "";
  // beat 展开：段 → 镜头（一格一镜）
  const beats = [];
  segs.forEach(s => (s.shots || []).forEach(sh => beats.push({seg: s, sh})));
  const cells = beats.length;
  const grid = tfGridLabel(cells);
  const title = (segs[0].core_action || "").slice(0, 12);
  const mood = segs.map(s=>s.core_action||"").join("").slice(0,30) + "…";
  const lines = beats.map((b, pi) => {
    const sh = b.sh;
    return `P${String(pi+1).padStart(2,"0")} / ${b.seg.id}-镜${sh.n||""} / ${sh.frame||""}·${sh.camera||""}；画面 —— ${sh.visual||b.seg.core_action}${sh.dialogue?`；对白「${sh.dialogue}」`:""}`;
  }).join("\n");
  return `单张故事板分镜稿，题材为日常剧情 / 叙事向，节奏平稳、注重情绪与场景交代。

【主体设定】现代极简制片分镜板，呈现一段日常叙事剧情：${mood}。通过镜头角度、人物姿态与表情倾向、人物空间关系、运动方向与固定场景，交代剧情推进与情绪变化。

【页眉规范】美术化制片分镜页眉，搭配贴合本场戏的字体与细分割线，层级清晰，仅在画格外围做克制简约装饰，画格内部不加任何装饰。页眉必须完整包含以下两句带引号文字：
"${title}"
"${mood}"

【分镜版面结构】按布局规则自动排版，版式 ${grid}（共 ${cells} 个 beat，一格对应一个分镜头，按 P 序号顺序阅读；不足的格子保持全空白）。每格小标题严格遵循：P 序号 / 段标签-镜号 / 景别·运镜。一格只呈现一个定格瞬间。
网格布局：${grid}（每格严格 16:9，不可违背）

${lines}

【画面美术风格】（锁定，不可更改）平面简约线条简笔画风格，单色 2D 铅笔 / 墨水草稿、白底、大面积留白。松散开放式轮廓 + 少量辅助结构线 + 简易透视参照物；人物无五官细节，仅保留体态。禁止：填色、灰调晕染、排线、阴影、环境闭塞光影、色彩、3D 建模体积、纹理、精细插画。

【参考素材约束】角色参考：仅用于参考角色剪影、身高体量、标志性外形特征与基础站姿，不用于参考细节与完整设计；所有角色剪影保持独立清晰，不可融合、重叠混淆。场景 / 道具参考：仅参考空间结构、核心地标位置、外轮廓与比例，不参考细节纹理与光影。

【强制要求】画格内部无任何文字、水印、签名；每格 16:9；简约线条风格不可被覆盖。`;
}
async function tfStoryGen(epN, gno, idxs){
  if(!IS_SERVER){ toast("AI 生成需要服务模式：请双击「启动项目台.bat」"); return; }
  const ep = (P.tingfeng?.episodes||[]).find(e => e.number === epN);
  if(!ep){ toast("未找到该集"); return; }
  const p = buildTfStoryPrompt(ep, idxs);
  if(!p){ toast("该板无分段内容"); return; }
  openGenModal("tingfeng", "tingfeng-" + epN + "-" + gno, p, "", ep.storyboard_prompt_cn || "");
}
async function tfBatchGenStory(){
  if(!IS_SERVER){ toast("AI 生成需要服务模式：请双击「启动项目台.bat」"); return; }
  const ep = (P.tingfeng?.episodes||[]).find(e => e.number === tfCurEp);
  if(!ep){ toast("请先进入一集"); return; }
  const boards = tfGroupBoards(ep, tfGridCap);
  let model = "", channelId = "", size = "1536x768";
  try{
    const cfg = await fetch("/gen-config").then(r => r.json());
    const ch = (cfg.channels||[]).find(c => c.configured);
    if(!ch){ toast("❌ 未配置可用生图渠道，请先到 ⚙ 设置完善"); return; }
    channelId = ch.id;
    const m0 = (ch.models||[])[0] || "";
    model = (typeof m0 === "string") ? m0 : (m0.name || "");
    if(!model){ toast("❌ 渠道无可用模型"); return; }
    size = (cfg.default_sizes && cfg.default_sizes.sketch_frame) || "1536x768";   // ★ 2026-09-03 用户拍板：故事板默认尺寸=设置里「草图·首帧」
  }catch(e){ toast("❌ 读取渠道配置失败"); return; }
  let cnt = 0;
  for(let gi = 0; gi < boards.length; gi++){
    const b = boards[gi];
    const sb = (ep.storyboards||[]).find(x => x.idx === gi+1);
    if(sb && sb.ready) continue;
    const p = buildTfStoryPrompt(ep, b.segIdxs);
    if(!p) continue;
    const ok = await batchEnqueue("tingfeng", "tingfeng-" + ep.number + "-" + (gi+1), p, model, size, channelId, undefined, 1);
    if(ok) cnt++;
  }
  toast(cnt ? `✅ 已入队 ${cnt} 张听风故事板生图` : "✅ 故事板已全部生成");
}

// ===== 复制提示词 =====
function tfCopy(i){
  const ep = (P.tingfeng?.episodes||[]).find(e => e.number === tfCurEp);
  const seg = (ep?.segments||[])[i];
  if(!seg || !seg.video_prompt){ toast("❌ 无提示词可复制"); return; }
  if(navigator.clipboard && navigator.clipboard.writeText){
    navigator.clipboard.writeText(seg.video_prompt).then(()=>toast("✅ 视频提示词已复制"), ()=>tfCopyFallback(seg.video_prompt));
  } else tfCopyFallback(seg.video_prompt);
}
function tfCopyFallback(txt){
  const ta = document.createElement("textarea");
  ta.value = txt; ta.style.position = "fixed"; ta.style.opacity = "0";
  document.body.appendChild(ta); ta.select();
  try{ document.execCommand("copy"); toast("✅ 视频提示词已复制"); }catch(e){ toast("❌ 复制失败，请手动选择复制"); }
  document.body.removeChild(ta);
}

function bindTingFeng(){
  document.querySelectorAll("#tingfeng-tabs .t").forEach(el => {
    el.addEventListener("click", () => {
      tfCurTab = el.dataset.tfTab;
      const c = $("content"); c.innerHTML = renderTingFeng(); bindTingFeng();
    });
  });
}
