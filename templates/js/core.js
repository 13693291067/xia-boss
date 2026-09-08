// 顶层：先声明所有被全局引用的常量（避免后续代码 TDZ）。
// 注意：const $ 在下方定义，这里不能调用 $()——mode-badge 设置放到 $ 定义后。
const IS_SERVER = location.protocol === "http:" || location.protocol === "https:";

// ★ 2026-08-21 防缓存：资产图片 URL 统一追加时间戳（上传/生成同名文件时避免浏览器缓存旧图）
function imgSrc(p){
  const s = String(p||"");
  if(!s || s.startsWith("data:")) return s;
  return s + (s.includes("?") ? "&" : "?") + "t=" + Date.now();
}

function openZoom(src, cap){
  if(!src) return;
  var m = $("zoom"); var img = $("zoom-img"); var c = $("zoom-cap");
  img.src = src;
  c.textContent = cap || "";
  m.classList.add("open");
}
function closeZoom(){ $("zoom").classList.remove("open"); }
document.addEventListener("keydown", function(e){ if(e.key === "Escape"){ closeZoom(); closeHist(); closeGen(); closeRefPicker(); closeScriptEditor(); } });


// ===== 路由 =====
function renderSection(name){
  curSection = name;
  const c = $("content");
  if(name==="xialiao"){ c.innerHTML = renderXialiao(); kgInit(); }
  else if(name==="xiage"){ c.innerHTML = renderXiage(); bindXiage(); }
  else if(name==="xiatang"){ c.innerHTML = renderXiatang(); bindXiatang(); }
  else if(name==="xiajing"){
    if(xjCurEp){ c.innerHTML = renderXiajing(); bindXiajing(); }
    else { c.innerHTML = renderXiajingGrid(); bindXiajingGrid(); }
  }
  else if(name==="tingfeng"){ c.innerHTML = renderTingFeng(); bindTingFeng(); }   // ★ 2026-09-01 听风电影工作台
  else if(name==="xiaju"){ c.innerHTML = renderXiaju(); bindXiaju(); }             // ★ 2026-09-05 虾剧·剧本输出工作台
  else if(name==="agent"){ c.innerHTML = renderAgent(); bindAgent(); }
  try { window.scrollTo(0, 0); } catch(e){}
}

function bindXiatang(){
  document.querySelectorAll("#xiatang-tabs .t").forEach(el => {
    el.addEventListener("click", () => {
      xtCurTab = el.dataset.tab;
      xtCurSel = null;
      const c = $("content"); c.innerHTML = renderXiatang(); bindXiatang();
    });
  });
  document.querySelectorAll(".role-list-item").forEach(el => {
    el.addEventListener("click", () => {
      xtCurSel = el.dataset.name;
      const c = $("content"); c.innerHTML = renderXiatang(); bindXiatang();
    });
  });
  document.querySelectorAll(".scene-list-item").forEach(el => {
    el.addEventListener("click", () => {
      xtCurSel = el.dataset.sname || el.dataset.kname;   // ★ data-sname=场景 / data-kname=关键场景
      const c = $("content"); c.innerHTML = renderXiatang(); bindXiatang();
    });
  });
}

function bindXiajing(){
  // 顶部 Tab 切换
  document.querySelectorAll('.tabs .t[data-tab]').forEach(el => {
    el.addEventListener("click", () => {
      xjCurTab = el.dataset.tab;
      xjCurBeat = null;
      const c = $("content"); c.innerHTML = renderXiajing(); bindXiajing();
    });
  });
  // 网格卡片点击切 Beat（草图/渲染图/视频 Tab）
  document.querySelectorAll('[data-sbeat],[data-rbeat],[data-vbeat]').forEach(el => {
    el.addEventListener("click", () => {
      xjCurBeat = +el.dataset.sbeat || +el.dataset.rbeat || +el.dataset.vbeat;
      const c = $("content"); c.innerHTML = renderXiajing(); bindXiajing();
    });
  });
}

function renderBeatDetail(){ return ''; /* 保留以兼容旧调用 */ }

function bindXiajingGrid(){
  document.querySelectorAll(".ep-card").forEach(el => {
    el.addEventListener("click", () => {
      xjCurEp = +el.dataset.ep;
      const c = $("content"); c.innerHTML = renderXiajing(); bindXiajing();
    });
  });
}

