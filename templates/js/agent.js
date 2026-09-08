// ===== Agent（对话型 LLM）=====
const AGENT_LS_KEY = "xiaji.agents.v1";     // localStorage 存所有对话
const AGENT_CFG_KEY = "xiaji.agentcfg.v1";  // localStorage 存用户偏好（model + system_prompt）
let agentState = {
  cfg: null,           // {channels, default_model, system_prompt, configured} from /agent-config
  channels: [],
  defaultModel: "deepseek-v4-flash",
  systemPrompt: "",
  convs: [],           // [{id, title, messages: [{role, content, ts}], createdAt, updatedAt}]
  curId: null,
  busy: false,
  abort: null,
};

function _agentLoad(){
  try{
    const raw = localStorage.getItem(AGENT_LS_KEY);
    if(raw){ agentState.convs = JSON.parse(raw) || []; }
    const cfgRaw = localStorage.getItem(AGENT_CFG_KEY);
    if(cfgRaw){ const c = JSON.parse(cfgRaw) || {}; agentState.defaultModel = c.model || agentState.defaultModel; agentState.systemPrompt = c.system || ""; }
  }catch(e){}
  if(agentState.convs.length === 0){
    agentState.convs.push(_agentNewConv("新对话"));
  }
  agentState.curId = agentState.convs[0].id;
}
function _agentNewConv(title){
  return { id: "c_" + Date.now() + "_" + Math.random().toString(36).slice(2,7),
           title: title || "新对话",
           messages: [],
           createdAt: Date.now(), updatedAt: Date.now() };
}
function _agentSave(){
  try{ localStorage.setItem(AGENT_LS_KEY, JSON.stringify(agentState.convs)); }catch(e){}
  try{ localStorage.setItem(AGENT_CFG_KEY, JSON.stringify({model: agentState.defaultModel, system: agentState.systemPrompt})); }catch(e){}
}
function _agentCur(){ return agentState.convs.find(c => c.id === agentState.curId) || agentState.convs[0]; }
function _agentAutoTitle(text){
  const t = (text || "").trim().replace(/\s+/g, " ");
  return t.length > 24 ? t.slice(0, 24) + "…" : t;
}

async function _agentLoadCfg(){
  try{
    const r = await fetch("/agent-config");
    const j = await r.json();
    if(j.ok){
      agentState.cfg = j;
      agentState.channels = j.channels || [];
      // 用户没手动改过配置时，用后端默认
      if(!localStorage.getItem(AGENT_CFG_KEY)){
        agentState.defaultModel = j.default_model || agentState.defaultModel;
        agentState.systemPrompt = j.system_prompt || "";
      }
    }
  }catch(e){ console.warn("agent cfg load failed", e); }
}

