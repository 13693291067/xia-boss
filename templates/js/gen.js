// ===== AI 生成图片弹窗 =====
// ★ 2026-08-23 标注提示词固定列表（首帧/尾帧弹窗下拉框；[标题, 内容]，内容可由设置页持久化配置覆盖）
const GEN_ANN_TAGS = [
  ["人物位置", "人物[]在图红框的位置"],
  ["机位方向", "画面标注有🎥机位标记与黄色虚线箭头指示拍摄方向，构图按箭头指向取景，镜头位置与朝向以机位标记为准。"],
  ["景别构图", "按画面标注的框选与景别要求取景，保持主体位置与画面留白关系。"],
  ["标注文字", "画面标注中的文字为补充说明，生图时按文字描述调整画面细节。"],
  ["忽略标注", "忽略画面标注中的机位箭头与框选标记，仅按提示词本身构图。"],
];
let genAnnTags = null;   // 运行时标注提示词（服务端持久化覆盖；null=未加载，用默认）
// ★ 2026-08-23 选择标注提示词 → 插入提示词框当前光标位置
function genInsertAnnTag(sel){
  const v = sel.value;
  sel.selectedIndex = 0;
  if(!v) return;
  const ta = $("gen-prompt");
  const s = ta.selectionStart != null ? ta.selectionStart : ta.value.length;
  const e = ta.selectionEnd != null ? ta.selectionEnd : ta.value.length;
  ta.value = ta.value.slice(0, s) + v + ta.value.slice(e);
  ta.focus();
  const pos = s + v.length;
  ta.setSelectionRange(pos, pos);
}
// ★ 2026-08-23 标注提示词设置（持久化到服务端 ann_tags_config.json）
function loadAnnTags(){
  fetch("/ann-tags").then(r => r.json()).then(j => {
    if(j && j.ok && Array.isArray(j.tags) && j.tags.length) genAnnTags = j.tags;
  }).catch(() => {});
}
function openAnnTagsSettings(){
  const list = $("anntags-list");
  const tags = (genAnnTags || GEN_ANN_TAGS);
  list.innerHTML = tags.map((t, i) => `
    <div id="anntags-row-${i}" style="display:flex;gap:8px;margin-bottom:8px;align-items:center">
      <input id="anntags-t-${i}" value="${esc(t[0])}" placeholder="标题" style="width:110px;box-sizing:border-box;border:1px solid var(--line);border-radius:6px;padding:6px 8px;font-size:12px">
      <textarea id="anntags-c-${i}" rows="2" placeholder="插入内容（插入到提示词光标处，可多行）" style="flex:1;min-width:0;box-sizing:border-box;border:1px solid var(--line);border-radius:6px;padding:6px 8px;font-size:12px;font-family:inherit;resize:vertical;line-height:1.5">${esc(t[1])}</textarea>
      <button class="btn-secondary" style="font-size:11px;padding:3px 8px;color:#b91c1c" onclick="annTagsDelRow(${i})">🗑</button>
    </div>`).join("");
  $("anntags").classList.add("open");
}
function closeAnnTagsSettings(){ const m = $("anntags"); if(m) m.classList.remove("open"); }
function annTagsAddRow(){
  const list = $("anntags-list");
  const idx = list.children.length;
  const div = document.createElement("div");
  div.id = "anntags-row-" + idx;
  div.style.cssText = "display:flex;gap:8px;margin-bottom:8px;align-items:center";
  div.innerHTML = `<input id="anntags-t-${idx}" placeholder="标题" style="width:110px;box-sizing:border-box;border:1px solid var(--line);border-radius:6px;padding:6px 8px;font-size:12px">
    <textarea id="anntags-c-${idx}" rows="2" placeholder="插入内容（插入到提示词光标处，可多行）" style="flex:1;min-width:0;box-sizing:border-box;border:1px solid var(--line);border-radius:6px;padding:6px 8px;font-size:12px;font-family:inherit;resize:vertical;line-height:1.5"></textarea>
    <button class="btn-secondary" style="font-size:11px;padding:3px 8px;color:#b91c1c" onclick="annTagsDelRow(${idx})">🗑</button>`;
  list.appendChild(div);
}
function annTagsDelRow(idx){
  const row = document.getElementById("anntags-row-" + idx);
  if(row) row.remove();
}
function annTagsSave(){
  const list = $("anntags-list");
  const rows = list.children;
  const tags = [];
  for(let i = 0; i < rows.length; i++){
    const t = rows[i].querySelector("input[id^='anntags-t-']");
    const c = rows[i].querySelector("textarea[id^='anntags-c-']");
    if(t && c && String(c.value || "").trim()) tags.push([String(t.value || "").trim(), String(c.value).trim()]);
  }
  if(!tags.length){ toast("⚠️ 请至少保留一条内容非空的标注提示词"); return; }
  fetch("/ann-tags", {method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify({tags})})
    .then(r => r.json()).then(j => {
      if(j.ok){
        genAnnTags = tags;
        closeAnnTagsSettings();
        toast("✅ 标注提示词已保存（" + tags.length + " 条）");
      } else toast("❌ " + (j.error || "保存失败"));
    }).catch(() => toast("❌ 保存请求失败"));
}
const GEN_DEFAULT_MODELS = ["gpt-image-2", "gpt-image-1", "nano-banana", "seedream", "midjourney"];
const GEN_DEFAULT_SIZES = [
  {label:"960x1280（3:4 竖版·主图默认）", value:"960x1280"},
  {label:"1024x1536（2:3 竖版）", value:"1024x1536"},
  {label:"1024x1024（1:1 方图）", value:"1024x1024"},
  {label:"1536x1024（3:2 横版）", value:"1536x1024"},
  {label:"1024x2048（1:2 竖版长图）", value:"1024x2048"},
  {label:"2048x2048（2K 方图）", value:"2048x2048"},
  {label:"1280x720（16:9 横屏）", value:"1280x720"},
  {label:"720x1280（9:16 小竖屏）", value:"720x1280"},
  {label:"auto", value:"auto"},
];
let genState = {cat:"", name:"", defaultPrompt:"", model:"", size:"", refImages:[], channelId:"", channels:[], autoRef:null, ep:1};
// ★ 2026-08-24 生视频模型选择（seedance / h3），全局，供 buildStoryVideoPrompt 路由
let genVideoModel = "seedance";
let genMainLine = "tingfeng";   // ★ 2026-09-01 分镜主力线（tingfeng 听风 / xiajing 虾镜）

async function openGenModal(cat, name, prompt, ep, promptCn){
  genState = {cat: cat, name: String(name||""), defaultPrompt: String(prompt||""), defaultPromptCn: String(promptCn||""), model:"", size:"", refImages:[], channelId:"", channels:[], ep: Number(ep)||1};
  $("gen-prompt").value = genState.defaultPrompt;
  // ★ 2026-09-06b 双语：弹窗顶部只读"中文参考稿"折叠区（理解层，不进生图；策略 B 中文只读）
  const _cnw = $("gen-prompt-cn-wrap");
  if(_cnw){
    if(genState.defaultPromptCn){
      _cnw.style.display = "";
      const _cnb = $("gen-prompt-cn-body");
      if(_cnb) _cnb.innerHTML = esc(genState.defaultPromptCn);
    } else { _cnw.style.display = "none"; }
  }
  // ★ 2026-08-23 标注提示词下拉框：仅首帧/尾帧显示（固定提示词，选择后插入提示词框光标处；内容优先用服务端持久化配置）
  const _atw = $("gen-ann-tag-wrap");
  if(_atw){
    if(cat === "firstframe" || cat === "tailframe"){
      _atw.style.display = "inline-flex";
      const _sel = $("gen-ann-tag");
      const _tags = genAnnTags || GEN_ANN_TAGS;
      _sel.innerHTML = '<option value="">选择固定提示词，插入光标处…</option>' + _tags.map(t => `<option value="${esc(t[1])}">${esc(t[0])}</option>`).join("");
    } else {
      _atw.style.display = "none";
    }
  }
  // 身份图锁脸：自动读取主图作为 ref[0]，并展示在参考图列表（不可移除）
  genState.autoRef = null;
  const _lh = $("gen-lock-hint");
  const _ob = $("gen-outfit-btn");
  if(_lh) _lh.style.display = "none";
  // ★ 2026-08-21 服装参考按钮：仅身份图显示（身份定妆照支持上传服装参考图）
  if(_ob) _ob.style.display = (cat === "identity") ? "" : "none";
  if(cat === "identity" && String(name||"").includes("-")){
    const _bn = String(name).split("-", 1)[0];
    const _path = findCurrentMainImage(_bn);   // ★ 当前主图(支持 set-current 换名)
    fetch(_path + "?t=" + Date.now(), {method:"HEAD"}).then(r => {
      if(!r.ok) return;
      if(_lh) _lh.style.display = "block";
      fetchMainRefAsDataUrl(_path).then(durl => {
        if(durl){ genState.autoRef = {name: _bn + ".png（主图·锁脸）", dataUrl: durl}; renderRefPreview(); }
      });
    }).catch(() => {});
  }
  // ★ 2026-08-20 调度图：自动垫当前 Beat 所属场景的线稿（plan_sketch）作为参考图
  if(cat === "blocking"){
    const _bn = parseInt(String(name||"").replace(/^beat/i,""), 10);
    const _ep = getCurEp();
    const _b = (_ep?.beats||[]).find(x => x.beat_number === _bn);
    const _sn = String(_b?.scene_name || "").replace(/^\d+-\d+\s*/, "");
    const _sc = (P.xiatang?.scenes||[]).find(s => s.name === _sn);
    if(_sc && _sc.plan_sketch){
      fetchAsDataUrl(_sc.plan_sketch).then(durl => {
        genState.refImages.push({name: "线稿·" + _sc.name, dataUrl: durl});
        renderRefPreview();
      }).catch(() => {});
    }
  }
  // ★ 2026-08-22 首帧/尾帧：自动注入角色/场景资产引用（提示词开头插入「角色名=图1 场景名=图2」+ 换行，并自动垫参考图）
  if(cat === "firstframe" || cat === "tailframe"){
    const _sn = String(name||"").replace(/^shot/i,"").trim();
    const _ep = getCurEp();
    // ★ 2026-08-22 修复：必须用编辑稿优先（与页面显示一致）——原 _ep.shots 是原始数据，编辑稿改过的出场人物会漏引用
    const _shotsArr = (_ep && (_ep.edited_shots || _ep.shots)) || [];
    const _sht = _shotsArr.find(s => String(s.shot_number) === _sn);
    if(_sht){
      const _chText = String(_sht.characters||"");
      // ★ 2026-08-22 角色匹配：①文本资产名/别名包含匹配；②★ CH 编号解析（"CH-01/02" → ep.ch_map → 角色资产名，背影/远景无名字时也能锁定角色资产）
      const _chs = (P.xiatang?.characters||[]).filter(c => {
        if(!c.name) return false;
        if(_chText.includes(c.name)) return true;
        if((c.aliases||[]).some(a => a && _chText.includes(a))) return true;
        return false;
      });
      // ★ 2026-08-22 CH 编号解析（"CH-01/02" 复合编号也要解析 → ep.ch_map → 角色资产名，远景/背影无名字也能锁定角色资产）
      const _chNums = [];
      const _re = /CH[- ]?(\d+)((?:\/\d+)*)/g;
      let _mm;
      while((_mm = _re.exec(_chText))){
        _chNums.push(_mm[1]);
        (_mm[2] || "").split("/").slice(1).forEach(_n => { if(_n) _chNums.push(_n); });
      }
      _chNums.forEach(_n => {
        const _cn = (_ep.ch_map || {})[_n];
        if(_cn && !_chs.some(c => c.name === _cn)){
          const _c = (P.xiatang?.characters||[]).find(x => x.name === _cn);
          if(_c) _chs.push(_c);
        }
      });
      // ★ 2026-08-22 镜头全文本（身份判定信号源）：角色/画面/动作/台词/叙事
      const _fullText = [_chText, _sht.visual, _sht.action, _sht.dialogue, _sht.narrative].filter(Boolean).join(" ");
      const _scName = _sht.scene_name || (_ep.scene_map || {})[_sht.scene_tag] || "";
      const _sc = (P.xiatang?.scenes||[]).find(s => s.name && (_scName === s.name || _scName.includes(s.name)));
      const _shotText = [_sht.visual, _sht.action, _sht.characters, _sht.narrative].filter(Boolean).join(" ");
      // 资产候选（角色→场景→道具→画面标注）；每个带多张候选图，逐个试加载
      const _cands = [];
      _chs.slice(0,4).forEach(c => {
        const _idn = pickIdentityByChapter(c, _sht.chapter) || pickIdentityByText(c, _fullText);   // ★ 先按当前剧情章节选身份
        const imgs = [];
        if(_idn && _idn.sheet_ready && _idn.sheet_image) imgs.push(_idn.sheet_image);   // 四视图优先
        if(_idn && _idn.image) imgs.push(_idn.image);                                    // 身份定妆照
        if(c.image) imgs.push(c.image);                                                  // 角色主图
        _cands.push({name: c.name, imgs});
      });
      if(_sc) _cands.push({name: _sc.name, imgs: [_sc.image].filter(Boolean)});
      (P.xiatang?.props||[]).forEach(p => {
        if(p.name && p.image && _shotText.includes(p.name)) _cands.push({name: p.name, imgs: [p.image]});
      });
      if(_sht.annotated_image) _cands.push({name: "画面标注", imgs: [_sht.annotated_image]});
      // ★ 原则：存在才引用——逐个试加载，取第一个能加载的图；全加载不到=不存在→不引用、不占图号
      (async () => {
        const _refs = [];
        for(const e of _cands){
          for(const img of e.imgs){
            const durl = await fetchAsDataUrl(img);
            if(durl){ _refs.push({name: e.name, dataUrl: durl}); break; }
          }
        }
        if(!_refs.length) return;
        const _names = _refs.map((r, i) => r.name + "=图" + (i + 1)).join(" ");
        const _ta = $("gen-prompt");
        const _cur = String(_ta.value || genState.defaultPrompt || "");
        if(!_cur.startsWith(_names)){ genState.defaultPrompt = _names + "\n\n" + _cur; _ta.value = genState.defaultPrompt; }
        genState.refImages = _refs.map((r, i) => ({name: r.name + "=图" + (i + 1), dataUrl: r.dataUrl, autoRef: true}));
        renderRefPreview();
      })();
    }
  }
  genRefClear();
  const rs = $("gen-result"); rs.style.display = "none"; rs.innerHTML = "";
  const mSel = $("gen-model"); mSel.innerHTML = "";
  const sSel = $("gen-size"); sSel.innerHTML = "";
  // 每次打开都拉取最新渠道配置（设置面板刚保存的立即生效）
  try{
    const r = await fetch("/gen-config");
    const cfg = await r.json();
    if(cfg && cfg.ok){
      genState.channels = cfg.channels || [];
      genState.sizes  = cfg.sizes  || GEN_DEFAULT_SIZES;
      genState.defaultSizes = cfg.default_sizes || {...DEFAULT_SIZE_MAP_FE};   // ★ 各类别默认尺寸（⚙ 设置可改）
    } else {
      genState.channels = []; genState.sizes = GEN_DEFAULT_SIZES; genState.defaultSizes = {...DEFAULT_SIZE_MAP_FE};
    }
  } catch(e){
    genState.channels = []; genState.sizes = GEN_DEFAULT_SIZES; genState.defaultSizes = {...DEFAULT_SIZE_MAP_FE};
  }
  const channels = genState.channels;
  const sizes  = genState.sizes;
  // 模型下拉 = 所有渠道模型聚合（label 带渠道名；优先选第一个已配置渠道的模型）
  let firstOpt = null;
  for(let ci=0; ci<channels.length; ci++){
    const ch = channels[ci];
    const chLabel = ch.name || ch.id || ("渠道" + (ci+1));
    for(const md of (ch.models || [])){
      const modelName = _modelName(md);
      const o = document.createElement("option");
      o.value = String(ch.id + "::" + modelName);
      o.text = String(modelName + "（" + chLabel + "）");
      if(ch.configured && !firstOpt) firstOpt = o;
      mSel.add(o);
    }
  }
  if(!mSel.options.length){
    const o = document.createElement("option"); o.value = "default::gpt-image-2"; o.text = "gpt-image-2（默认）";
    mSel.add(o);
  }
  if(firstOpt) mSel.value = firstOpt.value;
  // ★ 各类别默认尺寸（⚙ 设置可改）：角色主图/身份图/场景/道具 + 草图·首帧（sketch/frame/firstframe/tailframe/tingfeng 查 sketch_frame）
  // ★ 2026-08-22 修复：制作页首帧/尾帧生成的类别是 firstframe/tailframe（不是 frame），原映射查不到设置值 → 回退默认第一项
  // ★ 2026-09-03 用户拍板：听风故事板（tingfeng）默认尺寸 = 设置里「草图·首帧」（sketch_frame）的配置值
  const catKey = (cat === "sketch" || cat === "frame" || cat === "firstframe" || cat === "tailframe" || cat === "tingfeng") ? "sketch_frame" : cat;
  const defSize = (genState.defaultSizes && genState.defaultSizes[catKey]) || sizeDefaultMap[catKey] || null;
  for(let i=0;i<sizes.length;i++){
    const sz = sizes[i];
    const o = document.createElement("option"); o.value = String(sz.value); o.text = String(sz.label);
    if(defSize ? (String(sz.value) === defSize) : (i===0)) o.selected = true;
    sSel.add(o);
  }
  // 兜底：类别默认尺寸不在列表时回退第 1 项
  if(defSize && sSel.value !== defSize && sSel.options.length) sSel.selectedIndex = 0;
  $("gen-send").disabled = false;
  $("gen-send").textContent = "✨ 发送生成";
  $("gen").classList.add("open");
}
function closeGen(){ $("gen").classList.remove("open"); }
function resetGenPrompt(){ $("gen-prompt").value = genState.defaultPrompt || ""; }

