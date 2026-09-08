# -*- coding: utf-8 -*-
"""
api_slot.py —— 项目台「API 插槽」模块（可插拔）

把 server.py 中所有「API 设置」与「API 调用」内容抽离到这里，
server.py 只负责路由 / 保存 / 状态，通过固定接口调用本模块。

为什么要用插槽：
- 换 API 平台 / 换调用协议时，只改本文件，server.py 主体不动。
- 本模块不依赖 server.py（自带 log 与 ROOT），可独立测试、独立替换。

接口一览（server.py 只允许调用这些）：
  常量         SIZE_TO_RATIO / DEFAULT_MODELS / DEFAULT_PROTOCOL / PROTOCOLS / DEFAULT_SIZES / DEFAULT_AGENT_MODEL
               DEFAULT_VIDEO_MODEL / VIDEO_DURATIONS / VIDEO_ASPECT_RATIOS / VIDEO_RESOLUTIONS
  配置读写     load_img_config / save_img_config / load_agent_config / save_agent_config
               bootstrap_agent_config / atomic_write_json / merge_channels
  渠道工具     normalize_protocol / normalize_models_list / safe_channel / channel_configured
               find_channel / find_agent_channel / endpoint_with_protocol
  生图调用     generate_image(channel, model, prompt, image_b64s, image_datauris, size) -> (img_bytes|None, err|None, meta|dict)
  生视频调用   generate_video(channel, model, prompt, image_b64s, image_datauris,
                              duration, aspect_ratio, resolution) -> (video_bytes|None, err|None, meta|dict)
  Agent 调用   agent_chat_completion(channel, model, messages, system_prompt, stream,
                                     temperature, max_tokens, default_model) -> (ok, resp)
  测试         test_img_channel(channel) / fetch_models(base_url, api_key, api_format)
               test_agent_channel(channel, model, default_model)
"""
import os, re, json, sys, time, base64, uuid, urllib.request, urllib.error, subprocess
from datetime import datetime

# 本模块目录（与 server.py 同级 = project/）；所有相对路径以此为基准
ROOT = os.path.dirname(os.path.abspath(__file__))

# ============================================================
# 常量（API 设置）
# ============================================================

# 尺寸值（前端用）→ up.lk888.ai 平台的 aspect_ratio 映射
# ★ 2026-08-19 修复：改为动态计算（gcd 约分），任意尺寸正确映射，不再有未映射错标 1:1 的问题
#   （img_config.json sizes 已精简为 12 个精选尺寸，ratio_of 仍兼容全部尺寸）
SIZE_TO_RATIO = {
    "1024x1024": "1:1",  "1024x1536": "2:3",  "1536x1024": "3:2",
    "960x1280": "3:4",    "1280x960": "4:3",
    "1088x1920": "9:16",  "1920x1088": "16:9",
    "1024x1280": "4:5",   "1280x1024": "5:4",
    "960x1920": "1:2",    "1920x960": "2:1",
    "1536x768": "2:1",    "2048x1024": "2:1",  "3840x1920": "2:1",
    "auto": "1:1",
}

def _gcd(a, b):
    while b:
        a, b = b, a % b
    return a

def ratio_of(size):
    """任意尺寸 → 宽高比（先查手写映射，未命中按 gcd 动态计算）"""
    r = SIZE_TO_RATIO.get(size)
    if r:
        return r
    try:
        w, h = map(int, str(size).lower().split("x"))
        g = _gcd(w, h)
        return f"{w // g}:{h // g}"
    except Exception:
        return "1:1"

# 图片生成 API 配置（多渠道：每个渠道 = 独立 baseUrl/apiKey/协议/模型列表）
# 旧格式（api_key/endpoint 单 key）会在 load_img_config 时自动迁移为 channels[0]，不丢配置
IMG_CONFIG_PATH = os.path.join(ROOT, "img_config.json")
DEFAULT_MODELS = ["gpt-image-2", "gpt-image-1", "nano-banana", "seedream", "midjourney"]
DEFAULT_PROTOCOL = "up_lk888"
PROTOCOLS = ("openai", "gemini", "ark", "up_lk888", "minimax_h3")
DEFAULT_SIZES = [
    {"label": "960x1280（3:4 竖版·主图默认）", "value": "960x1280"},
    {"label": "1024x1536（2:3 竖版）", "value": "1024x1536"},
    {"label": "1024x1024（1:1 方图）", "value": "1024x1024"},
    {"label": "1536x1024（3:2 横版）", "value": "1536x1024"},
    {"label": "1024x2048（1:2 竖版长图）", "value": "1024x2048"},
    {"label": "2048x2048（2K 方图）", "value": "2048x2048"},
    {"label": "1280x720（16:9 横屏）", "value": "1280x720"},
    {"label": "720x1280（9:16 小竖屏）", "value": "720x1280"},
    {"label": "auto", "value": "auto"},
]

# Agent（对话型 LLM）配置：独立于 img_config.json，复用 lk888 渠道的 baseUrl/apiKey
# 协议固定 OpenAI 兼容透传（POST {base}/v1/chat/completions）
AGENT_CONFIG_PATH = os.path.join(ROOT, "agent_config.json")
DEFAULT_AGENT_MODEL = "deepseek-v4-flash"

# ============================================================
# 日志（与 server.py 共用 server.log；不依赖 server.py）
# ============================================================
LOG_PATH = os.path.join(ROOT, "server.log")

# Windows CMD 默认 GBK 代码页，emoji(🖼✅❌等)会乱码或不可见；过滤 emoji 让 CMD 输出清晰可读
_EMOJI_RE = re.compile(r"[\U0001F000-\U0001FFFF]|[\u2600-\u27BF]")


