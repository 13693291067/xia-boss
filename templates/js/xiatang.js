// ===== 虾塘 =====
let xtCurTab = "character";
let xtCurSel = null;
const SCENE_VIEWS = ["正面", "左侧", "右侧", "背面", "斜侧", "俯视", "45°俯视全景"];  // ★ 场景切换视角 7 视角名（2026-08-21 修复：JS 拆分时曾丢失导致 renderScenePage 报错；视距前移/后移独立为 👁️ 按钮机制，不在此列）

// ★ 四视图角色卡固定提示词（2026-08-21 用户钦定，逐字原样使用，不得改写；生成时自动引用该身份定妆照作参考）
const IDENTITY_SHEET_PROMPT = '请基于参考人物，输出一张真人角色定妆参考板四视图，采用干净的摄影棚灰背景，整体呈现为专业级别的真人形象设定参考图，排版工整、视觉简洁——注意这不是宣传海报，也不是杂志大片，画面中不要出现剧情动作，不要复杂环境布置。\n版面需严格按上下两段式划分：上段占据整体高度的三分之一，下段占据剩余三分之二。上段展示两张高精度面部特写，左边是正脸特写、右边是侧脸特写，两张图均以头部加肩颈为主体，构图要紧凑，把五官细节、骨相结构、妆容效果、发型走向、头饰配件与神情状态都清晰呈现出来。人物的面部特征、发型、妆容与头部饰品必须和参考图高度一致。皮肤要呈现真实质感，毛孔、细纹、绒毛、睫毛与碎发都要保留，皮肤受光后的细微起伏也不能磨掉，不允许磨皮、过度锐化或人像美容处理，最终效果要接近高清真人棚拍定妆照的质感。\n下段展示两张身体与穿搭参考图，左右并排。左边这张必须是被放大处理过的正面服装展示图，人物保持标准A字站姿，重点不在于展示完整全身，而是要让角色在画面里的占比明显更大——采取更近距离的正面取景，从肩颈以下开始入画一直到鞋子，头部因为构图放大会被自然裁切出画面外。请特别注意，这不是常规的远景全身照，而是刻意拉近放大后的正面服装图：人物在画面中的身形比例要显著更大，上身与下身穿搭都需要被放大呈现，整体感觉更像是时装定妆照里那种服装主体展示效果。双臂、双肩、双手、躯干、腰线、腿部与鞋子这些部位都必须完整入镜，画面边缘只能裁掉头部，绝不能裁掉手部、脚部或身体主干。左图相比右侧背面图，必须显得更"近"、更"满"、更"放大"，让服装的细节和身材比例更加突出。不允许把左图处理成普通小比例的全身照，不允许人物在左图中显得渺小，不允许头部残留 in 画面里，也不允许只裁掉半个头部而留下下巴、嘴唇、鼻子或发梢边缘。\n右边这张图是标准A字站姿的完整背面全身照，人物背对镜头，从头顶到鞋底的背面细节需要完整呈现，包括发型背部走向、服装背面结构、鞋子样式和整体轮廓，用来展示角色的背面造型。这张图属于常规比例的完整背面展示，不需要像左图那样做放大裁切处理。\n下段的两张图必须是同一人物、同一套服装、同一配饰、同一身体比例。整体维持修长的超模式身材比例，但不要做出夸张变形的效果。服装款式、面料层次、鞋履、穿搭风格、服装结构与配饰细节都必须严格还原原图设定。所有服装配饰都要呈现出真实的物理材质感——布料要有自然的褶皱、垂坠感和厚薄层次变化，金属要有真实反光效果，皮革、丝绸、纱料等材质的质感都要表现真实自然。如果原图中的服装是开叉长裙款式，左侧放大正面图里可以让人物自然地把一条腿向前迈出半步，展示开叉结构与露腿效果，但整体姿态仍要维持定妆照式的稳定感，不能做成走秀动作。\n灯光只使用简洁统一的摄影棚三点布光：主光源在正左侧，辅助光源在正右侧，轮廓光源在后右侧。不要杂乱的光效组合，不要使用彩色灯光，不要加入强烈的氛围效果。背景统一为纯净的无缝灰色摄影棚背景。\n强制要求：上段两张脸部特写占据画面上三分之一区域；下段两张身体图占据画面下三分之二区域；左下图必须是"放大处理后的正面服装展示图"，人物占比要明显更大，头部因近距取景被完整裁切出画面外；右下图必须是完整的背面全身图。不允许左下图变成普通比例的全身小图；不允许左下图出现任何头部信息；不允许左右两图的服装出现不一致；不允许人物身体比例出现漂移；不允许出现AI油腻感、塑料皮肤感、过度美颜感或廉价CG质感。';

function renderXiatang(){
  const t = P.xiatang || {};
  const tabs = [
    {k:"character", label:"角色", count: (t.characters||[]).length},
    {k:"scene", label:"场景", count: (t.scenes||[]).length},
    {k:"key_scene", label:"关键场景", count: (t.key_scenes||[]).length},
    {k:"prop", label:"道具", count: (t.props||[]).length},
    {k:"voice", label:"声线", count: 0},
  ];
  return `
    <div class="tabs" id="xiatang-tabs">
      ${tabs.map(t => `<div class="t ${t.k===xtCurTab?'active':''}" data-tab="${t.k}">${t.label}<span class="ct">${t.count}</span></div>`).join("")}
      <div style="flex:1"></div>
      <button class="pill primary" disabled title="开发中：新建成员" style="opacity:.5;cursor:not-allowed">+ 新建成员</button>
    </div>
    <div id="xiatang-body">${renderXiatangTab()}</div>
  `;
}

function renderXiatangTab(){
  const t = P.xiatang || {};
  if(xtCurTab==="character") return renderRolePage();
  if(xtCurTab==="scene") return renderScenePage();
  if(xtCurTab==="key_scene") return renderKeyScenePage();
  if(xtCurTab==="prop") return renderPropGrid();
  if(xtCurTab==="voice") return renderVoicePage();
}

