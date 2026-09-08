// ===== 📌 画面标注（★ 2026-08-22 从 xiaji-conductor 模板移植，适配虾镜 shots 架构：镜级标注，Canvas 工具，无历史）=====
// 制作页「📌 画面标注」资产位打开 → 底图默认该镜首帧图（无则选场景图）→ 文字/编号/圆/矩形/画笔标注 → 保存写 shot.annotated_image
let annShot = null;          // 当前标注 shot 对象
let annEp = 0;               // 当前 ep number
let annCtx = null;           // canvas 2d ctx
let annImg = null;           // 底图 Image
let annTool = "text";        // text | num | circle | rect | brush
let annColor = "#e11d48";    // 标注颜色
let annStack = [];           // 标注元素栈（撤回用）
let annNum = 1;              // 编号计数器
let annDrag = null;          // 拖拽中的元素（预览）
let annCamEdit = null;       // ★ 2026-08-23 机位工具：正在调整方向的机位元素（null=无编辑中）

// 弹窗 HTML 动态注入（防静态 DOM 缺失/缓存旧页）
const ANN_MODAL_HTML = `<div class="gen-mask" id="annmodal" onclick="if(event.target===this)closeAnnModal()">
  <div class="gen-box" id="ann-box" style="width:860px;position:relative">
    <div class="gb-head">
      <b>📌 画面标注 · <span id="ann-title">镜</span></b>
      <span class="x" onclick="closeAnnModal()">×</span>
    </div>
    <div id="ann-tools" style="display:flex;align-items:center;gap:6px;padding:10px 14px;border-bottom:1px solid var(--line);flex-wrap:wrap">
      <button class="ann-tool" data-tool="sel" onclick="annSetTool('sel')">🖱 选择</button>
      <button class="ann-tool" data-tool="text" onclick="annSetTool('text')">📝 文字</button>
      <button class="ann-tool" data-tool="num" onclick="annSetTool('num')">🔢 编号</button>
      <button class="ann-tool" data-tool="circle" onclick="annSetTool('circle')">⭕ 圆形框</button>
      <button class="ann-tool" data-tool="rect" onclick="annSetTool('rect')">▭ 矩形框</button>
      <button class="ann-tool" data-tool="brush" onclick="annSetTool('brush')">✏️ 画笔</button>
      <button class="ann-tool" data-tool="cam" onclick="annSetTool('cam')" title="机位：点画布放置 🎥，移动鼠标确定拍摄方向，再点一下确认（黄色虚线箭头表示方向）">🎥 机位</button>
      <span style="margin-left:8px;display:flex;gap:4px;align-items:center">
        <span class="ann-color" data-c="#e11d48" style="background:#e11d48" onclick="annColorPick('#e11d48')"></span>
        <span class="ann-color" data-c="#2563eb" style="background:#2563eb" onclick="annColorPick('#2563eb')"></span>
        <span class="ann-color" data-c="#16a34a" style="background:#16a34a" onclick="annColorPick('#16a34a')"></span>
        <span class="ann-color" data-c="#111827" style="background:#111827" onclick="annColorPick('#111827')"></span>
      </span>
      <div style="flex:1"></div>
      <button class="ann-tool" onclick="annZoom(1/1.25)" title="缩小">🔍−</button>
      <span id="ann-zoom-label" style="font-size:11px;color:var(--mut);min-width:38px;text-align:center">100%</span>
      <button class="ann-tool" onclick="annZoom(1.25)" title="放大">🔍+</button>
      <button class="ann-tool" onclick="annToggleFullscreen()" id="ann-fs-btn" title="全屏标注">⛶ 全屏</button>
      <button class="ann-tool" onclick="annUndo()" title="撤回上一步">↶ 撤回</button>
    </div>
    <div id="ann-canvas-wrap" style="padding:14px;background:#f3f4f6;flex:1;overflow:auto;display:flex">
      <div id="ann-canvas-holder" style="margin:auto;position:relative;background:#fff;border:1px solid var(--line);border-radius:8px;overflow:hidden;display:flex;align-items:center;justify-content:center;max-height:50vh;max-width:100%">
        <canvas id="ann-canvas" style="max-width:100%;max-height:50vh;cursor:crosshair"></canvas>
        <div id="ann-empty-tip" style="display:none;position:absolute;inset:0;align-items:center;justify-content:center;color:#9ca3af;font-size:13px;background:#fff">请先点击「🎬 选择场景」加载底图</div>
      </div>
      <div id="ann-scene-layer" style="display:none;position:absolute;inset:0;background:rgba(17,24,39,.45);z-index:6;align-items:center;justify-content:center;border-radius:0 0 8px 8px">
        <div style="background:#fff;border-radius:10px;width:780px;max-width:92vw;max-height:75%;display:flex;flex-direction:column;box-shadow:0 12px 40px rgba(0,0,0,.25)">
          <div style="padding:12px 16px;font-weight:600;border-bottom:1px solid var(--line);display:flex;justify-content:space-between;align-items:center">
            <span>🎬 选择场景底图</span><span class="x" onclick="annCloseScenePicker()">×</span>
          </div>
          <div id="ann-scene-list" style="overflow:auto;padding:10px;display:flex;flex-wrap:wrap;gap:10px;align-content:flex-start"></div>
        </div>
      </div>
    </div>
    <div id="ann-desc" style="padding:8px 14px;font-size:12px;color:var(--mut);border-top:1px solid var(--line);border-bottom:1px solid var(--line);max-height:66px;overflow:auto"></div>
    <div style="display:flex;align-items:center;gap:10px;padding:12px 14px">
      <button class="btn" onclick="annOpenScenePicker()">🎬 选择场景</button>
      <div style="flex:1"></div>
      <button class="btn" onclick="closeAnnModal()">取消</button>
      <button class="btn primary" onclick="annSave()">💾 保存</button>
    </div>
  </div>
</div>`;