// ★ 2026-08-20 保存提示词：当前输入保存到该资产/Beat（下次打开/生成用修改后的版本）
async function savePrompt(){
  const prompt = ($("gen-prompt").value||"").trim();
  if(!prompt){ toast("提示词为空，无法保存"); return; }
  const cat = genState.cat, nm = genState.name;
  if(!cat || !nm){ toast("⚠️ 无法定位当前资产/Beat"); return; }
  try{
    const r = await fetch("/save-prompt", {method:"POST", headers:{"Content-Type":"application/json"},
      body: JSON.stringify({category: cat, name: nm, prompt: prompt, ep: genState.ep || 1})});
    const j = await r.json();
    if(j.ok){
      // 内存同步：立即生效（不刷新页面）
      const base = nm.replace(/\.[^.]+$/, "");
      if(cat === "character"){
        (P.xiatang?.characters||[]).forEach(c => { if(c.name === base) c.prompt = prompt; });
      } else if(cat === "identity"){
        (P.xiatang?.characters||[]).forEach(c => (c.identities||[]).forEach(id => {
          if(c.name + "-" + id.name === base || id.name === base) id.prompt = prompt;
        }));
      } else if(cat === "scene"){
        (P.xiatang?.scenes||[]).forEach(s => { if(s.name === base) s.prompt = prompt; });
      } else if(cat === "prop"){
        (P.xiatang?.props||[]).forEach(p => { if(p.name === base) p.prompt = prompt; });
      } else if(["sketch","blocking","frame"].includes(cat)){
        const key = cat === "frame" ? "firstframe_prompt" : "blocking_prompt";
        const bn = parseInt(nm.replace(/^beat/i,""), 10);
        (P.xiajing?.episodes||[]).forEach(ep => {
          if(ep.number !== (genState.ep||1)) return;
          (ep.beats||[]).forEach(b => { if(b.beat_number === bn) b[key] = prompt; });
        });
      }
      genState.defaultPrompt = prompt;   // 恢复默认也指向新值
      toast("✅ 提示词已保存（下次打开/生成用此版本）");
    } else {
      toast("❌ 保存失败：" + (j.error || "未知错误"));
    }
  }catch(e){ toast("❌ 保存失败：网络错误"); }
}
function genRefPicked(inp){
  const files = inp.files ? Array.from(inp.files) : [];
  if(!files.length) return;
  const MAX_REF = 9;
  const left = MAX_REF - genState.refImages.length;
  if(left <= 0){ toast("参考图最多 9 张，请先移除部分再添加"); inp.value = ""; return; }
  const todo = files.slice(0, left);
  if(files.length > left) toast("参考图最多 9 张，已自动截取前 " + left + " 张");
  let done = 0;
  todo.forEach(f => {
    const rd = new FileReader();
    rd.onload = function(e){
      const b64 = String(e.target.result).split(",")[1] || "";
      genState.refImages.push({name: f.name, b64: b64, dataUrl: e.target.result});
      done++;
      if(done === todo.length){
        inp.value = "";
        renderRefPreview();
        toast("已添加参考图 " + genState.refImages.length + "/9");
      }
    };
    rd.readAsDataURL(f);
  });
}
function renderRefPreview(){
  const auto = genState.autoRef;
  const list = genState.refImages || [];
  const pv = $("gen-ref-preview");
  const clear = $("gen-ref-clear");
  const cnt = $("gen-ref-count");
  const total = (auto ? 1 : 0) + list.length;
  if(!total){
    pv.style.display = "none"; pv.innerHTML = "";
    clear.style.display = "none";
    if(cnt) cnt.textContent = "";
    return;
  }
  pv.style.display = "flex";
  clear.style.display = "";
  if(cnt) cnt.textContent = "（" + total + "/9）";
  let html = "";
  if(auto){
    html += `<div style="position:relative;border:2px solid #C4B5FD;border-radius:8px;overflow:hidden;width:110px;background:#F3E8FF" title="自动锁脸主图（不可移除）">
      <img src="${auto.dataUrl}" style="width:100%;height:80px;object-fit:cover;display:block">
      <div style="font-size:12px;color:#7C3AED;padding:3px 5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">🔒 ${esc(auto.name)}</div>
      <div style="position:absolute;top:2px;left:2px;background:rgba(29,78,216,.85);color:#fff;border-radius:6px;font-size:10px;padding:1px 5px">锁脸</div>
    </div>`;
  }
  html += list.map((it, i) => `
    <div style="position:relative;border:${it.isOutfit?'2px solid #d4af6a':'1px solid var(--line)'};border-radius:8px;overflow:hidden;width:110px;background:#fff" title="${it.isOutfit?'服装参考图（只取服装，忽略模特/场景/光线）':'参考图'}">
      <img src="${it.dataUrl}" style="width:100%;height:80px;object-fit:cover;display:block">
      <div style="font-size:12px;color:${it.isOutfit?'#b45309':'#475569'};padding:3px 5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${it.isOutfit?'👗 服装参考':'🖼 '}${esc(it.name)}</div>
      <div style="position:absolute;top:2px;right:2px;width:18px;height:18px;line-height:16px;text-align:center;background:rgba(15,23,42,.6);color:#fff;border-radius:50%;font-size:12px;cursor:pointer" onclick="event.stopPropagation();genRefRemove(${i})" title="移除">×</div>
    </div>`).join("");
  pv.innerHTML = html;
}
function genRefRemove(idx){
  const wasOutfit = genState.refImages[idx] && genState.refImages[idx].isOutfit;
  genState.refImages.splice(idx, 1);
  renderRefPreview();
  // ★ 2026-08-21 移除服装参考图后若无其他服装参考 → 提示词恢复标准版（原身份提示词）
  if(wasOutfit && !hasOutfitRef()){
    const tp = $("gen-prompt");
    if(tp) tp.value = genState.defaultPrompt || "";
    toast("已移除服装参考图，提示词已恢复标准版");
  } else {
    toast("已移除参考图");
  }
}
function genRefClear(){
  genState.refImages = [];
  const i = $("gen-ref"); if(i) i.value = "";
  renderRefPreview();
  // ★ 2026-08-21 全部移除后恢复标准版提示词
  const tp = $("gen-prompt");
  if(tp) tp.value = genState.defaultPrompt || "";
}