// ===== 关键场景 Tab（画面素材，非资产；★ 2026-08-21 布局改为场景页式：左列表 + 右详情） =====
function renderKeyScenePage(){
  const ks = P.xiatang?.key_scenes || [];
  if(!xtCurSel || !ks.find(k=>k.name===xtCurSel)) xtCurSel = ks[0]?.name;
  const cur = ks.find(k => k.name===xtCurSel) || {};
  const rawP = cur.prompt || "";
  const p = typeof rawP === "string" ? rawP : (typeof rawP === "object" ? Object.values(rawP).filter(Boolean).join("\n") : "");
  return `
    <div class="scene-page">
      <div style="grid-column:1/-1;display:flex;align-items:center;justify-content:flex-end;gap:8px;margin-bottom:-8px">
        <span style="font-size:12px;color:var(--mut)">素材 ${ks.length} 张 · 未生成 ${ks.filter(k=>!k.image_ready).length} 张</span>
        <button class="pill primary" onclick="batchGenImages('key_scene')" title="批量生成未生成的关键场景图（画面素材）">✨ 批量生图</button>
      </div>
      <div class="scene-list">
        ${ks.map(k => `
          <div class="scene-list-item ${k.name===xtCurSel?'active':''}" data-kname="${esc(k.name)}">
            <div class="th" ${k.image_ready?`onclick="event.stopPropagation();openZoom('${esc(imgSrc(k.image))}','${esc(k.name)}')" style="cursor:zoom-in"`:`style="cursor:not-allowed"`}>${k.image_ready?'<img src="'+esc(imgSrc(k.image))+'">':'<div style="display:flex;align-items:center;justify-content:center;height:100%;font-size:9px;color:var(--mut)">无图</div>'}</div>
            <div class="info"><b>${esc(k.name)}${k.poster?' <span style="color:#d4af6a;font-weight:700">★</span>':''}</b><span>${k.image_ready?'✓ 已生成':'未生成'}${k.shot_ref?' · 镜 '+esc(k.shot_ref):''}</span></div>
          </div>`).join("")}
      </div>
      <div class="scene-detail">
        <h2>${esc(cur.name||"")} ${cur.poster?'<span class="tag" style="color:#d4af6a;border-color:#d4af6a">★ 海报候选</span>':''} ${cur.shot_ref?'<span class="tag">关联镜头 '+esc(cur.shot_ref)+'</span>':''}</h2>
        <div class="scene-views">
          <div class="v" ${cur.image_ready?`onclick="openZoom('${esc(imgSrc(cur.image))}', '${esc(cur.name)}')" style="cursor:zoom-in"`:`style="cursor:not-allowed" title="尚未生成关键场景图（点 ✨ 生成）"`}><img src="${esc(imgSrc(cur.image))}" onerror="this.style.display='none'"><div class="lbl">素材图</div></div>
        </div>
        <div class="scene-actions">
          <label class="btn primary" style="cursor:pointer">↑ 上传素材<input type="file" accept="image/*" style="display:none" onchange="doUpload(this,'key_scene','${esc((cur.image||"").split("/").pop().split("?")[0])}')"></label>
          ${genBtn("key_scene", cur.name || (cur.image||"").split("/").pop().split("?")[0], p, "", cur.prompt_cn)}
          ${histWidget("key_scene", (cur.image||"").split("/").pop().split("?")[0])}
        </div>
        <div class="scene-desc">${esc(cur.desc||"暂无描述。")}</div>
        <details style="margin-top:12px"><summary style="cursor:pointer;padding:10px 14px;background:var(--bg);border:1px solid var(--line);border-radius:10px;font-size:12.5px;font-weight:600">📋 12 字段提示词</summary><div style="padding-top:10px">${promptBlockDual(cur.prompt_cn, p)}</div></details>
      </div>
    </div>`;
}