// ★ 2026-08-22 画面标注集窗口（复用标注）：展示全部镜头已生成的标注图，点击应用（内存+持久化）
const ANN_LIB_HTML = `<div class="gen-mask" id="annlib" onclick="if(event.target===this)closeAnnLib()">
  <div class="gen-box" style="width:760px">
    <div class="gb-head"><b>📋 画面标注集</b><span class="x" onclick="closeAnnLib()">×</span></div>
    <div style="font-size:12px;color:var(--mut);padding:10px 16px 0">点击任意标注图 → 应用到当前镜头（自动保存到数据库）。</div>
    <div id="annlib-grid" style="overflow:auto;padding:12px 16px 16px;display:flex;flex-wrap:wrap;gap:10px;align-content:flex-start;max-height:62vh"></div>
  </div>
</div>`;
let annLibEp = 1, annLibShot = "";
function ensureAnnLib(){
  if($("annlib-grid")) return;
  const wrap = document.createElement("div");
  wrap.innerHTML = ANN_LIB_HTML;
  while(wrap.firstChild) document.body.appendChild(wrap.firstChild);
}
function openAnnLib(shotNumber){
  ensureAnnLib();
  annLibShot = String(shotNumber || "");
  const _ep0 = getCurEp();
  annLibEp = _ep0 ? (_ep0.number || 1) : 1;
  const t = Date.now();
  const items = [];
  (P.xiajing?.episodes||[]).forEach(_ep => {
    const _arr = _ep.edited_shots || _ep.shots || [];
    _arr.forEach(_sh => {
      if(_sh.annotated_image) items.push({img: _sh.annotated_image, label: "第" + _ep.number + "集·镜" + _sh.shot_number});
    });
  });
  const grid = $("annlib-grid");
  if(!items.length){
    grid.innerHTML = `<div style="width:100%;text-align:center;color:var(--mut);font-size:13px;padding:40px 0">暂无已生成的画面标注图</div>`;
  } else {
    grid.innerHTML = items.map(it => `
      <div style="width:150px;border:1px solid var(--line);border-radius:8px;overflow:hidden;cursor:pointer;background:#fff" onclick="annPickLib('${esc(it.img)}','${esc(it.label)}')" title="应用到当前镜头：${esc(it.label)}">
        <div style="height:110px;background:#f0f0f0;display:flex;align-items:center;justify-content:center;overflow:hidden"><img src="${esc(it.img)}?t=${t}" loading="lazy" style="width:100%;height:100%;object-fit:cover;display:block" onerror="this.parentNode.innerHTML='<span style=font-size:12px;color:var(--mut)>图缺失</span>'"></div>
        <div style="font-size:12px;color:#475569;padding:4px 6px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${esc(it.label)}</div>
      </div>`).join("");
  }
  $("annlib").classList.add("open");
}
function closeAnnLib(){ const m = $("annlib"); if(m) m.classList.remove("open"); }
async function annPickLib(img, label){
  if(!annLibShot){ toast("❌ 无当前镜头"); closeAnnLib(); return; }
  const _arr = xjShots(xjEpObj());
  const s = _arr.find(x => String(x.shot_number) === String(annLibShot));
  if(!s){ toast("❌ 当前镜头不存在"); closeAnnLib(); return; }
  if(s.annotated_image && !confirm("当前镜头已有标注图，确认覆盖？")) return;
  try{
    const r = await fetch("/reuse-annotation", {method:"POST", headers:{"Content-Type":"application/json"},
      body: JSON.stringify({ep: annLibEp, shot_number: annLibShot, image: img})});
    const j = await r.json();
    if(!j.ok){ toast("❌ " + (j.error || "复用失败")); return; }
    s.annotated_image = img + "?t=" + Date.now();   // ★ 内存更新（与持久化同步）
    closeAnnLib();
    rerenderCurrent();
    toast("✅ 已复用标注：" + label);
  }catch(e){ toast("❌ 复用请求失败"); }
}