// ★ 2026-08-21 服装参考图（身份定妆照）：自动作为第 2 张参考；提示词**整体替换**为固定的「服装通用参考版」（用户钦定，逐字写死，图1/图2 写法原封不动）
const OUTFIT_REF_PROMPT = `Full-body character sheet style portrait, front-facing full standing pose, arms naturally relaxed at sides, complete outfit fully visible.
Face identical to 图1 (main portrait), only change styling, NOT face.
Outfit, hairstyle and makeup: strictly replicate 图2 (clothing reference) — garment fabric, cut, color, silhouette, hairstyle and makeup all identical to the reference; do not redesign, do not alter sleeve or hem length. Only take the look itself from 图2, ignore the model's face, scene, lighting and background in it.
Plain light-grey solid background, no scene elements, no other people, no text, no watermark, no labels.
Single soft even frontal light from front-above, 5600K, 85mm portrait lens f/1.8 shallow depth of field, natural lens sharpness, subtle film grain, not over-retouched, not plastic.
negative: text, watermark, logo, labels, size marks, other people, scene elements, clothing drift, misplaced accessories, extra fingers, deformed limbs, no redesign of the outfit, no altering the reference garment.`;
function hasOutfitRef(){ return (genState.refImages||[]).some(r=>r.isOutfit); }
function genOutfitRefPicked(inp){
  const f = inp.files && inp.files[0];
  if(!f){ toast("未选择服装参考图"); return; }
  const MAX_REF = 9;
  if(genState.refImages.length >= MAX_REF){ toast("参考图最多 9 张，请先移除部分再添加"); inp.value = ""; return; }
  const rd = new FileReader();
  rd.onload = function(e){
    const b64 = String(e.target.result).split(",")[1] || "";
    genState.refImages.push({name: "👗服装参考·" + f.name, b64: b64, dataUrl: e.target.result, isOutfit: true});
    inp.value = "";
    renderRefPreview();
    const tp = $("gen-prompt");
    // ★ 提示词整体替换为「服装通用参考版」（固定写死，不是追加）
    if(tp) tp.value = OUTFIT_REF_PROMPT;
    toast("✅ 已添加服装参考图（提示词已替换为「服装通用参考版」）");
  };
  rd.readAsDataURL(f);
}
// ===== 选择参考图（从项目已生成图片库中挑选） =====
let refpTab = "character";
const REFP_TABS = [
  {key:"character", label:"🎭 角色"},
  {key:"prop", label:"📦 道具"},
  {key:"scene", label:"🏯 场景"},
];
function openRefPicker(){
  refpTab = "character";
  renderRefTabs();
  renderRefGrid();
  $("refpicker").classList.add("open");
}
function closeRefPicker(){ $("refpicker").classList.remove("open"); }
function refpSwitch(tab){ refpTab = tab; renderRefTabs(); renderRefGrid(); }
function renderRefTabs(){
  const wrap = $("refp-tabs");
  wrap.innerHTML = REFP_TABS.map(t => {
    const active = t.key === refpTab;
    const cnt = refpCount(t.key);
    return `<button class="btn-secondary" style="font-size:12px;padding:5px 12px;cursor:pointer;${active?'background:var(--acc);color:#fff;border-color:var(--acc)':''}" onclick="refpSwitch('${t.key}')">${t.label} (${cnt})</button>`;
  }).join("");
}
function refpCount(tab){
  const list = refpCollect(tab);
  return list.length;
}
function refpCollect(tab){
  const out = [];
  // ★ 2026-08-19 加固：只要有 image 路径就显示（ready 标记可能缺失/旧数据未置位），
  //   无图资产（image 为空）仍不显示；图缺失由网格 onerror 兜底显示"图缺失"
  if(tab === "character"){
    (P.xiatang?.characters||[]).forEach(c => {
      if(c.image) out.push({src:c.image, label:c.name+" · 定妆"});
      (c.identities||[]).forEach(id => {
        if(id.image) out.push({src:id.image, label:c.name+" · "+id.name});
        // ★ 2026-08-22 四视图角色卡也作为参考图可选
        if(id.sheet_image) out.push({src:id.sheet_image, label:c.name+" · "+id.name+" · 四视图"});
      });
    });
  } else if(tab === "prop"){
    (P.xiatang?.props||[]).forEach(p => { if(p.image) out.push({src:p.image, label:p.name}); });
  } else if(tab === "scene"){
    (P.xiatang?.scenes||[]).forEach(s => {
      if(s.image) out.push({src:s.image, label:s.name});
      // ★ 2026-08-20 多视角图：场景已生成的 views 视角图也作为参考图可选
      Object.keys(s.views || {}).forEach(v => {
        if(s.views[v]) out.push({src:s.views[v], label:s.name+" · "+v});
      });
      // ★ 2026-08-22 视距图：场景已生成的 dists（前移/后移）也作为参考图可选
      Object.keys(s.dists || {}).forEach(k => {
        if(s.dists[k]) out.push({src:s.dists[k], label:s.name+" · "+String(k).replace("|","·")});
      });
    });
  }
  return out;
}
function renderRefGrid(){
  const list = refpCollect(refpTab);
  const grid = $("refp-grid");
  const empty = $("refp-empty");
  if(!list.length){
    grid.innerHTML = ""; empty.style.display = "block"; return;
  }
  empty.style.display = "none";
  grid.innerHTML = list.map((it, i) => `
    <div style="border:1px solid var(--line);border-radius:8px;overflow:hidden;cursor:pointer;background:#fff" onclick="refPickImage('${esc(it.src).replace(/'/g,"\\'")}','${esc(it.label).replace(/'/g,"\\'")}')" title="点击选用：${esc(it.label)}">
      <div style="height:110px;background:var(--bg);display:flex;align-items:center;justify-content:center;overflow:hidden">
        <img src="${esc(imgSrc(it.src))}" loading="lazy" style="width:100%;height:100%;object-fit:cover;display:block" onerror="this.parentNode.innerHTML='<span style=font-size:12px;color:var(--mut)>图缺失</span>'">
      </div>
      <div style="font-size:12px;color:#475569;padding:4px 6px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${esc(it.label)}</div>
    </div>`).join("");
}
function refPickImage(src, label){
  // 项目内图片 → fetch → base64 垫图
  fetch(src).then(r => r.blob()).then(blob => new Promise((res, rej) => {
    const rd = new FileReader();
    rd.onload = e => res(e.target.result);
    rd.onerror = rej;
    rd.readAsDataURL(blob);
  })).then(dataUrl => {
    if(genState.refImages.length >= 9){ toast("参考图最多 9 张，请先移除部分再添加"); return; }
    const b64 = String(dataUrl).split(",")[1] || "";
    genState.refImages.push({name: label, b64: b64, dataUrl: dataUrl});
    renderRefPreview();
    toast("已选用参考图：" + label + "（" + genState.refImages.length + "/9）");
  }).catch(() => toast("读取参考图失败"));
}
// 锁脸（★ xiatang-characters 铁律）：身份图自动读取角色主图作 ref
// 找到角色当前主图路径（★ 支持 set-current 换名后的 {name}-<时间戳>.png）
function findCurrentMainImage(baseName){
  try{
    const chars = (P && P.xiatang && P.xiatang.characters) || [];
    for(const c of chars){
      if(c.name === baseName && c.image){
        return String(c.image).split("?")[0];
      }
    }
  }catch(e){}
  return "assets/characters/" + baseName + ".png";
}
async function fetchMainRefAsDataUrl(relPath){
  try {
    const r = await fetch(relPath + "?t=" + Date.now());
    if(!r.ok) return null;
    const b = await r.arrayBuffer();
    let bin = "";
    const bytes = new Uint8Array(b);
    for(let i=0;i<bytes.length;i++) bin += String.fromCharCode(bytes[i]);
    return "data:image/png;base64," + btoa(bin);
  } catch(e){ return null; }
}
// ★ 2026-08-22 通用相对路径 → dataURL（首帧/尾帧自动垫角色/场景参考图用；原 blocking 分支引用的同名函数从未定义）
async function fetchAsDataUrl(relPath){
  try {
    const r = await fetch(relPath + "?t=" + Date.now());
    if(!r.ok) return null;
    const b = await r.arrayBuffer();
    const bytes = new Uint8Array(b);
    let bin = "";
    for(let i=0;i<bytes.length;i++) bin += String.fromCharCode(bytes[i]);
    return "data:image/png;base64," + btoa(bin);
  } catch(e){ return null; }
}
// ★ 2026-09-09 按当前剧情章节选身份：命中 chapter_range 区间 → 起点≤当前的最大者 → 否则 null（交调用方回退文本匹配）
function pickIdentityByChapter(c, chapter){
  const ids = c.identities || [];
  if(!ids.length) return null;
  if(ids.length === 1) return ids[0];
  const ch = Number(chapter);
  if(!ch || !isFinite(ch)) return null;
  const parse = (r) => {
    const m = String(r || "").match(/ch\s*0*(\d+)(?:\s*[-–—]\s*(?:ch\s*0*)?(\d+)?)?/i);
    if(!m) return null;
    return [parseInt(m[1],10), m[2] ? parseInt(m[2],10) : Infinity];
  };
  let hit = ids.find(id => { const rg = parse(id.chapter_range); return rg && ch >= rg[0] && ch <= rg[1]; });
  if(hit) return hit;
  let best = null, bs = -1, anyStart = false;
  ids.forEach(id => { const rg = parse(id.chapter_range); if(!rg) return; anyStart = true; if(rg[0] <= ch && rg[0] > bs){ best = id; bs = rg[0]; } });
  if(best) return best;
  if(!anyStart) return ids[0];   // 无区间信息 → 最早形态
  return null;                    // 全部起点 > 当前章（该角色尚未登场）→ 交回退
}
// ★ 2026-08-22 按镜头文本选择身份（多身份角色用哪个四视图/定妆照）：全名→短名→短名 2+字子串→兜底有图身份
// ★ 2026-09-09 修：子串命中必须排除"其实是角色名自身的一部分"（如身份"晚晚楼主"含于角色"苏晚晚"→误选未生成的未来身份）；兜底优先有图身份
function pickIdentityByText(c, text){
  const ids = c.identities || [];
  if(!ids.length) return null;
  const t = String(text || "");
  const cn = String(c.name || "");
  const shortOf = (name) => String(name).replace(new RegExp("^" + cn + "\\s*"), "").replace(/身份$|造型$|装$/, "").trim();
  const notSelf = (frag) => !!frag && !cn.includes(frag);   // 排除"片段是角色名自身子串"的伪命中
  let hit = ids.find(id => id.name && t.includes(id.name) && notSelf(id.name));   // ① 全名
  if(hit) return hit;
  let best = null, bestLen = 0;
  ids.forEach(id => {
    const s = shortOf(id.name);
    if(!s || !notSelf(s)) return;
    if(t.includes(s)){ if(s.length > bestLen){ best = id; bestLen = s.length; } return; }
    for(let i=0;i<s.length-1;i++){                        // ② 短名 2+ 字连续子串
      for(let j=i+2;j<=s.length;j++){
        const sub = s.slice(i,j);
        if(sub.length >= 2 && notSelf(sub) && t.includes(sub) && sub.length > bestLen){ best = id; bestLen = sub.length; }
      }
    }
  });
  if(best) return best;
  // ③ 兜底：优先第一个"有图"的身份（四视图就绪 或 有定妆照路径），否则 ids[0]
  return ids.find(id => (id.sheet_ready && id.sheet_image) || id.image) || ids[0];
}
async function genSend(){
  let prompt = ($("gen-prompt").value||"").trim();
  // ★ 2026-08-21 服装参考图兜底：参考图含服装参考且提示词丢失了「服装通用参考版」→ 整体替换补回（固定写死）
  if(hasOutfitRef() && !prompt.includes("Outfit, hairstyle and makeup")) prompt = OUTFIT_REF_PROMPT;
  if(!prompt){ alert("提示词不能为空"); return; }
  // ★ 2026-08-20：去掉批量锁定——批量进行中也可继续提交（排队上限 60 由后端统一把关）
  const modelVal = String($("gen-model").value || "");
  let channelId = "", model = modelVal;
  const sep = modelVal.indexOf("::");
  if(sep >= 0){ channelId = modelVal.slice(0, sep); model = modelVal.slice(sep + 2); }
  const cat = genState.cat, nm = genState.name;
  // ★ 前置校验：资产无图且无名称时（如新加资产未命名/未生成图），直接提示不发请求
  if(!cat || !nm){ toast("❌ 该资产暂无名称，无法生成——请先在资产列表中确认名称后重试"); return; }
  // 身份图自动垫主图（锁脸）：openGenModal 已加载 genState.autoRef（展示在参考图列表，🔒 不可移除）
  const autoRef = (cat === "identity" && genState.autoRef) ? genState.autoRef.dataUrl : null;
  if(cat === "identity" && !autoRef){ toast("⚠️ 未找到主图，身份图无法锁脸（请先生成主图）"); return; }
  const manualRefs = (genState.refImages||[]).map(r => r.dataUrl || ("data:image/png;base64," + r.b64));
  const images = autoRef ? [autoRef, ...manualRefs] : manualRefs;
  const body = {
    category: cat, name: nm, prompt: prompt,
    model: model, size: $("gen-size").value, channel_id: channelId,
    images: images,
    ep: genState.ep || 1   // ★ 2026-08-20 分集
  };
  // 异步后台生图：入队后立即返回（任务在队列中执行），完成后任务面板可见
  const rs = $("gen-result"); rs.style.display = "block";
  rs.innerHTML = `<div style="display:flex;align-items:center;gap:8px;color:var(--mut);font-size:12px;line-height:1.6"><span class="gen-spinner" style="display:inline-block;width:14px;height:14px;border:2px solid var(--line);border-top-color:var(--acc);border-radius:50%;animation:gen-spin 1s linear infinite"></span><span>⏳ 已提交「${esc(nm)}」AI 生成…<br><span style="color:var(--acc)">已加入任务队列，可关闭本窗口继续操作，完成自动应用</span></span></div>`;
  toast("⏳ 已提交「" + nm + "」AI 生成，进入任务队列");
  const sendBtn = $("gen-send");
  if(sendBtn){ sendBtn.disabled = true; sendBtn.textContent = "⏳ 已入队…"; }
  try {
    const res = await fetch("/gen-image", {method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify(body)}).then(r => r.json());
    if(res.ok){
      // 入队成功：注册完成监听（任务完成时刷新资产位）
      if(res.task_id){
        genWatchTask(res.task_id, cat, nm, genState.ep || 1);
      } else {
        markReadyInMemory(cat, nm, res.hist_path || "");
        toast("✅ 「" + nm + "」已生成并自动应用" + (res.model ? "（" + res.model + "）" : ""));
        rerenderCurrent();
      }
    } else if(res.queue_full){
      toast("⚠️ " + String(res.error || "任务队列已满，请等待"));
      rs.innerHTML = `<div style="color:#b91c1c;font-size:12px;line-height:1.6">⚠️ 任务队列已满，请等待现有任务完成后重试</div>`;
    } else {
      toast("❌ 「" + nm + "」生成失败：" + String(res.error || "未知错误").slice(0, 120));
    }
  } catch(err) {
    toast("❌ 「" + nm + "」请求失败：" + err.message);
  } finally {
    if($("gen-send")){ $("gen-send").disabled = false; $("gen-send").textContent = "✨ 发送生成"; }
  }
}
// 监听队列任务完成 → 刷新资产位
// ★ 2026-08-21 优化 C：单一全局轮询（替代每任务一个 setInterval，避免批量任务定时器风暴）
// ★ 2026-08-21 优化 A：任务完成重渲染 300ms 防抖（多个任务连续完成合并为一次 rerenderCurrent，避免连环整页重建+图片重下）
const genWatch = {};      // task_id → {category, name, ep}
let watchTimer = null;    // 全局轮询定时器（无监听任务时自动停止）
let rerenderTimer = null; // 重渲染防抖定时器

function scheduleRerender(){
  if(rerenderTimer) return;
  rerenderTimer = setTimeout(() => { rerenderTimer = null; rerenderCurrent(); }, 300);
}

function ensureWatchTimer(){
  if(watchTimer || !Object.keys(genWatch).length) return;
  watchTimer = setInterval(pollTasks, 1000);
}

function pollTasks(){
  const keys = Object.keys(genWatch);
  if(!keys.length){ if(watchTimer){ clearInterval(watchTimer); watchTimer = null; } return; }
  fetch("/tasks").then(r => r.json()).then(res => {
    if(!res.ok) return;
    const pool = [...(res.running||[]), ...(res.done||[])];
    keys.forEach(tid => {
      const w = genWatch[tid];
      if(!w) return;
      const found = pool.find(t => t.task_id === tid);
      if(!found){ delete genWatch[tid]; if(w.onDone) w.onDone("failed"); return; }   // 任务列表消失（极端情况）→ 移除监听并计入完成
      if(found.status === "success"){
        delete genWatch[tid];
        markReadyInMemory(w.category, w.name, found.hist_path || "", found.result || "", w.ep);
        toast("✅ 「" + w.name + "」已生成并自动应用");
        if(w.onDone) w.onDone("success");
        rerenderCurrent();   // ★ 2026-08-24：成功即立即重渲染（去掉 300ms 防抖合并，避免并发任务"一起出现"观感）
      } else if(found.status === "failed"){
        delete genWatch[tid];
        toast("❌ 「" + w.name + "」生成失败：" + String(found.error || "未知错误").slice(0, 120));
        if(w.onDone) w.onDone("failed");
      }
    });
    if(!Object.keys(genWatch).length && watchTimer){ clearInterval(watchTimer); watchTimer = null; }
  }).catch(() => {});
}

function genWatchTask(taskId, category, name, ep, onDone){
  if(genWatch[taskId]) return;
  genWatch[taskId] = {category, name, ep: Number(ep)||1, onDone};
  ensureWatchTimer();
}
function genApply(){
  // 服务端已写盘 + mark_ready（SQLite 快照已含）。前端只需更新内存标记并原地重渲染当前视图：
  // 复用 markReadyInMemory（与上传图片同一套逻辑），不整页刷新、不丢 tab/集/Beat 状态。
  try{
    if(genState.cat && genState.name){
      markReadyInMemory(genState.cat, genState.name, genState.histPath || "");
    }
  }catch(e){ /* 内存标记失败不阻塞；data.js 已是权威数据 */ }
  closeGen();
  rerenderCurrent();
  toast("已应用到资产位");
}
// 启动时拉取渠道配置（服务模式）
if(IS_SERVER){
  fetch("/gen-config").then(r=>r.json()).then(cfg => {
    if(cfg && cfg.ok){
      genState.channels = cfg.channels || [];
      genState.sizes  = cfg.sizes  || GEN_DEFAULT_SIZES;
    }
  }).catch(()=>{});
}