function renderRolePage(){
  const chars = P.xiatang?.characters || [];
  if(!xtCurSel || !chars.find(c => c.name===xtCurSel)) xtCurSel = chars[0]?.name;
  const cur = chars.find(c => c.name===xtCurSel) || {};
  return `
    <div class="role-page">
      <div style="grid-column:1/-1;display:flex;align-items:center;justify-content:flex-end;gap:8px;margin-bottom:-8px">
        <span style="font-size:12px;color:var(--mut)">未生成主图 ${chars.filter(c=>!c.image).length} 个</span>
        <button class="pill" onclick="batchGenIdentities()" title="批量生成所有角色的定妆照（前提：该角色已生成主图；不满足自动跳过）" style="background:linear-gradient(135deg,#38BDF8,#0EA5E9);color:#fff;border:none;white-space:nowrap;border-radius:10px;padding:7px 14px;font-size:12.5px;font-weight:600;box-shadow:0 2px 6px rgba(14,165,233,.25);cursor:pointer;transition:all .15s">🎭 批量生定妆</button>
        <button class="pill" onclick="batchGenIdentitySheets()" title="批量生成所有角色的四视图卡（前提：该身份定妆照已生成；不满足自动跳过）" style="background:linear-gradient(135deg,#FBBF24,#F59E0B);color:#fff;border:none;white-space:nowrap;border-radius:10px;padding:7px 14px;font-size:12.5px;font-weight:600;box-shadow:0 2px 6px rgba(245,158,11,.25);cursor:pointer;transition:all .15s">🀄 批量生四视</button>
        <button class="pill primary" onclick="batchGenImages('character')" title="批量生成角色主图（身份图不在批量范围）">✨ 批量生图</button>
      </div>
      <div class="role-list">
        ${chars.map(c => `
          <div class="role-list-item ${c.name===xtCurSel?'active':''}" data-name="${esc(c.name)}">
            <div class="av" ${c.image_ready?`onclick="event.stopPropagation();openZoom('${esc(imgSrc(c.image))}','${esc(c.name)}')" style="cursor:zoom-in"`:`style="cursor:default"`}>${c.image_ready?'<img src="'+esc(imgSrc(c.image))+'">':c.name.slice(0,1)}</div>
            <div class="nm">${esc(c.name)}<div class="st">${c.image_ready?'✓ 已就绪':'未生成'}</div></div>
          </div>`).join("")}
      </div>
      <div class="role-detail">
        <div class="role-detail-top">
          <div class="role-left-col">
          <div class="role-portrait" ${cur.image_ready?`onclick="openZoom('${esc(imgSrc(cur.image))}', '${esc(cur.name)} 定妆')" style="cursor:zoom-in"`:`style="cursor:not-allowed" title="尚未生成主图（点 ✨ 生成）"`}>
            ${cur.image_ready?'<img src="'+esc(imgSrc(cur.image))+'">':'<div>定妆照<br>未生成</div>'}
            <div class="st">${cur.is_main?"主角":"配角"}</div>
          </div>
          <div class="role-portrait-actions">
            ${uploadWidget("character", (cur.image||"").split("/").pop().split("?")[0])}${genBtn("character", cur.name || (cur.image||"").split("/").pop().split("?")[0], cur.prompt, "", cur.prompt_cn)}${histWidget("character", (cur.image||"").split("/").pop().split("?")[0])}
          </div>
          </div>
          <div class="role-form">
            <div class="row"><label>别名</label><div class="v">${esc(cur.aliases||"") || '<span style="color:var(--mut)">-</span>'}</div></div>
            <div class="row"><label>角色定位</label><div class="v">${esc(cur.role||"")}</div></div>
            <div class="row"><label>角色状态</label><div class="v">${cur.is_main?"主角":"配角"}</div></div>
            <div class="row"><label>年龄段</label><div class="v">${esc(cur.age_group||"") || '<span style="color:var(--mut)">-</span>'}</div></div>
            <div class="row"><label>性别</label><div class="v">${esc(cur.gender||"") || '<span style="color:var(--mut)">-</span>'}</div></div>
            <div class="row" style="align-items:flex-start"><label>简介</label><textarea class="v" readonly>${esc(cur.desc||"")}</textarea></div>
          </div>
        </div>
        <div class="identity-section">
          <h3>🔁 身份/造型 <span style="font-size:12px;color:var(--mut);font-weight:400">${(cur.identities||[]).length} 个</span></h3>
          <div class="identity-grid">
          ${(cur.identities||[]).map(id => `
            <div class="id-card">
              <div class="id-head">${esc(id.name)} <span style="color:var(--mut);font-weight:400;font-size:12px">${esc(id.identity||"")}</span></div>
              <div class="id-body">
                ${id.image_ready?`<div class="iv id-iv" onclick="openZoom('${esc(imgSrc(id.image))}', '${esc(cur.name)} - ${esc(id.name)} 定妆照')" title="点击放大"><img src="${esc(imgSrc(id.image))}"></div>`:`<div class="iv id-iv placeholder" title="尚未生成定妆照（点 ✨ 生成）">定妆照<br>未生成</div>`}
                ${id.sheet_ready?`<div class="iv id-iv" onclick="openZoom('${esc(imgSrc(id.sheet_image))}', '${esc(cur.name)} - ${esc(id.name)} 四视图卡')" title="点击放大"><img src="${esc(imgSrc(id.sheet_image))}"></div>`:`<div class="iv id-iv placeholder" title="尚未生成四视图卡（点【四视图】生成）">四视图卡<br>未生成</div>`}
              </div>
              <div class="id-actions">
                <div class="actions">${uploadWidget("identity", (id.image||"").split("/").pop().split("?")[0])}${genBtn("identity", (id.image||"").split("/").pop().split("?")[0] || (cur.name + "-" + id.name), id.prompt, "", id.prompt_cn)}${histWidget("identity", (id.image||"").split("/").pop().split("?")[0])}</div>
                <div class="actions">${uploadWidget("character", cur.name + "-" + id.identity_id + "-sheet")}<button class="pill" onclick="genIdentitySheet('${esc(cur.name)}','${esc(id.identity_id||"")}')" title="以该身份定妆照为参考，用固定模板生成四视图角色卡" style="font-size:12px;padding:7px 12px;border-radius:10px;border:1px solid #bfdbfe;background:#eff6ff;color:#1d4ed8;font-weight:600;white-space:nowrap;cursor:pointer">生成</button>${histWidget("character", cur.name + "-" + id.identity_id + "-sheet")}</div>
              </div>
            </div>`).join("")}
          </div>
          <button class="pill" disabled title="开发中：添加身份" style="opacity:.55;cursor:not-allowed;font-size:12px;padding:7px 16px;border-radius:10px;border:1px dashed #cbd5e1;background:#f8fafc;color:#64748b;font-weight:500;width:100%;margin-top:4px">+ 添加身份</button>
        </div>
        <div class="voice-section">
          <h3>🎤 声线管理</h3>
          <div class="voice-row">
            <span class="name">${esc(cur.name)}</span>
            <div class="player"><span class="ctrl">▶</span><div class="bar"><i></i></div><span class="time">0:00 / 0:12</span></div>
            <span class="status" style="font-size:11.5px;color:#b45309;background:linear-gradient(135deg,#fffbeb,#fef3c7);border:1px solid #fde68a;padding:3px 10px;border-radius:999px;font-weight:500;white-space:nowrap">⏳ 待录制</span>
            <button class="pill" disabled title="开发中：上传样本" style="opacity:.55;cursor:not-allowed;font-size:11.5px;padding:5px 12px;border-radius:999px;border:1px solid #e2e8f0;background:#f8fafc;color:#94a3b8;font-weight:500">上传样本</button>
          </div>
        </div>
        <details style="margin-top:14px">
          <summary style="cursor:pointer;padding:10px 14px;background:linear-gradient(135deg,#f8fafc,#f1f5f9);border:1px solid #e2e8f0;border-radius:10px;font-size:12.5px;font-weight:600;color:#475569;list-style:none;user-select:none;transition:all .15s">📋 定妆提示词（点击展开）</summary>
          <div style="padding-top:8px">${promptBlockDual(cur.prompt_cn, cur.prompt)}</div>
        </details>
        ${(cur.identities||[]).some(i=>i.prompt||i.sheet_prompt) ? `<details style="margin-top:8px"><summary style="cursor:pointer;padding:10px 14px;background:linear-gradient(135deg,#f8fafc,#f1f5f9);border:1px solid #e2e8f0;border-radius:10px;font-size:12.5px;font-weight:600;color:#475569;list-style:none;user-select:none;transition:all .15s">📋 身份图提示词（①定妆照 + ②四视图角色卡，点击展开）</summary><div style="padding-top:10px">${(cur.identities||[]).map(i=>`<div style="margin-bottom:12px"><b style="font-size:12.5px;color:#1e293b">${esc(i.name)}</b>${i.prompt?`<div style="font-size:11px;color:#64748b;margin:6px 0 2px">① 定妆照</div>${promptBlockDual(i.prompt_cn, i.prompt)}`:"<div style='font-size:11px;color:#b45309;margin:4px 0'>⚠️ 定妆照提示词缺失</div>"}${i.sheet_prompt?`<div style="font-size:11px;color:#64748b;margin:6px 0 2px">② 四视图角色卡（固定模板）</div>${promptBlockDual(i.sheet_prompt_cn, i.sheet_prompt)}`:"<div style='font-size:11px;color:#b45309;margin:4px 0'>⚠️ 四视图卡提示词缺失</div>"}</div>`).join("")}</div></details>` : ""}
      </div>
    </div>`;
}