function renderAgent(){
  _agentLoad();
  if(!agentState.cfg) _agentLoadCfg();   // 异步，不 await
  const cur = _agentCur();
  const msgsHtml = (cur.messages.length === 0) ? `
    <div class="agent-empty">
      <div>
        <div style="font-size:32px;margin-bottom:8px">🤖</div>
        <div style="font-size:14px;font-weight:500;color:var(--txt)">${esc(agentState.defaultModel)}</div>
        <div style="margin-top:4px">lk888 渠道 · OpenAI 协议透传 · 流式输出</div>
        <div class="hint">
          <b>试试这些场景：</b><br>
          · 帮我把 ch031 续写 200 字，POV 角色A<br>
          · 给主角生成一段角色定妆照的中文提示词<br>
          · 检查这段对话有没有 POV 四步缺失的视角<br>
          · 把这段剧情改编成分镜脚本格式（场景/角色/动作/对白）
        </div>
      </div>
    </div>` : cur.messages.map(m => _agentMsgHtml(m)).join("");

  const modelOptions = (() => {
    const set = new Set();
    (agentState.channels || []).forEach(ch => (ch.models || []).forEach(m => set.add(m.name || (typeof m === "string" ? m : ""))));
    if(set.size === 0) set.add(agentState.defaultModel);
    return Array.from(set);
  })();

  return `
    <div class="agent-page">
      <aside class="agent-side">
        <h3>💬 对话 <span class="ct" id="agent-conv-ct">${agentState.convs.length}</span></h3>
        <div class="agent-conv-list" id="agent-conv-list">
          ${agentState.convs.map(c => `
            <div class="agent-conv-item ${c.id===agentState.curId?"active":""}" data-cid="${c.id}" title="${esc(c.title)}">
              <span class="ti" onclick="agentSwitch('${c.id}')">${esc(c.title)}</span>
              <span class="x" onclick="event.stopPropagation();agentDel('${c.id}')" title="删除">×</span>
            </div>`).join("")}
        </div>
        <button class="newconv" onclick="agentNew()">+ 新建对话</button>
        <div class="agent-cfg" id="agent-cfg">
          <div class="row"><b>渠道状态</b><span id="agent-cfg-ok" class="${agentState.cfg?.configured?"ok":"ng"}">${agentState.cfg?.configured?"● 已连通":"● 未配置"}</span></div>
          <div class="row"><b>默认模型</b><span>${esc(agentState.defaultModel)}</span></div>
          <div class="row"><b>渠道数</b><span>${agentState.channels.length}</span><button onclick="agentTest()">🔌 测试</button></div>
        </div>
      </aside>
      <section class="agent-main">
        <div class="agent-head">
          <span style="font-size:13px;font-weight:600">🤖 Agent · 对话</span>
          <span class="sys">·</span>
          <select class="modsel" id="agent-model" onchange="agentSetModel(this.value)">
            ${modelOptions.map(m => `<option value="${esc(m)}" ${m===agentState.defaultModel?"selected":""}>${esc(m)}</option>`).join("")}
          </select>
          <span class="sys" id="agent-sys-state">${agentState.systemPrompt?`已设置系统提示（${agentState.systemPrompt.length} 字）`:"无系统提示"}</span>
          <button class="edit-sys" onclick="agentEditSys()">✏ 系统提示</button>
          <button class="clr" onclick="agentClearCur()">🗑 清空</button>
        </div>
        <div class="agent-msgs" id="agent-msgs">${msgsHtml}</div>
        <div class="agent-input">
          <textarea id="agent-input" rows="1" placeholder="输入消息，回车发送，Shift+回车换行" onkeydown="if(event.key==='Enter' && !event.shiftKey){event.preventDefault();agentSend();}" oninput="this.style.height='auto';this.style.height=Math.min(this.scrollHeight,160)+'px'"></textarea>
          ${agentState.busy ? '<button class="stop" onclick="agentStop()">⏹ 停止</button>' : '<button class="send" id="agent-send" onclick="agentSend()">发送 ➤</button>'}
        </div>
      </section>
    </div>`;
}

function _agentMsgHtml(m){
  const ts = m.ts ? new Date(m.ts).toLocaleTimeString("zh-CN", {hour:"2-digit", minute:"2-digit"}) : "";
  if(m.role === "user"){
    return `<div class="agent-msg user"><div class="who">你 · ${ts}</div>${esc(m.content)}</div>`;
  }
  if(m.role === "assistant"){
    return `<div class="agent-msg assistant" data-mid="${m.id||''}"><div class="who">🤖 ${esc(agentState.defaultModel)} · ${ts}</div>${m.content?esc(m.content):'<span class="agent-typing"><span class="dot"></span><span class="dot"></span><span class="dot"></span></span>'}</div>`;
  }
  if(m.role === "system"){
    return `<div class="agent-msg" style="align-self:center;max-width:90%;background:var(--bg);color:var(--mut);font-size:12px;padding:6px 12px;border-radius:8px">⚙ ${esc(m.content)}</div>`;
  }
  return "";
}

function bindAgent(){
  const el = $("agent-msgs");
  if(el) el.scrollTop = el.scrollHeight;
  setTimeout(()=>{ const t = $("agent-input"); if(t) t.focus(); }, 50);
}