// ===== 设置弹窗（渠道管理 + 图片默认比例） =====
let channelEditList = [];  // 设置面板编辑态渠道列表（apiKey 后端不回传，保存时为空则保留原值）
let channelDraft = null;   // 渠道编辑器草稿
// ---- 图片默认比例设置 ----
const DEFAULT_SIZE_MAP_FE = {character:"960x1280", identity:"1088x1920", scene:"1536x768", prop:"1280x960", sketch_frame:"1536x768", video:"16:9"};   // ★ 2026-08-21 identity 默认 9:16（身份图/四视图卡）；2026-08-23 video 默认 16:9 比例
// ★ 2026-08-23 视频比例候选（值即 aspect_ratio，直接下发 888 平台）
const VIDEO_RATIO_OPTIONS = [
  {value:"16:9", label:"16:9 横屏（推荐）"},
  {value:"9:16", label:"9:16 竖屏"},
  {value:"1:1", label:"1:1 方图"},
  {value:"4:3", label:"4:3 横屏"},
  {value:"3:4", label:"3:4 竖屏"},
  {value:"21:9", label:"21:9 超宽屏"}
];
const SIZE_CAT_LABELS = {character:"角色主图", identity:"身份图", scene:"场景", prop:"道具", sketch_frame:"草图·首帧/听风故事板", video:"视频"};   // ★ 2026-09-03 听风故事板默认尺寸同查 sketch_frame
let sizeDefaultMap = {...DEFAULT_SIZE_MAP_FE};  // 编辑态（打开设置时从后端载入，保存时提交）
let sizeDefOptions = [];                        // 尺寸下拉候选（gen-config 返回）
function renderSizeDefaults(){
  const box = document.getElementById("set-default-sizes");
  if(!box) return;
  box.innerHTML = "";
  const opts = sizeDefOptions.length ? sizeDefOptions : GEN_DEFAULT_SIZES;
  Object.keys(SIZE_CAT_LABELS).forEach(k => {
    const row = document.createElement("div");
    row.style.cssText = "display:flex;align-items:center;gap:8px;margin-bottom:6px";
    const lbl = document.createElement("span");
    lbl.style.cssText = "width:76px;font-size:12px;color:var(--mut);flex-shrink:0";
    lbl.textContent = SIZE_CAT_LABELS[k];
    const sel = document.createElement("select");
    sel.style.cssText = "flex:1;border:1px solid var(--line);border-radius:8px;padding:5px 8px;font-size:12px;background:#fff";
    // ★ 2026-08-23 视频分类用比例候选（非像素尺寸）
    const cand = (k === "video") ? VIDEO_RATIO_OPTIONS : opts;
    cand.forEach(sz => {
      const o = document.createElement("option");
      o.value = String(sz.value); o.text = String(sz.label);
      if(String(sz.value) === String(sizeDefaultMap[k] || "")) o.selected = true;
      sel.add(o);
    });
    sel.onchange = () => { sizeDefaultMap[k] = sel.value; };
    row.appendChild(lbl); row.appendChild(sel);
    box.appendChild(row);
  });
}
const PROTOCOL_LABELS = {openai:"OpenAI", gemini:"Gemini", ark:"方舟", up_lk888:"LK888(异步)", minimax_h3:"MiniMax H3(官方)"};
// ★ 2026-08-24 生视频模型选择下拉渲染
const VIDEO_MODEL_OPTIONS = [
  {value:"seedance", label:"Seedance 2.0（中文 STYLE LOCK 模板）"},
  {value:"h3", label:"MiniMax-H3（官方全参考六段式）"}
];
function renderVideoModelSelect(){
  const box = document.getElementById("set-video-model");
  if(!box) return;
  box.innerHTML = "";
  VIDEO_MODEL_OPTIONS.forEach(o => {
    const el = document.createElement("div");
    el.style.cssText = "display:flex;align-items:center;gap:8px;padding:7px 10px;border:1px solid var(--line);border-radius:8px;cursor:pointer;font-size:12px;background:#fff;margin-bottom:6px";
    el.innerHTML = '<span style="font-size:14px;width:16px;text-align:center">' + (o.value === genVideoModel ? "●" : "○") + '</span><span>' + o.label + '</span>';
    el.onclick = () => { genVideoModel = o.value; renderVideoModelSelect(); };
    box.appendChild(el);
  });
}
// ★ 2026-09-01 分镜主力线选择渲染（tingfeng 听风电影 / xiajing 虾镜拆镜）
const MAIN_LINE_OPTIONS = [
  {value:"tingfeng", label:"听风电影（storyboard-cinematic：戏剧节拍分段 + 五层结构 + 15s 段）"},
  {value:"xiajing", label:"虾镜拆镜（xiajing-episodes：场景一致性闸门 + 11 字段逐镜）"}
];
function renderMainLineSelect(){
  const box = document.getElementById("set-main-line");
  if(!box) return;
  box.innerHTML = "";
  MAIN_LINE_OPTIONS.forEach(o => {
    const el = document.createElement("div");
    el.style.cssText = "display:flex;align-items:center;gap:8px;padding:7px 10px;border:1px solid var(--line);border-radius:8px;cursor:pointer;font-size:12px;background:#fff;margin-bottom:6px";
    el.innerHTML = '<span style="font-size:14px;width:16px;text-align:center">' + (o.value === genMainLine ? "●" : "○") + '</span><span>' + o.label + '</span>';
    el.onclick = () => { genMainLine = o.value; renderMainLineSelect(); };
    box.appendChild(el);
  });
}
// ★ 侧栏入口标注当前主力线（⭐）
function updateMainLineBadge(){
  document.querySelectorAll(".sb-item[data-section]").forEach(it => {
    const sec = it.getAttribute("data-section");
    const base = it.getAttribute("data-base") || it.textContent.replace(/[⭐]/g, "").trim();
    it.setAttribute("data-base", base);
    it.textContent = base + ((sec === genMainLine) ? " ⭐" : "");
  });
}
const PROTOCOL_BASEURLS = {openai:"https://api.openai.com", gemini:"https://generativelanguage.googleapis.com", ark:"https://ark.cn-beijing.volces.com/api/v3", up_lk888:"https://api.lk888.ai", minimax_h3:"https://metaso.cn/api/minimax"};
// ★ 2026-09-02 生视频渠道选择：MiniMax H3 官方渠道优先，888 中转回退（H3 视频生成替换原 888 路径）
function pickVideoChannel(channels){
  const ok = (channels || []).filter(c => c.configured && (c.apiFormat === "minimax_h3" || c.apiFormat === "up_lk888"));
  return ok.find(c => c.apiFormat === "minimax_h3") || ok[0] || null;
}

function openSettings(){
  if(!IS_SERVER){ alert("请通过「启动项目台.bat」运行服务模式后再设置"); return; }
  fetch("/gen-config").then(r=>r.json()).then(cfg => {
    if(!cfg || !cfg.ok){ alert("读取配置失败"); return; }
    channelEditList = (cfg.channels || []).map(c => ({...c}));
    renderChannels();
    // 载入图片默认比例（后端缺失字段时用默认值）
    sizeDefOptions = cfg.sizes || GEN_DEFAULT_SIZES;
    sizeDefaultMap = {...DEFAULT_SIZE_MAP_FE, ...(cfg.default_sizes || {})};
    renderSizeDefaults();
    // ★ 2026-08-24 生视频模型选择（seedance / h3）
    genVideoModel = (cfg.video_model === "h3") ? "h3" : "seedance";
    window._savedVideoModel = genVideoModel; // ★ 记住已落库值，保存时对比是否切换
    renderVideoModelSelect();
    // ★ 2026-09-01 分镜主力线选择（tingfeng / xiajing）
    genMainLine = (cfg.storyboard_main_line === "xiajing") ? "xiajing" : "tingfeng";
    renderMainLineSelect();
    const status = document.getElementById("set-status");
    if(cfg.configured){
      status.style.background = "#ecfdf5"; status.style.color = "#15803d"; status.style.border = "1px solid #a7f3d0";
      status.textContent = "✅ 已配置可用渠道（保存后生图弹窗模型下拉自动更新）";
    } else {
      status.style.background = "#fef2f2"; status.style.color = "#b91c1c"; status.style.border = "1px solid #fecaca";
      status.textContent = "⚠️ 尚无可用渠道（Base URL + API Key 齐全才算可用）";
    }
    document.getElementById("settings").classList.add("open");
  });
}
function closeSettings(){ document.getElementById("settings").classList.remove("open"); }
function renderChannels(){
  const box = document.getElementById("set-channels"); box.innerHTML = "";
  if(!channelEditList.length){
    box.innerHTML = '<div style="font-size:12px;color:var(--mut);padding:10px;text-align:center">暂无渠道，点下方「+ 新增渠道」添加</div>';
    return;
  }
  channelEditList.forEach((ch, i) => {
    const card = document.createElement("div");
    card.style.cssText = "display:flex;align-items:center;justify-content:space-between;gap:10px;border:1px solid var(--line);border-radius:10px;padding:10px 12px;margin-bottom:8px;background:var(--bg)";
    const left = document.createElement("div"); left.style.minWidth = "0";
    const badge = ch.configured
      ? '<span style="font-size:12px;color:#15803d;background:#ecfdf5;border:1px solid #a7f3d0;border-radius:999px;padding:1px 7px;margin-left:6px">已配置</span>'
      : '<span style="font-size:12px;color:#b91c1c;background:#fef2f2;border:1px solid #fecaca;border-radius:999px;padding:1px 7px;margin-left:6px">未配置</span>';
    left.innerHTML =
      '<div style="font-size:13px;font-weight:600">' + esc(ch.name || "未命名渠道") + badge + '</div>' +
      '<div style="font-size:12px;color:var(--mut);margin-top:3px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">' + esc(PROTOCOL_LABELS[ch.apiFormat] || ch.apiFormat || "") + ' · ' + (ch.models || []).length + ' 个模型 · ' + esc(ch.baseUrl || "未填 URL") + '</div>';
    const right = document.createElement("div"); right.style.cssText = "display:flex;gap:6px;flex-shrink:0";
    const edit = document.createElement("button"); edit.textContent = "✏ 编辑";
    edit.style.cssText = "font-size:12px;padding:4px 10px;border:1px solid var(--line);background:#fff;border-radius:6px;cursor:pointer";
    edit.onclick = () => channelEdit(ch.id);
    const del = document.createElement("button"); del.textContent = "🗑";
    del.style.cssText = "font-size:12px;padding:4px 10px;border:1px solid #fecaca;background:#fff;color:#b91c1c;border-radius:6px;cursor:pointer";
    del.onclick = () => {
      if(channelEditList.length <= 1){ alert("至少保留一个渠道"); return; }
      if(!confirm("删除渠道「" + (ch.name || "") + "」？")) return;
      channelEditList.splice(i, 1); renderChannels();
    };
    right.appendChild(edit); right.appendChild(del);
    card.appendChild(left); card.appendChild(right);
    box.appendChild(card);
  });
}

// ---- 渠道编辑器（右侧抽屉） ----
let fetchedModels = [];    // 拉取到的平台模型候选（未加入 channelDraft）
let fetchedSelected = new Set();  // 候选中已勾选的模型名
let fetchedFilter = "";    // 筛选关键字