function ensureAnnModal(){
  if($("ann-canvas")) return;
  const wrap = document.createElement("div");
  wrap.innerHTML = ANN_MODAL_HTML;
  while(wrap.firstChild) document.body.appendChild(wrap.firstChild);
  const cv = $("ann-canvas");
  if(!cv){ console.error("画面标注弹窗注入失败"); return; }
  cv.addEventListener("pointerdown", annMouseDown);
  cv.addEventListener("pointermove", annMouseMove);
  cv.addEventListener("pointerup", annMouseUp);
  cv.addEventListener("pointerleave", annMouseUp);
  cv.addEventListener("wheel", e => {
    e.preventDefault();
    annZoom(e.deltaY < 0 ? 1.15 : 1/1.15);
  }, {passive:false});
}

let annFullscreen = false;
function annToggleFullscreen(){
  annFullscreen = !annFullscreen;
  const box = $("ann-box");
  if(!box) return;
  box.classList.toggle("ann-fullscreen", annFullscreen);
  const btn = $("ann-fs-btn");
  if(btn) btn.textContent = annFullscreen ? "✕ 退出全屏" : "⛶ 全屏";
  annResizeCanvas();
  setTimeout(() => { annRender(); }, 60);
}

// ★ 2026-08-22 打开标注（虾镜制作页入口）：shotNumber 为镜头镜号；底图默认用该镜首帧图，无则提示选场景
function openAnnModal(shotNumber){
  const ep = getCurEp();
  if(!ep) return;
  const s = xjShots(ep).find(x => String(x.shot_number) === String(shotNumber));
  if(!s){ toast("⚠️ 镜头不存在"); return; }
  ensureAnnModal();
  if(!window._annSpaceBound){ annBindSpace(); window._annSpaceBound = true; }
  annShot = s; annEp = ep.number || 1;
  $("ann-title").textContent = `第 ${annEp} 集 · 镜 ${s.shot_number}`;
  $("ann-desc").textContent = "画面内容：" + (s.visual || s.outline_visual || "（无描述）");
  annStack = []; annNum = 1; annDrag = null; annCamEdit = null; annImg = null; annScale = 1; annSel = null; annSelMode = null;
  const cv = $("ann-canvas");
  cv.width = 800; cv.height = 600;
  cv.style.maxWidth = "100%"; cv.style.maxHeight = "50vh"; cv.style.width = ""; cv.style.height = "";
  annCtx = cv.getContext("2d");
  annCtx.clearRect(0, 0, 800, 600);
  const zl = $("ann-zoom-label"); if(zl) zl.textContent = "100%";
  if(s.annotated_image){
    annLoadImage(s.annotated_image + "?t=" + Date.now());
  } else if(s.firstframe_image){
    // 底图：有首帧用首帧图
    annLoadImage(s.firstframe_image + "?t=" + Date.now());
  } else {
    // ★ 2026-08-22 空白未做 → 默认展示当前分镜所属场景资产图（★ 优先「正面」资产 views.正面，正面未生成则用主图）
    const _ep0 = getCurEp();
    const _scName0 = s.scene_name || (_ep0 && _ep0.scene_map ? _ep0.scene_map[s.scene_tag] : "") || "";
    const _sc0 = (_scName0 && P.xiatang) ? (P.xiatang.scenes||[]).find(x => x.name === _scName0) : null;
    if(_sc0){
      const _front0 = (_sc0.views && _sc0.views["正面"]) ? _sc0.views["正面"] : "";
      const _img0 = _front0 || (_sc0.image || null);
      if(_img0){
        annLoadImage(_img0 + "?t=" + Date.now());
      } else {
        $("ann-empty-tip").style.display = "flex";
        toast("ℹ️ 该镜未标注，所属场景无资产图；可点「🎬 选择场景」换底图");
      }
    } else {
      $("ann-empty-tip").style.display = "flex";
      toast("ℹ️ 该镜未标注，可点「🎬 选择场景」加载底图");
    }
  }
  annSetTool(annTool);
  $("annmodal").style.display = "flex";
}

function closeAnnModal(){
  const m = $("annmodal"); if(m) m.style.display = "none";
}

function annLoadImage(url){
  const img = new Image();
  img.onload = () => {
    annImg = img;
    annScale = 1;
    annResizeCanvas();
    const t = $("ann-empty-tip"); if(t) t.style.display = "none";
    annRender();
  };
  img.onerror = () => { toast("❌ 图片加载失败"); };
  img.src = url;
}