function agentSwitch(cid){
  if(agentState.busy){ toast("请先停止当前生成"); return; }
  agentState.curId = cid;
  _agentSave();
  rerenderCurrent();
}
function agentNew(){
  if(agentState.busy){ toast("请先停止当前生成"); return; }
  const c = _agentNewConv("新对话 " + (agentState.convs.length + 1));
  agentState.convs.unshift(c);
  agentState.curId = c.id;
  _agentSave();
  rerenderCurrent();
}
function agentDel(cid){
  if(agentState.convs.length <= 1){ toast("至少保留一个对话"); return; }
  if(!confirm("删除这个对话？")) return;
  agentState.convs = agentState.convs.filter(c => c.id !== cid);
  if(agentState.curId === cid){
    agentState.curId = agentState.convs[0].id;
  }
  _agentSave();
  rerenderCurrent();
}
function agentClearCur(){
  const cur = _agentCur();
  if(!cur || cur.messages.length === 0){ toast("当前对话为空"); return; }
  if(!confirm("清空当前对话所有消息？")) return;
  cur.messages = [];
  cur.updatedAt = Date.now();
  _agentSave();
  rerenderCurrent();
}
function agentSetModel(m){
  agentState.defaultModel = m;
  _agentSave();
  toast("模型已切换：" + m);
}
function agentEditSys(){
  const cur = (agentState.systemPrompt || "");
  const v = prompt("系统提示（System Prompt）—— 设置 Agent 的角色与行为规范：", cur);
  if(v === null) return;
  agentState.systemPrompt = v;
  _agentSave();
  toast(v ? "系统提示已设置（" + v.length + " 字）" : "系统提示已清空");
  // 同步到后端配置
  fetch("/agent-config", { method:"POST", headers:{"Content-Type":"application/json"},
    body: JSON.stringify({ default_model: agentState.defaultModel, system_prompt: v, channels: agentState.channels.map(c => ({id:c.id, name:c.name, baseUrl:c.baseUrl, apiKey:"", apiFormat:c.apiFormat, models:c.models})) })})
    .then(r=>r.json()).then(j=>{ if(j.ok) toast("已同步到后端配置"); else toast("同步失败："+(j.error||"")); })
    .catch(e=>toast("同步出错："+e.message));
  rerenderCurrent();
}
async function agentTest(){
  const btn = event?.target; const old = btn?.textContent; if(btn){ btn.disabled = true; btn.textContent = "测试中…"; }
  try{
    const r = await fetch("/agent-test", { method:"POST", headers:{"Content-Type":"application/json"},
      body: JSON.stringify({ channel_id: agentState.channels?.[0]?.id, model: agentState.defaultModel })});
    const j = await r.json();
    if(j.ok){ toast("✅ " + (j.note || "连通成功")); }
    else { toast("❌ " + (j.error || "测试失败")); }
  }catch(e){ toast("请求失败：" + e.message); }
  finally{ if(btn){ btn.disabled = false; btn.textContent = old || "🔌 测试"; } }
}
function agentStop(){
  if(agentState.abort){ try{ agentState.abort.abort(); }catch(e){} }
  agentState.busy = false;
  agentState.abort = null;
  rerenderCurrent();
}