function channelEdit(id){
  const ch = id ? channelEditList.find(c => c.id === id) : null;
  channelDraft = ch ? {...ch, models: [...(ch.models || [])]} : {id:"", name:"", baseUrl:"", apiKey:"", apiFormat:"openai", models:[], configured:false};
  fetchedModels = [];
  fetchedSelected = new Set();
  fetchedFilter = "";
  document.getElementById("ch-title").textContent = ch ? "编辑渠道" : "新增渠道";
  document.getElementById("ch-name").value = channelDraft.name || "";
  document.getElementById("ch-protocol").value = channelDraft.apiFormat || "openai";
  document.getElementById("ch-baseurl").value = channelDraft.baseUrl || "";
  document.getElementById("ch-apikey").value = channelDraft.apiKey || "";
  document.getElementById("ch-result").textContent = "";
  document.getElementById("ch-fetched-panel").style.display = "none";
  renderChModels();
  document.getElementById("ch-editor").classList.add("open");
}
function closeChannelEditor(){ document.getElementById("ch-editor").classList.remove("open"); channelDraft = null; }
function chProtocolChanged(){
  const p = document.getElementById("ch-protocol").value;
  const cur = document.getElementById("ch-baseurl").value.trim();
  const oldP = channelDraft.apiFormat || "";
  if(!cur || cur === (PROTOCOL_BASEURLS[oldP] || "")) document.getElementById("ch-baseurl").value = PROTOCOL_BASEURLS[p] || "";
  channelDraft.apiFormat = p;
}
function _modelName(m){ return typeof m === "string" ? m : m.name; }
function _modelHasScript(m){ return typeof m === "object" && (m.script || "").trim(); }
function renderChModels(){
  const box = document.getElementById("ch-models"); box.innerHTML = "";
  const list = channelDraft.models || [];
  if(!list.length){ box.innerHTML = '<div style="font-size:12px;color:var(--mut);padding:8px;text-align:center">暂无模型，可手动添加或「⛏ 拉取平台模型」</div>'; return; }
  list.forEach((md, i) => {
    const name = _modelName(md);
    const hasScript = _modelHasScript(md);
    const row = document.createElement("div"); row.style.cssText = "display:flex;align-items:center;gap:6px;margin-bottom:6px";
    const span = document.createElement("span");
    span.textContent = name; span.style.cssText = "flex:1;font-size:12px;font-family:monospace;overflow:hidden;text-overflow:ellipsis;white-space:nowrap";
    if(hasScript){ span.title = "已配置调用脚本"; span.style.color = "#0F6E56"; }
    const scriptBtn = document.createElement("button");
    scriptBtn.textContent = hasScript ? "📜 脚本" : "📜";
    scriptBtn.title = hasScript ? "已配置调用脚本，点此编辑" : "为此模型添加调用脚本";
    scriptBtn.style.cssText = "flex-shrink:0;font-size:12px;padding:3px 8px;border:1px solid " + (hasScript ? "#5DCAA5" : "var(--line)") + ";background:" + (hasScript ? "#E1F5EE" : "#fff") + ";color:" + (hasScript ? "#0F6E56" : "var(--mut)") + ";border-radius:4px;cursor:pointer";
    scriptBtn.onclick = () => openScriptEditor(i);
    const del = document.createElement("button"); del.textContent = "×"; del.className = "x-del";
    del.style.cssText = "flex-shrink:0;border:none;background:transparent;color:#b91c1c;font-size:16px;cursor:pointer;padding:0 4px";
    del.onclick = () => { list.splice(i, 1); renderChModels(); };
    row.appendChild(span); row.appendChild(scriptBtn); row.appendChild(del);
    box.appendChild(row);
  });
}
function chAddModel(){
  const inp = document.getElementById("ch-newmodel");
  const name = inp.value.trim();
  if(!name) return;
  if(!channelDraft.models.some(m => _modelName(m) === name)) channelDraft.models.push({name, script: ""});
  fetchedSelected.add(name);
  inp.value = "";
  renderChModels();
  renderChFetched();
}
async function chFetchModels(){
  const baseUrl = document.getElementById("ch-baseurl").value.trim();
  const apiKey = document.getElementById("ch-apikey").value.trim();
  if(!baseUrl || !apiKey){ setChResult("请先填写 Base URL 和 API Key", true); return; }
  setChResult("⏳ 正在拉取平台模型…");
  try{
    const r = await fetch("/gen-fetch-models", {method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify({baseUrl, apiKey, apiFormat: document.getElementById("ch-protocol").value})});
    const res = await r.json();
    if(res.ok){
      // 只显示"未在 channelDraft.models 里"的候选（已添加的灰色不显示）
      const cur = channelDraft.models || [];
      const prevSelected = new Set(fetchedSelected);
      fetchedModels = (res.models || []).slice();
      fetchedSelected = new Set();
      // 保留之前选过的（如果还在新候选里）
      prevSelected.forEach(m => { if(fetchedModels.includes(m) && !cur.some(x => _modelName(x) === m)) fetchedSelected.add(m); });
      // 默认勾选所有未添加的（让用户先看到全选状态，可改）
      // ——不预选，用户点全选更清晰
      fetchedFilter = "";
      renderChFetched();
      setChResult("✅ 已拉取 " + res.count + " 个模型，请勾选要加入的（已添加的不显示）");
    } else {
      setChResult("❌ " + (res.error || "拉取失败"), true);
    }
  }catch(e){ setChResult("❌ 请求失败：" + e.message, true); }
}
function renderChFetched(){
  const panel = document.getElementById("ch-fetched-panel");
  if(!fetchedModels.length){ panel.style.display = "none"; return; }
  panel.style.display = "";
  const cur = channelDraft.models || [];
  const list = fetchedModels.filter(m => !cur.some(x => _modelName(x) === m));  // 已添加的不再显示
  const filterK = fetchedFilter.trim().toLowerCase();
  const visible = filterK ? list.filter(m => m.toLowerCase().includes(filterK)) : list;
  document.getElementById("ch-fetched-stat").textContent = list.length ? `共 ${list.length} 个未添加${filterK?`（已筛 ${visible.length}）`:""}` : "已全部添加";
  const box = document.getElementById("ch-fetched-list"); box.innerHTML = "";
  if(!visible.length){
    box.innerHTML = '<div style="font-size:12px;color:var(--mut);padding:14px;text-align:center">' + (list.length ? "无匹配项" : "全部已添加") + '</div>';
    return;
  }
  visible.forEach(m => {
    const row = document.createElement("label");
    row.style.cssText = "display:flex;align-items:center;gap:6px;padding:4px 4px;border-radius:4px;cursor:pointer;font-size:12px";
    row.onmouseover = () => row.style.background = "var(--bg)";
    row.onmouseout = () => row.style.background = "transparent";
    const cb = document.createElement("input"); cb.type = "checkbox";
    cb.checked = fetchedSelected.has(m);
    cb.onchange = () => { if(cb.checked) fetchedSelected.add(m); else fetchedSelected.delete(m); };
    const span = document.createElement("span"); span.textContent = m; span.style.cssText = "font-family:monospace;flex:1;word-break:break-all";
    row.appendChild(cb); row.appendChild(span);
    box.appendChild(row);
  });
}
function chFetchToggle(checked){
  const cur = channelDraft.models || [];
  const list = fetchedModels.filter(m => !cur.some(x => _modelName(x) === m));
  list.forEach(m => { if(checked) fetchedSelected.add(m); else fetchedSelected.delete(m); });
  renderChFetched();
}
function chFetchSearch(){
  const k = prompt("输入筛选关键字（留空显示全部）");
  if(k === null) return;
  fetchedFilter = k;
  renderChFetched();
}
function chAddSelected(){
  if(!fetchedSelected.size){ setChResult("请先勾选要添加的模型", true); return; }
  const cur = channelDraft.models || [];
  let added = 0;
  fetchedSelected.forEach(m => {
    if(!cur.some(x => _modelName(x) === m)){ cur.push({name: m, script: ""}); added++; }
  });
  channelDraft.models = cur;
  cur.forEach(m => fetchedSelected.delete(_modelName(m)));
  renderChModels();
  renderChFetched();
  setChResult("✅ 已添加 " + added + " 个模型（共 " + cur.length + " 个）");
}
async function chTestConn(){
  const baseUrl = document.getElementById("ch-baseurl").value.trim();
  const apiKey = document.getElementById("ch-apikey").value.trim();
  if(!baseUrl || !apiKey){ setChResult("请先填写 Base URL 和 API Key", true); return; }
  setChResult("⏳ 测试中…");
  try{
    const r = await fetch("/gen-test", {method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify({baseUrl, apiKey, apiFormat: document.getElementById("ch-protocol").value})});
    const res = await r.json();
    if(res.ok) setChResult("✅ " + (res.note || "连接成功"));
    else setChResult("❌ " + (res.error || "连接失败"), true);
  }catch(e){ setChResult("❌ 请求失败：" + e.message, true); }
}
function setChResult(text, isErr){
  const el = document.getElementById("ch-result");
  el.style.color = isErr ? "#b91c1c" : "#15803d";
  el.textContent = text;
}
const SCRIPT_TPL_OPENAI = `// 同步 OpenAI /v1/images/generations（无垫图）
const body = {
  model, prompt, n: 1,
  response_format: 'b64_json',
  size: params.raw_size && params.raw_size !== 'auto' ? params.raw_size : '1024x1024',
};
const r = await http.post('images/generations', body);
const b64 = r?.data?.[0]?.b64_json;
if (!b64) throw new Error('未返回 b64_json：' + JSON.stringify(r).slice(0, 300));
return ['data:image/png;base64,' + b64];`;
const SCRIPT_TPL_GEMINI = `// Gemini :generateContent（同步，无轮询）
const body = {
  contents: [{ parts: [{ text: prompt }, ...(images || []).map(d => ({inline_data: {mime_type: 'image/png', data: d.replace(/^data:image\/\\w+;base64,/, '')}}))] }],
};
const r = await http.post('models/' + model + ':generateContent', body);
const parts = r?.candidates?.[0]?.content?.parts || [];
const b64 = parts.map(p => p.inline_data?.data || p.inlineData?.data).find(Boolean);
if (!b64) throw new Error('未返回图片：' + JSON.stringify(r).slice(0, 300));
return ['data:image/png;base64,' + b64];`;
const SCRIPT_TPL_UP_LK = `// up.lk888 异步任务式：建任务 → 轮询 → 下载
const submit = await http.post('media/generate', {
  model, prompt,
  params: { aspect_ratio: params.size, images: images || [], n: 1, response_format: 'url', quality: 'auto' },
});
const taskId = submit?.data?.task_id || submit?.task_id;
if (!taskId) throw new Error('未返回 task_id：' + JSON.stringify(submit).slice(0, 300));
const result = await poll(
  () => http.get('media/status?task_id=' + taskId),
  res => {
    const d = res?.data || res;
    return d?.is_final === true;
  },
  { intervalMs: 8000, timeoutMs: 600000 }
);
const finalData = result?.data || result;
if (finalData?.state === 'failed') throw new Error(finalData.error || JSON.stringify(result));
const url = finalData?.result_url;
if (!url) throw new Error('is_final=true 但 result_url 缺失: ' + JSON.stringify(result));
return [url];`;
let scriptEditingIdx = -1;
function openScriptEditor(idx){
  scriptEditingIdx = idx;
  const m = channelDraft.models[idx];
  const name = _modelName(m);
  document.getElementById("script-title").textContent = "调用脚本 · " + name;
  document.getElementById("script-text").value = (typeof m === "object" ? (m.script || "") : "");
  document.getElementById("script-result").textContent = "";
  document.getElementById("script-mask").classList.add("open");
}
function closeScriptEditor(){ document.getElementById("script-mask").classList.remove("open"); scriptEditingIdx = -1; }
function insertScriptTemplate(which){
  const tpl = which === "openai" ? SCRIPT_TPL_OPENAI : which === "gemini" ? SCRIPT_TPL_GEMINI : SCRIPT_TPL_UP_LK;
  const ta = document.getElementById("script-text");
  ta.value = tpl; ta.focus();
}
function clearScript(){ document.getElementById("script-text").value = ""; }
function syncDraftToChannelList(){
  if(!channelDraft) return;
  if(!channelDraft.id){
    channelDraft.id = "ch_" + Date.now().toString(36);
    channelEditList.push(channelDraft);
  } else {
    const idx = channelEditList.findIndex(c => c.id === channelDraft.id);
    if(idx >= 0) channelEditList[idx] = channelDraft;
  }
}
function saveScript(){
  if(scriptEditingIdx < 0) return;
  const code = document.getElementById("script-text").value;
  const m = channelDraft.models[scriptEditingIdx];
  if(typeof m === "string") channelDraft.models[scriptEditingIdx] = {name: m, script: code};
  else m.script = code;
  renderChModels();
  closeScriptEditor();
  // 一步到位：脚本写回渠道列表 + 提交后端（不再需要额外点"保存渠道"）
  syncDraftToChannelList();
  commitChannels({successMsg: code.trim() ? "✅ 脚本已保存并提交渠道" : "已清空脚本（按协议默认调用）"});
}
function chSave(){
  const name = document.getElementById("ch-name").value.trim();
  const baseUrl = document.getElementById("ch-baseurl").value.trim();
  if(!name){ alert("请填写渠道名称"); return; }
  if(!baseUrl){ alert("请填写 Base URL"); return; }
  const draft = channelDraft;
  draft.name = name;
  draft.baseUrl = baseUrl;
  draft.apiKey = document.getElementById("ch-apikey").value;
  syncDraftToChannelList();
  closeChannelEditor();
  commitChannels({successMsg: "✅ 渠道已保存（可继续编辑其他渠道，点底部「保存」关闭）"});
}
async function commitChannels(opts){
  opts = opts || {};
  if(!channelEditList.length){ alert("至少添加一个渠道"); return; }
  try{
    const r = await fetch("/gen-config", {method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify({channels: channelEditList, default_sizes: sizeDefaultMap, video_model: genVideoModel, storyboard_main_line: genMainLine})});
    const res = await r.json();
    if(res.ok){
      renderChannels();
      // ★ 2026-08-24 改版：视频提示词「双模型并存」，切换模型只是存偏好 + 重绘显示，
      //   不再重算（提示词已同时存了 seedance + h3，显示/使用哪个由 genVideoModel 决定）。
      window._savedVideoModel = genVideoModel;
      if(typeof renderXiajing === "function") renderXiajing();
      updateMainLineBadge();   // ★ 主力线保存后刷新侧栏 ⭐ 标注
      toast((opts.successMsg || "✅ 渠道已保存") + " · 生视频模型：" + (genVideoModel === "h3" ? "MiniMax-H3" : "Seedance 2.0"));
      if(opts.closeSettings) closeSettings();
    } else {
      alert("保存失败：" + (res.error || ""));
    }
  }catch(e){ alert("请求失败：" + e.message); }
}

// ===== 历史图片管理 =====
// 定位对象：category + 主文件名（如 {{角色名}}.png / beat3.png）
// ★ 2026-08-19：支持一个或多个时间戳后缀文件名（{{角色名}}-1787xxx.png / {{角色名}}-1787xxx-1787xxx.png），匹配时自动剥离
function findHistObj(category, name){
  const base = String(name||"").replace(/\.[^.]+$/, "").replace(/(?:-\d{13})+$/, "");
  const baseNoTs = (p)=>String(p||"").split("/").pop().split("?")[0].replace(/\.[^.]+$/, "").replace(/(?:-\d{13})+$/, "");
  const eq = (p)=>baseNoTs(p)===base;
  const t = P.xiatang||{};
  if(category==="character"){
    for(const c of (t.characters||[])){
      if(eq(c.image)) return {obj:c, key:"image", imgKey:"image"};
      for(const id of (c.identities||[])){
        if(eq(id.image)) return {obj:id, key:"image", imgKey:"image"};
        // ★ 2026-08-21 四视图角色卡历史：name=「角色名-身份id-sheet」→ 匹配身份对象的 sheet 字段（历史独立存 sheet_history）
        if(base === (c.name||"") + "-" + (id.identity_id||"") + "-sheet") return {obj:id, key:"sheet_ready", imgKey:"sheet_image", histKey:"sheet_history"};
      }
    }
  } else if(category==="identity"){
    for(const c of (t.characters||[])) for(const id of (c.identities||[])) if(eq(id.image)) return {obj:id, key:"image", imgKey:"image"};
  } else if(category==="scene"){
    for(const s of (t.scenes||[])) if(eq(s.image)) return {obj:s, key:"image", imgKey:"image"};
  } else if(category==="prop"){
    for(const p of (t.props||[])) if(eq(p.image)) return {obj:p, key:"image", imgKey:"image"};
  } else if(category==="sketch" || category==="frame"){
    const imgKey = category==="sketch" ? "sketch_image" : "frame_image";
    for(const ep of (P.xiajing?.episodes||[])) for(const b of (ep.beats||[])) if(eq(b[imgKey])) return {obj:b, key:category==="sketch"?"sketch_ready":"frame_ready", imgKey};
  } else if(category==="video"){
    for(const ep of (P.xiajing?.episodes||[])) for(const b of (ep.beats||[])){
      const vp = "assets/ep" + String(ep.number).padStart(3,"0") + "/videos/beat" + b.beat_number + ".mp4";
      if(baseNoTs(vp)===base) return {obj:b, key:"video_ready", imgKey:"video"};
    }
  } else if(category==="storyboard"){
    // ★ 2026-08-22 故事板多张：name=story-{ep}-{idx} → ep.storyboards[idx].history；旧 story-{ep} 兼容按集
    const sm = /^story-(\d+)-(\d+)$/.exec(base);
    for(const ep of (P.xiajing?.episodes||[])){
      if(sm && String(ep.number) === sm[1]){
        const sb = (ep.storyboards||[]).find(s=>String(s.idx)===sm[2]);
        if(sb) return {obj:sb, key:"ready", imgKey:"image", histKey:"history"};
      } else if(!sm && String(ep.number) === (base.replace(/^story-/,"")) && ep.storyboard_image){
        return {obj:ep, key:"storyboard_ready", imgKey:"storyboard_image"};
      }
    }
  }
  return null;
}

// 生成历史按钮（有历史才显示）
function histWidget(category, name){
  if(!IS_SERVER) return "";
  const f = findHistObj(category, name);
  const hist = (f && f.obj && f.obj[f.histKey || "history"]) ? f.obj[f.histKey || "history"] : [];
  if(!hist.length) return "";
  return `<span class="hist-btn" onclick="event.stopPropagation();openHist('${category}','${esc(name)}')">🕘 历史(${hist.length})</span>`;
}

function openHist(category, name){
  const f = findHistObj(category, name);
  const hist = (f && f.obj && f.obj[f.histKey || "history"]) ? f.obj[f.histKey || "history"] : [];
  $("hist-title").textContent = "历史图片 · " + name;
  $("hist-grid").innerHTML = hist.length ? hist.map((hp, i) => `
    <div class="hist-item">
      <img src="${esc(hp)}?t=${Date.now()}" onclick="openZoom('${esc(hp)}?t=${Date.now()}','历史图 ${i+1}')">
      <div class="hi-ts">版本 ${i+1}</div>
      <div class="hi-act">
        <button class="primary" onclick="setHistCurrent('${category}','${esc(name)}','${esc(hp)}')">设为当前</button>
      </div>
    </div>`).join("") : '<div class="hist-empty">暂无历史图片</div>';
  $("hist").classList.add("open");
}
function closeHist(){ $("hist").classList.remove("open"); }

async function setHistCurrent(category, name, histPath){
  if(!IS_SERVER){ toast("需服务模式"); return; }
  try{
    const r = await fetch(`/set-current?category=${category}&name=${encodeURIComponent(name)}&hist=${encodeURIComponent(histPath)}`, {method:"POST"});
    const j = await r.json();
    if(j.ok){
      toast("已设为当前: "+j.path);
      closeHist();
      // 同步内存：服务端已把原当前图归档为 j.hist_path、选中历史图复制到当前位。
      // history 应移除被选中的 histPath（它现在是当前图），加入新归档的原当前图。
      const f = findHistObj(category, name);
      if(f){
        const hist = f.obj.history || [];
        f.obj.history = hist.filter(h => h !== histPath);
        if(j.hist_path && !f.obj.history.includes(j.hist_path)) f.obj.history.unshift(j.hist_path);
        f.obj.current_hist = j.hist_path || "";
        // ★ set-current 换文件名：image 直接用后端返回的新路径（带时间戳，URL 变化避免浏览器缓存旧图）
        f.obj[f.imgKey] = (j.path || String(f.obj[f.imgKey]||"").split("?")[0]) + "?t=" + Date.now();
        if(f.obj.image_ready !== undefined) f.obj.image_ready = true;
      }
      rerenderCurrent();
    } else toast("操作失败: "+(j.error||"未知"));
  }catch(e){ toast("操作出错: "+e.message); }
}