let annScale = 1;
function annResizeCanvas(){
  const cv = $("ann-canvas");
  if(!cv || !annImg) return;
  cv.width = Math.max(1, Math.round(annImg.naturalWidth * annScale));
  cv.height = Math.max(1, Math.round(annImg.naturalHeight * annScale));
  annCtx = cv.getContext("2d");
  const holder = $("ann-canvas-holder");
  const isFs = !!(window.annFullscreen && $("ann-box") && $("ann-box").classList.contains("ann-fullscreen"));
  if(annScale > 1){
    cv.style.maxWidth = "none"; cv.style.maxHeight = "none";
    cv.style.width = cv.width + "px"; cv.style.height = cv.height + "px";
    if(holder){ holder.style.maxHeight = "none"; holder.style.maxWidth = "none"; }
  } else {
    cv.style.maxWidth = "100%";
    cv.style.maxHeight = isFs ? "calc(100vh - 210px)" : "50vh";
    cv.style.width = ""; cv.style.height = "";
    if(holder){ holder.style.maxHeight = ""; holder.style.maxWidth = ""; }
  }
  const lbl = $("ann-zoom-label");
  if(lbl) lbl.textContent = Math.round(annScale * 100) + "%";
}
function annZoom(factor){
  annScale = Math.min(4, Math.max(0.2, annScale * factor));
  annResizeCanvas();
  annRender();
}

const ANN_NUMS = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳";

function drawAnnElement(el){
  if(!annCtx) return;
  const c = annCtx;
  const z = annScale || 1;
  c.save();
  c.strokeStyle = el.color; c.fillStyle = el.color; c.lineWidth = (el.lineWidth || 3) / z;
  if(el.type === "text"){
    c.font = `bold ${(el.size||22)/z}px "Microsoft YaHei", sans-serif`;
    c.fillText(el.text, el.x, el.y);
  } else if(el.type === "num"){
    const t = (el.n <= 20) ? ANN_NUMS[el.n-1] : String(el.n);
    c.font = `bold ${(el.size||26)/z}px "Microsoft YaHei", sans-serif`;
    c.textAlign = "center"; c.textBaseline = "middle";
    c.fillStyle = "rgba(255,255,255,.85)";
    c.beginPath(); c.arc(el.x, el.y, 15/z, 0, Math.PI*2); c.fill();
    c.fillStyle = el.color;
    c.fillText(t, el.x, el.y + 1);
    c.textAlign = "start"; c.textBaseline = "alphabetic";
  } else if(el.type === "circle"){
    c.beginPath(); c.ellipse(el.x + el.w/2, el.y + el.h/2, Math.abs(el.w/2), Math.abs(el.h/2), 0, 0, Math.PI*2); c.stroke();
  } else if(el.type === "rect"){
    c.strokeRect(Math.min(el.x, el.x+el.w), Math.min(el.y, el.y+el.h), Math.abs(el.w), Math.abs(el.h));
  } else if(el.type === "brush"){
    c.lineCap = "round"; c.lineJoin = "round";
    c.beginPath();
    (el.pts||[]).forEach((p, i) => i ? c.lineTo(p.x, p.y) : c.moveTo(p.x, p.y));
    c.stroke();
  } else if(el.type === "cam"){
    // ★ 2026-08-23 机位：🎥 图标随 angle 旋转（拍摄方向）+ 黄色虚线箭头 + 编辑态高亮圈
    // ★ 2026-08-23 用户反馈：🎥 太小 → 8 倍（18→144px）；箭头太细 → 加粗 2 倍（3→6px）；箭头起点/长度/头随 🎥 比例同步放大
    const size = el.size || 100;   // ★ 2026-08-23 用户反馈：144 太大 → 100px
    const len = el.len || 160;                 // ★ 2026-08-23 用户反馈：260 太长 → 160px（箭头终点，自机位点）
    const arrowStart = size / 2 + 12;          // 箭头起点 = 🎥 右缘外
    const editing = !!el.editing;
    c.save();
    c.translate(el.x, el.y);
    c.rotate(el.angle || 0);
    c.strokeStyle = "#eab308"; c.fillStyle = "#eab308";
    c.lineWidth = 6 / z; c.lineCap = "round";
    // 黄色虚线箭头（自 🎥 右缘延伸）
    c.setLineDash([12, 8]);
    c.beginPath(); c.moveTo(arrowStart, 0); c.lineTo(len, 0); c.stroke();
    c.setLineDash([]);
    // 实心箭头头部
    c.beginPath(); c.moveTo(len, 0); c.lineTo(len - 22, -13); c.lineTo(len - 22, 13); c.closePath(); c.fill();
    // 🎥 图标（随旋转指向拍摄方向；8 倍大）
    c.font = `${(size) / z}px "Segoe UI Emoji","Apple Color Emoji","Microsoft YaHei",sans-serif`;
    c.textAlign = "center"; c.textBaseline = "middle";
    c.fillText("🎥", 0, 0);
    // 编辑中：机位高亮圈（闪烁虚线圆，随 🎥 大小）
    if(editing){
      c.globalAlpha = 0.55 + 0.35 * Math.sin(Date.now() / 180);
      c.strokeStyle = "#eab308"; c.lineWidth = 4 / z;
      c.setLineDash([8, 6]);
      c.beginPath(); c.arc(0, 0, size / 2 + 18, 0, Math.PI * 2); c.stroke();
      c.setLineDash([]);
      c.globalAlpha = 1;
    }
    c.restore();
  }
  c.restore();
}