async function agentSend(){
  if(agentState.busy){ toast("正在生成中…"); return; }
  const ta = $("agent-input"); if(!ta) return;
  const text = (ta.value || "").trim();
  if(!text) return;
  // 等配置加载完（修复异步竞态：用户首屏立刻发消息时 cfg 还没回来）
  if(!agentState.cfg){ await _agentLoadCfg(); }
  if(!agentState.cfg?.configured){
    toast("Agent 未配置渠道，请先在 ⚙ 设置中添加 lk888 渠道");
    // 兜底：若 agent_config 缺失但 img_config 有 lk888 渠道，提示用户去设置一键补一个
    const imgHasL = await fetch("/gen-config").then(r=>r.json()).then(j => (j.channels||[]).some(c => c.apiFormat === "up_lk888" && c.apiKey)).catch(()=>false);
    if(imgHasL) toast("检测到 ⚙ 设置里有 lk888 渠道配置；点 🤖 顶部「系统提示」可一键补 Agent 渠道");
    return;
  }

  const cur = _agentCur();
  if(!cur.title || cur.title === "新对话" || /^新对话 \d+$/.test(cur.title)){
    cur.title = _agentAutoTitle(text);
  }
  const userMsg = { id: "m_" + Date.now(), role: "user", content: text, ts: Date.now() };
  const asstMsg = { id: "m_" + (Date.now()+1), role: "assistant", content: "", ts: Date.now() };
  cur.messages.push(userMsg, asstMsg);
  cur.updatedAt = Date.now();
  _agentSave();   // 先持久化再重绘：否则 rerenderCurrent → renderAgent → _agentLoad 会用旧 localStorage 冲掉刚 push 的消息
  ta.value = ""; ta.style.height = "auto";

  // 先把 user/asst 占位渲染出来
  appendAgentMessageDom(userMsg);
  const asstDom = appendAgentMessageDom(asstMsg);

  agentState.busy = true;
  agentState.abort = new AbortController();
  rerenderCurrent();
  $("agent-input")?.focus();

  // 构造请求 messages：只取 role+content（不带 ts/id），system 走 header（避免重复）
  const apiMessages = cur.messages.filter(m => m.role !== "system").slice(0, -1).map(m => ({role: m.role, content: m.content}));
  // 如果全局 systemPrompt 设置过，server 会自动注入；这里不再重复加

  const payload = { model: agentState.defaultModel, messages: apiMessages, stream: true };

  let fullText = "";
  try{
    const resp = await fetch("/agent-chat", { method:"POST", headers:{"Content-Type":"application/json"},
      body: JSON.stringify(payload), signal: agentState.abort.signal });
    if(!resp.ok){
      let err = "HTTP " + resp.status;
      try{ const j = await resp.json(); err = j.error || err; }catch(e){}
      asstMsg.content = "❌ " + err;
      asstMsg.error = true;
      agentState.busy = false; agentState.abort = null;
      _agentSave();
      rerenderCurrent();
      return;
    }
    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    while(true){
      const { done, value } = await reader.read();
      if(done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";
      for(const line of lines){
        const t = line.trim();
        if(!t || !t.startsWith("data:")) continue;
        const payloadStr = t.slice(5).trim();
        if(payloadStr === "[DONE]") continue;
        try{
          const obj = JSON.parse(payloadStr);
          // deepseek 思考时 delta.content 经常为空(都在 delta.reasoning_content)，三种字段都兜底取
          const choice = obj.choices?.[0] || {};
          const delta = choice.delta || {};
          const piece = delta.content || delta.reasoning_content || choice.message?.content || "";
          if(piece){
            fullText += piece;
            asstMsg.content = fullText;
            updateAgentMessageDom(asstMsg);
          }
        }catch(e){ /* ignore parse */ }
      }
    }
  }catch(e){
    if(e.name === "AbortError"){
      asstMsg.content = (asstMsg.content || "") + "\n\n⏹ 已手动停止";
    } else {
      asstMsg.content = "❌ 网络错误：" + e.message;
      asstMsg.error = true;
    }
  } finally {
    agentState.busy = false;
    agentState.abort = null;
    cur.updatedAt = Date.now();
    _agentSave();
    rerenderCurrent();
  }
}

function appendAgentMessageDom(m){
  const box = $("agent-msgs"); if(!box) return null;
  // 清掉空态
  const empty = box.querySelector(".agent-empty"); if(empty) empty.remove();
  const wrap = document.createElement("div");
  wrap.innerHTML = _agentMsgHtml(m);
  const node = wrap.firstElementChild;
  box.appendChild(node);
  box.scrollTop = box.scrollHeight;
  return node;
}
function updateAgentMessageDom(m){
  const box = $("agent-msgs"); if(!box) return;
  const nodes = box.querySelectorAll(`.agent-msg[data-mid="${m.id}"]`);
  nodes.forEach(n => { n.outerHTML = _agentMsgHtml(m); });
  box.scrollTop = box.scrollHeight;
}


// ===== Agent 右侧滑出面板（右上角按钮触发，精细版）=====
function toggleAgentDrawer(){
  const d = $("agent-drawer"), m = $("agent-mask"), btn = $("agent-btn");
  if(!d) return;
  const open = !d.classList.contains("open");
  d.classList.toggle("open", open);
  if(m) m.classList.toggle("open", open);
  if(btn) btn.classList.toggle("active", open);
  if(open){
    document.body.style.overflow = "hidden";
    const b = $("agent-drawer-body");
    if(b && !b.querySelector(".agent-main")){ b.innerHTML = renderAgent(); bindAgent(); }
    const ms = $("agent-msgs");
    if(ms) ms.scrollTop = ms.scrollHeight;
  } else {
    document.body.style.overflow = "";
  }
}
function closeAgentDrawer(){
  const d = $("agent-drawer"), m = $("agent-mask"), btn = $("agent-btn");
  if(d) d.classList.remove("open");
  if(m) m.classList.remove("open");
  if(btn) btn.classList.remove("active");
  document.body.style.overflow = "";
}
document.addEventListener("keydown", function(e){ if(e.key === "Escape") closeAgentDrawer(); });

