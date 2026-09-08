// ===== 虾格（当前风格页：无预设库、无风格列表；每次按剧情新做一种风格或上传参考图反推；含全剧定风格图）=====
// ★ v3.1.0 改造：预设库已废弃，页面只呈现"当前确定的这一种风格"；左=当前风格+全剧风格图，右=做新风格工作区+三步向导。

function renderXiage(){
  const xi = P.xiage || {styles: [], current: ""};
  const styles = xi.styles || [];
  // 只认"当前风格"：优先 xi.current，其次唯一一张，否则空
  const cur = styles.find(s => s.style_id === xi.current) || (styles.length === 1 ? styles[0] : {}) || {};
  const hasCur = !!cur.style_id;
  const isCurrent = hasCur && (cur.style_id === xi.current);
  const KF = xi.keyframe || "assets/styles/style_keyframe.png";

  return `
  <div class="xiage-page">
    <div class="xiage-left">
      <div class="xiage-head">🎨 当前风格 ${isCurrent?'<span class="pill" style="background:#ecfdf5;color:#059669;border:1px solid #a7f3d0">✓ 已确认</span>':(hasCur?'<span class="pill" style="color:var(--mut)">未确认</span>':'<span class="pill" style="color:var(--mut)">尚未确定</span>')}</div>
      ${hasCur ? `
        <div class="xiage-imgwrap">
          ${cur.image_ready
            ? `<img src="${esc(cur.image)}?t=${Date.now()}" class="xiage-img">`
            : `<div class="xiage-img xiage-ph">风格预览图（人物近景含环境）<br><span style="opacity:.6;font-size:11px">提示词可让 AI 生成，图片由用户外部生成后放入 assets/styles/</span></div>`}
        </div>
        <div class="xiage-kv"><b>${esc(cur.style_label||cur.style_id)}</b><div class="v">style_id：${esc(cur.style_id)}</div></div>
        <div class="xiage-kv"><b>style_tag（风格标签）</b><div class="v">${esc(cur.style_tag)}</div></div>
        <div class="xiage-kv"><b>style_instructions（风格指令）</b><div class="v">${esc(cur.style_instructions)}</div></div>
        <div class="xiage-kv"><b>avoid_instructions（避免指令）</b><div class="v">${esc(cur.avoid_instructions)}</div></div>
        ${!isCurrent ? `<button class="pill primary" style="margin-top:8px" onclick="xiageConfirm('${esc(cur.style_id)}')">✓ 确认使用此风格</button>` : ""}
        ${hasCur ? `<button class="pill" style="margin-top:8px;margin-left:6px" onclick="xiageExportStyle('${esc(cur.style_id)}')">📤 导出风格包</button>` : ""}
      ` : `<div style="color:var(--mut);padding:16px;font-size:12px;line-height:1.8">本剧还没有确定风格。<br>去右侧「做一种新风格」——按本剧剧情生成、或上传参考图反推，然后走三步向导确认。</div>`}

      <div class="xiage-cd" style="border-top:1px solid var(--line);margin-top:14px;padding-top:12px">
        <div class="xiage-head">🖼 全剧风格图（美术圣经锚）</div>
        <div class="xiage-imgwrap">
          <img src="${KF}?t=${Date.now()}" class="xiage-img" onerror="this.style.display='none';this.nextElementSibling.style.display='flex';">
          <div class="xiage-img xiage-ph" style="display:none">尚未生成全剧风格图<br><span style="opacity:.6;font-size:11px">一张图示范 人物/环境/光影/色彩/质感 五要素，供虾塘资产与虾镜统一引用</span></div>
        </div>
        <button class="pill primary" style="width:100%;margin-top:8px" onclick="xiageGenKeyframe()">🎨 生成全剧风格图</button>
        <div style="font-size:11px;color:var(--mut);margin-top:4px">点击弹出生图窗，已按当前风格预填定风格提示词，可微调后生成（存为 assets/styles/style_keyframe.png）。</div>
      </div>
    </div>

    <div class="xiage-right">
      <div class="xiage-head">＋ 做一种新风格 <span style="color:var(--mut);font-weight:400;font-size:11px">无预设库 · 每次按剧情新做，或上传参考图反推；已验证风格库在虾格①风格类型时由对话选择，不在本页列出</span></div>
      <div class="xiage-new">
        <input id="xiage-n-name" placeholder="style_id（英文/拼音，如 inkwash_xuanhuan_horror）" style="width:100%;box-sizing:border-box;margin-bottom:6px;padding:6px 8px;border:1px solid var(--line);border-radius:8px;font-size:12px">
        <input id="xiage-n-label" placeholder="中文名（如 新中式水墨玄幻恐怖）" style="width:100%;box-sizing:border-box;margin-bottom:6px;padding:6px 8px;border:1px solid var(--line);border-radius:8px;font-size:12px">
        <textarea id="xiage-n-topic" placeholder="本剧剧情/题材/世界观摘要（AI 据此生成全新风格三要素）" style="width:100%;box-sizing:border-box;margin-bottom:6px;padding:6px 8px;border:1px solid var(--line);border-radius:8px;font-size:12px;min-height:64px"></textarea>
        <button class="pill primary" style="width:100%;margin-bottom:6px" onclick="xiageGenByTopic()">🤖 按剧情生成新风格</button>
        <label class="up" style="display:flex;align-items:center;justify-content:center;gap:6px;border:1px dashed var(--line);border-radius:8px;padding:8px;font-size:12px;color:var(--mut);cursor:pointer">📷 上传参考图反推风格（走三步确认）
          <input type="file" class="upfile" accept="image/*" onchange="xiageUploadRef(this)" style="display:none"></label>
        <div id="xiage-ref-box" style="margin-top:6px"></div>
      </div>

      <div class="xiage-cd" style="border-top:1px solid var(--line);margin-top:14px;padding-top:12px">
        <div class="xiage-head">🎬 创作方向（三步向导）<span style="color:var(--mut);font-weight:400;font-size:11px">①风格(按剧情/参考图) → ②视觉参考 → ③影片基调</span></div>
        <div class="xiage-kv"><b>① 风格类型</b><div class="v">${hasCur?esc(cur.style_label||cur.style_id):'<span style="opacity:.6;color:var(--mut)">未确定</span>'}</div></div>
        <div class="xiage-kv"><b>② 视觉参考</b><div class="v">${(xi.visual_references||[]).map(r=>{const n=typeof r==='string'?r:((r&&(r.name||r.work))||'');const no=(typeof r==='object'&&r&&r.note)?(' — '+esc(r.note)):'';return '· '+esc(n)+no;}).join('<br>') || '<span style="opacity:.6;color:var(--mut)">未选定（三步向导第二步确认）</span>'}</div></div>
        <div class="xiage-kv"><b>③ 影片基调</b><div class="v">${(()=>{const t=xi.tonal_direction;if(!t)return '<span style="opacity:.6;color:var(--mut)">未选定（三步向导第三步确认）</span>';if(typeof t==='object')return esc((t.name||'')+(t.note?' — '+t.note:''));return esc(t);})()}</div></div>
      </div>
      <div id="xiage-gen-result"></div>
    </div>
  </div>`;
}
function bindXiage(){ /* 内联 onclick，无需额外绑定 */ }