function annRender(){
  if(!annCtx) return;
  const cv = $("ann-canvas");
  annCtx.clearRect(0, 0, cv.width, cv.height);
  annCtx.setTransform(annScale, 0, 0, annScale, 0, 0);
  if(annImg) annCtx.drawImage(annImg, 0, 0, annImg.naturalWidth, annImg.naturalHeight);
  annStack.forEach(drawAnnElement);
  if(annDrag) drawAnnElement(annDrag);
  annCtx.setTransform(1, 0, 0, 1, 0, 0);
  annRenderSel();
}

function annSetTool(t){
  if(annCamEdit){ annCamEdit.editing = false; annCamEdit = null; }   // ★ 切工具退出机位方向编辑
  annTool = t;
  document.querySelectorAll("#ann-tools .ann-tool").forEach(el => el.classList.toggle("active", el.dataset.tool === t));
}

function annColorPick(c){
  annColor = c;
  document.querySelectorAll("#ann-tools .ann-color").forEach(el => el.classList.toggle("sel", el.dataset.c === c));
}

let annSel = null;
let annSelMode = null;
let annSelResize = null;
let annSelOrig = null;

function annSelBox(el){
  if(el.type === "rect"){
    return {x: Math.min(el.x, el.x+el.w), y: Math.min(el.y, el.y+el.h), w: Math.abs(el.w), h: Math.abs(el.h)};
  }
  if(el.type === "circle"){
    const rx = Math.abs(el.w)/2, ry = Math.abs(el.h)/2;
    return {x: el.x + el.w/2 - rx, y: el.y + el.h/2 - ry, w: rx*2, h: ry*2};
  }
  if(el.type === "num"){
    return {x: el.x - 18, y: el.y - 18, w: 36, h: 36};
  }
  if(el.type === "text"){
    const sz = el.size || 22;
    return {x: el.x - 4, y: el.y - sz, w: Math.max(40, (el.text||"").length * sz * 0.95), h: sz * 1.35};
  }
  if(el.type === "brush"){
    let x0=1e9, y0=1e9, x1=-1e9, y1=-1e9;
    (el.pts||[]).forEach(p => { x0=Math.min(x0,p.x); y0=Math.min(y0,p.y); x1=Math.max(x1,p.x); y1=Math.max(y1,p.y); });
    const pad = 8;
    return {x: x0-pad, y: y0-pad, w: Math.max(20, x1-x0+pad*2), h: Math.max(20, y1-y0+pad*2)};
  }
  if(el.type === "cam"){
    // ★ 2026-08-23 机位：选择框覆盖 🎥（100px）+ 方向柄区域
    const sz = (el.size || 100) / 2 + 24;
    return {x: el.x - sz, y: el.y - sz, w: sz * 2, h: sz * 2};
  }
  return {x: el.x-10, y: el.y-10, w: 20, h: 20};
}

function annHitTest(x, y){
  for(let i = annStack.length - 1; i >= 0; i--){
    const el = annStack[i];
    const b = annSelBox(el);
    if(x >= b.x && x <= b.x + b.w && y >= b.y && y <= b.y + b.h) return el;
  }
  return null;
}

function annSelHandleAt(x, y){
  if(!annSel) return null;
  const b = annSelBox(annSel);
  const z = annScale || 1, h = 10 / z;
  const corners = {nw:[b.x, b.y], ne:[b.x+b.w, b.y], sw:[b.x, b.y+b.h], se:[b.x+b.w, b.y+b.h]};
  for(const k in corners){
    const [cx, cy] = corners[k];
    if(Math.abs(x-cx) <= h && Math.abs(y-cy) <= h) return k;
  }
  return null;
}

function annRenderSel(){
  if(!annCtx || !annSel) return;
  const b = annSelBox(annSel);
  const z = annScale || 1;
  annCtx.save();
  annCtx.setTransform(z, 0, 0, z, 0, 0);
  annCtx.strokeStyle = "#8B5CF6";
  annCtx.lineWidth = 1.5 / z;
  annCtx.setLineDash([6/z, 4/z]);
  annCtx.strokeRect(b.x, b.y, b.w, b.h);
  annCtx.setLineDash([]);
  const hs = 7 / z;
  annCtx.fillStyle = "#8B5CF6";
  [[b.x,b.y],[b.x+b.w,b.y],[b.x,b.y+b.h],[b.x+b.w,b.y+b.h]].forEach(([hx,hy]) => {
    annCtx.fillRect(hx - hs/2, hy - hs/2, hs, hs);
  });
  annCtx.restore();
}