let P = {};   // 数据源：SQLite（GET /api/data 异步加载，替代原 data.js）
const $ = (id) => document.getElementById(id);
// 从 SQLite 加载全部数据（前端唯一数据源）
async function loadProjectFromDb(){
  try{
    const r = await fetch("/api/data", {cache: "no-store"});   // ★ 2026-08-31 防浏览器缓存旧数据
    const j = await r.json();
    if(!j.ok){ toast("❌ " + (j.error||"数据加载失败")); return false; }
    P = j.data || {};
    try{ fillTopbar(); }catch(e){}   // ★ 2026-08-22 数据加载完成后填充顶部（风格/共x集）
    try{ loadAnnTags(); }catch(e){}  // ★ 2026-08-23 加载持久化标注提示词（下拉框内容）
    return true;
  }catch(e){ return false; }
}
// 重新加载数据（虾格确认/保存新风格/上传等操作后刷新数据与视图）
function reloadDataJs(){
  if(!IS_SERVER){ toast("需服务模式（双击启动项目台.bat）"); return; }
  loadProjectFromDb().then(ok => {
    if(ok){ rerenderCurrent(); toast("✅ 数据已刷新"); }
    else toast("刷新失败");
  });
}
(function initModeBadge(){
  const b = $("mode-badge");
  if(!b) return;
  b.textContent = IS_SERVER ? "● 服务模式" : "○ 静态模式";
  b.style.background = IS_SERVER ? "#dcfce7" : "#fef3c7";
  b.style.color = IS_SERVER ? "#15803d" : "#a16207";
  b.title = IS_SERVER ? "服务模式：可上传图片/视频" : "静态模式：仅浏览（双击启动项目台.bat 可启用上传）";
})();
// ★ 2026-08-24 页面启动即同步「生视频模型」设置（设置页保存后下次启动/强刷即时生效）
(function initVideoModel(){
  try{
    fetch("/gen-config").then(r => r.json()).then(cfg => {
      if(cfg && cfg.ok){
        genVideoModel = (cfg.video_model === "h3") ? "h3" : "seedance";
        // ★ 2026-09-01 分镜主力线启动同步（tingfeng / xiajing）
        genMainLine = (cfg.storyboard_main_line === "xiajing") ? "xiajing" : "tingfeng";
        updateMainLineBadge();
      }
    }).catch(() => {});
  }catch(e){}
})();
function pillList(s){return s.split(/[\u002f\u3001\uff0c,]/).filter(Boolean).map(function(c){return '<span class="pill" style="font-size:12px">' + esc(c.trim()) + '</span>'}).join('')}

function toCharPill(c){return '<span class="pill" style="font-size:12px">' + esc(c.trim()) + '</span>'}

const esc = (s) => String(s||"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");
// IS_SERVER 已在 script 开头声明；此处不再重复声明（避免 TDZ/重复执行）

function toast(msg){const t=$("toast");t.textContent=msg;t.classList.add("show");setTimeout(()=>t.classList.remove("show"),1800);}
function copyText(txt){if(navigator.clipboard&&window.isSecureContext){navigator.clipboard.writeText(txt).then(()=>toast("已复制"));}else{const ta=document.createElement("textarea");ta.value=txt;document.body.appendChild(ta);ta.select();document.execCommand("copy");ta.remove();toast("已复制");}}
function promptBlock(txt){return `<div class="prompt"><button class="copy" onclick='copyText(${JSON.stringify(txt||"")})'>复制</button>${esc(txt||"(无)")}</div>`;}
// ★ 2026-09-06b 双语提示词块：中文理解稿默认展示，英文生图执行版折叠；任一缺失自动降级单语
function promptBlockDual(cn, en){
  const _cn = String(cn||"").trim(), _en = String(en||"").trim();
  if(!_cn && !_en) return promptBlock("");
  if(!_cn) return promptBlock(_en);
  const enBlock = _en ? `<details style="margin-top:6px"><summary style="cursor:pointer;font-size:11.5px;color:#64748b;user-select:none">🖥 生图执行版（EN）</summary><div style="margin-top:6px">${promptBlock(_en)}</div></details>` : "";
  return `<div class="prompt"><button class="copy" onclick='copyText(${JSON.stringify(_cn)})'>复制中文</button>${esc(_cn)}</div>${enBlock}`;
}
function uploadWidget(category, name){
  if(!IS_SERVER) return `<button title="需启动服务" style="flex:1;font-size:12.5px;font-weight:600;padding:8px 12px;border-radius:10px;border:1px solid #cbd5e1;background:#f1f5f9;color:#64748b;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;cursor:pointer" onclick="toast('上传需要服务模式：请双击「启动项目台.bat」，用地址栏 http://127.0.0.1:8320 打开');">↑ 上传图片</button>`;
  const lbl = category==="audio"?"音频":category==="video"?"视频":"图片";
  return `<label class="up" style="display:inline-flex;align-items:center;justify-content:center;gap:6px;background:linear-gradient(135deg,#A78BFA,#7C3AED);color:#fff;border-radius:10px;padding:7px 16px;font-size:12.5px;font-weight:600;cursor:pointer;white-space:nowrap;letter-spacing:.2px;box-shadow:0 2px 6px rgba(139,92,246,.25);transition:all .15s"><span>↑ 上传${lbl}</span><input type="file" class="upfile" accept="${acceptFor(category)}" onchange="doUpload(this,'${category}','${esc(name)}')" style="display:none"></label>`;
}
function acceptFor(category){
  if(category==="video") return "video/*";
  if(category==="audio") return "audio/*";
  return "image/*";
}
function genBtn(category, name, prompt, ep, promptCn){
  if(!IS_SERVER) return `<button title="需启动服务" style="flex:1;font-size:12.5px;font-weight:600;padding:8px 12px;border-radius:10px;border:1px solid #cbd5e1;background:#f1f5f9;color:#64748b;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;cursor:pointer" onclick="toast('AI 生成需要服务模式：请双击「启动项目台.bat」，用地址栏 http://127.0.0.1:8320 打开');">✨ 生成</button>`;
  // 用 data-* 属性 + 事件委托传参，避免 onclick 内嵌单引号/特殊字符导致 JS 截断或注入
  return `<button class="pill gen-btn" data-cat="${esc(category)}" data-name="${esc(name||"")}" data-prompt="${esc(prompt||"")}" data-prompt-cn="${esc(promptCn||"")}" data-ep="${esc(ep||"")}" style="background:linear-gradient(135deg,#A78BFA,#7C3AED);color:#fff;border:none;white-space:nowrap;border-radius:10px;padding:7px 16px;font-size:12.5px;font-weight:600;box-shadow:0 2px 6px rgba(139,92,246,.25);cursor:pointer;transition:all .15s" title="AI 生成图片（弹窗含中文参考稿）">✨ 生成</button>`;
}
// gen-btn 事件委托：捕获阶段执行（先于 .up 的 stopPropagation），避免被详情页 .up/.role-portrait 冒泡拦截
document.addEventListener("click", function(e){
  const btn = e.target && e.target.closest ? e.target.closest(".gen-btn") : null;
  if(!btn) return;
  e.stopPropagation();
  e.preventDefault();
  openGenModal(btn.dataset.cat || "", btn.dataset.name || "", btn.dataset.prompt || "", btn.dataset.ep || "", btn.dataset.promptCn || "");
}, true);
async function doUpload(input, category, targetName, ep){
  const f = input.files && input.files[0];
  if(!f){toast("未选择文件");return;}
  const ext = f.name.split(".").pop() || "png";
  const name = targetName.includes(".") ? targetName : targetName + "." + ext;
  const fd = new FormData();
  fd.append("file", f, name);
  try{
    const r = await fetch(`/upload?category=${category}&name=${encodeURIComponent(name)}&ep=${ep||1}`, {method:"POST", body:fd});
    const j = await r.json();
    if(j.ok){
      toast("已上传: "+j.path);
      markReadyInMemory(category, name, j.hist_path);
      rerenderCurrent();
    }
    else toast("上传失败: "+(j.error||"未知"));
  }catch(e){toast("上传出错: "+e.message);}
}

// 上传成功后：只更新内存就绪标记 + 原地重渲染当前视图（不刷新页面、不丢 tab/集/Beat 状态）
let curSection = "xiaju";  // 默认虾剧（★ 2026-09-08 剧本先行：成稿→确认→虾料）
function markReadyInMemory(category, name, histPath, newPath, ep){
  const base = name.replace(/\.[^.]+$/, "").replace(/(?:-\d{13})+$/, "");
  const ts = "?t=" + Date.now();
  // ★ newPath：生图队列完成时后端返回的最新文件名（带时间戳，URL 变化防缓存）；缺省用 ?t= 缓存破坏
  const setImg = (cur, np) => np ? String(np).split("?")[0] + ts : (cur||"").split("?")[0] + ts;
  const pushHist = (obj) => {
    if(histPath && obj){
      obj.history = obj.history || [];
      if(!obj.history.includes(histPath)) obj.history.unshift(histPath);
    }
  };
  if(category==="style"){
    const xi = (P.xiage = P.xiage || {});
    if(/^style_keyframe/.test(base)){
      xi.keyframe = (newPath ? String(newPath).split("?")[0] : "assets/styles/style_keyframe.png");
      xi.keyframe_ready = true;
    } else {
      (xi.styles||[]).forEach(s => { if(s.style_id === base){ s.image = setImg(s.image, newPath); s.image_ready = true; pushHist(s); } });
    }
    if(typeof rerenderCurrent === "function") rerenderCurrent();
    return;
  }
  if(category==="character" || category==="identity"){
    (P.xiatang?.characters||[]).forEach(c => {
      if(category==="character"){
        const fn = (c.image||"").split("/").pop().replace(/\.[^.]+$/,"").replace(/(?:-\d{13})+$/,"");
        if(fn === base){ c.image_ready = true; pushHist(c); c.image = setImg(c.image, newPath); }
      }
      (c.identities||[]).forEach(id => {
        // ★ 2026-08-21 四视图角色卡：name=「角色名-身份id-sheet」→ 写入 id.sheet_image/sheet_ready
        if(category==="character" && base === (c.name||"") + "-" + (id.identity_id||"") + "-sheet"){
          id.sheet_ready = true;
          id.sheet_image = setImg(id.sheet_image, newPath);
          return;
        }
        if(category==="identity"){
          const fn = (id.image||"").split("/").pop().replace(/\.[^.]+$/,"").replace(/(?:-\d{13})+$/,"");
          if(fn === base){ id.image_ready = true; pushHist(id); id.image = setImg(id.image, newPath); }
        }
      });
    });
  } else if(category==="scene"){
    (P.xiatang?.scenes||[]).forEach(s => {
      const fn = (s.image||"").split("/").pop().replace(/\.[^.]+$/,"").replace(/(?:-\d{13})+$/,"");
      if(fn === base){ s.image_ready = true; pushHist(s); s.image = setImg(s.image, newPath); }
      // ★ 2026-08-20 多视角：name=「场景名-视角」→ 写入 s.views[视角]（派生图，不写 history）
      for(const _v of SCENE_VIEWS){
        if(base === s.name + "-" + _v){
          s.views = s.views || {}; s.views_ready = s.views_ready || {};
          if(newPath) s.views[_v] = newPath;
          s.views_ready[_v] = true;
          break;
        }
      }
      // ★ 2026-08-22 视距变体：name=「场景名-源标签-前移X米/后移X米/航拍系」→ s.dists[源标签|视距]（独立于 views，不写 history）
      const _dm = String(base).match(/^(.*?)-([^-]+)-((?:前移|后移)\d+米|(?:45°)?高?航拍)$/);
      if(_dm && _dm[1] === s.name){
        const _dk = _dm[2] + "|" + _dm[3];
        s.dists = s.dists || {}; s.dists_ready = s.dists_ready || {};
        if(newPath) s.dists[_dk] = newPath;
        s.dists_ready[_dk] = true;
      }
      // ★ 2026-08-20 上帝视角：平面布局 / 线稿（均不写 history）
      if(base === s.name + "-平面布局"){
        if(newPath) s.plan = newPath;
        s.plan_ready = true;
      } else if(base === s.name + "-线稿"){
        if(newPath) s.plan_sketch = newPath;
        s.plan_sketch_ready = true;
      }
    });
  } else if(category==="prop"){
    (P.xiatang?.props||[]).forEach(p => {
      const fn = (p.image||"").split("/").pop().replace(/\.[^.]+$/,"").replace(/(?:-\d{13})+$/,"");
      if(fn === base){ p.image_ready = true; pushHist(p); p.image = setImg(p.image, newPath); }
    });
  } else if(category==="storyboard"){
    // ★ 2026-08-22 故事板多张：name=story-{ep}-{idx} → 更新 ep.storyboards[idx]；旧 story-{ep} 兼容按集单张
    const sm = /^story-(\d+)-(\d+)$/.exec(base);
    (P.xiajing?.episodes||[]).forEach(_epi => {
      if(ep && _epi.number !== Number(ep)) return;
      if(sm){
        const _sb = (_epi.storyboards||[]).find(s=>String(s.idx)===sm[2]);
        if(_sb){ _sb.ready = true; if(newPath) _sb.image = newPath; }
        else { _epi.storyboards = _epi.storyboards||[]; _epi.storyboards.push({idx:Number(sm[2]), image:newPath||"", ready:true, history:[]}); }
      } else {
        _epi.storyboard_ready = true;
        if(newPath) _epi.storyboard_image = newPath;
      }
    });
  } else if(category === "tingfeng"){
    // ★ 2026-09-01 听风电影故事板（独立模块）：name=tingfeng-{ep}-{idx} → 写 tingfeng.episodes[ep].storyboards[idx]
    const _tfm = /^tingfeng-(\d+)-(\d+)$/.exec(base);
    if(_tfm){
      (P.tingfeng?.episodes||[]).forEach(_te => {
        if(_te.number !== Number(_tfm[1])) return;
        _te.storyboards = _te.storyboards || [];
        let _tsb = _te.storyboards.find(x => x.idx === Number(_tfm[2]));
        if(!_tsb){ _tsb = {idx: Number(_tfm[2])}; _te.storyboards.push(_tsb); }
        _tsb.ready = true;
        if(newPath) _tsb.image = newPath;
      });
    }
  } else if(category === "tf_space_map"){
    // ★ 2026-09-04 听风空间拓扑图按场集合（每场一张）：name=tf-space-map-{ep}-{idx} → 写 space_maps[idx].image/ready；
    //   旧 name=tf-space-map-{ep} 兼容写 space_map_image/ready（旧项目数据不动）——与 server.py mark_ready 同口径
    const _tfsmE = /^tf-space-map-(\d+)$/.exec(base);
    const _tfsmM = /^tf-space-map-(\d+)-(\d+)$/.exec(base);
    (P.tingfeng?.episodes||[]).forEach(_tep => {
      if(_tfsmM && _tep.number === Number(_tfsmM[1])){
        const _idx = Number(_tfsmM[2]);
        if(!Array.isArray(_tep.space_maps)) _tep.space_maps = [];
        while(_tep.space_maps.length <= _idx){
          _tep.space_maps.push({name:"空间拓扑图·场"+(_tep.space_maps.length+1), prompt:"", image:"", ready:false});
        }
        _tep.space_maps[_idx].ready = true;
        if(newPath) _tep.space_maps[_idx].image = setImg(_tep.space_maps[_idx].image, newPath);
      } else if(_tfsmE && _tep.number === Number(_tfsmE[1])){
        _tep.space_map_ready = true;
        _tep.space_map_image = setImg(_tep.space_map_image, newPath);
      }
    });
  } else if(category === "space_map"){
    // ★ 2026-08-31 空间拓扑图（按集单张）：name=space-map-{ep} → 写 ep.space_map_image/space_map_ready
    const _sme = /^space-map-(\d+)$/.exec(base);
    (P.xiajing?.episodes||[]).forEach(_epi => {
      if(_sme && _epi.number !== Number(_sme[1])) return;
      _epi.space_map_ready = true;
      _epi.space_map_image = setImg(_epi.space_map_image, newPath);
    });
  } else if(category === "firstframe" || category === "tailframe"){
    // ★ 2026-08-22 制作页首帧/尾帧（shots 架构）：name=shot{N} → 匹配 ep.shots/edited_shots（与页面显示数据源一致）
    //   修复：此前无此分支 → 任务完成只写内存失败 → 资产位不刷新显示（刷新后从服务端才显示）
    const _sn = String(base).replace(/^shot/i, "").replace(/^0+/, "");
    (P.xiajing?.episodes||[]).forEach(_epi => {
      if(ep && _epi.number !== Number(ep)) return;
      const _arr = _epi.edited_shots || _epi.shots || [];
      _arr.forEach(_sh => {
        if(String(_sh.shot_number||"").replace(/^0+/, "") === _sn){
          const _k = category === "firstframe" ? "firstframe_image" : "tailframe_image";
          _sh[_k] = setImg(_sh[_k], newPath);
        }
      });
    });
  } else if(["sketch","frame","blocking","audio","video"].includes(category)){
    const key = {sketch:"sketch_ready", frame:"frame_ready", blocking:"blocking_ready", audio:"audio_ready", video:"video_ready"}[category];
    const imgKey = {sketch:"sketch_image", frame:"frame_image", blocking:"blocking_image"}[category];
    const bn = parseInt(base.replace(/^beat/i,""), 10);
    (P.xiajing?.episodes||[]).forEach(_epi => {
      if(ep && _epi.number !== Number(ep)) return;   // ★ 2026-08-20 分集：只匹配指定集
      (_epi.beats||[]).forEach(b => {
      if(b.beat_number === bn){
        b[key] = true;
        pushHist(b);
        // ★ 首次生成时 image 字段为空也必须写入新路径（否则要刷新页面才能看到）
        if(imgKey) b[imgKey] = setImg(b[imgKey], newPath);
      }
      });
    });
  }
}
function rerenderCurrent(){
  const de = document.documentElement || {scrollTop:0};
  const sc = (typeof window.scrollY !== "undefined" ? window.scrollY : de.scrollTop) || 0;
  const c = $("content");
  if(curSection==="xiaju"){ c.innerHTML = renderXiaju(); bindXiaju(); }
  else if(curSection==="xialiao"){ c.innerHTML = renderXialiao(); kgInit(); }
  else if(curSection==="xiage"){ c.innerHTML = renderXiage(); bindXiage(); }
  else if(curSection==="xiatang"){ c.innerHTML = renderXiatang(); bindXiatang(); }
  else if(curSection==="xiajing"){
    if(xjCurEp){ c.innerHTML = renderXiajing(); bindXiajing(); }
    else { c.innerHTML = renderXiajingGrid(); bindXiajingGrid(); }
  }
  // ★ 2026-09-01 补听风 section（缺失导致听风页生图完成后不重绘，需手动刷新才显示）
  else if(curSection==="tingfeng"){ c.innerHTML = renderTingFeng(); bindTingFeng(); }
  else if(curSection==="agent"){ c.innerHTML = renderAgent(); bindAgent(); }
  try { window.scrollTo(0, sc); } catch(e){}
}