// ★ v3.4.0-风格库 导出当前风格为 zip（含库条目 json + 预览图 + 定风格图），可解压丢进 skill styles-library/
function xiageExportStyle(sid){
  if(!sid){ toast("当前无风格可导出"); return; }
  window.location.href = "/api/export-style?style_id=" + encodeURIComponent(sid);
}

function xiageConfirm(sid){
  if(!IS_SERVER){ toast("需服务模式（双击启动项目台.bat）"); return; }
  fetch("/styles/confirm?style_id=" + encodeURIComponent(sid), {method:"POST"})
    .then(r => r.json())
    .then(res => { if(res.ok){ toast("✅ 已确认风格: " + sid); reloadDataJs(); } else toast("❌ " + (res.error||"确认失败")); })
    .catch(e => toast("❌ 请求失败: " + e.message));
}

// 按剧情生成全新风格三要素（无预设，走 agent-chat 文本模型）
function xiageGenByTopic(){
  const sid = ($("#xiage-n-name")||{value:""}).value.trim();
  const label = ($("#xiage-n-label")||{value:""}).value.trim();
  const topic = ($("#xiage-n-topic")||{value:""}).value.trim();
  if(!topic){ toast("请填写本剧剧情/题材摘要"); return; }
  if(!sid){ toast("请填写 style_id"); return; }
  if(!IS_SERVER){ toast("需服务模式（双击启动项目台.bat）"); return; }
  const out = $("xiage-gen-result");
  out.innerHTML = '<div style="color:var(--mut);font-size:12px">⏳ AI 正在按剧情生成全新风格三要素…</div>';
  const sys = "你是专业 AI 绘图风格设计师。根据用户提供的本剧剧情/题材/世界观，为这部剧【从零设计一种全新的、贴合剧情的】画面风格（不要套用任何现成预设）。输出风格三要素 JSON（只输出 JSON）。规范：style_tag 只描述介质+成色（大写，禁时代/地域/服化道词如 MODERN/ANCIENT/古装/民国）；style_instructions 以 Create a 开头，按 总述→光影调色→场景环境→主体→技术质感 顺序；avoid_instructions 按 风格边界→质感→技术→人体→杂物 5 类排除，全部否定句式。";
  const usr = `风格 style_id: ${sid}\n中文名: ${label||sid}\n本剧剧情/题材/世界观: ${topic}\n请输出 JSON: {"style_id":"${sid}","style_label":"...","style_tag":"...","style_instructions":"Create a ...","avoid_instructions":"...","recommended_for":"..."}`;
  fetch("/agent-chat", {method:"POST", headers:{"Content-Type":"application/json"},
    body: JSON.stringify({messages:[{role:"user",content:usr}], system:sys, stream:false, model:"", temperature:0.5})})
    .then(r => r.json())
    .then(res => {
      const txt = (res && (res.content || res.message?.content || res.choices?.[0]?.message?.content || res.text)) || "";
      const m = txt.match(/\{[\s\S]*\}/);
      let s = {};
      try{ s = JSON.parse(m ? m[0] : txt); }catch(e){ out.innerHTML = '<div style="color:#b91c1c;font-size:12px">解析失败：' + esc(txt.slice(0,400)) + '</div>'; return; }
      s.style_id = s.style_id || sid; s.style_label = s.style_label || (label||sid);
      xiageShowGen(s);
    })
    .catch(e => out.innerHTML = '<div style="color:#b91c1c;font-size:12px">❌ ' + esc(e.message) + '</div>');
}
function xiageShowGen(s){
  const out = $("xiage-gen-result");
  out.innerHTML = `
    <div style="border:1px solid var(--line);border-radius:10px;padding:10px;margin-top:8px;background:#fff">
      <b>${esc(s.style_label||"新风格")} 三要素预览</b>
      <div class="xiage-kv"><b>style_tag</b><div class="v">${esc(s.style_tag)}</div></div>
      <div class="xiage-kv"><b>风格指令</b><div class="v">${esc(s.style_instructions)}</div></div>
      <div class="xiage-kv"><b>避免指令</b><div class="v">${esc(s.avoid_instructions)}</div></div>
      ${s.recommended_for ? `<div class="xiage-kv"><b>适用</b><div class="v">${esc(s.recommended_for)}</div></div>` : ""}
      <button class="pill primary" onclick='xiageSave(${JSON.stringify(JSON.stringify(s))})'>💾 保存并去确认此风格</button>
    </div>`;
}
function xiageSave(jsonStr){
  let s = {};
  try{ s = JSON.parse(jsonStr); }catch(e){ toast("数据异常"); return; }
  if(!IS_SERVER){ toast("需服务模式"); return; }
  fetch("/styles/save", {method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify(s)})
    .then(r => r.json())
    .then(res => { if(res.ok){ toast("✅ 已保存 " + res.style_id + "，请在左侧点『确认使用此风格』"); reloadDataJs(); } else toast("❌ " + (res.error||"保存失败")); })
    .catch(e => toast("❌ " + e.message));
}
// 上传参考图反推：上传后交 AI 反推风格三要素（仍走三步确认）
function xiageUploadRef(input){
  const f = input.files && input.files[0];
  if(!f){ toast("未选择文件"); return; }
  const name = "ref_" + Date.now() + "." + (f.name.split(".").pop() || "png");
  const fd = new FormData(); fd.append("file", f, name);
  if(!IS_SERVER){ toast("需服务模式（双击启动项目台.bat）"); return; }
  fetch("/upload?category=style&name=" + encodeURIComponent(name), {method:"POST", body: fd})
    .then(r => r.json())
    .then(j => {
      const box = $("xiage-ref-box");
      if(j.ok){
        box.innerHTML = `<img src="${esc(j.hist_path||j.path)}?t=${Date.now()}" style="max-width:100%;border-radius:8px;border:1px solid var(--line)"><div style="font-size:11px;color:var(--mut);margin-top:4px">参考图已上传。请把这张图发给 AI（对话中粘贴路径或截图），让 AI 反推风格三要素 → 保存 → 走三步向导确认。</div>`;
        toast("参考图已上传: " + (j.hist_path||j.path));
      } else box.innerHTML = '<div style="color:#b91c1c;font-size:12px">上传失败: ' + esc(j.error||"") + '</div>';
    })
    .catch(e => toast("上传出错: " + e.message));
}