function renderScenePage(){
  const scenes = P.xiatang?.scenes || [];
  if(!xtCurSel || !scenes.find(s=>s.name===xtCurSel)) xtCurSel = scenes[0]?.name;
  const cur = scenes.find(s => s.name===xtCurSel) || {};
  return `
    <div class="scene-page">
      <div style="grid-column:1/-1;display:flex;align-items:center;justify-content:flex-end;gap:8px;margin-bottom:-8px">
        <span style="font-size:12px;color:var(--mut)">未生成场景 ${scenes.filter(s=>!s.image).length} 个</span>
        <button class="pill primary" onclick="batchGenImages('scene')" title="批量生成未生成的场景图（空镜）">✨ 批量生图</button>
      </div>
      <div class="scene-list">
        ${scenes.map(s => `
          <div class="scene-list-item ${s.name===xtCurSel?'active':''}" data-sname="${esc(s.name)}">
            <div class="th" ${s.image_ready?`onclick="event.stopPropagation();openZoom('${esc(imgSrc(s.image))}','${esc(s.name)}')" style="cursor:zoom-in"`:`style="cursor:not-allowed"`}>${s.image_ready?'<img src="'+esc(imgSrc(s.image))+'">':'<div style="display:flex;align-items:center;justify-content:center;height:100%;font-size:9px;color:var(--mut)">无图</div>'}</div>
            <div class="info"><b>${esc(s.name)}</b><span>${(s.usage_count||0)} 次使用</span></div>
          </div>`).join("")}
      </div>
      <div class="scene-detail">
        <h2>${esc(cur.name)} <span class="tag">${esc(cur.header||"")}</span></h2>
        <div class="scene-views">
          <!-- ★ 2026-08-20：主图与正面视角区分——主图标签「主图」；正面视角（views.正面）单独显示 -->
          <!-- ★ 2026-08-27：主图位始终渲染，未生成时显示占位，避免资产位消失 -->
          ${cur.image_ready
            ? `<div class="v" onclick="openZoom('${esc(imgSrc(cur.image))}', '${esc(cur.name)}')" style="cursor:zoom-in"><img src="${esc(imgSrc(cur.image))}" onerror="this.style.display='none'"><div class="lbl">主图</div><button class="sv-sv-btn" onclick="event.stopPropagation();openSceneViewModal('${esc(cur.image)}','主图')" title="以主图为参考图，切换生成其他视角">👀</button><button class="sv-del-btn" onclick="event.stopPropagation();svDeleteImg('image')" title="删除此图（文件与数据）">×</button><button class="sv-dist-btn" onclick="event.stopPropagation();openViewDistModal('${esc(cur.image)}','主图')" title="基于此图生成视距变体（推拉/航拍）">👁️</button></div>`
            : `<div class="v" style="cursor:not-allowed" title="尚未生成场景主图（点 ✨ 生成）"><div class="lbl">主图</div>未生成</div>`}
          ${SCENE_VIEWS.map(v => (cur.views_ready && cur.views_ready[v] && cur.views && cur.views[v])
            ? `<div class="v" onclick="openZoom('${esc(imgSrc(cur.views[v]))}', '${esc(cur.name)} ${v}')"><img src="${esc(imgSrc(cur.views[v]))}" onerror="this.style.display='none'"><div class="lbl">${v}</div><button class="sv-sv-btn" onclick="event.stopPropagation();openSceneViewModal('${esc(cur.views[v])}','${esc(v)}')" title="以此图为参考图，切换生成其他视角">👀</button><button class="sv-del-btn" onclick="event.stopPropagation();svDeleteImg('view:${esc(v)}')" title="删除此图（文件与数据）">×</button><button class="sv-dist-btn" onclick="event.stopPropagation();openViewDistModal('${esc(cur.views[v])}','${v}')" title="基于此图生成视距变体（推拉/航拍）">👁️</button></div>` : "").join("")}
          ${cur.plan_ready && cur.plan
            ? `<div class="v" onclick="openZoom('${esc(imgSrc(cur.plan))}', '${esc(cur.name)} 平面布局')"><img src="${esc(imgSrc(cur.plan))}" onerror="this.style.display='none'"><div class="lbl">平面布局</div><button class="sv-del-btn" onclick="event.stopPropagation();svDeleteImg('plan')" title="删除此图（文件与数据）">×</button><button class="sv-dist-btn" onclick="event.stopPropagation();openViewDistModal('${esc(cur.plan)}','平面布局')" title="基于此图生成视距变体（推拉/航拍）">👁️</button></div>` : ""}
          ${cur.plan_sketch_ready && cur.plan_sketch
            ? `<div class="v" onclick="openZoom('${esc(imgSrc(cur.plan_sketch))}', '${esc(cur.name)} 线稿')"><img src="${esc(imgSrc(cur.plan_sketch))}" onerror="this.style.display='none'"><div class="lbl">线稿</div><button class="sv-del-btn" onclick="event.stopPropagation();svDeleteImg('plan_sketch')" title="删除此图（文件与数据）">×</button><button class="sv-dist-btn" onclick="event.stopPropagation();openViewDistModal('${esc(cur.plan_sketch)}','线稿')" title="基于此图生成视距变体（推拉/航拍）">👁️</button></div>` : ""}
          ${Object.keys(cur.dists_ready||{}).filter(k => cur.dists_ready[k] && cur.dists && cur.dists[k]).map(k => {
            const _dl = String(k).split("|");
            const _lbl = _dl[0]||"主图", _dist = _dl[1]||"";
            return `<div class="v" onclick="openZoom('${esc(imgSrc(cur.dists[k]))}', '${esc(cur.name)} ${_lbl}·${_dist}')"><img src="${esc(imgSrc(cur.dists[k]))}" onerror="this.style.display='none'"><div class="lbl">${esc(_lbl)}·${esc(_dist)}</div><button class="sv-sv-btn" onclick="event.stopPropagation();openSceneViewModal('${esc(cur.dists[k])}','${esc(_lbl)}·${esc(_dist)}')" title="以此图为参考图，切换生成其他视角">👀</button><button class="sv-del-btn" onclick="event.stopPropagation();svDeleteImg('dist:${esc(k)}')" title="删除此图（文件与数据）">×</button><button class="sv-dist-btn" onclick="event.stopPropagation();openViewDistModal('${esc(cur.dists[k])}','${esc(_lbl)}·${esc(_dist)}')" title="基于此图继续生成视距变体">👁️</button></div>`;
          }).join("")}
        </div>
        <div class="scene-actions">
          <label class="btn primary" style="cursor:pointer">↑ 上传场景<input type="file" accept="image/*" style="display:none" onchange="doUpload(this,'scene','${esc((cur.image||"").split("/").pop().split("?")[0])}')"></label>
          ${genBtn("scene", cur.name || (cur.image||"").split("/").pop().split("?")[0], cur.prompt, "", cur.prompt_cn)}
          ${histWidget("scene", (cur.image||"").split("/").pop().split("?")[0])}
          <button class="btn primary" onclick="openSceneViewModal()" title="基于当前场景图生成多视角（正面/左侧/右侧/背面/斜侧/俯视），可多选">↔ 切换视角</button>
          <button class="btn primary" onclick="godViewGen()" title="自动引用正面/背面/45°俯视全景生成平面布局（90°上帝视角），完成后自动生成线稿">👁 上帝视角</button>
        </div>
        <div class="scene-desc">${esc(cur.desc||"暂无描述。")}</div>
        <div class="scene-tools">
          <button class="btn" disabled title="开发中：X 框" style="opacity:.5;cursor:not-allowed">🧊 上传/替换 X 框</button>
          <button class="btn" disabled title="开发中：X 框" style="opacity:.5;cursor:not-allowed">↔ 删除 X 框</button>
          <button class="btn" disabled title="开发中：导演世界" style="opacity:.5;cursor:not-allowed">📐 正图→导演世界</button>
          <button class="btn" disabled title="开发中：导演世界" style="opacity:.5;cursor:not-allowed">📐 背图→导演世界</button>
          <button class="btn" disabled title="开发中：导演世界" style="opacity:.5;cursor:not-allowed">🎲 360→导演世界</button>
          <button class="btn" disabled title="开发中：导演世界" style="opacity:.5;cursor:not-allowed">🚪 打开导演世界</button>
        </div>
        <details style="margin-top:14px"><summary style="cursor:pointer;padding:8px;background:var(--bg);border-radius:8px;font-size:12px">📋 场景提示词（点击展开）</summary><div style="padding-top:8px">${promptBlockDual(cur.prompt_cn, cur.prompt)}</div></details>
      </div>
    </div>`;
}