def log(msg):
    """写一条日志：server.log 文件 + CMD 窗口(stderr)。任何异常都不影响主流程。"""
    try:
        line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
        try:
            with open(LOG_PATH, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            pass
        # 终端输出过滤 emoji（避免 GBK 终端乱码）；server.log 仍保留 emoji
        try:
            safe = _EMOJI_RE.sub("", line)
        except Exception:
            safe = line
        print(safe, file=sys.stderr, flush=True)
    except Exception:
        pass


# ============================================================
# 配置读写（API 设置）
# ============================================================

def atomic_write_json(path, obj):
    """原子写 JSON：先写 <path>.tmp 再 os.replace，3 次重试。免疫 Windows 瞬时文件锁/半写损坏。"""
    tmp = path + ".tmp"
    last_err = None
    for attempt in range(3):
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(json.dumps(obj, ensure_ascii=False, indent=2))
            os.replace(tmp, path)
            return True
        except OSError as e:
            last_err = e
            try:
                time.sleep(0.4 * (attempt + 1))
            except Exception:
                pass
    try:
        os.remove(tmp)
    except Exception:
        pass
    return f"写入失败: {last_err}"


def load_img_config():
    """读取图片生成配置；旧格式（api_key/endpoint）自动迁移为 channels[0] 并写回；未配置返回 None"""
    if not os.path.exists(IMG_CONFIG_PATH):
        return None
    try:
        cfg = json.load(open(IMG_CONFIG_PATH, encoding="utf-8"))
    except Exception:
        return None
    channels = cfg.get("channels")
    if isinstance(channels, list) and channels:
        cfg["channels"] = [safe_channel(c, f"ch_{i}") for i, c in enumerate(channels)]
        return cfg
    # 旧格式迁移（单 key）
    api_key = str(cfg.get("api_key") or "").strip()
    if not api_key:
        return None
    new_cfg = {
        "channels": [{
            "id": "default",
            "name": "默认渠道",
            "baseUrl": (str(cfg.get("endpoint") or "")).strip() or "https://api.lk888.ai",
            "apiKey": api_key,
            "apiFormat": DEFAULT_PROTOCOL,
            "models": normalize_models_list(cfg.get("models") or DEFAULT_MODELS),
        }],
        "sizes": cfg.get("sizes") if isinstance(cfg.get("sizes"), list) and cfg["sizes"] else DEFAULT_SIZES,
    }
    atomic_write_json(IMG_CONFIG_PATH, new_cfg)
    return new_cfg


def save_img_config(cfg):
    """保存图片生成配置（写 img_config.json）"""
    return atomic_write_json(IMG_CONFIG_PATH, cfg)


def load_agent_config():
    """读取 agent_config.json；不存在则自动从 img_config.json 第一个已配置渠道引导生成。"""
    if not os.path.exists(AGENT_CONFIG_PATH):
        bootstrap_agent_config()
    try:
        return json.loads(open(AGENT_CONFIG_PATH, encoding="utf-8").read())
    except Exception:
        return {"default_model": DEFAULT_AGENT_MODEL, "system_prompt": "", "channels": []}


def save_agent_config(cfg):
    return atomic_write_json(AGENT_CONFIG_PATH, cfg)


def bootstrap_agent_config():
    """首次启动时从 img_config.json 引导一份 Agent 配置（仅当 img_config 已有 lk888 渠道时）。"""
    img = {}
    try:
        img = json.loads(open(IMG_CONFIG_PATH, encoding="utf-8").read())
    except Exception:
        pass
    src = None
    for ch in (img.get("channels") or []):
        if ch.get("baseUrl") and ch.get("apiKey"):
            src = ch
            break
    seed = {
        "default_model": DEFAULT_AGENT_MODEL,
        "system_prompt": "",
        "channels": [
            {
                "id": "lk888_default",
                "name": "LK888 Chat",
                "baseUrl": (src.get("baseUrl") if src else "https://api.lk888.ai").rstrip("/"),
                "apiKey": src.get("apiKey") if src else "",
                "apiFormat": "openai",
                "models": [{"name": DEFAULT_AGENT_MODEL, "script": ""}],
            }
        ],
    }
    atomic_write_json(AGENT_CONFIG_PATH, seed)


def merge_channels(existing_channels, patch_channels, id_prefix):
    """合并渠道列表（保存配置用）：前端传 apiKey 为空则保留旧值；id 为空自动生成。"""
    old_map = {ch.get("id"): ch for ch in (existing_channels or [])}
    new_channels = []
    for i, ch in enumerate(patch_channels or []):
        if not isinstance(ch, dict):
            continue
        cid = (str(ch.get("id") or "")).strip() or (id_prefix + uuid.uuid4().hex[:8])
        old = old_map.get(cid) or {}
        api_key = str(ch.get("apiKey") or "")
        if not api_key:
            api_key = old.get("apiKey") or ""
        new_channels.append(safe_channel({**ch, "id": cid, "apiKey": api_key}, cid))
    return new_channels


# ============================================================
# 渠道工具（API 设置）
# ============================================================

def normalize_protocol(value):
    return value if value in PROTOCOLS else DEFAULT_PROTOCOL


def normalize_models_list(models):
    """统一规范化模型列表：支持 ['gpt-image-2'] 或 [{name, script?}]"""
    out = []
    for m in models or []:
        if isinstance(m, str):
            name = m.strip()
            if name:
                out.append({"name": name, "script": ""})
        elif isinstance(m, dict):
            name = (m.get("name") or "").strip()
            if name:
                out.append({"name": name, "script": m.get("script") or ""})
    return out


def safe_channel(ch, default_id=None):
    """规范化一个渠道对象（保证字段齐全）"""
    return {
        "id": (str(ch.get("id") or "")).strip() or (default_id or "ch_" + uuid.uuid4().hex[:8]),
        "name": (str(ch.get("name") or "")).strip() or "未命名渠道",
        "baseUrl": (str(ch.get("baseUrl") or "")).strip(),
        "apiKey": str(ch.get("apiKey") or ""),
        "apiFormat": normalize_protocol(ch.get("apiFormat")),
        "models": normalize_models_list(ch.get("models")),
    }


def channel_configured(ch):
    return bool(ch and ch.get("baseUrl") and ch.get("apiKey"))


def find_channel(cfg, channel_id):
    """按 id 找渠道；无 id 时返回第一个已配置的渠道"""
    channels = (cfg or {}).get("channels") or []
    if channel_id:
        for ch in channels:
            if ch.get("id") == channel_id:
                return ch
    for ch in channels:
        if channel_configured(ch):
            return ch
    return channels[0] if channels else None


def find_agent_channel(cfg, channel_id):
    """找已配置的 Agent 渠道；按 id 优先，无则第一个已配置的渠道。"""
    channels = (cfg or {}).get("channels") or []
    if channel_id:
        for ch in channels:
            if ch.get("id") == channel_id:
                return ch
    for ch in channels:
        if ch.get("baseUrl") and ch.get("apiKey"):
            return ch
    return channels[0] if channels else None


def endpoint_with_protocol(endpoint, api_format):
    """按协议补全 baseUrl 路径：openai/up_lk888→/v1；gemini→/v1beta；ark→/api/v3；minimax_h3→原样（路径自带 /api/minimax/v2）"""
    endpoint = (endpoint or "").strip().rstrip("/")
    if not endpoint:
        return ""
    low = endpoint.lower()
    if api_format == "minimax_h3":
        return endpoint
    if api_format == "gemini":
        return endpoint if (low.endswith("/v1") or low.endswith("/v1beta")) else endpoint + "/v1beta"
    if api_format == "ark":
        return endpoint if low.endswith("/api/v3") else endpoint + "/api/v3"
    return endpoint if low.endswith("/v1") else endpoint + "/v1"


# ============================================================
# Node 脚本引擎（生图调用 · 模型自定义脚本）
# ============================================================

def _download_result(url, timeout=60):
    """下载生图结果图（★ 2026-08-22 加固：带 UA/Accept 头 + 最多 3 次重试（间隔 1.5s 递增）。
    背景：lk888 平台 result_url 偶发瞬时拒绝（WinError 10061）或 CDN 拒无 UA 请求；
    错误信息带 URL 前 120 字符便于诊断。返回 (bytes|None, err|None)。"""
    last = None
    for i in range(3):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 WorkBuddy/1.0",
                "Accept": "image/*,*/*;q=0.8",
            })
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read(), None
        except Exception as e:
            last = e
            if i < 2:
                time.sleep(1.5 * (i + 1))
    return None, f"下载图片失败：{last}（url={str(url)[:120]}）"