// 生成"全剧定风格图"：按当前风格 + 视觉参考 infusion 组装提示词，弹出生图窗（存 assets/styles/style_keyframe.png）
function xiageGenKeyframe(){
  if(!IS_SERVER){ toast("需服务模式（双击启动项目台.bat）"); return; }
  const xi = P.xiage || {};
  const styles = xi.styles || [];
  const cur = styles.find(s => s.style_id === xi.current) || (styles.length===1?styles[0]:null);
  if(!cur){ toast("先确定一种风格，再生成全剧风格图"); return; }
  const inf = (xi.visual_references||[]).map(r => (r && r.infusion) ? r.infusion : "").filter(Boolean).join("; ");
  const scene = "A cinematic wide 16:9 establishing frame that defines the whole series' art direction, covering character, environment, light, color and texture. Exterior scene with a clearly-lit human figure in the foreground — face, costume and fabric texture visible, NOT a silhouette — plus rich environment depth and the world's signature weather and light.";
  const prompt = [scene, cur.style_instructions || "", (inf ? ("Visual language references: " + inf) : "")].filter(Boolean).join(" ");
  const cn = "全剧定风格图（美术圣经锚）：一张图示范 人物/环境/光影/色彩/质感 五要素；外景优先、人物清晰非剪影、只放克制级奇观。已按当前风格预填，可微调后生成。";
  openGenModal("style", "style_keyframe", prompt, null, cn);
}