function renderPropGrid(){
  const props = P.xiatang?.props || [];
  return `
    <div class="prop-grid">
      <div style="grid-column:1/-1;display:flex;align-items:center;justify-content:flex-end;gap:8px">
        <span style="font-size:12px;color:var(--mut)">未生成道具 ${props.filter(p=>!p.image).length} 个</span>
        <button class="pill primary" onclick="batchGenImages('prop')" title="批量生成未生成的道具图（产品特写）">✨ 批量生图</button>
      </div>
      ${props.map(p => `
        <div class="prop-card">
          <div class="head">
            <div><div class="name">${esc(p.name)}</div><div class="meta">${esc(p.owner||"")} · ${esc(p.reason||"")}</div></div>
            <span class="pill" style="font-size:12px;padding:2px 8px">${p.image_ready?'✓ 已生成':'未生成'}</span>
          </div>
          <div class="prop-main" ${p.image_ready?`onclick="openZoom('${esc(imgSrc(p.image))}', '${esc(p.name)}')" style="cursor:zoom-in"`:`style="cursor:not-allowed" title="尚未生成道具图（点 ✨ 生成）"`}>
            <img src="${esc(imgSrc(p.image))}" onerror="this.style.display='none';var ph=this.nextElementSibling;if(ph)ph.style.display='flex'">
            <div class="ph" style="display:none">未生成</div>
          </div>
          <div class="prop-actions">
            ${uploadWidget("prop", (p.image||"").split("/").pop().split("?")[0])}
            ${genBtn("prop", p.name || (p.image||"").split("/").pop().split("?")[0], p.prompt, "", p.prompt_cn)}
            ${histWidget("prop", (p.image||"").split("/").pop().split("?")[0])}
            <span>应用于 <b>1</b> 个镜头</span>
          </div>
          <details><summary style="cursor:pointer;padding:6px 8px;background:var(--bg);border-radius:6px;font-size:12px">📋 参考图提示词</summary><div style="padding-top:6px">${promptBlockDual(p.prompt_cn, p.prompt)}</div></details>
        </div>`).join("")}
    </div>`;
}

function renderVoicePage(){
  const chars = P.xiatang?.characters || [];
  return `
    <div class="voice-page">
      <div class="voice-card">
        <h3>🎤 角色声线</h3>
        <div class="voice-slots">
          ${chars.map(c => `
            <div class="voice-slot">
              <span class="lbl">${esc(c.name)}</span>
              <span class="status">⏳ 待上传样本</span>
              <button class="pill" disabled title="开发中：上传声线" style="opacity:.5;cursor:not-allowed">↑ 上传</button>
              <button class="pill" disabled title="开发中：录制声线" style="opacity:.5;cursor:not-allowed">🎤 录制</button>
              <button class="pill" disabled title="开发中：裁剪声线" style="opacity:.5;cursor:not-allowed">✂ 裁剪</button>
            </div>`).join("")}
        </div>
      </div>
      <div class="voice-card">
        <h3>📖 解说声线</h3>
        <div class="voice-slots">
          <div class="voice-slot"><span class="lbl">解说（默认）</span><span class="status">⏳ 待上传</span><button class="pill" disabled title="开发中：上传声线" style="opacity:.5;cursor:not-allowed">↑ 上传</button><button class="pill" disabled title="开发中：录制声线" style="opacity:.5;cursor:not-allowed">🎤 录制</button></div>
        </div>
      </div>
    </div>`;
}

// ===== 场景切换视角 + 上帝视角（★ 2026-08-21 修复：JS 拆分丢失，按 SKILL §1.4 规范恢复）=====
const SCENE_VIEW_PROMPTS = {
  "正面": "基于参考图生成同一场景多视角画面，固定空间结构与家具布局全程不变，仅移动摄像机生成正面机位；按原有空间逻辑补全遮挡区域，保持透视、比例、材质、光影、整体风格完全统一；不新增元素、不改结构、不重新设计空间。",
  "左侧": "基于参考图生成同一场景多视角画面，固定空间结构与家具布局全程不变，仅移动摄像机生成左侧机位；按原有空间逻辑补全遮挡区域，保持透视、比例、材质、光影、整体风格完全统一；不新增元素、不改结构、不重新设计空间。",
  "右侧": "基于参考图生成同一场景多视角画面，固定空间结构与家具布局全程不变，仅移动摄像机生成右侧机位；按原有空间逻辑补全遮挡区域，保持透视、比例、材质、光影、整体风格完全统一；不新增元素、不改结构、不重新设计空间。",
  "背面": "基于参考图生成同一场景多视角画面，固定空间结构与家具布局全程不变，生成同一场景对向反向平视回望；按原有空间逻辑补全遮挡区域，保持透视、比例、材质、光影、整体风格完全。",
  "斜侧": "基于参考图生成同一场景多视角画面，固定空间结构与家具布局全程不变，仅移动摄像机生成斜侧机位；按原有空间逻辑补全遮挡区域，保持透视、比例、材质、光影、整体风格完全统一；不新增元素、不改结构、不重新设计空间。",
  "俯视": "基于参考图生成同一场景多视角画面，固定空间结构与家具布局全程不变，仅移动摄像机生成俯视机位；按原有空间逻辑补全遮挡区域，保持透视、比例、材质、光影、整体风格完全统一；不新增元素、不改结构、不重新设计空间。",
  "45°俯视全景": "基于参考图生成同一场景多视角画面，固定空间结构与家具布局全程不变，生成同一场景的45°俯视斜角全景；按原有空间逻辑补全遮挡区域，保持透视、比例、材质、光影、整体风格完全。"
};
const svState = { name:"", refImg:"", refLabel:"", sel:{} };   // ★ 2026-09-01 refImg/refLabel 取代 ref（参考图 = 触发 👀 的那张图）