function annPos(e){
  const cv = $("ann-canvas");
  const r = cv.getBoundingClientRect();
  return { x: (e.clientX - r.left) * cv.width / r.width / annScale,
           y: (e.clientY - r.top) * cv.height / r.height / annScale };
}

let annSpaceHeld = false;
let annPan = null;
function annBindSpace(){
  document.addEventListener("keydown", e => {
    if(e.code !== "Space") return;
    const m = $("annmodal");
    if(!m || m.style.display !== "flex") return;
    e.preventDefault();
    if(!annSpaceHeld){
      annSpaceHeld = true;
      const cv = $("ann-canvas");
      if(cv) cv.style.cursor = "grab";
    }
  });
  document.addEventListener("keyup", e => {
    if(e.code !== "Space" || !annSpaceHeld) return;
    annSpaceHeld = false;
    const cv = $("ann-canvas");
    if(cv) cv.style.cursor = "crosshair";
    annPan = null;
  });
}

function annMouseDown(e){
  e.preventDefault();
  if(!annImg){ toast("⚠️ 请先选择场景底图（或先生成首帧图）"); return; }
  try{ if(e.pointerId != null) e.currentTarget.setPointerCapture(e.pointerId); }catch(_){}
  if(annSpaceHeld){
    const wrap = $("ann-canvas-wrap");
    annPan = {sx: e.clientX, sy: e.clientY, sl: wrap.scrollLeft, st: wrap.scrollTop};
    const cv = $("ann-canvas");
    if(cv) cv.style.cursor = "grabbing";
    return;
  }
  const p = annPos(e);
  if(annTool === "sel"){
    const h = annSelHandleAt(p.x, p.y);
    if(h && annSel){
      annSelMode = "resize"; annSelResize = h;
      annSelOrig = {box: annSelBox(annSel), size: annSel.size || 22, pts: annSel.pts ? annSel.pts.map(pt => ({...pt})) : null};
      return;
    }
    const hit = annHitTest(p.x, p.y);
    if(hit){
      annSel = hit; annSelMode = "move";
      annSelOrig = {x: hit.x, y: hit.y, w: hit.w, h: hit.h, pts: hit.pts ? hit.pts.map(pt => ({...pt})) : null, px: p.x, py: p.y};
      annRender();
      return;
    }
    annSel = null; annSelMode = null; annRender();
    return;
  }
  if(annTool === "text"){
    const t = prompt("输入标注文字：");
    if(t && t.trim()){ annStack.push({type:"text", x:p.x, y:p.y, text:t.trim(), color:annColor}); annSel = null; annRender(); }
  } else if(annTool === "num"){
    annStack.push({type:"num", x:p.x, y:p.y, n:annNum++, color:annColor}); annSel = null; annRender();
  } else if(annTool === "circle" || annTool === "rect"){
    annDrag = {type:annTool, x:p.x, y:p.y, w:0, h:0, color:annColor};
  } else if(annTool === "brush"){
    annDrag = {type:"brush", pts:[p], color:annColor, lineWidth:4};
  } else if(annTool === "cam"){
    // ★ 2026-08-23 机位：放置 🎥 → 鼠标移动定方向 → 再点确认（黄色虚线箭头定格）
    if(annCamEdit){
      annCamEdit.editing = false; annCamEdit = null;   // 编辑中再点击 = 确认方向
      annRender();
      return;
    }
    let hitCam = null;
    for(let i = annStack.length - 1; i >= 0; i--){
      const el = annStack[i];
      if(el.type === "cam" && Math.hypot(el.x - p.x, el.y - p.y) < ((el.size || 100) / 2 + 10)){ hitCam = el; break; }
    }
    if(hitCam){ hitCam.editing = true; annCamEdit = hitCam; annRender(); return; }
    const cam = {type:"cam", x:p.x, y:p.y, angle:0, len:160, size:100, color:"#eab308", editing:true};
    annStack.push(cam); annCamEdit = cam; annSel = null;
    annRender();
  }
}

function annMouseMove(e){
  if(annPan){
    const wrap = $("ann-canvas-wrap");
    wrap.scrollLeft = annPan.sl - (e.clientX - annPan.sx);
    wrap.scrollTop  = annPan.st - (e.clientY - annPan.sy);
    return;
  }
  if(annCamEdit){
    // ★ 2026-08-23 机位方向实时跟随鼠标（🎥 转动指向鼠标）
    const p = annPos(e);
    annCamEdit.angle = Math.atan2(p.y - annCamEdit.y, p.x - annCamEdit.x);
    annRender();
    return;
  }
  if(annSelMode && annSelOrig){
    const p = annPos(e);
    if(annSelMode === "move"){
      const dx = p.x - annSelOrig.px, dy = p.y - annSelOrig.py;
      if(annSel.type === "brush"){
        annSel.pts = annSelOrig.pts.map(pt => ({x: pt.x + dx, y: pt.y + dy}));
      } else {
        annSel.x = annSelOrig.x + dx; annSel.y = annSelOrig.y + dy;
      }
      annRender();
      return;
    }
    if(annSelMode === "resize"){
      annSelResizeEl(p);
      annRender();
      return;
    }
  }
  if(!annDrag) return;
  const p = annPos(e);
  if(annDrag.type === "brush"){ annDrag.pts.push(p); annRender(); }
  else { annDrag.w = p.x - annDrag.x; annDrag.h = p.y - annDrag.y; annRender(); }
}