def find_node_executable():
    """找 node 可执行路径：1) NODE_BIN 环境变量 2) 系统 PATH 3) WorkBuddy 自带 node 4) 系统常见安装位置"""
    env_path = os.environ.get("NODE_BIN")
    if env_path and os.path.isfile(env_path):
        return env_path
    # 系统 PATH
    for p in os.environ.get("PATH", "").split(os.pathsep):
        cand = os.path.join(p, "node.exe" if sys.platform == "win32" else "node")
        if os.path.isfile(cand):
            return cand
    # WorkBuddy 自带
    wb = r"C:\Users\123\.workbuddy\binaries\node\versions"
    if os.path.isdir(wb):
        for d in sorted(os.listdir(wb), reverse=True):
            cand = os.path.join(wb, d, "node.exe" if sys.platform == "win32" else "node")
            if os.path.isfile(cand):
                return cand
    # Windows 常见安装位置
    if sys.platform == "win32":
        for p in (r"C:\Program Files\nodejs\node.exe", r"C:\Program Files (x86)\nodejs\node.exe"):
            if os.path.isfile(p):
                return p
    return None


# Node 沙箱模板：注入 http/poll helpers + 用户脚本。返回 string[]（图片 URL 或 dataURL）
WRAPPER_JS_TEMPLATE = r'''const fs = require('fs');
const ARGS = JSON.parse(fs.readFileSync(process.argv[2], 'utf-8'));

const http = {
  async post(path, body, opts = {}) {
    const url = ARGS.baseUrl.replace(/\/$/, '') + '/' + String(path).replace(/^\//, '');
    const headers = Object.assign({'Authorization': 'Bearer ' + ARGS.apiKey}, opts.headers || {});
    const init = { method: 'POST', headers };
    if (body !== undefined && body !== null) {
      if (typeof body === 'string') init.body = body;
      else { headers['Content-Type'] = headers['Content-Type'] || 'application/json'; init.body = JSON.stringify(body); }
    }
    const r = await fetch(url, init);
    return await r.json();
  },
  async get(path, opts = {}) {
    const url = ARGS.baseUrl.replace(/\/$/, '') + '/' + String(path).replace(/^\//, '');
    const headers = Object.assign({'Authorization': 'Bearer ' + ARGS.apiKey}, opts.headers || {});
    const r = await fetch(url, Object.assign({method: 'GET', headers}, opts));
    return await r.json();
  }
};
async function poll(fetcher, isFinal, opts = {}) {
  const interval = opts.intervalMs || 5000;
  const timeout = opts.timeoutMs || 600000;
  const deadline = Date.now() + timeout;
  let lastErr = null;
  while (Date.now() < deadline) {
    try { const res = await fetcher(); if (isFinal(res)) return res; } catch(e) { lastErr = e; }
    await new Promise(r => setTimeout(r, interval));
  }
  throw new Error('轮询超时' + (lastErr ? '：' + (lastErr.message || lastErr) : ''));
}

(async () => {
  try {
    // userCode 从 args.json 读取，不嵌入源码——避免反引号/美元符嵌套 SyntaxError
    const userCode = ARGS.userCode || '';
    const userFn = new Function('apiKey', 'baseUrl', 'model', 'prompt', 'images', 'params', 'http', 'poll',
      'return (async () => { ' + userCode + ' })();'
    );
    const result = await userFn(ARGS.apiKey, ARGS.baseUrl, ARGS.model, ARGS.prompt, ARGS.images, ARGS.params, http, poll);
    if (!Array.isArray(result)) throw new Error('脚本必须返回 string[]（图片 URL 或 dataURL），实际: ' + typeof result);
    process.stdout.write(JSON.stringify(result));
  } catch(e) {
    const msg = e && e.stack ? e.stack : String(e);
    process.stdout.write(JSON.stringify({error: msg}));
    process.exit(1);
  }
})();
'''


def _resolve_model_obj(channel, model_name):
    """从渠道的 models 列表查找模型对象（支持字符串或对象），找不到返回 {name, script:''}"""
    name = (model_name or "").strip()
    for m in (channel.get("models") or []):
        if isinstance(m, dict) and (m.get("name") or "").strip() == name:
            return m
    return {"name": name, "script": ""}


def _run_model_script(channel, model_name, prompt, images, size):
    """在 Node 沙箱执行模型自定义脚本（带 http/poll helpers），返回 (img_bytes, error)。
    images: list[str] base64（可为空）"""
    api_key = channel.get("apiKey") or ""
    api_format = channel.get("apiFormat") or DEFAULT_PROTOCOL
    base_url = endpoint_with_protocol(channel.get("baseUrl"), api_format)
    if not api_key:
        return None, "渠道未配置 API Key"
    if not base_url:
        return None, "渠道 Base URL 为空"
    images = [b for b in (images or []) if b]
    params = {"size": ratio_of(size), "raw_size": size, "aspect_ratio": ratio_of(size)}
    model_obj = _resolve_model_obj(channel, model_name)
    user_code = (model_obj.get("script") or "").strip()
    if not user_code:
        return None, "模型未配置调用脚本"
    tmp_dir = os.path.join(ROOT, "_tmp_script")
    os.makedirs(tmp_dir, exist_ok=True)
    job_id = uuid.uuid4().hex
    args_path = os.path.join(tmp_dir, f"args_{job_id}.json")
    script_path = os.path.join(tmp_dir, f"script_{job_id}.js")
    try:
        with open(args_path, "w", encoding="utf-8") as f:
            json.dump({"apiKey": api_key, "baseUrl": base_url, "model": model_name, "prompt": prompt, "images": images, "params": params, "userCode": user_code}, f, ensure_ascii=False)
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(WRAPPER_JS_TEMPLATE)
        node_exe = find_node_executable()
        if not node_exe:
            return None, "Node.js 未安装或不在 PATH（脚本引擎需要 node 可执行；可安装 Node.js 或在系统环境变量设 NODE_BIN 指向 node.exe）"
        proc = subprocess.run([node_exe, script_path, args_path], capture_output=True, timeout=600, cwd=ROOT)
        if proc.returncode != 0:
            err = proc.stderr.decode("utf-8", errors="replace")[:500]
            out = proc.stdout.decode("utf-8", errors="replace").strip()
            return None, f"脚本执行失败 (exit={proc.returncode})：{err or out or '无输出'}"
        out = proc.stdout.decode("utf-8", errors="replace").strip()
        # 最后一行 JSON
        last_line = out.splitlines()[-1] if out else ""
        try:
            result = json.loads(last_line)
        except Exception:
            return None, f"脚本输出非 JSON：{out[:300]}"
        if isinstance(result, dict) and result.get("error"):
            return None, f"脚本错误：{result['error'][:400]}"
        if not isinstance(result, list) or not result:
            return None, f"脚本应返回 string[]，实际：{str(result)[:200]}"
        url = result[0]
        if not isinstance(url, str):
            return None, f"脚本返回的不是字符串 URL：{str(url)[:200]}"
        if url.startswith("data:"):
            try:
                return base64.b64decode(url.split(",", 1)[1]), None
            except Exception as e:
                return None, f"dataURL 解码失败：{e}"
        try:
            return _download_result(url)
        except Exception as e:
            return None, f"下载图片失败：{e}"
    except subprocess.TimeoutExpired:
        return None, "脚本执行超时（>600s）"
    except FileNotFoundError:
        return None, "Node.js 未安装或不在 PATH（脚本引擎需要 node 可执行）"
    except Exception as e:
        return None, f"脚本运行异常：{e}"
    finally:
        try: os.remove(args_path)
        except Exception: pass
        try: os.remove(script_path)
        except Exception: pass


# ============================================================
# 生图调用（按渠道协议分叉；返回图片字节，不负责保存）
# ============================================================