// ===== 顶部填充（★ 2026-08-22 封装为函数：P 异步加载完成后再调用，否则顶层执行时 P 为空 → 风格/集数空白）=====
function fillTopbar(){
  const _name = P.meta?.name || "{{项目名}}";
  $("title").textContent = _name;                            // 顶部 h1
  document.title = _name + " · 项目台";                    // ★ 2026-08-22 浏览器标签（防 {{项目名}} 字面残留）
  const _sb = document.querySelector(".sb-prof-name");
  if(_sb) _sb.textContent = _name;                            // ★ 2026-08-22 左侧 Logo 下项目名
  $("meta-style").innerHTML = esc(P.meta?.style_label || "");
  $("meta-name").textContent = "共" + (P.xiajing?.episodes?.length || 0) + "集";   // ★ 2026-08-22 第x集 → 共x集
}

// ===== 资产下载窗口（★ 2026-08-22 用户需求：Tab 角色/道具/场景/首帧/尾帧/视频 · 全选 · 打包 zip）=====
// ★ 2026-08-22 用户拍板修正：**tab 级隔离 = 切换 tab 清空全部勾选、下载只打包当前 tab**；不持久化（窗口关闭/刷新即清空）
const ASDL_TABS = ["角色","道具","场景","首帧","尾帧","视频"];
let asdlTab = "角色";
let asdlSel = {};    // tab → [path...]（仅当前 tab 生效；切换清空）
function assetDlItems(tab){
  const Px = P.xiatang || {}, Pj = P.xiajing || {};
  const items = [];
  if(tab === "角色"){
    (Px.characters||[]).forEach(c => {
      if(c.image && c.image_ready) items.push({name: c.name + "（主图）", path: c.image});
      (c.identities||[]).forEach(id => {
        if(id.image && id.image_ready) items.push({name: c.name + "·" + id.name + "（定妆照）", path: id.image});
        if(id.sheet_image && id.sheet_ready) items.push({name: c.name + "·" + id.name + "（四视图）", path: id.sheet_image});
      });
    });
  } else if(tab === "道具"){
    (Px.props||[]).forEach(p => { if(p.image && p.image_ready) items.push({name: p.name, path: p.image}); });
  } else if(tab === "场景"){
    (Px.scenes||[]).forEach(s => {
      if(s.image && s.image_ready) items.push({name: s.name + "（主图）", path: s.image});
      // ★ 2026-08-22 多角度 / 视距 / 平面布局 / 线稿 全部纳入下载
      Object.keys(s.views || {}).forEach(v => { if(s.views[v]) items.push({name: s.name + "·" + v, path: s.views[v]}); });
      Object.keys(s.dists || {}).forEach(k => { if(s.dists[k]) items.push({name: s.name + "·" + String(k).replace("|","·"), path: s.dists[k]}); });
      if(s.plan && s.plan_ready) items.push({name: s.name + "·平面布局", path: s.plan});
      if(s.plan_sketch && s.plan_sketch_ready) items.push({name: s.name + "·线稿", path: s.plan_sketch});
    });
  } else if(tab === "首帧" || tab === "尾帧" || tab === "视频"){
    (Pj.episodes||[]).forEach(ep => {
      (ep.shots||[]).forEach(sh => {
        const tag = tab === "首帧" ? "firstframe_image" : (tab === "尾帧" ? "tailframe_image" : "video");
        if(sh[tag]) items.push({name: `第${ep.number}集·镜${sh.shot_number}·${tab}`, path: sh[tag], type: (tab==="视频") ? "video" : "image"});
      });
      // ★ 2026-08-24：视频 tab 同时收集「故事板多镜视频」（落库在 storyboards[idx].video_segments[seg].video）
      if(tab === "视频"){
        (ep.storyboards||[]).forEach(sb => {
          (sb.video_segments||[]).forEach((seg, si) => {
            if(seg && seg.video) items.push({name: `第${ep.number}集·故事板${sb.idx}·段${si+1}`, path: seg.video, type: "video"});
          });
        });
      }
    });
  }
  return items;
}
function openAssetDownload(){
  const m = $("assetdl"); if(!m) return;
  const tabs = ASDL_TABS.map(t => `<button class="pill" style="font-size:12px;padding:6px 12px;${t===asdlTab?'background:var(--acc);color:#fff':''}" type="button" onclick="asdlSwitch('${t}')">${t}</button>`).join("");
  $("asdl-tabs").innerHTML = tabs;
  m.classList.add("open");
  asdlRender();
}
function closeAssetDownload(){ const m = $("assetdl"); if(m) m.classList.remove("open"); }
function asdlSwitch(t){
  asdlTab = t;
  asdlSel = {};    // ★ 2026-08-22 切 tab 清空全部勾选（tab 级隔离）
  asdlRender();
}
function asdlRender(){
  // tab 高亮
  $("asdl-tabs").innerHTML = ASDL_TABS.map(t => `<button class="pill" style="font-size:12px;padding:6px 12px;${t===asdlTab?'background:var(--acc);color:#fff':''}" type="button" onclick="asdlSwitch('${t}')">${t}</button>`).join("");
  const items = assetDlItems(asdlTab);
  const sel = asdlSel[asdlTab] || (asdlSel[asdlTab] = []);
  const grid = $("asdl-grid"), empty = $("asdl-empty");
  if(!items.length){ grid.innerHTML = ""; empty.style.display = "block"; }
  else {
    empty.style.display = "none";
    // ★ 2026-08-22 图片用稳定 src（不加时间戳）：asdlRender 全量重建时不触发全部图片重新下载（否则勾选一次闪一遍像刷新页面）
    // ★ 2026-08-24 视频项用 <video> 预览；图片/视频均支持双击全屏查看（asdlPreview）
    grid.innerHTML = items.map(it => {
      const on = sel.includes(it.path);
      const isVid = it.type === "video";
      const media = isVid
        ? `<video src="${esc(it.path)}" style="width:100%;height:100px;object-fit:cover;display:block;background:#000" preload="metadata" onerror="this.style.opacity=.2"></video>`
        : `<img src="${esc(it.path)}" style="width:100%;height:100px;object-fit:cover;display:block" onerror="this.style.opacity=.2">`;
      return `<div data-p="${esc(it.path)}" style="border:2px solid ${on?'var(--acc)':'var(--line)'};border-radius:8px;overflow:hidden;background:#fff;cursor:pointer" onclick="assetDlToggle('${asdlTab}','${esc(it.path)}')" ondblclick="asdlPreview('${isVid?'video':'image'}','${esc(it.path)}')" title="双击全屏查看">
        ${media}
        <div style="font-size:11px;padding:4px 6px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;color:${on?'var(--acc)':'#475569'}" title="${esc(it.name)}">${on?'☑ ':'☐ '}${esc(it.name)}</div>
      </div>`;
    }).join("");
  }
  $("asdl-all").textContent = (sel.length && sel.length === items.length) ? "☑ 取消全选" : "☑ 全选";
  asdlCount();
}
function assetDlToggle(tab, path){
  const sel = asdlSel[tab] || (asdlSel[tab] = []);
  const i = sel.indexOf(path);
  if(i >= 0) sel.splice(i,1); else sel.push(path);
  // ★ 2026-08-22 局部更新卡片样式（不重建 grid，避免全部图片重载）
  const card = document.querySelector('#asdl-grid div[data-p="' + CSS.escape(path) + '"]');
  if(card){
    const on = sel.includes(path);
    card.style.border = "2px solid " + (on ? "var(--acc)" : "var(--line)");
    const nm = card.querySelector("div[style*='font-size:11px']");
    if(nm){ nm.style.color = on ? "var(--acc)" : "#475569"; nm.textContent = (on?"☑ ":"☐ ") + nm.title; }
  }
  const items = assetDlItems(tab);
  $("asdl-all").textContent = (sel.length && sel.length === items.length) ? "☑ 取消全选" : "☑ 全选";
  asdlCount();
}
function assetDlToggleAll(){
  const items = assetDlItems(asdlTab);
  const sel = asdlSel[asdlTab] || (asdlSel[asdlTab] = []);
  const all = items.every(it => sel.includes(it.path));
  if(all){ asdlSel[asdlTab] = []; }
  else { asdlSel[asdlTab] = items.map(it => it.path); }
  asdlRender();
}
function asdlCount(){
  // ★ 2026-08-22 计数仅当前 tab（tab 级下载）
  $("asdl-count").textContent = "已选 " + ((asdlSel[asdlTab]||[]).length) + " 张";
}
function assetDlStart(){
  // ★ 2026-08-22 下载仅打包当前 tab 选中（tab 级隔离）
  // ★ 2026-08-23 文件名用页面展示名称（items 带 name），不再用原始文件 basename
  const sel = asdlSel[asdlTab] || [];
  if(!sel.length){ toast("未选择任何图片"); return; }
  if(!IS_SERVER){ toast("需服务模式（双击启动项目台.bat）"); return; }
  const items = assetDlItems(asdlTab).filter(it => sel.includes(it.path)).map(it => ({path: it.path, name: it.name}));
  fetch("/download-zip", {method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify({items})})
    .then(r => { if(!r.ok) throw new Error(r.status); return r.blob(); })
    .then(blob => {
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = "资产下载_" + new Date().toISOString().slice(0,19).replace(/[:T]/g,"-") + ".zip";
      document.body.appendChild(a); a.click(); a.remove();
      toast("✅ 已打包下载 " + items.length + " 张图片");
    }).catch(() => toast("❌ 下载失败（服务异常）"));
}
// ★ 2026-08-24 双击全屏查看：图片放大、视频全屏播放
function asdlPreview(type, path){
  const m = $("asdl-preview");
  if(!m) return;
  let html;
  if(type === "video"){
    html = `<video src="${esc(path)}" controls autoplay playsinline style="max-width:92vw;max-height:88vh;background:#000;border-radius:8px"></video>`;
  } else {
    html = `<img src="${esc(path)}" style="max-width:92vw;max-height:88vh;object-fit:contain;border-radius:8px;background:#000" onerror="this.style.opacity=.3">`;
  }
  m.querySelector(".asdl-pv-body").innerHTML = html;
  m.classList.add("open");
}
function asdlPreviewClose(){
  const m = $("asdl-preview");
  if(!m) return;
  // ★ 暂停视频，避免后台继续播放
  const v = m.querySelector("video");
  if(v){ try{ v.pause(); }catch(e){} }
  m.classList.remove("open");
  m.querySelector(".asdl-pv-body").innerHTML = "";
}