function annSelResizeEl(p){
  const el = annSel, o = annSelOrig;
  if(!o) return;
  if(el.type === "rect" || el.type === "circle"){
    const bx = o.box.x, by = o.box.y, bw = o.box.w, bh = o.box.h;
    let nx = bx, ny = by, nw = bw, nh = bh;
    if(annSelResize === "se"){ nw = p.x - bx; nh = p.y - by; }
    else if(annSelResize === "nw"){ nx = p.x; ny = p.y; nw = bx + bw - p.x; nh = by + bh - p.y; }
    else if(annSelResize === "ne"){ ny = p.y; nw = p.x - bx; nh = by + bh - p.y; }
    else if(annSelResize === "sw"){ nx = p.x; nw = bx + bw - p.x; nh = p.y - by; }
    nw = Math.max(8, nw); nh = Math.max(8, nh);
    el.x = nx; el.y = ny; el.w = nw; el.h = nh;
  } else if(el.type === "text" || el.type === "num"){
    const oc = {x: o.box.x + o.box.w/2, y: o.box.y + o.box.h/2};
    const od = Math.max(20, Math.hypot(o.box.w, o.box.h) / 2 || 20);
    const nd = Math.max(10, Math.hypot(p.x - oc.x, p.y - oc.y));
    el.size = Math.max(8, Math.min(300, Math.round(o.size * nd / od)));
  } else if(el.type === "brush"){
    const bx = o.box.x, by = o.box.y, bw = o.box.w, bh = o.box.h;
    const oc = {x: bx + bw/2, y: by + bh/2};
    const od = Math.max(20, Math.hypot(bw, bh) / 2);
    const nd = Math.max(10, Math.hypot(p.x - oc.x, p.y - oc.y));
    const s = nd / od;
    el.pts = o.pts.map(pt => ({x: oc.x + (pt.x - oc.x) * s, y: oc.y + (pt.y - oc.y) * s}));
  }
}

function annMouseUp(){
  if(annPan){ annPan = null; const cv = $("ann-canvas"); if(cv) cv.style.cursor = "grab"; return; }
  if(annSelMode){ annSelMode = null; annSelResize = null; annSelOrig = null; return; }
  if(!annDrag) return;
  if((annDrag.type === "circle" || annDrag.type === "rect") && Math.abs(annDrag.w) < 5 && Math.abs(annDrag.h) < 5){
    annDrag = null; annRender(); return;
  }
  annStack.push(annDrag);
  annDrag = null;
  annRender();
}

function annUndo(){
  if(!annStack.length){ toast("没有可撤回的标注"); return; }
  annStack.pop();
  if(annSel && !annStack.includes(annSel)) annSel = null;
  annRender();
}