// ★ 2026-08-22 视距推拉镜（用户钦定，固定写死逐字原样使用，不得改写；[ORIGINAL LENS] 为镜头参数占位符保持原样）
//   入口 = 场景每张图上的 👁️ 按钮 → 弹【视距】窗口 → 前移/后移 1/2/3/5/10 米可多选批量生成
const VD_DISTS = ["前移1米","前移2米","前移3米","前移5米","前移10米","后移1米","后移2米","后移3米","后移5米","后移10米","航拍","45°航拍","高航拍","45°高航拍"];   // ★ 2026-09-01 增加航拍系 4 选项（45°航拍/高航拍/45°高航拍=用户钦定逐字；航拍=同句式起草待确认）
const SCENE_VIEW_DIST_PROMPTS = {
  "前移1米": "[ORIGINAL LENS], camera dolly forward 1 meter toward the subject, composition subtly tightened, subject appears slightly larger in frame, background elements barely affected, depth of field marginally shallower, natural perspective maintained, no distortion",
  "前移2米": "[ORIGINAL LENS], camera dolly forward 2 meters toward the subject, composition clearly tightened, subject appears noticeably larger in frame, background elements begin to fall out of frame at the edges, depth of field visibly shallower, natural perspective maintained, no distortion",
  "前移3米": "[ORIGINAL LENS], camera dolly forward 3 meters toward the subject, composition visibly tightened, subject appears clearly larger in frame, background elements start to fall out of frame at the edges, depth of field noticeably shallower, natural perspective maintained, no distortion",
  "前移5米": "[ORIGINAL LENS], camera dolly forward 5 meters toward the subject, composition heavily tightened, subject now dominates the frame, most background elements pushed out of frame, only soft blurred hints remain, depth of field strongly compressed, background bokeh intensified, natural perspective maintained, no distortion",
  "前移10米": "[ORIGINAL LENS], camera dolly forward 10 meters toward the subject, composition dramatically tightened, subject fills most of the frame, background almost completely out of frame, reduced to pure bokeh, depth of field maximally compressed, fine details of the subject clearly visible, natural perspective maintained, no distortion",
  "后移1米": "[ORIGINAL LENS], camera dolly backward 1 meter away from the subject, composition slightly widened, subject appears slightly smaller in frame, a little more background becomes visible around the edges, depth of field marginally deeper, natural perspective maintained, no distortion",
  "后移2米": "[ORIGINAL LENS], camera dolly backward 2 meters away from the subject, composition visibly widened, subject appears noticeably smaller in frame, more background elements enter the frame at the edges, depth of field clearly deeper, background slightly sharper, natural perspective maintained, no distortion",
  "后移3米": "[ORIGINAL LENS], camera dolly backward 3 meters away from the subject, composition noticeably widened, subject appears clearly smaller in frame, background elements around the subject become more visible, depth of field deeper, background sharpness increases, natural perspective maintained, no distortion",
  "后移5米": "[ORIGINAL LENS], camera dolly backward 5 meters away from the subject, composition opens up significantly, subject appears much smaller in frame, surrounding environment now clearly visible, more background enters from all edges, depth of field much deeper, background detail increases, natural perspective maintained, no distortion",
  "后移10米": "[ORIGINAL LENS], camera dolly backward 10 meters away from the subject, composition expands to a wide establishing view, subject becomes small in frame, the full surrounding environment is revealed, background dominates the frame, depth of field maximally deep, everything in focus, natural perspective maintained, no distortion",
  // ★ 2026-09-01 航拍系（45°航拍/高航拍/45°高航拍 = 用户钦定逐字原样；航拍 = 同句式起草，待用户确认）
  "航拍": "based on the reference image, keep all elements, scenes, props, styles, colors, textures and lighting of the original image completely unchanged, only adjust the camera perspective and shot scale, drone aerial shot, bird's eye view, elevated overhead perspective, drone hovering above the scene, full panoramic view, complete spatial layout visible from above.",
  "45°航拍": "based on the reference image, keep all elements, scenes, props, styles, colors, textures and lighting of the original image completely unchanged, only adjust the camera perspective and shot scale, 45° aerial shot, 45-degree oblique aerial view, high-angle oblique perspective, drone aerial shot, bird's eye view, high altitude overhead perspective, hovering drone camera, full panoramic top-down view, wide sweeping aerial vista, complete spatial layout visible from above.",
  "高航拍": "based on the reference image, keep all elements, scenes, props, styles, colors, textures and lighting of the original image completely unchanged, only increase the drone flight altitude and adjust the perspective, ultra-high altitude drone aerial shot, extremely high elevation bird's eye view, drone hovering at extreme height far above the scene, steep vertical top-down perspective, vast sweeping aerial panorama, complete regional layout visible, ground objects appear small in frame.",
  "45°高航拍": "based on the reference image, keep all elements, scenes, props, styles, colors, textures and lighting of the original image completely unchanged, only increase the drone flight altitude and adjust the perspective, ultra-high altitude drone aerial shot, 45-degree oblique bird's eye view, extremely high elevation, drone hovering at extreme height far above the scene, 45° downward looking angle, vast sweeping aerial panorama, complete regional layout visible, ground objects appear small in frame."
};
const vdState = { name:"", img:"", label:"", sel:{} };

// ★ 2026-08-22 删除场景图（文件 + 数据库）：key = image | view:正面 | plan | plan_sketch | dist:源标签|视距
function svDeleteImg(key){
  const cur = (P.xiatang?.scenes||[]).find(s => s.name === xtCurSel);
  if(!cur){ toast("请先选择场景"); return; }
  if(!confirm("⚠️ 删除当前图片？\n\n将同时删除图片文件与数据库记录，不可恢复。")) return;
  fetch("/scene-del-img", {
    method:"POST", headers:{"Content-Type":"application/json"},
    body: JSON.stringify({ scene: cur.name, key: key })
  }).then(r=>r.json()).then(j=>{
    if(j.ok){
      // ★ 2026-08-22 同步前端内存（后端已持久化 SQLite + 删文件，此处对称清理 P，防 rerender 读旧数据）
      if(key === "image"){ delete cur.image; cur.image_ready = false; }
      else if(key.indexOf("view:") === 0){ const _v = key.slice(5); if(cur.views) delete cur.views[_v]; if(cur.views_ready) cur.views_ready[_v] = false; }
      else if(key === "plan"){ delete cur.plan; cur.plan_ready = false; }
      else if(key === "plan_sketch"){ delete cur.plan_sketch; cur.plan_sketch_ready = false; }
      else if(key.indexOf("dist:") === 0){ const _dk = key.slice(5); if(cur.dists) delete cur.dists[_dk]; if(cur.dists_ready) cur.dists_ready[_dk] = false; }
      toast("🗑 已删除 " + (j.cleared || key));
      rerenderCurrent();
    } else {
      toast("❌ " + (j.error || "删除失败"));
    }
  }).catch(()=>toast("❌ 删除请求失败"));
}

function openViewDistModal(img, label){
  const cur = (P.xiatang?.scenes||[]).find(s => s.name === xtCurSel);
  if(!cur){ toast("请先选择场景"); return; }
  vdState.name = cur.name; vdState.img = img || ""; vdState.label = label || "主图"; vdState.sel = {};
  $("vd-name").textContent = "场景：" + cur.name + " · " + vdState.label;
  $("vd-dists").innerHTML = VD_DISTS.map(d =>
    '<label style="border:1px solid var(--line);border-radius:8px;padding:8px 4px;font-size:12.5px;cursor:pointer;text-align:center;' + (d.startsWith("后移") ? 'background:#f8fafc' : (d.indexOf("航拍") > -1 ? 'background:#eff6ff' : '')) + '">' +
    '<input type="checkbox" value="' + d + '" onchange="vdState.sel[\'' + d + '\']=this.checked"> ' + d + '</label>'
  ).join("");
  $("viewdistmodal").style.display = "flex";
}
function closeViewDistModal(){ $("viewdistmodal").style.display = "none"; }

async function viewDistSend(){
  const dists = VD_DISTS.filter(d => vdState.sel[d]);
  if(!dists.length){ toast("请至少勾选 1 个视距"); return; }
  if(!vdState.img){ toast("❌ 无底图，无法生成视距变体"); return; }
  const cur = (P.xiatang?.scenes||[]).find(s => s.name === vdState.name);
  if(!cur) return;
  let model="", channelId="", size="1536x768";
  try{
    const cfg = await fetch("/gen-config").then(r=>r.json());
    const ch = (cfg.channels||[]).find(c=>c.configured);
    if(!ch){ toast("❌ 未配置可用生图渠道，请先到 ⚙ 设置完善"); return; }
    channelId = ch.id;
    const m0 = (ch.models||[])[0]||"";
    model = (typeof m0==="string")?m0:(m0.name||"");
    if(!model){ toast("❌ 渠道无可用模型"); return; }
    size = (cfg.default_sizes||{}).scene || "1536x768";
  }catch(e){ toast("❌ 读取渠道配置失败"); return; }
  const imgs = [vdState.img];
  let ok=0, fail=0;
  for(const d of dists){
    const ok1 = await batchEnqueue("scene", vdState.name + "-" + vdState.label + "-" + d, SCENE_VIEW_DIST_PROMPTS[d], model, size, channelId, imgs, 1);
    if(ok1) ok++; else fail++;
  }
  closeViewDistModal();
  toast(fail ? "⚠️ 视距入队：成功 " + ok + "，失败 " + fail + "（任务面板可重试）" : "✅ 已入队 " + ok + " 个视距生图任务");
}