def generate_image(channel, model, prompt, image_b64s, image_datauris, size):
    """调图片生成 API 拿图片字节。内部按协议分叉：
    - up_lk888：异步任务式（/v1/media/generate 建任务 → 轮询 status → 下载 result_url）
    - openai：POST /v1/images/generations（b64_json）；垫图走 /v1/images/edits（multipart）
    - gemini：POST /v1beta/models/{m}:generateContent（inline_data）
    - ark：POST /api/v3/images/generations（JSON 内 image 数组垫图）
    - 模型配置了自定义脚本（model.script）时优先走 Node 沙箱脚本
    返回 (img_bytes|None, err|None, meta|dict)：meta 含 task_id/result_url/script 等附加信息（供调用方透传）。"""
    api_format = channel.get("apiFormat") or DEFAULT_PROTOCOL
    endpoint = endpoint_with_protocol(channel.get("baseUrl"), api_format)
    api_key = channel.get("apiKey") or ""
    if not endpoint:
        return None, "渠道 Base URL 为空", {}
    if not api_key:
        return None, "渠道未配置 API Key", {}
    if not endpoint:
        return None, "渠道 Base URL 为空", {}
    if not api_key:
        return None, "渠道未配置 API Key", {}
    # 默认 model：取第一个模型的 name（兼容字符串列表或对象列表）
    if not model:
        models_list = channel.get("models") or [{"name": DEFAULT_MODELS[0]}]
        first = models_list[0] if models_list else {"name": DEFAULT_MODELS[0]}
        model = first.get("name") if isinstance(first, dict) else first
    aspect_ratio = ratio_of(size)
    image_b64 = image_b64s[0] if image_b64s else ""

    # ========== 模型自定义脚本（最高优先级） ==========
    model_obj = _resolve_model_obj(channel, model)
    if (model_obj.get("script") or "").strip():
        log(f"🖼 生图走模型脚本: model={model} script长度={len(model_obj['script'])}字符")
        # ★ 垫图传 data URI（image_datauris）而非纯 base64：lk888 等平台要求
        #    data:image/...;base64,... 或 URL；纯 base64 会被拒（400 image 参数格式错误）。
        #    脚本如需纯 base64 可从 data URI split(";base64,",1)[1] 自取。
        img_bytes, err = _run_model_script(channel, model, prompt, image_datauris, size)
        return img_bytes, err, {"script": True}

    try:
        # ========== up_lk888：异步任务式（JSON 提交） ==========
        if api_format == "up_lk888":
            payload = {
                "model": model,
                "prompt": prompt,
                "n": 1,
                "params": {
                    "aspect_ratio": aspect_ratio,
                    "size": size,
                    "resolution": "1K",
                    "response_format": "url",
                    "quality": "high",
                },
            }
            if image_datauris:
                payload["params"]["images"] = image_datauris
            body = json.dumps(payload).encode("utf-8")
            try:
                r = urllib.request.Request(endpoint + "/media/generate", data=body,
                    headers={"Authorization": f"Bearer {api_key}",
                             "Content-Type": "application/json"},
                    method="POST")
                with urllib.request.urlopen(r, timeout=60) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as e:
                detail = e.read().decode("utf-8", errors="replace")[:400]
                return None, f"create task failed HTTP {e.code}: {detail}", {}
            except Exception as e:
                return None, f"create task failed: {e}", {}
            task_id = (data.get("data") or {}).get("task_id") or data.get("task_id")
            if not task_id:
                log(f"❌ 生图建任务失败(无task_id): model={model} resp={json.dumps(data, ensure_ascii=False)[:200]}")
                return None, f"no task_id: {json.dumps(data, ensure_ascii=False)[:300]}", {}
            log(f"🖼 生图建任务 ok: model={model} task_id={task_id}")
            task_start = time.time()
            deadline = time.time() + 300
            last_status_err = "none"
            while time.time() < deadline:
                time.sleep(5)
                try:
                    pr = urllib.request.Request(endpoint + f"/media/status?task_id={task_id}",
                        headers={"Authorization": f"Bearer {api_key}"}, method="GET")
                    with urllib.request.urlopen(pr, timeout=30) as presp:
                        pdata = json.loads(presp.read().decode("utf-8"))
                    # API 文档中 status 字段在顶层；兼容部分平台包在 data 里的情况
                    pdat = pdata.get("data") or pdata or {}
                    is_final = bool(pdat.get("is_final"))
                    state = pdat.get("state", "")
                    result_url = pdat.get("result_url")
                    err_msg = pdat.get("error") or pdat.get("error_message")
                    # 终态判定：is_final === true（平台文档规范）
                    if is_final:
                        if state == "success" and result_url:
                            img_bytes, dl_err = _download_result(result_url)
                            if img_bytes is None:
                                log(f"❌ 生图结果下载失败: task_id={task_id} {dl_err}")
                                return None, f"下载图片失败 task_id={task_id}: {dl_err}", {"task_id": task_id, "result_url": result_url}
                            log(f"✅ 生图完成: task_id={task_id} state=success 耗时={time.time()-task_start:.0f}s 图片={len(img_bytes)}B")
                            return img_bytes, None, {"task_id": task_id, "result_url": result_url}
                        if state == "failed":
                            log(f"❌ 生图任务失败: task_id={task_id} err={err_msg or pdat}")
                            return None, f"task failed task_id={task_id}: {err_msg or pdat}", {}
                        # 终态但 state 既不是 success 也不是 failed（罕见）：按失败处理
                        log(f"❌ 生图终态异常: task_id={task_id} state={state!r} resp={json.dumps(pdat, ensure_ascii=False)[:200]}")
                        return None, f"task ended (is_final=true) but state={state!r}: {pdat}", {}
                except Exception as e:
                    # 状态轮询单次失败继续，但保留最近错误便于超时后提示
                    last_status_err = str(e)
            log(f"❌ 生图轮询超时(300s): task_id={task_id} last_err={last_status_err or 'none'}")
            return None, f"task timeout task_id={task_id} (300s). last err: {last_status_err or 'none'}", {}

        # ========== gemini：generateContent ==========
        if api_format == "gemini":
            payload = {"contents": [{"parts": [{"text": prompt}]}]}
            if image_b64s:
                try:
                    extra_parts = []
                    for b64 in image_b64s:
                        extra_parts.append({"inline_data": {"mime_type": "image/png", "data": b64}})
                    payload["contents"][0]["parts"] = extra_parts + [{"text": prompt}]
                except Exception:
                    return None, "垫图 base64 解码失败", {}
            r = urllib.request.Request(f"{endpoint}/models/{urllib.parse.quote(model)}:generateContent",
                data=json.dumps(payload).encode("utf-8"),
                headers={"x-goog-api-key": api_key, "Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(r, timeout=180) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            img_bytes = None
            for cand in (data.get("candidates") or []):
                for part in (cand.get("content") or {}).get("parts") or []:
                    inline = part.get("inlineData") or part.get("inline_data") or {}
                    if inline.get("data"):
                        img_bytes = base64.b64decode(inline["data"])
                        break
                    file_uri = part.get("fileData") or {}
                    if file_uri.get("fileUri"):
                        with urllib.request.urlopen(file_uri["fileUri"], timeout=60) as ir:
                            img_bytes = ir.read()
                        break
                if img_bytes:
                    break
            if not img_bytes:
                return None, f"Gemini 未返回图片：{json.dumps(data, ensure_ascii=False)[:300]}", {}
            return img_bytes, None, {}

        # ========== ark：/api/v3/images/generations（JSON，image 数组垫图） ==========
        if api_format == "ark":
            payload = {"model": model, "prompt": prompt, "n": 1, "response_format": "b64_json"}
            if size and size != "auto":
                payload["size"] = size
            if image_datauris:
                payload["image"] = image_datauris
            r = urllib.request.Request(f"{endpoint}/images/generations",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(r, timeout=180) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            img_bytes = _extract_image_bytes(data)
            if not img_bytes:
                return None, f"方舟未返回图片：{json.dumps(data, ensure_ascii=False)[:300]}", {}
            return img_bytes, None, {}

        # ========== openai（默认）：同步 /images/generations，垫图走 /images/edits multipart ==========
        if image_b64:
            try:
                img_bytes_list = [base64.b64decode(b) for b in image_b64s]
            except Exception:
                return None, "垫图 base64 解码失败", {}
            boundary = "----FormBoundary" + uuid.uuid4().hex
            parts = []
            for fname2, val in (("model", model), ("prompt", prompt), ("n", "1"), ("response_format", "b64_json"), ("quality", "high")):
                parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{fname2}"\r\n\r\n{val}\r\n'.encode("utf-8"))
            if size and size != "auto":
                parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="size"\r\n\r\n{size}\r\n'.encode("utf-8"))
            for i, img_bytes in enumerate(img_bytes_list):
                file_header = (f'--{boundary}\r\n'
                               f'Content-Disposition: form-data; name="image"; filename="ref{i}.png"\r\n'
                               f'Content-Type: image/png\r\n\r\n').encode("utf-8")
                parts.append(file_header + img_bytes + b"\r\n")
            body = b"".join(parts) + f'--{boundary}--\r\n'.encode("utf-8")
            r = urllib.request.Request(f"{endpoint}/images/edits", data=body,
                headers={"Authorization": f"Bearer {api_key}",
                         "Content-Type": f"multipart/form-data; boundary={boundary}"}, method="POST")
            with urllib.request.urlopen(r, timeout=180) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        else:
            payload = {"model": model, "prompt": prompt, "n": 1, "response_format": "b64_json", "quality": "high"}
            if size and size != "auto":
                payload["size"] = size
            r = urllib.request.Request(f"{endpoint}/images/generations",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(r, timeout=180) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        img_bytes = _extract_image_bytes(data)
        if not img_bytes:
            return None, f"API 未返回图片：{json.dumps(data, ensure_ascii=False)[:300]}", {}
        return img_bytes, None, {}
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")[:400]
        return None, f"API 返回 {e.code}: {detail}", {}
    except Exception as e:
        return None, f"调用失败: {e}", {}


def _extract_image_bytes(data):
    """从 OpenAI 兼容响应提取图片二进制（b64_json 或 url）"""
    try:
        item = (data.get("data") or [{}])[0]
    except Exception:
        return None
    if item.get("b64_json"):
        try:
            return base64.b64decode(item["b64_json"])
        except Exception:
            return None
    url = item.get("url") or item.get("result_url")
    if url:
        try:
            with urllib.request.urlopen(url, timeout=60) as ir:
                return ir.read()
        except Exception:
            return None
    return None


# ============================================================
# 生视频调用（★ 2026-08-23 集成 888 中转平台 海螺 H3 参考生）
# ============================================================
# 视频生成与图像生成在 888 平台共用 /v1/media/generate 端点（不同 model + 不同 params）；
#   POST 建任务 → 异步 → GET /v1/media/status 轮询到 is_final=true → 下载 result_url
# 默认模型：海螺 H3 参考生（hailuo-h3-cankaosheng），上传 1~9 张参考图生成 2K 有声视频
DEFAULT_VIDEO_MODEL = "hailuo-h3-cankaosheng"
# ★ 2026-08-24 视频模型清单（888 平台）：
#   hailuo-h3-cankaosheng【参考生】= 现有模型，params 用 images 字段，duration 整数
#   hailuo-h3-quannengcankao【全能参考】= 全能参考，params 用 image_url/video_url/audio_url 三组，duration 字符串
VIDEO_MODEL_PRESETS = (
    {"model": "hailuo-h3-cankaosheng",     "label": "海螺 H3 参考生",   "ref_field": "images",     "video_field": None,         "audio_field": None,         "duration_str": False},
    {"model": "hailuo-h3-quannengcankao",  "label": "海螺 H3 全能参考", "ref_field": "image_url",  "video_field": "video_url",  "audio_field": "audio_url",  "duration_str": True},
)
VIDEO_MODEL_IDS = tuple(p["model"] for p in VIDEO_MODEL_PRESETS)
# 时长合法值（4~15 整数）
VIDEO_DURATIONS = (4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15)
# 宽高比合法值
VIDEO_ASPECT_RATIOS = ("adaptive", "16:9", "9:16", "1:1", "4:3", "3:4", "21:9")
# 分辨率合法值
VIDEO_RESOLUTIONS = ("768P", "1080P", "2K", "4K")


def generate_video(channel, model, prompt, image_b64s, image_datauris,
                   duration, aspect_ratio, resolution,
                   video_urls=None, audio_urls=None):
    """调视频生成 API 拿视频字节（mp4）。当前仅支持 up_lk888（888 中转平台）。
    - 共用 /v1/media/generate 端点：模型分支
        hailuo-h3-cankaosheng【参考生】params={aspect_ratio, duration(整数), resolution, images}
        hailuo-h3-quannengcankao【全能参考】params={aspect_ratio, duration(字符串), resolution,
                                              image_url, video_url, audio_url}
    - 异步任务式：建任务（POST /v1/media/generate）→ 轮询 status（GET /v1/media/status?task_id=）→ is_final=true
      后下载 result_url 的 mp4 字节
    - duration 必传（4~15 整数），aspect_ratio/resolution 选传（用合法值或默认）
    - image_b64s / image_datauris 任一非空即可（优先 data URI，888 平台要求）
    - video_urls / audio_urls 仅 quannengcankao 用（可选；cankaosheng 忽略）
    返回 (video_bytes|None, err|None, meta|dict)：
      meta = {"task_id", "result_url", "duration", "aspect_ratio", "resolution"}
    """
    api_format = channel.get("apiFormat") or DEFAULT_PROTOCOL
    endpoint = endpoint_with_protocol(channel.get("baseUrl"), api_format)
    api_key = channel.get("apiKey") or ""
    if not endpoint:
        return None, "渠道 Base URL 为空", {}
    if not api_key:
        return None, "渠道未配置 API Key", {}
    # 默认 model：海螺 H3 参考生
    if not model:
        model = DEFAULT_VIDEO_MODEL
    if model not in VIDEO_MODEL_IDS:
        log(f"⚠️ 未知视频模型 {model}，回退到 {DEFAULT_VIDEO_MODEL}")
        model = DEFAULT_VIDEO_MODEL
    preset = next(p for p in VIDEO_MODEL_PRESETS if p["model"] == model)
    # 参数规范化
    try:
        d = int(duration)
    except Exception:
        d = 6
    if d not in VIDEO_DURATIONS:
        d = min(VIDEO_DURATIONS, key=lambda x: abs(x - d))
    ar = aspect_ratio if aspect_ratio in VIDEO_ASPECT_RATIOS else "adaptive"
    rs = resolution if resolution in VIDEO_RESOLUTIONS else "768P"
    # 参考图：只取前 9 张（API 上限）；空列表不传 images 字段
    images_norm = []
    for s in (image_datauris or []):
        s = str(s).strip()
        if not s:
            continue
        images_norm.append(s)
        if len(images_norm) >= 9:
            break
    # 协议分支：minimax_h3（MiniMax 官方 H3）优先；up_lk888 为 888 中转回退
    if api_format == "minimax_h3":
        return _generate_video_minimax_h3(channel, prompt, images_norm, d, ar, rs,
                                          video_urls=video_urls, audio_urls=audio_urls)
    if api_format != "up_lk888":
        return None, f"当前协议 {api_format} 暂不支持视频生成（已集成：minimax_h3 / up_lk888）", {}

    params = {
        "aspect_ratio": ar,
        "duration": (str(d) if preset["duration_str"] else d),
        "resolution": rs,
    }
    # 参考图：cankaosheng → params.images，quannengcankao → params.image_url
    if images_norm:
        params[preset["ref_field"]] = images_norm
    # 仅 quannengcankao 才支持 video_url / audio_url（cankaosheng 忽略）
    if preset["video_field"]:
        v_urls = [str(s).strip() for s in (video_urls or []) if str(s).strip()]
        if v_urls:
            params[preset["video_field"]] = v_urls[:3]   # 文档：最多 3 个
    if preset["audio_field"]:
        a_urls = [str(s).strip() for s in (audio_urls or []) if str(s).strip()]
        if a_urls:
            params[preset["audio_field"]] = a_urls[:3]   # 文档：最多 3 段

    payload = {
        "model": model,
        "prompt": prompt,
        "params": params,
    }
    body = json.dumps(payload).encode("utf-8")
    try:
        r = urllib.request.Request(endpoint + "/media/generate", data=body,
            headers={"Authorization": f"Bearer {api_key}",
                     "Content-Type": "application/json"},
            method="POST")
        with urllib.request.urlopen(r, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")[:400]
        return None, f"create video task failed HTTP {e.code}: {detail}", {}
    except Exception as e:
        return None, f"create video task failed: {e}", {}
    task_id = (data.get("data") or {}).get("task_id") or data.get("task_id")
    if not task_id:
        log(f"❌ 生视频建任务失败(无task_id): model={model} resp={json.dumps(data, ensure_ascii=False)[:200]}")
        return None, f"no task_id: {json.dumps(data, ensure_ascii=False)[:300]}", {}
    log(f"🎬 生视频建任务 ok: model={model} task_id={task_id} duration={d}s ratio={ar} resolution={rs} refs={len(images_norm)}")
    # 视频比图像慢：5~60 分钟常见（按官方建议 5~10s 轮询）；超时 1800s = 30 分钟（★ 2026-08-23 由 25→30 分钟）
    task_start = time.time()
    deadline = task_start + 1800
    last_status_err = "none"
    while time.time() < deadline:
        time.sleep(8)
        try:
            pr = urllib.request.Request(endpoint + f"/media/status?task_id={task_id}",
                headers={"Authorization": f"Bearer {api_key}"}, method="GET")
            with urllib.request.urlopen(pr, timeout=30) as presp:
                pdata = json.loads(presp.read().decode("utf-8"))
            pdat = pdata.get("data") or pdata or {}
            is_final = bool(pdat.get("is_final"))
            state = pdat.get("state", "")
            result_url = pdat.get("result_url")
            err_msg = pdat.get("error") or pdat.get("error_message")
            progress = pdat.get("progress", "")
            if is_final:
                if state == "success" and result_url:
                    # 视频文件较大，给 _download_result 更长超时（★ 2026-08-23 由 3 分钟→5 分钟）
                    video_bytes, dl_err = _download_result(result_url, timeout=300)
                    if video_bytes is None:
                        log(f"❌ 生视频结果下载失败: task_id={task_id} {dl_err}")
                        return None, f"下载视频失败 task_id={task_id}: {dl_err}", {"task_id": task_id, "result_url": result_url}
                    log(f"✅ 生视频完成: task_id={task_id} state=success 耗时={time.time()-task_start:.0f}s 视频={len(video_bytes)}B")
                    return video_bytes, None, {"task_id": task_id, "result_url": result_url,
                                                "duration": d, "aspect_ratio": ar, "resolution": rs}
                if state == "failed":
                    log(f"❌ 生视频任务失败: task_id={task_id} err={err_msg or pdat}")
                    return None, f"video task failed task_id={task_id}: {err_msg or pdat}", {"task_id": task_id}
                # 终态但 state 异常
                log(f"❌ 生视频终态异常: task_id={task_id} state={state!r} resp={json.dumps(pdat, ensure_ascii=False)[:200]}")
                return None, f"video task ended (is_final=true) but state={state!r}: {pdat}", {"task_id": task_id}
            # 未终态：日志进度（节流）
            elapsed = int(time.time() - task_start)
            if elapsed % 30 == 0:
                log(f"⏳ 生视频进行中: task_id={task_id} elapsed={elapsed}s state={state} progress={progress}")
        except Exception as e:
            last_status_err = str(e)
    log(f"❌ 生视频轮询超时(1500s): task_id={task_id} last_err={last_status_err or 'none'}")
    return None, f"video task timeout task_id={task_id} (1500s). last err: {last_status_err or 'none'}", {"task_id": task_id}


def _generate_video_minimax_h3(channel, prompt, image_datauris, duration, aspect_ratio, resolution,
                               video_urls=None, audio_urls=None):
    """MiniMax H3 官方 API（多模态参考生视频 r2va）。apiFormat = minimax_h3。
    - 建任务：POST {base}/api/minimax/v2/video_generation
      body = {model:"MiniMax-H3", content:[{type:"text",text}, {type:"image_url",image_url:{url},role:"reference_image"}...,
              {type:"video_url",url,role:"reference_video"}..., {type:"audio_url",url,role:"reference_audio"}...],
              resolution, duration:int, ratio}
      响应：{"task_id": "..."}（顶层）
    - 轮询：GET {base}/api/minimax/v2/query/video_generation/{task_id}
      响应：{"task": {"status": "queued|running|succeeded|failed", "content": {"url": mp4}(succeeded), ...}}
      无独立结果接口：succeeded 后从 task.content.url 下载 mp4
    - 图片：传 data URI（本地资产无公网 URL）；若上游报格式错误需按官方文档调整编码方式
    返回 (video_bytes|None, err|None, meta|dict)"""
    base = (channel.get("baseUrl") or "").strip().rstrip("/")
    api_key = channel.get("apiKey") or ""
    if not base:
        return None, "渠道 Base URL 为空", {}
    if not api_key:
        return None, "渠道未配置 API Key", {}
    # ★ 2026-09-03 修复 SSL: UNEXPECTED_EOF_WHILE_READING——api.metaso.cn 的 WAF 会掐断无 User-Agent 的
    #   urllib 请求（888 平台 _download_result 同款教训），所有请求必须带浏览器 UA + Accept
    # ★ 2026-09-03 host 归一化：metaso 正确 API base = https://metaso.cn/api/minimax
    #   （api.metaso.cn 未开放 443，曾误用）；MiniMax 官方 host = https://api.minimaxi.com（/v2 原样）；自建端点原样
    low_b = base.lower()
    if "api.metaso.cn" in low_b:
        base = "https://metaso.cn/api/minimax"
    elif "metaso.cn" in low_b and not base.rstrip("/").lower().endswith("/api/minimax"):
        base = base.rstrip("/") + "/api/minimax"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json",
               "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
               "Accept": "application/json"}
    # ① 建任务（SSL 握手被掐偶发：网络类失败自动重试 1 次）
    content = [{"type": "text", "text": prompt or ""}]
    for du in (image_datauris or [])[:9]:
        du = str(du).strip()
        if du:
            content.append({"type": "image_url", "image_url": {"url": du}, "role": "reference_image"})
    for vu in [str(s).strip() for s in (video_urls or []) if str(s).strip()][:3]:
        content.append({"type": "video_url", "url": vu, "role": "reference_video"})
    for au in [str(s).strip() for s in (audio_urls or []) if str(s).strip()][:3]:
        content.append({"type": "audio_url", "url": au, "role": "reference_audio"})
    body = json.dumps({
        "model": "MiniMax-H3",
        "content": content,
        "resolution": resolution if resolution in ("768P", "2K") else "768P",
        "duration": int(duration),
        "ratio": aspect_ratio if aspect_ratio in VIDEO_ASPECT_RATIOS else "adaptive",
    }).encode("utf-8")
    data = None
    last_err = None
    for attempt in (1, 2):
        try:
            r = urllib.request.Request(base + "/v2/video_generation", data=body,
                                       headers=headers, method="POST")
            with urllib.request.urlopen(r, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            break
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")[:400]
            return None, f"create MiniMax H3 task failed HTTP {e.code}: {detail}", {}
        except Exception as e:
            last_err = e
            log(f"⚠️ MiniMax H3 建任务第 {attempt} 次网络失败（{e}），{'2s 后重试' if attempt == 1 else '放弃'}")
            if attempt == 1:
                time.sleep(2)
    if data is None:
        return None, f"create MiniMax H3 task failed: {last_err}", {}
    task_id = data.get("task_id") or (data.get("data") or {}).get("task_id")
    if not task_id:
        log(f"❌ MiniMax H3 建任务失败(无task_id): resp={json.dumps(data, ensure_ascii=False)[:200]}")
        return None, f"no task_id: {json.dumps(data, ensure_ascii=False)[:300]}", {}
    log(f"🎬 MiniMax H3 建任务 ok: task_id={task_id} duration={int(duration)}s ratio={aspect_ratio} resolution={resolution} refs={len(image_datauris or [])}")
    # ② 轮询（视频 5~25 分钟常见；超时 1800s；每 8s 一次）
    task_start = time.time()
    deadline = task_start + 1800
    last_status_err = "none"
    qurl = f"{base}/v2/query/video_generation/{task_id}"
    while time.time() < deadline:
        time.sleep(8)
        try:
            pr = urllib.request.Request(qurl, headers=headers, method="GET")
            with urllib.request.urlopen(pr, timeout=30) as presp:
                pdata = json.loads(presp.read().decode("utf-8"))
            t = pdata.get("task") or pdata or {}
            status = str(t.get("status") or "").lower()
            if status == "succeeded":
                url = ((t.get("content") or {}).get("url")) or t.get("url")
                if not url:
                    log(f"❌ MiniMax H3 succeeded 但无 content.url: {json.dumps(t, ensure_ascii=False)[:200]}")
                    return None, f"MiniMax H3 task succeeded but no content.url: {json.dumps(t)[:300]}", {"task_id": task_id}
                video_bytes, dl_err = _download_result(url, timeout=300)
                if video_bytes is None:
                    log(f"❌ MiniMax H3 结果下载失败: task_id={task_id} {dl_err}")
                    return None, f"下载视频失败 task_id={task_id}: {dl_err}", {"task_id": task_id, "result_url": url}
                log(f"✅ MiniMax H3 完成: task_id={task_id} 耗时={time.time() - task_start:.0f}s 视频={len(video_bytes)}B")
                return video_bytes, None, {"task_id": task_id, "result_url": url,
                                           "duration": int(duration), "aspect_ratio": aspect_ratio, "resolution": resolution}
            if status in ("failed", "fail", "error", "cancelled", "canceled"):
                msg = t.get("error") or t.get("message") or json.dumps(t, ensure_ascii=False)[:200]
                log(f"❌ MiniMax H3 任务失败: task_id={task_id} status={status} err={msg}")
                return None, f"MiniMax H3 task failed task_id={task_id} status={status}: {msg}", {"task_id": task_id}
            # 未终态：节流日志
            elapsed = int(time.time() - task_start)
            if elapsed % 30 == 0:
                log(f"⏳ MiniMax H3 进行中: task_id={task_id} elapsed={elapsed}s status={status}")
        except Exception as e:
            last_status_err = str(e)
    log(f"❌ MiniMax H3 轮询超时(1800s): task_id={task_id} last_err={last_status_err or 'none'}")
    return None, f"MiniMax H3 task timeout task_id={task_id} (1800s). last err: {last_status_err or 'none'}", {"task_id": task_id}




# ============================================================
# Agent 对话调用（OpenAI Chat Completions 透传）
# ============================================================

def agent_chat_completion(channel, model, messages, system_prompt, stream=False,
                          temperature=None, max_tokens=None, default_model=None):
    """调 Agent LLM（OpenAI 兼容 /chat/completions）。
    入参 messages 会被注入 system（优先级：调用方传入 system_prompt > 全局 system_prompt > 已有 system 消息）。
    返回 (ok, resp)：
      非流式成功: {"ok": True, "stream": False, "content_type": "...", "body": bytes}
      流式成功:   {"ok": True, "stream": True, "upstream": <urlopen 对象>}
      失败:       {"ok": False, "status": int, "error": str}"""
    base = (channel.get("baseUrl") or "").rstrip("/")
    api_key = channel.get("apiKey") or ""
    if not api_key:
        return False, {"status": 501, "error": "Agent 未配置 API 渠道：请在 ⚙ 设置 → Agent 标签页中添加渠道"}
    if not base:
        return False, {"status": 400, "error": "Agent 渠道 Base URL 为空"}
    model = (str(model or "")).strip() or (default_model or DEFAULT_AGENT_MODEL)
    messages = messages or []
    # 注入 system：优先级 请求 system > 全局 system_prompt > 已有 system 消息
    sys_p = system_prompt
    if sys_p and (not messages or messages[0].get("role") != "system"):
        messages = [{"role": "system", "content": str(sys_p)}] + messages
    payload = {"model": model, "messages": messages, "stream": bool(stream)}
    if temperature is not None:
        try:
            payload["temperature"] = float(temperature)
        except Exception:
            pass
    if max_tokens is not None:
        try:
            payload["max_tokens"] = int(max_tokens)
        except Exception:
            pass
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    endpoint = endpoint_with_protocol(base, "openai")  # 补全到 /v1
    url = f"{endpoint}/chat/completions"
    upstream_req = urllib.request.Request(url, data=body, headers={
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json" if not stream else "text/event-stream",
    }, method="POST")

    if not stream:
        try:
            with urllib.request.urlopen(upstream_req, timeout=300) as resp:
                data = resp.read()
            return True, {"ok": True, "stream": False, "content_type": "application/json; charset=utf-8", "body": data}
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")[:600]
            return False, {"status": 502, "error": f"上游 HTTP {e.code}: {detail}"}
        except Exception as e:
            return False, {"status": 502, "error": f"请求失败: {e}"}

    # 流式：SSE 透传（返回上游连接对象，由调用方逐行转发）
    try:
        upstream = urllib.request.urlopen(upstream_req, timeout=300)
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")[:600]
        return False, {"status": 502, "error": f"上游 HTTP {e.code}: {detail}"}
    except Exception as e:
        return False, {"status": 502, "error": f"连接失败: {e}"}
    return True, {"ok": True, "stream": True, "upstream": upstream}


# ============================================================
# 测试 / 拉取模型（设置页用）
# ============================================================

def test_img_channel(channel):
    """测试生图渠道连通性：up_lk888 → /media/generate 极小任务（拿 task_id 即通）；
    openai/ark → GET /models；gemini → GET v1beta/models。
    返回 (ok, payload_dict)：payload 含 ok/models/count/note 或 error。"""
    api_format = channel.get("apiFormat") or DEFAULT_PROTOCOL
    endpoint = endpoint_with_protocol(channel.get("baseUrl"), api_format)
    api_key = channel.get("apiKey") or ""
    if not api_key:
        return False, {"error": "未提供 API Key", "status": 400}
    if not endpoint:
        return False, {"error": "未填写 Base URL", "status": 400}
    try:
        if api_format == "minimax_h3":
            # MiniMax H3 无 /models：探测假任务 id——200/400/404 = host 可达 + 鉴权通过；401/403 = Key 无效
            base_raw = (channel.get("baseUrl") or "").strip().rstrip("/")
            low_raw = base_raw.lower()
            if "api.metaso.cn" in low_raw:
                base_raw = "https://metaso.cn/api/minimax"
            elif "metaso.cn" in low_raw and not base_raw.lower().endswith("/api/minimax"):
                base_raw = base_raw.rstrip("/") + "/api/minimax"
            url = f"{base_raw}/v2/query/video_generation/connection-test-probe"
            r = urllib.request.Request(url, headers={"Authorization": f"Bearer {api_key}",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
                "Accept": "application/json"}, method="GET")
            try:
                with urllib.request.urlopen(r, timeout=30) as resp:
                    resp.read()
                return True, {"models": ["MiniMax-H3"], "count": 1, "note": "✅ MiniMax H3 渠道连通（鉴权通过）"}
            except urllib.error.HTTPError as e2:
                if e2.code in (401, 403):
                    return False, {"error": f"❌ MiniMax H3 鉴权失败 {e2.code}：Key 无效。详情：{e2.read().decode('utf-8', errors='replace')[:200]}", "status": 401}
                return True, {"models": ["MiniMax-H3"], "count": 1, "note": f"✅ MiniMax H3 渠道连通（探测响应 HTTP {e2.code}）"}
        if api_format == "gemini":
            url = f"{endpoint}/models"
            r = urllib.request.Request(url, headers={"x-goog-api-key": api_key}, method="GET")
            with urllib.request.urlopen(r, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            models = [m.get("name", "").replace("models/", "") for m in (data.get("models") or []) if m.get("name")]
            return True, {"models": models, "count": len(models), "note": f"✅ 连接成功，Gemini 平台有 {len(models)} 个模型"}
        elif api_format == "ark":
            url = f"{endpoint}/models"
            r = urllib.request.Request(url, headers={"Authorization": f"Bearer {api_key}"}, method="GET")
            with urllib.request.urlopen(r, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            models = [m.get("id") for m in (data.get("data") or []) if m.get("id")]
            return True, {"models": models, "count": len(models), "note": f"✅ 连接成功，方舟平台有 {len(models)} 个模型"}
        else:  # openai / up_lk888（两者 /models 响应均为 {"data":[{"id":...}]}）
            url = f"{endpoint}/models"
            r = urllib.request.Request(url, headers={"Authorization": f"Bearer {api_key}"}, method="GET")
            with urllib.request.urlopen(r, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            models = [m.get("id") for m in (data.get("data") or []) if m.get("id")]
            return True, {"models": models, "count": len(models), "note": f"✅ 连接成功，平台有 {len(models)} 个模型"}
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")[:400]
        if e.code in (401, 403):
            return False, {"error": f"❌ 鉴权失败 {e.code}：Key 无效或无权访问。详情：{detail}", "status": 401}
        return False, {"error": f"HTTP {e.code}: {detail}", "status": 502}
    except Exception as e:
        return False, {"error": f"连接失败: {e}", "status": 502}


def fetch_models(base_url, api_key, api_format):
    """拉取平台模型列表（渠道编辑器用）。openai / up_lk888 走 /v1/models，gemini 走 /v1beta/models。
    返回 (ok, payload_dict)：payload 含 models/count 或 error。"""
    if not base_url or not api_key:
        return False, {"error": "请先填写 Base URL 和 API Key"}
    endpoint = endpoint_with_protocol(base_url, normalize_protocol(api_format))
    try:
        if api_format == "minimax_h3":
            # MiniMax H3 无 /models 端点：返回固定模型
            return True, {"models": ["MiniMax-H3"], "count": 1}
        if api_format == "gemini":
            r = urllib.request.Request(f"{endpoint}/models", headers={"x-goog-api-key": api_key}, method="GET")
            with urllib.request.urlopen(r, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            models = sorted(m.get("name", "").replace("models/", "") for m in (data.get("models") or []) if m.get("name"))
        else:
            r = urllib.request.Request(f"{endpoint}/models", headers={"Authorization": f"Bearer {api_key}"}, method="GET")
            with urllib.request.urlopen(r, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            models = sorted(m.get("id") for m in (data.get("data") or []) if m.get("id"))
        return True, {"models": models, "count": len(models)}
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")[:300]
        return False, {"error": f"拉取失败 HTTP {e.code}: {detail}"}
    except Exception as e:
        return False, {"error": f"拉取失败: {e}"}


def test_agent_channel(channel, model=None, default_model=None):
    """测试 Agent 连通：用最小请求试一次 chat 补全（不强制 stream）。
    返回 (ok, payload_dict)：payload 含 echo/note 或 error。"""
    base = (channel.get("baseUrl") or "").rstrip("/")
    api_key = channel.get("apiKey") or ""
    if not api_key:
        return False, {"error": "Agent 未配置渠道：请先在 ⚙ 设置 → Agent 中配置 API Key", "status": 400}
    if not base:
        return False, {"error": "未填写 Base URL", "status": 400}
    endpoint = endpoint_with_protocol(base, "openai")  # 补全到 /v1
    url = f"{endpoint}/chat/completions"
    body = json.dumps({
        "model": model or default_model or DEFAULT_AGENT_MODEL,
        "messages": [{"role": "user", "content": "ping"}],
        "stream": False,
        "max_tokens": 8,
    }).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
        content = (((data.get("choices") or [{}])[0]).get("message") or {}).get("content", "")
        return True, {"echo": content[:80], "note": f"✅ 连通成功，回复前缀：{content[:60]!r}"}
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")[:400]
        if e.code in (401, 403):
            return False, {"error": f"❌ 鉴权失败 {e.code}：Key 无效或无权访问。详情：{detail}", "status": 401}
        return False, {"error": f"HTTP {e.code}: {detail}", "status": 502}
    except Exception as e:
        return False, {"error": f"连接失败: {e}", "status": 502}