// ===== 左侧菜单 =====
document.querySelectorAll("#sidebar .sb-item").forEach(el => {
  el.addEventListener("click", () => {
    document.querySelectorAll("#sidebar .sb-item").forEach(s => s.classList.remove("active"));
    el.classList.add("active");
    renderSection(el.dataset.section);
  });
});


// ===== 批量生图（★ 2026-08-19 循环入队；2026-08-20 去掉全局 batchLock——改为每任务独立 watch，可并发多批量/边批量边单张）=====
// 各类别批量默认尺寸（设置里 default_sizes 优先，键：character/scene/prop/storyboard_frame）
const BATCH_SIZE_MAP = {storyboard:"1536x768", frame:"1536x768", scene:"1536x768", key_scene:"1536x768", prop:"1280x960", character:"960x1280"};
const BATCH_LABEL = {storyboard:"故事板", scene:"场景", key_scene:"关键场景", prop:"道具", character:"角色主图"};

function getCurEp(){
  // 当前选中的集（分镜脚本 Tab 由 renderShotsTab(ep) 渲染，ep 来自 episodes）
  const eps = (P.xiajing?.episodes)||[];
  const cur = eps.find(e => e.number === xjCurEp) || eps[0];
  return cur;
}

// 兼容入口：故事板 Tab 按钮 → 批量生成故事板图（勾选分镜 6/9 格 → 整张故事板图，走任务队列）
function batchGenStoryboard(){ return batchGenImages("storyboard"); }
// ★ 2026-08-22 故事板拼板：返回容量序列（9/6 格板）——板数最少 + 总格数最少，末板不足也生成（留白）
//   37→[9,9,9,6,6]（第5板 4beat+2白）；38→[9,9,9,6,6]；39→[9,9,9,6,6]满；40→[9,9,9,9,6]；43→[9,9,9,9,9]；61→[9×7]
function storyBoardSplit(total){
  let best = null;
  for(let b=0; b<=Math.floor(total/6); b++){
    const rem = total - 6*b;
    const a = Math.max(0, Math.ceil(rem/9));
    const tot = 9*a + 6*b;
    if(tot < total) continue;
    const boards = [];
    for(let i=0;i<a;i++) boards.push(9);
    for(let i=0;i<b;i++) boards.push(6);
    if(!best || boards.length < best.boards.length || (boards.length===best.boards.length && tot < best.tot)){
      best = {boards, tot};
    }
  }
  return best ? best.boards : [9];
}

async function batchGenImages(cat){
  if(!IS_SERVER){ toast("AI 生成需要服务模式：请双击「启动项目台.bat」"); return; }
  const lbl = BATCH_LABEL[cat] || cat;
  // 收集目标（跳过已生成）
  let items = [];
  if(cat === "storyboard"){
    // ★ 2026-08-22 故事板多张：拼板分组（storyBoardSplit：9/6 格，末板不足也生成留白），name=story-{ep}-{idx}
    const ep = getCurEp();
    const epN = ep?.number || 1;
    const shots = xjShots(ep) || [];
    const caps = storyBoardSplit(shots.length);
    const groups = [];
    let sidx = 0;
    caps.forEach((cap, gi)=>{
      const cnt = Math.min(cap, shots.length - sidx);
      const idxs = [];
      for(let k=sidx; k<sidx+cnt; k++) idxs.push(k);
      sidx += cnt;
      const bp = (typeof buildStoryPrompt === "function") ? buildStoryPrompt(ep, idxs) : null;
      if(!bp) return;
      const gno = gi + 1;
      const sb = (ep.storyboards||[]).find(s=>s.idx===gno);
      if(sb && sb.ready) return;
      groups.push({idx:gno, prompt:bp.prompt, ep:epN});
    });
    items = groups.map(g => ({name:"story-"+epN+"-"+g.idx, prompt:g.prompt, ep:epN}));
  } else if(cat === "scene"){
    // ★ 2026-08-22 修复：已生成判断用 image_ready（image 字段恒有 latest_versioned 路径值，不能作为判断依据）
    items = (P.xiatang?.scenes||[]).filter(s => !s.image_ready).map(s => ({name:s.name, prompt:s.prompt||"", ep:1}));
  } else if(cat === "key_scene"){
    // ★ 2026-08-22 关键场景批量生图（画面素材）：未生成的 key_scenes（prompt 兼容字符串/对象两种形态）
    items = (P.xiatang?.key_scenes||[]).filter(k => !k.image_ready).map(k => {
      const p = typeof k.prompt === "string" ? k.prompt
        : (k.prompt && typeof k.prompt === "object" ? Object.values(k.prompt).filter(Boolean).join("\n") : "");
      return {name:k.name, prompt:p, ep:1};
    });
  } else if(cat === "prop"){
    items = (P.xiatang?.props||[]).filter(p => !p.image_ready).map(p => ({name:p.name, prompt:p.prompt||"", ep:1}));
  } else if(cat === "character"){
    // ★ 只有角色主图（身份图需要锁脸垫主图，不在批量范围）；★ 2026-08-22 修复：用 image_ready 判断已生成
    items = (P.xiatang?.characters||[]).filter(c => !c.image_ready).map(c => ({name:c.name, prompt:c.prompt||"", ep:1}));
  }
  if(!items.length){ toast("✅ " + lbl + "已全部生成"); return; }
  const msg = cat === "storyboard"
    ? `将为当前集生成 1 张故事板图（${items[0].prompt ? "已按勾选镜头生成提示词" : ""}），确认开始？`
    : `将为 ${items.length} 个未生成的${lbl}批量生图（已生成自动跳过，${cat === "character" ? "仅主图，不含身份图" : "无参考图"}），同时最多执行 5 个，确认开始？`;
  if(!confirm(msg)) return;
  // 拉取渠道配置：第一个已配置渠道 + 默认模型 + 类别默认尺寸（设置优先）
  let model = "", channelId = "", size = BATCH_SIZE_MAP[cat] || "1536x768";
  try{
    const cfg = await fetch("/gen-config").then(r => r.json());
    const ch = (cfg.channels||[]).find(c => c.configured);
    if(!ch){ toast("❌ 未配置可用生图渠道，请先到 ⚙ 设置完善"); return; }
    channelId = ch.id;
    // models 可能是 [{name,script}] 对象数组或字符串数组
    const m0 = (ch.models||[])[0] || "";
    model = (typeof m0 === "string") ? m0 : (m0.name || "");
    if(!model){ toast("❌ 渠道无可用模型"); return; }
    const ds = cfg.default_sizes || {};
    const dk = cat === "storyboard" ? "storyboard_frame" : cat;   // 设置键：storyboard/frame 合并为 storyboard_frame
    size = ds[dk] || BATCH_SIZE_MAP[cat] || "1536x768";
  } catch(e){ toast("❌ 读取渠道配置失败"); return; }
  // 入队（★ 2026-08-20：每个任务独立 watch，批量期间可继续提交其他生图）
  // ★ 2026-08-22：批量完成汇总——收集 task_id，全部完成后统一提示「已全部完成」
  toast(`⏳ 开始批量生成${lbl}（${items.length} 个，并发 5，完成后逐个自动应用）…`);
  let queued = 0, fail = 0;
  const taskIds = [];
  let done = 0, succ = 0, fdone = 0;
  const onBatchDone = (st) => {
    done++;
    if(st === "success") succ++; else fdone++;
    if(done >= taskIds.length){
      toast(fdone ? `✅ ${lbl}已全部完成：成功 ${succ} 个${fdone ? `，失败 ${fdone} 个` : ""}` : `✅ ${lbl}已全部完成（${succ} 个）`);
    }
  };
  for(const it of items){
    const ok = await batchEnqueue(cat, it.name, it.prompt, model, size, channelId, undefined, it.ep || 1, onBatchDone);
    if(ok){ queued++; taskIds.push(ok); } else { fail++; }
  }
  if(fail){
    toast(`⚠️ 批量入队完成：成功 ${queued} 个，失败 ${fail} 个（失败的可在任务面板重试）`);
  } else if(queued){
    toast(`✅ ${lbl}已全部入队（${queued} 个），生成完成后自动提示`);
  }
}

// 单个入队请求：满队列(429)时等待 3s 重试（最多 20 次）；入队成功即注册独立 watch（★ 2026-08-20 无全局锁，可并发多批量）
function sleep(ms){ return new Promise(r => setTimeout(r, ms)); }
async function batchEnqueue(cat, name, prompt, model, size, channelId, images, ep, onDone){
  // ★ 2026-08-21 修复：参考图统一转 data URL——相对路径（assets/...）→ fetch → base64，
  //   避免路径字符串被后端当裸 base64 解码报「images[0] base64 无效」（覆盖场景视角/上帝视角/四视图卡等一键入口）
  images = await Promise.all((images||[]).map(async it => {
    const s = String(it||"");
    if(!s || s.startsWith("data:") || s.startsWith("http://") || s.startsWith("https://")) return s;
    try{
      const r = await fetch(s + (s.includes("?")?"&":"?") + "t=" + Date.now());
      if(!r.ok) return s;
      const blob = await r.blob();
      return await new Promise(res => {
        const rd = new FileReader();
        rd.onload = () => res(rd.result || s);
        rd.onerror = () => res(s);
        rd.readAsDataURL(blob);
      });
    }catch(e){ return s; }
  }));
  for(let i=0;i<20;i++){
    try{
      const r = await fetch("/gen-image", {method:"POST", headers:{"Content-Type":"application/json"},
        body: JSON.stringify({category:cat, name, prompt, model, size, channel_id:channelId, images: images || [], batch:true, ep: ep || 1})});
      const j = await r.json();
      if(j.ok){ genWatchTask(j.task_id, cat, name, ep || 1, onDone); return j.task_id; }
      if(j.queue_full){ await sleep(3000); continue; }
      return false;
    } catch(e){ await sleep(3000); }
  }
  return false;
}


// ===== 底部任务队列面板（任务中 / 任务完成，轮询 /tasks）=====
let taskbarTimer = null;
function initTaskbar(){
  const bar = $("taskbar");
  if(!bar) return;
  if(taskbarTimer) clearInterval(taskbarTimer);
  taskbarTimer = setInterval(() => {
    if(!IS_SERVER) return;               // 静态模式无队列
    fetch("/tasks").then(r => r.json()).then(res => {
      if(!res.ok) return;
      taskbarUpdate(res);
    }).catch(() => {});
  }, 1000);
}
function taskbarUpdate(res){
  const bar = $("taskbar");
  const line = $("taskbar-line");
  const badge = $("taskbar-badge");
  if(!bar || !line || !badge) return;
  const running = res.running || [];
  const done = res.done || [];
  const stats = res.stats || {};
  const isOpen = bar.classList.contains("open");
  // 一行模式：最新状态（优先任务中，其次最近完成）
  if(running.length){
    const r0 = running[0];
    const ts = r0.status === "queued" ? r0.created_at : (r0.started_at || r0.created_at);
    line.textContent = `⏳ ${r0.status === "queued" ? "排队中" : "生成中"} ${r0.name} ${ts ? fmtClock(ts) : ""}${r0.duration ? " " + r0.duration + "s" : ""}…（${running.length} 个任务中）`;
  } else if(done.length){
    const d0 = done[done.length - 1];
    line.textContent = `${d0.status === "success" ? "✅" : "❌"} ${d0.name} ${d0.status === "success" ? "完成" : "失败"} ${d0.finished_at ? fmtClock(d0.finished_at) : ""}${d0.duration ? " " + d0.duration + "s" : ""}`;
  } else {
    line.textContent = "无任务（队列上限 " + (stats.max || 5) + "）";
  }
  line.title = line.textContent;
  // 角标：任务中数量（满排队上限 60 变橙色，上限值来自后端 stats.max；★ 2026-08-20 普通/批量统一 60）
  const rn = running.length;
  badge.textContent = rn > 0 ? String(rn) : "0";
  badge.classList.toggle("warn", rn >= (stats.max || 5));
  // 展开渲染两块
  if(isOpen){
    const elRun = $("tb-running"), elDone = $("tb-done");
    const nRun = $("tb-running-n"), nDone = $("tb-done-n");
    if(!elRun || !elDone) return;
    nRun.textContent = String(running.length);
    nDone.textContent = String(done.length);
    elRun.innerHTML = running.length ? running.map(t => taskRow(t)).join("") :
      `<div class="tb-empty">暂无任务中</div>`;
    elDone.innerHTML = done.length ? [...done].reverse().map(t => taskRow(t)).join("") :
      `<div class="tb-empty">暂无完成任务</div>`;
  }
}
function taskRow(t){
  const stCls = t.status; // queued / running / success / failed
  const stTxt = t.status === "queued" ? "排队中" : t.status === "running" ? "生成中" : t.status === "success" ? "✅ 完成" : "❌ 失败";
  // 时间：排队/生成中显示开始时间，完成显示完成时间
  const ts = t.status === "queued" ? t.created_at : t.status === "running" ? (t.started_at || t.created_at) : t.finished_at;
  const tm = ts ? fmtClock(ts) : "";
  const dur = t.duration != null ? ` <span class="dur">${t.duration}s</span>` : "";
  const err = t.error ? `<span class="err" title="${esc(t.error)}">${esc(String(t.error).slice(0, 30))}</span>` : "";
  // 任务中：名称后追加 size(→ratio) 垫图数（★ 2026-08-22 images 是数组，显示数组长度）
  const _imgN = Array.isArray(t.images) ? t.images.length : ((typeof t.images === "number") ? t.images : 0);
  const meta = (t.status === "queued" || t.status === "running")
    ? ` <span class="meta">${esc(t.size || "")}${t.ratio ? "（→" + esc(t.ratio) + "）" : ""} 垫图数=${_imgN}</span>` : "";
  return `<div class="tb-task ${stCls}" title="${esc(t.name)}｜${stTxt}${t.error ? "｜" + esc(t.error) : ""}">
    <span class="st"></span><span class="nm">${esc(t.name)}</span>${meta}<span class="tm">${tm}${dur}</span>${err}</div>`;
}
function fmtClock(ts){
  if(!ts) return "";
  const d = new Date(ts * 1000);
  const p = n => String(n).padStart(2, "0");
  return `${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
}
function toggleTaskbar(){
  const bar = $("taskbar");
  if(!bar) return;
  const isOpen = bar.classList.toggle("open");
  const mini = $("taskbar-mini");
  if(mini) mini.style.display = isOpen ? "inline-flex" : "none";
  // 展开时立即拉一次
  if(isOpen && IS_SERVER) fetch("/tasks").then(r => r.json()).then(res => { if(res.ok) taskbarUpdate(res); }).catch(() => {});
}