function openSceneViewModal(refImg, refLabel){
  const cur = (P.xiatang?.scenes||[]).find(s => s.name === xtCurSel);
  if(!cur){ toast("请先选择场景"); return; }
  // ★ 2026-09-01 参考图 = 触发 👀 的那张图（主图/任意视角图）；顶部「↔ 切换视角」无参调用 → 默认主图
  svState.refImg = refImg || cur.image || "";
  svState.refLabel = refLabel || "主图";
  if(!svState.refImg){ toast("❌ 该场景无主图，无法作为参考图"); return; }
  svState.name = cur.name; svState.sel = {};
  $("sv-name").textContent = "场景：" + cur.name;
  $("sv-ref").innerHTML = '<span style="font-size:13px"><b>参考图：' + esc(svState.refLabel) + '</b>（以当前这张图为基准生成其他视角）</span>';
  $("sv-options").innerHTML = SCENE_VIEWS.map(v => {
    // ★ 2026-09-01 用户拍板：不管是否已生成，全部可勾选再次生成（"已生成"仅灰字提示，重生成将替换旧图）
    const ready = !!(cur.views_ready && cur.views_ready[v]);
    return '<label style="border:1px solid var(--line);border-radius:8px;padding:8px;font-size:12.5px;cursor:pointer">' +
      '<input type="checkbox" value="' + v + '" onchange="svState.sel[\'' + v + '\']=this.checked"> ' + v + (ready?' <span style="color:#94a3b8;font-size:11px">已生成·重生成将替换</span>':'') + '</label>';
  }).join("");
  $("scenemodal").style.display = "flex";
}
function closeSceneViewModal(){ $("scenemodal").style.display = "none"; }

async function sceneViewSend(){
  const views = SCENE_VIEWS.filter(v => svState.sel[v]);
  if(!views.length){ toast("请至少勾选 1 个视角"); return; }
  const cur = (P.xiatang?.scenes||[]).find(s => s.name === svState.name);
  if(!cur) return;
  let model="", channelId="", size="1536x768";
  try{
    const cfg = await fetch("/gen-config").then(r=>r.json());
    const ch = (cfg.channels||[]).find(c=>c.configured);
    if(!ch){ toast("❌ 未配置可用生图渠道，请先到 ⚙ 设置完善"); return; }
    channelId = ch.id;
    const m0 = (ch.models||[])[0]||"";
    model = (typeof m0==="string")?m0:(m0.name||"");
    if(!model){ toast("❌ 渠道无可用模型"); return; }
    size = (cfg.default_sizes||{}).scene || "1536x768";
  }catch(e){ toast("❌ 读取渠道配置失败"); return; }
  const imgs = svState.refImg ? [svState.refImg] : [];
  let ok=0, fail=0;
  for(const v of views){
    const ok1 = await batchEnqueue("scene", cur.name + "-" + v, SCENE_VIEW_PROMPTS[v], model, size, channelId, imgs, 1);
    if(ok1) ok++; else fail++;
  }
  closeSceneViewModal();
  toast(fail ? "⚠️ 视角入队：成功 " + ok + "，失败 " + fail + "（任务面板可重试）" : "✅ 已入队 " + ok + " 个视角生图任务");
}

async function godViewGen(){
  const cur = (P.xiatang?.scenes||[]).find(s=>s.name===xtCurSel);
  if(!cur){ toast("请先选择场景"); return; }
  const v = cur.views_ready||{};
  if(!v["背面"] || !v["45°俯视全景"]){ toast("❌ 上帝视角需要先生成「背面」和「45°俯视全景」视角"); return; }
  if(!confirm("将基于「正面(或主图)/背面/45°俯视全景」生成平面布局（9:16），完成后自动生成线稿，确认？")) return;
  let model="", channelId="";
  try{
    const cfg = await fetch("/gen-config").then(r=>r.json());
    const ch = (cfg.channels||[]).find(c=>c.configured);
    if(!ch){ toast("❌ 未配置可用生图渠道"); return; }
    channelId = ch.id;
    const m0 = (ch.models||[])[0]||"";
    model = (typeof m0==="string")?m0:(m0.name||"");
  }catch(e){ toast("❌ 读取渠道配置失败"); return; }
  const front = (v["正面"] && cur.views && cur.views["正面"]) ? cur.views["正面"] : cur.image;
  const imgs = [front, cur.views["背面"], cur.views["45°俯视全景"]].filter(Boolean);
  const planPrompt = "以图1、图2、图3为场景母版，生成同一场景的90°垂直正俯上帝视角。镜头从正上方垂直向下拍摄，呈现完整平面布局。";
  toast("⏳ 正在生成平面布局…");
  const okPlan = await batchEnqueue("scene", cur.name + "-平面布局", planPrompt, model, "1088x1920", channelId, imgs, 1);
  if(!okPlan){ toast("❌ 平面布局入队失败"); return; }
  const done = await waitTaskDone(150000);
  if(!done){ toast("⚠️ 平面布局等待超时，可稍后手动重试线稿"); return; }
  toast("⏳ 平面布局完成，正在生成线稿…");
  await batchEnqueue("scene", cur.name + "-线稿", "转成线稿", model, "1088x1920", channelId, ["assets/scenes/" + cur.name + "-平面布局.png"], 1);
}

function waitTaskDone(timeoutMs){
  return new Promise(resolve => {
    const t0 = Date.now();
    const timer = setInterval(() => {
      fetch("/tasks").then(r=>r.json()).then(res => {
        if(!res.ok) return;
        const run = res.running||[];
        if(!run.length){ clearInterval(timer); resolve(true); }
        else if(Date.now()-t0 > (timeoutMs||150000)){ clearInterval(timer); resolve(false); }
      }).catch(()=>{ if(Date.now()-t0 > (timeoutMs||150000)){ clearInterval(timer); resolve(false); } });
    }, 2000);
  });
}

// ★ 2026-09-01 「设为正面」按钮与 setSceneAsFront 已移除（用户拍板）：任何视角图可用 👀 作为参考图生成其他视角；
//   后端 /scene-set-front 端点保留未动（不再有前端入口）。

// ===== 四视图角色卡生成（★ 2026-08-21 用户拍板：身份图两图制第二图；固定模板 + 自动引用该身份定妆照作参考）=====
async function genIdentitySheet(roleName, idId){
  if(!IS_SERVER){ toast("AI 生成需要服务模式：请双击「启动项目台.bat」"); return; }
  const role = (P.xiatang?.characters||[]).find(c=>c.name===roleName);
  const idn = (role?.identities||[]).find(i=>String(i.identity_id)===String(idId));
  if(!idn){ toast("未找到该身份"); return; }
  if(!idn.image_ready){ toast("⚠️ 请先生成该身份的定妆照（四视图卡以其为参考）"); return; }
  let model="", channelId="", size="1088x1920";
  try{
    const cfg = await fetch("/gen-config").then(r=>r.json());
    const ch = (cfg.channels||[]).find(c=>c.configured);
    if(!ch){ toast("❌ 未配置可用生图渠道，请先到 ⚙ 设置完善"); return; }
    channelId = ch.id;
    const m0 = (ch.models||[])[0]||"";
    model = (typeof m0==="string")?m0:(m0.name||"");
    if(!model){ toast("❌ 渠道无可用模型"); return; }
    size = (cfg.default_sizes||{}).identity || "1088x1920";   // ★ 2026-08-21 四视图卡：跟随设置面板「身份图」类别比例，未配置默认 9:16（1088x1920）
  }catch(e){ toast("❌ 读取渠道配置失败"); return; }
  const name = `${role.name}-${idId}-sheet`;
  const ok = await batchEnqueue("character", name, IDENTITY_SHEET_PROMPT, model, size, channelId, [idn.image], 1);
  toast(ok ? `✅ 已入队四视图卡任务：${name}` : "⚠️ 四视图卡入队失败（任务面板可重试）");
}