// ---- 场景选择（底图）----
// ★ 2026-08-22 完全对齐参考图窗口（refpCollect/renderRefGrid）卡片结构：图片 110px + 名称一行，无第二行标签（防行重叠遮挡）
function annOpenScenePicker(){
  const scenes = (P.xiatang?.scenes) || [];
  const list = $("ann-scene-list");
  if(!scenes.length){ toast("⚠️ 暂无场景资产"); return; }
  const t = Date.now();
  const imgBox = (src) => `<div style="height:110px;background:#f0f0f0;display:flex;align-items:center;justify-content:center;overflow:hidden;flex-shrink:0"><img src="${esc(src)}?t=${t}" loading="lazy" style="width:100%;height:100%;object-fit:cover;display:block" onerror="this.parentNode.innerHTML='<span style=font-size:12px;color:var(--mut)>图缺失</span>'"></div>`;
  const noImgBox = `<div style="height:110px;background:#f0f0f0;display:flex;align-items:center;justify-content:center;flex-shrink:0"><span style="font-size:22px;color:#bbb">🏯</span></div>`;
  const nameRow = (nm) => `<div style="font-size:12px;color:#475569;padding:6px 6px 8px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;flex-shrink:0;background:#fff">${esc(nm)}</div>`;
  list.innerHTML = scenes.map(s => {
    const views = Object.keys(s.views || {}).filter(v => s.views[v]);
    const dists = Object.keys(s.dists || {}).filter(k => s.dists[k]);
    const mainCard = `<div style="width:140px;border:1px solid var(--line);border-radius:8px;overflow:hidden;cursor:${s.image?'pointer':'not-allowed'};opacity:${s.image?1:.45};background:#fff" onclick="${s.image?`annPickScene('${esc(s.name)}')`:'void 0'}" title="${esc(s.name)}（主图）">
      ${s.image ? imgBox(s.image) : noImgBox}
      ${nameRow(s.name)}
    </div>`;
    const viewCards = views.map(v => {
      const src = s.views[v];
      return `<div style="width:140px;border:1px solid #c7d2fe;border-radius:8px;overflow:hidden;cursor:pointer;background:#fff" onclick="annPickScene('${esc(s.name)}','${v}')" title="${esc(s.name)}·${v}（多视角）">
        ${imgBox(src)}
        ${nameRow(s.name + "·" + v)}
      </div>`;
    }).join("");
    const distCards = dists.map(k => {
      const src = s.dists[k];
      const _dl = String(k).split("|");
      const _nm = (s.name + "·" + (_dl[0]||"主图") + "·" + (_dl[1]||""));
      return `<div style="width:140px;border:1px solid #a7f3d0;border-radius:8px;overflow:hidden;cursor:pointer;background:#fff" onclick="annPickScene('${esc(s.name)}','','${esc(k)}')" title="${esc(_nm)}（视距）">
        ${imgBox(src)}
        ${nameRow(_nm)}
      </div>`;
    }).join("");
    // ★ 2026-08-23 平面布局 / 线稿 也作为底图可选（用户反馈缺失）
    const planCard = (s.plan && s.plan_ready)
      ? `<div style="width:140px;border:1px solid #bfdbfe;border-radius:8px;overflow:hidden;cursor:pointer;background:#fff" onclick="annPickScene('${esc(s.name)}','','','plan')" title="${esc(s.name)}·平面布局">
        ${imgBox(s.plan)}
        ${nameRow(s.name + "·平面布局")}
      </div>` : "";
    const sketchCard = (s.plan_sketch && s.plan_sketch_ready)
      ? `<div style="width:140px;border:1px solid #e2e8f0;border-radius:8px;overflow:hidden;cursor:pointer;background:#fff" onclick="annPickScene('${esc(s.name)}','','','plan_sketch')" title="${esc(s.name)}·线稿">
        ${imgBox(s.plan_sketch)}
        ${nameRow(s.name + "·线稿")}
      </div>` : "";
    return mainCard + viewCards + distCards + planCard + sketchCard;
  }).join("");
  $("ann-scene-layer").style.display = "flex";
}

function annCloseScenePicker(){
  const l = $("ann-scene-layer"); if(l) l.style.display = "none";
}

function annPickScene(sceneName, view, distKey, kind){
  const scenes = (P.xiatang?.scenes) || [];
  const s = scenes.find(x => x.name === sceneName);
  if(!s){ toast("⚠️ 场景不存在"); annCloseScenePicker(); return; }
  let img;
  if(kind === "plan") img = s.plan;
  else if(kind === "plan_sketch") img = s.plan_sketch;
  else img = distKey ? (s.dists||{})[distKey] : (view ? (s.views||{})[view] : s.image);
  if(!img){ toast(distKey ? "⚠️ 该视距图缺失" : (kind === "plan" ? "⚠️ 平面布局缺失" : (kind === "plan_sketch" ? "⚠️ 线稿缺失" : (view ? "⚠️ 该视角图缺失" : "⚠️ 该场景暂无图片")))); annCloseScenePicker(); return; }
  if((annStack.length > 0 || annImg) && !confirm("确认覆盖现有标注？选择新场景将替换当前图片并清空已标注内容。")) return;
  annStack = []; annNum = 1;
  annCloseScenePicker();
  annLoadImage(img + "?t=" + Date.now());
}

// ---- 保存（★ 适配虾镜：写 shot.annotated_image）----
async function annSave(){
  if(!annShot){ toast("⚠️ 无当前镜头"); return; }
  if(!annImg){ toast("⚠️ 请先选择场景底图（或先生成首帧图）"); return; }
  const cv = $("ann-canvas");
  const dataUrl = cv.toDataURL("image/png");
  try{
    const r = await fetch("/save-annotation", {method:"POST", headers:{"Content-Type":"application/json"},
      body: JSON.stringify({shot_number: annShot.shot_number, ep: annEp, data_url: dataUrl})});
    const j = await r.json();
    if(j.ok){
      annShot.annotated_image = j.image;   // 同步内存 → 制作页标注位即时显示
      toast("✅ 画面标注已保存");
      closeAnnModal();
      if(curSection === "xiajing") rerenderCurrent();
    } else {
      toast("❌ 保存失败：" + (j.error || "未知错误"));
    }
  }catch(e){
    toast("❌ 保存失败：网络错误");
  }
}