// ===== 批量生定妆照 / 批量生四视图（★ 2026-08-28 用户新增：角色页顶部按钮；★ 2026-09-02 同步进模板）=====
// 【批量生定妆】：所有角色的身份定妆照批量生成。前提=该角色已生成主图（自动垫主图锁脸）；不满足自动跳过。
async function batchGenIdentities(){
  if(!IS_SERVER){ toast("AI 生成需要服务模式：请双击「启动项目台.bat」"); return; }
  const chars = (P.xiatang?.characters) || [];
  const items = [], skipNoMain = [], skipDone = [];
  for(const c of chars){
    if(!c.image_ready){ skipNoMain.push(c.name); continue; }                       // 前提①：主图已生成
    for(const id of (c.identities||[])){
      if(id.image_ready){ skipDone.push(c.name + "·" + id.name); continue; }        // 已生成跳过
      if(!id.prompt){ skipDone.push(c.name + "·" + id.name + "（无提示词）"); continue; }
      items.push({name: c.name + "-" + id.identity_id + ".png", prompt: id.prompt, ref: findCurrentMainImage(c.name)});
    }
  }
  if(!items.length){
    toast("✅ 定妆照已全部生成" + (skipNoMain.length ? `（跳过 ${skipNoMain.length} 个未生成主图的角色）` : ""));
    return;
  }
  const msg = `将为 ${items.length} 个身份的定妆照批量生图（自动垫主图锁脸）\n` +
    (skipNoMain.length ? `\n⏭ 跳过 ${skipNoMain.length} 个角色：主图未生成（${skipNoMain.join("、")}）\n` : "") +
    (skipDone.length ? `\n⏭ 跳过 ${skipDone.length} 个身份：已生成或提示词缺失` : "") +
    `\n\n确认开始？`;
  if(!confirm(msg)) return;
  let model = "", channelId = "", size = "1088x1920";
  try{
    const cfg = await fetch("/gen-config").then(r => r.json());
    const ch = (cfg.channels||[]).find(c => c.configured);
    if(!ch){ toast("❌ 未配置可用生图渠道，请先到 ⚙ 设置完善"); return; }
    channelId = ch.id;
    const m0 = (ch.models||[])[0] || "";
    model = (typeof m0 === "string") ? m0 : (m0.name || "");
    if(!model){ toast("❌ 渠道无可用模型"); return; }
    size = (cfg.default_sizes||{}).identity || "1088x1920";
  }catch(e){ toast("❌ 读取渠道配置失败"); return; }
  toast(`⏳ 开始批量生成定妆照（${items.length} 个）…`);
  let queued = 0, fail = 0;
  const taskIds = [];
  let done = 0, succ = 0, fdone = 0;
  const onBatchDone = (st) => {
    done++;
    if(st === "success") succ++; else fdone++;
    if(done >= taskIds.length){
      toast(fdone ? `✅ 定妆照完成：成功 ${succ} 个${fdone ? `，失败 ${fdone} 个` : ""}` : `✅ 定妆照已全部完成（${succ} 个）`);
    }
  };
  for(const it of items){
    const ok = await batchEnqueue("identity", it.name, it.prompt, model, size, channelId, [it.ref], 1, onBatchDone);
    if(ok){ queued++; taskIds.push(ok); } else { fail++; }
  }
  if(fail){ toast(`⚠️ 定妆照入队：成功 ${queued}，失败 ${fail}（任务面板可重试）`); }
  else if(queued){ toast(`✅ 定妆照已全部入队（${queued} 个）`); }
}

// 【批量生四视】：所有角色的四视图卡批量生成（固定模板，引用该身份定妆照作参考）。
// 前提=该身份的定妆照已生成；不满足自动跳过。
async function batchGenIdentitySheets(){
  if(!IS_SERVER){ toast("AI 生成需要服务模式：请双击「启动项目台.bat」"); return; }
  const chars = (P.xiatang?.characters) || [];
  const items = [], skipNoId = [], skipDone = [];
  for(const c of chars){
    for(const id of (c.identities||[])){
      if(!id.image_ready){ skipNoId.push(c.name + "·" + id.name); continue; }       // 前提：定妆照已生成
      if(id.sheet_ready){ skipDone.push(c.name + "·" + id.name); continue; }        // 已生成跳过
      items.push({name: c.name + "-" + id.identity_id + "-sheet.png", ref: id.image});
    }
  }
  if(!items.length){
    toast("✅ 四视图已全部生成" + (skipNoId.length ? `（跳过 ${skipNoId.length} 个定妆照未生成的身份）` : ""));
    return;
  }
  const msg = `将为 ${items.length} 个身份的四视图卡批量生图（固定模板，引用该身份定妆照作参考）\n` +
    (skipNoId.length ? `\n⏭ 跳过 ${skipNoId.length} 个身份：定妆照未生成` : "") +
    (skipDone.length ? `\n⏭ 跳过 ${skipDone.length} 个身份：四视图已生成` : "") +
    `\n\n确认开始？`;
  if(!confirm(msg)) return;
  let model = "", channelId = "", size = "1088x1920";
  try{
    const cfg = await fetch("/gen-config").then(r => r.json());
    const ch = (cfg.channels||[]).find(c => c.configured);
    if(!ch){ toast("❌ 未配置可用生图渠道，请先到 ⚙ 设置完善"); return; }
    channelId = ch.id;
    const m0 = (ch.models||[])[0] || "";
    model = (typeof m0 === "string") ? m0 : (m0.name || "");
    if(!model){ toast("❌ 渠道无可用模型"); return; }
    size = (cfg.default_sizes||{}).identity || "1088x1920";
  }catch(e){ toast("❌ 读取渠道配置失败"); return; }
  toast(`⏳ 开始批量生成四视图（${items.length} 个）…`);
  let queued = 0, fail = 0;
  const taskIds = [];
  let done = 0, succ = 0, fdone = 0;
  const onBatchDone = (st) => {
    done++;
    if(st === "success") succ++; else fdone++;
    if(done >= taskIds.length){
      toast(fdone ? `✅ 四视图完成：成功 ${succ} 个${fdone ? `，失败 ${fdone} 个` : ""}` : `✅ 四视图已全部完成（${succ} 个）`);
    }
  };
  for(const it of items){
    const ok = await batchEnqueue("character", it.name, IDENTITY_SHEET_PROMPT, model, size, channelId, [it.ref], 1, onBatchDone);
    if(ok){ queued++; taskIds.push(ok); } else { fail++; }
  }
  if(fail){ toast(`⚠️ 四视图入队：成功 ${queued}，失败 ${fail}（任务面板可重试）`); }
  else if(queued){ toast(`✅ 四视图已全部入队（${queued} 个）`); }
}

