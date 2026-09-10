# -*- coding: utf-8 -*-
"""
{{项目名}} · 本地服务（上传 + 静态托管）
用法:
  python server.py            # 默认 127.0.0.1:8320，浏览器打开 http://127.0.0.1:8320
  python server.py 9000       # 指定端口
说明:
  - 静态托管 project/ 目录（index.html / data.js / assets/）
  - POST /upload 接收图片写入 assets/ 指定子目录（相对路径安全校验，防穿越）；
    若同名文件已存在，先把旧文件归档到 <dir>/history/<时间戳>-<文件名>，并把历史路径写入 data.js 对应对象的 history[]
  - POST /set-current 把某张历史图设为当前（复制到主路径，原当前图归档进 history[]）
  - 上传/回滚后自动把对应 data.js 字段 *_ready 置 true（按约定路径映射）
"""
# 抑制启动噪声：第三方库(urllib3/werkzeug)的 DEBUG/INFO/警告在 Windows CMD GBK 终端会乱码淹没业务 log
import warnings as _warnings
_warnings.filterwarnings("ignore")
import logging as _logging
for _n in ("urllib3", "urllib3.connectionpool", "urllib3.poolmanager", "urllib3.util.retry",
           "werkzeug", "http.server", "asyncio"):
    _logging.getLogger(_n).setLevel(_logging.WARNING)
import os, re, json, sys, mimetypes, shutil, time, base64
import threading as _threading
from http.server import HTTPServer, SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
from datetime import datetime
import api_slot as slot

ROOT = os.path.dirname(os.path.abspath(__file__))
# 项目根目录（server.py 位于 <项目根>/project/server.py；outputs/、docs/、pipeline-state.json 都在项目根）
PROJECT_ROOT = os.path.dirname(ROOT)
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8320

# ---------- SQLite 快照库（保原样存储，零转换） ----------
import sqlite3 as _sqlite3
DB_PATH = os.path.join(ROOT, "xiaji.db")   # project/xiaji.db（与 server.py 同级）

def db_conn():
    """获取 SQLite 连接（每次新建，用完关闭，避免线程锁）"""
    conn = _sqlite3.connect(DB_PATH)
    conn.execute("CREATE TABLE IF NOT EXISTS snapshots (module TEXT PRIMARY KEY, data TEXT NOT NULL, updated_at TEXT NOT NULL)")
    conn.commit()
    return conn

def db_upsert(module, data_obj):
    """把一个模块数据以 JSON 原样写入 snapshots（保原样：json.dumps 后整体存字符串）"""
    try:
        conn = db_conn()
        conn.execute("INSERT OR REPLACE INTO snapshots(module, data, updated_at) VALUES (?,?,?)",
                     (module, json.dumps(data_obj, ensure_ascii=False), datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit(); conn.close()
        return True
    except Exception:
        return False

def db_read_all():
    """读取全部模块快照 → dict（module → 已解析对象）"""
    try:
        conn = db_conn()
        rows = conn.execute("SELECT module, data FROM snapshots").fetchall()
        conn.close()
        return {m: json.loads(d) for m, d in rows}
    except Exception:
        return {}

# ★ 2026-08-23 全局 DB 写锁：保护「读-改-写」临界区（如视频落库 _mark_video_ready_in_db）。
# 否则多个并发视频任务（视频独立并发=3）同时读 DB 旧值 → 各自改 → 各自写回 → 互相覆盖，
# 最终只剩最后一个写回的任务生效（前 N-1 个视频资产位丢失）。加锁后读改写串行化，杜绝丢失更新。
_DB_WRITE_LOCK = _threading.Lock()

def db_migrate_from_datajs():
    """从 project/data.js 读取 window.PROJECT，按顶层 key 拆模块原样写入 SQLite。
    返回 (迁移模块数, 错误列表)。"""
    datajs = os.path.join(ROOT, "data.js")
    if not os.path.exists(datajs):
        return 0, ["data.js 不存在"]
    try:
        txt = open(datajs, encoding="utf-8").read()
        m = re.search(r"window\.PROJECT\s*=\s*(\{.*?\})\s*;\s*$", txt, re.DOTALL)
        if not m:
            return 0, ["data.js 中未找到 window.PROJECT"]
        proj = json.loads(m.group(1))
    except Exception as e:
        return 0, [f"data.js 解析失败: {e}"]
    errors = []
    n = 0
    for k, v in proj.items():
        # 模块名 = 顶层 key；值原样 JSON 存储（不拆分、不转换，保证原样性）
        if not db_upsert(k, v):
            errors.append(f"模块 {k} 写入失败")
        else:
            n += 1
    return n, errors

def db_verify_against_datajs():
    """校验 SQLite 快照与 data.js 是否完全一致（逐模块 JSON 文本对比 + 结构深度对比）。
    返回 {ok, modules, diffs}。"""
    datajs = os.path.join(ROOT, "data.js")
    if not os.path.exists(datajs):
        return {"ok": False, "error": "data.js 不存在"}
    try:
        txt = open(datajs, encoding="utf-8").read()
        m = re.search(r"window\.PROJECT\s*=\s*(\{.*?\})\s*;\s*$", txt, re.DOTALL)
        proj = json.loads(m.group(1))
    except Exception as e:
        return {"ok": False, "error": f"data.js 解析失败: {e}"}
    dbd = db_read_all()
    modules = list(proj.keys())
    diffs = []
    for k in modules:
        # 文本级对比（json.dumps 稳定排序后比对，防键序差异误报）
        s1 = json.dumps(proj[k], ensure_ascii=False, sort_keys=True)
        if k not in dbd:
            diffs.append({"module": k, "issue": "SQLite 缺失该模块"})
            continue
        s2 = json.dumps(dbd[k], ensure_ascii=False, sort_keys=True)
        if s1 != s2:
            diffs.append({"module": k, "issue": "内容不一致", "len_datajs": len(s1), "len_db": len(s2)})
    return {"ok": len(diffs) == 0, "modules": modules, "db_modules": list(dbd.keys()), "diffs": diffs}

def db_sync_xiage():
    """从 outputs/styles/ 重新组装 xiage 模块并写入 SQLite（虾格保存/确认后调用，保证前端刷新可见）"""
    try:
        sdir = os.path.join(PROJECT_ROOT, "outputs", "styles")
        if not os.path.isdir(sdir):
            return False
        styles = []
        cur = ""
        for f in sorted(os.listdir(sdir)):
            if not f.endswith(".json"):
                continue
            try:
                s = json.load(open(os.path.join(sdir, f), encoding="utf-8"))
            except Exception:
                continue
            sid = s.get("style_id", "")
            styles.append({
                "style_id": sid,
                "style_label": s.get("style_label", ""),
                "style_tag": s.get("style_tag", ""),
                "style_instructions": s.get("style_instructions", ""),
                "avoid_instructions": s.get("avoid_instructions", ""),
                "recommended_for": s.get("recommended_for", ""),
                "is_preset": bool(s.get("is_preset", False)),
                "confirmed_by_user": bool(s.get("confirmed_by_user", False)),
                "image": f"assets/styles/{sid}.png",
                "image_ready": os.path.exists(os.path.join(ROOT, "assets", "styles", f"{sid}.png")) or os.path.exists(os.path.join(ROOT, "assets", "styles", f"{s.get('style_tag','')}.png"))
            })
        # 当前风格：pipeline-state 的 handoff
        try:
            ps = json.load(open(os.path.join(PROJECT_ROOT, "pipeline-state.json"), encoding="utf-8"))
            ho = (ps.get("modules", {}).get("xiage-styles", {}) or {}).get("handoff", "")
            if ho and str(ho).endswith(".json"):
                cur = os.path.splitext(os.path.basename(ho))[0]
        except Exception:
            pass
        # 全剧定风格图：扫 assets/styles/style_keyframe*.png 取最新（重生成带时间戳名也能命中）
        kf = ""
        try:
            _kd = os.path.join(ROOT, "assets", "styles")
            if os.path.isdir(_kd):
                _cands = [f for f in os.listdir(_kd) if f.startswith("style_keyframe") and f.lower().endswith(".png")]
                if _cands:
                    _cands.sort(key=lambda f: os.path.getmtime(os.path.join(_kd, f)))
                    kf = f"assets/styles/{_cands[-1]}"
        except Exception:
            kf = ""
        return db_upsert("xiage", {"styles": styles, "current": cur, "keyframe": kf, "keyframe_ready": bool(kf)})
    except Exception:
        return False


# ===== 日志（写入 server.log + 打印到 CMD 窗口）=====
LOG_PATH = os.path.join(ROOT, "server.log")

# ================= 各类别生图默认尺寸（⚙ 设置可改，前端生图弹窗自动选中） =================
DEFAULT_SIZE_MAP = {
    "character":    "960x1280",   # 角色主图 3:4 竖版
    "identity":     "1088x1920",  # 身份图/四视图卡 9:16 竖版（★ 2026-08-21 用户拍板：四视图卡上下两段式版式）
    "scene":        "1536x768",   # 场景 2:1 横版宽屏
    "key_scene":    "1536x768",   # 关键场景画面素材 2:1 横版（★ 2026-08-22 批量生图支持）
    "prop":         "1280x960",   # 道具 4:3 横版
    "sketch_frame": "1536x768",   # 草图·首帧 2:1 横版宽屏
    "video":        "16:9",       # ★ 2026-08-23 视频默认比例（aspect_ratio，非像素尺寸）
}

# ================= 生图任务队列（容量5，线程安全，不持久化） =================
import uuid as _uuid

class GenTaskQueue:
    """生图/生视频统一任务队列（★ 2026-08-19 改造为调度器模式；2026-08-23 视频独立并发）。
    任务状态机：queued(排队) → running(执行中) → success(成功) / failed(失败)
    - ★ 2026-08-20 用户拍板：去掉批量限制，普通/批量统一——等待+执行 < MAX_QUEUED 均可入队
    - ★ 2026-08-23：视频与生图共用排队上限 60，但视频有独立并发上限 VIDEO_MAX_CONCURRENT=3
      （生图仍 MAX_CONCURRENT=5），避免 60 个视频把整条队列堵 10 小时、挡住生图
    - 调度器 take_next() 按 category 各自并发上限取任务，完成一个自动取下一个"""

    MAX_CONCURRENT = 5      # 同时最多跑 5 个生图任务（避免中转 API 报错）
    VIDEO_MAX_CONCURRENT = 3  # ★ 2026-08-23 视频独立并发上限（不挤占生图并发位）
    MAX_QUEUED = 60         # ★ 排队上限（2026-08-20 起普通/批量统一 60，视频+生图共享）
    DONE_KEEP = 60          # ★ 2026-08-23 完成区保留 60 条（原 20，避免 60 个视频跑完早期查不到）
    VIDEO_MAX_RETRY = 2     # ★ 2026-08-23 视频超时/失败后最多自动重试 2 次（总计 3 次尝试）

    # 每类并发上限映射（take_next 用）
    _CONC_BY_CAT = {"video": VIDEO_MAX_CONCURRENT, None: MAX_CONCURRENT}

    def __init__(self):
        self._lock = _threading.Lock()
        self._tasks = {}     # task_id → task dict
        self._order = []     # 插入顺序（用于裁剪完成区）

    @classmethod
    def _conc_limit(cls, category):
        """按 category 取并发上限：video→3，其余→5"""
        if category == "video":
            return cls.VIDEO_MAX_CONCURRENT
        return cls.MAX_CONCURRENT

    # ---- 任务记录 ----
    def add_task(self, category, name, model, size, prompt, images, channel_id, batch=False, ep=1,
                 video_meta=None, retry=0):
        """尝试入队。队列满返回 (None, queue_full)；成功返回 (task_id, None)。
        ★ 2026-08-20 起普通/批量统一：等待+执行 < MAX_QUEUED 均可入队（batch 参数仅保留兼容）。
        ★ 2026-08-23：video_meta 直接随任务存储（重试时复用，不必再单独挂）；retry 记录重试次数。"""
        with self._lock:
            total = sum(1 for t in self._tasks.values() if t["status"] in ("queued", "running"))
            limit = self.MAX_QUEUED
            if total >= limit:
                return None, True
            task_id = _uuid.uuid4().hex[:12]
            self._tasks[task_id] = {
                "task_id": task_id,
                "category": category, "name": name, "model": model, "size": size,
                "ep": int(ep or 1),
                "ratio": slot.SIZE_TO_RATIO.get(size, "1:1"),
                "images": list(images or []),   # ★ 保存原始垫图列表（调度器执行时重建，批量无垫图不受影响）
                "prompt": prompt,   # ★ 2026-08-20 修复：必须存完整提示词！之前 prompt[:80] 截断导致生图提示词被截断（列表显示截断改在 snapshot 做）
                "channel_id": channel_id,
                "status": "queued", "created_at": time.time(),
                "started_at": None, "finished_at": None, "duration": None,
                "result": None, "error": None, "hist_path": None,
                "video_meta": dict(video_meta) if video_meta else None,  # ★ 视频专用字段随任务存
                "retry": int(retry or 0),   # ★ 重试计数
            }
            self._order.append(task_id)
            return task_id, None

    def take_next(self):
        """调度器取下一个可执行任务：按 category 各自并发上限判定，running < 该类上限 且有 queued →
        置 running（预占并发位）并返回 (task_id, task)。否则返回 None。"""
        with self._lock:
            # 统计每类正在 running 的数量
            running_by_cat = {}
            for t in self._tasks.values():
                if t["status"] == "running":
                    running_by_cat[t["category"]] = running_by_cat.get(t["category"], 0) + 1
            for tid in self._order:
                t = self._tasks.get(tid)
                if t and t["status"] == "queued":
                    cat = t["category"]
                    limit = self._conc_limit(cat)
                    if running_by_cat.get(cat, 0) >= limit:
                        continue   # 该类并发已满，跳过看下一个
                    t["status"] = "running"
                    t["started_at"] = time.time()
                    return tid, t
            return None

    def requeue(self, task_id, retry=0, error_hint=""):
        """★ 2026-08-23 视频重试：把已失败/超时的任务原地复位为 queued，复用同一 task_id。
        返回 True 表示成功重排；若队列已满（queued+running >= MAX_QUEUED）返回 False。"""
        with self._lock:
            t = self._tasks.get(task_id)
            if not t:
                return False
            # 排队上限保护：仅在仍有空位时允许重排（避免无限撑大）
            total = sum(1 for x in self._tasks.values() if x["status"] in ("queued", "running"))
            if total >= self.MAX_QUEUED:
                return False
            t["status"] = "queued"
            t["retry"] = int(retry or 0)
            t["started_at"] = None
            t["finished_at"] = None
            t["duration"] = None
            t["result"] = None
            t["error"] = None
            t["hist_path"] = None
            # 确保仍在 _order（一般不会丢）；丢则补回
            if task_id not in self._order:
                self._order.append(task_id)
            return True

    def mark_running(self, task_id):
        with self._lock:
            t = self._tasks.get(task_id)
            if t:
                t["status"] = "running"
                t["started_at"] = time.time()

    def mark_done(self, task_id, ok, result=None, error=None, hist_path=None):
        with self._lock:
            t = self._tasks.get(task_id)
            if not t:
                return
            t["status"] = "success" if ok else "failed"
            t["finished_at"] = time.time()
            t["duration"] = round(t["finished_at"] - (t["started_at"] or t["created_at"]), 1)
            t["result"] = result
            t["error"] = str(error)[:200] if error else None
            t["hist_path"] = hist_path
            # 裁剪完成区：保留最近 DONE_KEEP 条（按完成时间倒序）
            done_ids = [tid for tid in self._order if self._tasks[tid]["status"] in ("success", "failed")]
            over = len(done_ids) - self.DONE_KEEP
            if over > 0:
                for tid in done_ids[:over]:
                    del self._tasks[tid]
                    self._order.remove(tid)

    def snapshot(self):
        """线程安全快照：任务中(queued/running) + 完成(success/failed)"""
        with self._lock:
            running = []
            done = []
            for tid in self._order:
                t = dict(self._tasks[tid])
                t["prompt"] = (t.get("prompt") or "")[:80]   # ★ 列表显示截断（不截断存储的执行提示词）
                t["created_at"] = round(t.get("created_at") or 0, 1)
                t["started_at"] = round(t.get("started_at") or 0, 1)
                t["finished_at"] = round(t.get("finished_at") or 0, 1)
                if t["status"] in ("queued", "running"):
                    running.append(t)
                else:
                    done.append(t)
            return running, done

    def stats(self):
        with self._lock:
            running = sum(1 for t in self._tasks.values() if t["status"] in ("queued", "running"))
            running_by_cat = {}
            for t in self._tasks.values():
                if t["status"] in ("queued", "running"):
                    running_by_cat[t["category"]] = running_by_cat.get(t["category"], 0) + 1
            # ★ 2026-08-20：max 返回排队上限 60（前端角标/队列上限显示跟随）；并发数见 max_concurrent
            # ★ 2026-08-23：video_running / video_max 单独暴露视频并发占用
            return {"running": running, "queued": running, "max": self.MAX_QUEUED,
                    "max_concurrent": self.MAX_CONCURRENT,
                    "video_max_concurrent": self.VIDEO_MAX_CONCURRENT,
                    "video_running": running_by_cat.get("video", 0),
                    "image_running": running_by_cat.get(None, 0) + running_by_cat.get("image", 0),
                    "done_total": sum(1 for t in self._tasks.values() if t["status"] in ("success", "failed"))}

GEN_QUEUE = GenTaskQueue()


# ============================================================
# ★ 2026-08-23 生视频任务（并入 GEN_QUEUE，独立并发 3）
# 设计：视频与生图共用 GEN_QUEUE（排队上限 60），但视频有独立并发上限 VIDEO_MAX_CONCURRENT=3：
#   category="video" 的任务由 _dispatch_loop 分派到 _execute_video_task
# 视频任务专用字段（ep/idx/seg_idx/duration/aspect_ratio/resolution/retry）存于 task["video_meta"]
# 超时/失败自动重新入队（最多 VIDEO_MAX_RETRY 次）；前端通过 GET /gen-video-status?task_id= 轮询
# ============================================================
def _video_task_meta(task):
    """从 GEN_QUEUE 任务 dict 取视频专用字段（存于 video_meta）"""
    return (task or {}).get("video_meta") or {}


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


# 允许的图片扩展名
ALLOWED_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif"}

# 路径类别 → 允许的 assets 子目录
CATEGORY_DIRS = {
    "character": "characters",
    "identity": "characters",
    "scene": "scenes",
    "key_scene": "key-scenes",   # ★ 2026-08-21 关键场景素材（画面素材，非资产，独立 Tab）
    "prop": "props",
    "sketch": "epNNN/sketches",
    "frame": "epNNN/frames",
    "firstframe": "epNNN/frames",   # ★ 2026-08-21 新版制作页首帧（与 frame 同目录）
    "tailframe": "epNNN/frames",   # ★ 2026-08-21 尾帧（与首帧同目录）
    "audio": "epNNN/audio",
    "video": "epNNN/videos",
    "style": "styles",          # 虾格：风格预设图（人物近景含环境）
    "storyboard": "epNNN/storyboards",   # ★ 2026-08-21 故事板：整张故事板图（按集）
    "space_map": "epNNN/space-maps",   # ★ 2026-08-31 空间拓扑图（按集单张，故事板页顶部参考位）
    "tingfeng": "tingfeng/epNNN/storyboards",   # ★ 2026-09-01 听风电影故事板（独立目录，与虾镜完全隔离）
    "tf_space_map": "tingfeng/epNNN/space-maps",   # ★ 2026-09-01 听风空间拓扑图（独立目录，与虾镜完全隔离）
}

# ★ 2026-09-04 听风拓扑图按场集合（每场一张）辅助：归一化 + 取/扩容
def _tf_ensure_space_maps(_te):
    """归一化 tingfeng ep 的 space_maps 集合（旧单数字段 space_map_prompt/image 兜底为第 0 项，旧项目数据不丢）"""
    _sms = _te.get("space_maps")
    if isinstance(_sms, list):
        return _sms
    _sms = []
    if _te.get("space_map_image") or _te.get("space_map_prompt"):
        _sms.append({"name": "空间拓扑图", "prompt": _te.get("space_map_prompt", ""), "image": _te.get("space_map_image", ""), "ready": bool(_te.get("space_map_ready"))})
    _te["space_maps"] = _sms
    return _sms

def _tf_space_map_at(_te, _idx):
    """取/扩容第 _idx 场条目（每场一张铁律；条目名用通用占位场序，AI 产出后覆盖为带场景标识的名字）"""
    _sms = _tf_ensure_space_maps(_te)
    while len(_sms) <= _idx:
        _sms.append({"name": "空间拓扑图·场" + str(len(_sms) + 1), "prompt": "", "image": "", "ready": False})
    return _sms[_idx]


def _xj_ensure_space_maps(_xe):
    """归一化虾镜 ep 的 space_maps 集合（★ 2026-09-10 3.5.14；旧单数字段兜底为第 0 项，旧项目数据不丢）"""
    _sms = _xe.get("space_maps")
    if isinstance(_sms, list):
        return _sms
    _sms = []
    if _xe.get("space_map_image") or _xe.get("space_map_prompt"):
        _sms.append({"name": "空间拓扑图", "prompt": _xe.get("space_map_prompt", ""),
                     "image": _xe.get("space_map_image", ""), "ready": bool(_xe.get("space_map_ready"))})
    _xe["space_maps"] = _sms
    return _sms


def _xj_space_map_at(_xe, _idx):
    """取/扩容第 _idx 场条目（每场一张铁律；条目名通用占位场序，AI 产出后覆盖为带场景标识的名字）"""
    _sms = _xj_ensure_space_maps(_xe)
    while len(_sms) <= _idx:
        _sms.append({"name": "空间拓扑图·场" + str(len(_sms) + 1), "prompt": "", "image": "", "ready": False})
    return _sms[_idx]


def _xj_backfill_space_maps(ep_num, idx, rel_path):
    """★ 2026-09-10 3.5.14 闭环：虾镜拓扑图上传后回写文件真源。
       只写 db 的话——space_maps.json（单一真源）与 shots.json 内嵌那份都不动，
       结果 D2 永远红、下次 build-data-js 重建还会被文件覆盖回空。
       best-effort：文件不在就跳过并记日志，绝不让上传本身失败。"""
    try:
        d = os.path.join(PROJECT_ROOT, "outputs", "xiajing", "ep%03d" % int(ep_num))
        smap = os.path.join(d, "space_maps.json")
        if not os.path.exists(smap):
            log(u"⚠️ 拓扑图回写跳过：未找到 %s（db 已更新，请让 AI 补登记该场）" % smap)
            return False
        doc = json.load(open(smap, encoding="utf-8"))
        lst = doc.get("space_maps")
        if not isinstance(lst, list):
            lst = []
            doc["space_maps"] = lst
        while len(lst) <= idx:
            lst.append({"name": u"空间拓扑图·场" + str(len(lst) + 1), "prompt": "", "image": "", "ready": False})
        lst[idx]["image"] = rel_path
        lst[idx]["ready"] = True
        open(smap, "w", encoding="utf-8", newline="").write(json.dumps(doc, ensure_ascii=False, indent=2))
        # shots.json 内嵌一份拷贝（历史坑：改源文件不会自动同步进 shots，而 check-scenes 优先读内嵌那份）
        shp = os.path.join(d, "shots.json")
        if os.path.exists(shp):
            sdoc = json.load(open(shp, encoding="utf-8"))
            sdoc["space_maps"] = lst
            open(shp, "w", encoding="utf-8", newline="").write(json.dumps(sdoc, ensure_ascii=False, indent=2))
        log(u"🗺 拓扑图已回写真源: ep%s 场%d → %s（含 shots.json 内嵌同步）" % (ep_num, idx + 1, rel_path))
        return True
    except Exception as e:
        log(u"⚠️ 拓扑图回写异常（不影响上传）：%s" % e)
        return False

# 历史归档子目录名
HIST_DIR = "history"

# 各 category 的 data.js 目标字段映射
READY_KEY = {
    "sketch": "sketch_ready", "frame": "frame_ready",
    "firstframe": "firstframe_ready",   # ★ 2026-08-21 新版制作页
    "tailframe": "tailframe_ready",   # ★ 2026-08-21
    "audio": "audio_ready", "video": "video_ready",
    "storyboard": "storyboard_ready",   # ★ 2026-08-21 故事板（按集）
}
CUR_IMG_KEY = {"sketch": "sketch_image", "frame": "frame_image", "firstframe": "firstframe_image", "tailframe": "tailframe_image", "storyboard": "storyboard_image"}


def safe_join(base: str, *parts: str) -> str:
    """安全拼接，防路径穿越"""
    path = os.path.realpath(os.path.join(base, *parts))
    base_real = os.path.realpath(base)
    if not path.startswith(base_real + os.sep) and path != base_real:
        raise ValueError("非法路径")
    return path


def load_datajs():
    """读取 data.js 返回 (data, 是否成功)"""
    dj = os.path.join(ROOT, "data.js")
    if not os.path.exists(dj):
        return None, False
    txt = open(dj, encoding="utf-8").read()
    m = re.search(r"window\.PROJECT\s*=\s*(\{.*?\})\s*;\s*$", txt, re.DOTALL)
    if not m:
        return None, False
    try:
        return json.loads(m.group(1)), True
    except Exception:
        return None, False


def save_datajs(data):
    """写回 data.js"""
    data["meta"]["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    js = ("// 由 xia_Director 自动生成，勿手改；AI 每步产出后重新生成本文件。续集时读本文件 + 项目根 pipeline-state.json 即可恢复。\n"
          "window.PROJECT = " + json.dumps(data, ensure_ascii=False, indent=2) + ";\n")
    open(os.path.join(ROOT, "data.js"), "w", encoding="utf-8").write(js)


def find_target(data, category, fname):
    """按 category + 文件名定位 data.js 中对应对象，返回 (对象, 当前图路径 或 None)"""
    base = os.path.splitext(fname)[0]
    if category == "character":
        for c in data.get("xiatang", {}).get("characters", []):
            if os.path.basename(c.get("image") or "") == fname:
                return c, c.get("image", "")
            for idn in c.get("identities", []):
                if os.path.basename(idn.get("image") or "") == fname:
                    return idn, idn.get("image", "")
    elif category == "scene":
        for s in data.get("xiatang", {}).get("scenes", []):
            if os.path.basename(s.get("image") or "") == fname:
                return s, s.get("image", "")
    elif category == "prop":
        for p in data.get("xiatang", {}).get("props", []):
            if os.path.basename(p.get("image") or "") == fname:
                return p, p.get("image", "")
    elif category in ("sketch", "frame", "blocking"):
        img_key = CUR_IMG_KEY[category]
        for _e in data.get("xiajing", {}).get("episodes", []):
            if ep is not None and _e.get("number") != ep:   # ★ 2026-08-20 分集：只匹配指定集
                continue
            for b in _e.get("beats", []):
                img = b.get(img_key, "")
                if os.path.basename(img or "") == fname:
                    return b, img
    elif category == "video":
        for ep in data.get("xiajing", {}).get("episodes", []):
            for b in ep.get("beats", []):
                img = "assets/ep%03d/videos/beat%s.mp4" % (ep.get("number", 1), b.get("beat_number", 0))
                if os.path.basename(img or "") == fname:
                    return b, img
    return None, None


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT, **kwargs)

    def log_message(self, fmt, *args):
        pass  # 安静模式

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/" or path == "":
            self.path = "/index.html"
        elif path == "/api/info":
            self.send_json({"ok": True, "project": "{{项目名}}", "mode": "server", "time": datetime.now().strftime("%Y-%m-%d %H:%M")})
            return
        elif path == "/gen-config":
            self.handle_gen_config()
            return
        elif path == "/ann-tags":
            self.handle_ann_tags_get()
            return
        elif path == "/agent-config":
            self.handle_agent_config_get()
            return
        elif path == "/logs":
            self.handle_logs()
            return
        elif path == "/tasks":
            self.handle_tasks()
            return
        elif path == "/tasks/count":
            self.handle_tasks_count()
            return
        elif path == "/gen-video-status":
            # ★ 2026-08-23 生视频状态轮询：前端按 task_id 查
            self.handle_gen_video_status(parse_qs(urlparse(self.path).query))
            return
        elif path == "/db/status":
            self.handle_db_status()
            return
        elif path == "/db/snapshot":
            self.handle_db_snapshot()
            return
        elif path == "/api/data":
            self.handle_api_data()
            return
        elif path == "/api/export-style":
            self.handle_export_style(parse_qs(urlparse(self.path).query))
            return
        super().do_GET()

    def handle_logs(self):
        """GET /logs?lines=30：返回 server.log 最近 N 行（任务栏展示）"""
        try:
            q = parse_qs(urlparse(self.path).query)
            n = min(int(q.get("lines", ["30"])[0]), 200)
        except Exception:
            n = 30
        logs = []
        if os.path.exists(LOG_PATH):
            try:
                with open(LOG_PATH, encoding="utf-8") as f:
                    lines = f.readlines()
                logs = [l.rstrip() for l in lines[-n:]]
            except Exception:
                logs = []
        self.send_json({"ok": True, "logs": logs})

    def handle_tasks(self):
        """GET /tasks：返回任务队列快照（任务中 + 任务完成）"""
        running, done = GEN_QUEUE.snapshot()
        self.send_json({"ok": True, "running": running, "done": done, "stats": GEN_QUEUE.stats()})

    def handle_tasks_count(self):
        """GET /tasks/count：返回队列状态（角标用）"""
        self.send_json({"ok": True, **GEN_QUEUE.stats()})

    # ---------- SQLite 快照库 ----------
    def handle_api_data(self):
        """GET /api/data：从 SQLite 组装完整 PROJECT（前端唯一数据源，替代 data.js）"""
        dbd = db_read_all()
        if not dbd:
            self.send_json({"ok": False, "error": "数据库为空，请先 POST /db/migrate 迁移数据"}, 404); return
        # 按固定顺序组装（meta 在前，其余按 key 排序），结构与原 window.PROJECT 完全一致
        order = ["meta", "xiaju", "xialiao", "xiage", "xiatang", "xiajing", "pipeline", "resume_guide"]
        proj = {}
        for k in order:
            if k in dbd:
                proj[k] = dbd[k]
        for k in sorted(dbd.keys()):
            if k not in proj:
                proj[k] = dbd[k]
        self.send_json({"ok": True, "data": proj, "modules": list(proj.keys())})

    def handle_db_status(self):
        """GET /db/status：数据库状态（路径/表/模块清单）"""
        try:
            conn = db_conn()
            rows = conn.execute("SELECT module, length(data), updated_at FROM snapshots ORDER BY module").fetchall()
            conn.close()
            self.send_json({"ok": True, "db_path": DB_PATH, "exists": os.path.exists(DB_PATH),
                            "modules": [{"module": m, "bytes": b, "updated_at": u} for m, b, u in rows]})
        except Exception as e:
            self.send_json({"ok": False, "error": str(e)}, 500)

    def handle_db_snapshot(self):
        """GET /db/snapshot?module=xxx：查询单个模块快照（原样返回）"""
        q = parse_qs(urlparse(self.path).query)
        module = q.get("module", [""])[0]
        if not module:
            self.send_json({"ok": False, "error": "module 缺失"}, 400); return
        try:
            conn = db_conn()
            row = conn.execute("SELECT data, updated_at FROM snapshots WHERE module=?", (module,)).fetchone()
            conn.close()
            if not row:
                self.send_json({"ok": False, "error": f"模块 {module} 不存在"}, 404); return
            self.send_json({"ok": True, "module": module, "updated_at": row[1], "data": json.loads(row[0])})
        except Exception as e:
            self.send_json({"ok": False, "error": str(e)}, 500)

    def handle_db_migrate(self):
        """POST /db/migrate：把 data.js 的 window.PROJECT 全量迁移到 SQLite（原样存储）"""
        try:
            n, errors = db_migrate_from_datajs()
            self.send_json({"ok": len(errors) == 0, "migrated": n, "errors": errors})
        except Exception as e:
            self.send_json({"ok": False, "error": str(e)}, 500)

    def handle_db_verify(self):
        """POST /db/verify：校验 SQLite 快照与 data.js 完全一致（逐模块对比）"""
        try:
            r = db_verify_against_datajs()
            self.send_json(r)
        except Exception as e:
            self.send_json({"ok": False, "error": str(e)}, 500)

    def handle_save_prompt(self):
        """POST /save-prompt：保存生图提示词到资产/Beat（2026-08-20 用户需求：
        生图弹窗修改提示词后可保存，下次打开/生成用修改后的版本）。
        body: { category, name, prompt, ep }
        → character: c.prompt / identity: 角色名-身份名 → id.prompt / scene: s.prompt / prop: p.prompt
        → sketch|blocking: beat.blocking_prompt / frame: beat.firstframe_prompt（按 ep+beat_number）"""
        length = int(self.headers.get("Content-Length", 0))
        try:
            req = json.loads(self.rfile.read(length).decode("utf-8"))
        except Exception:
            self.send_json({"ok": False, "error": "JSON 解析失败"}, 400)
            return
        category = req.get("category", "")
        name = str(req.get("name") or "")
        prompt = str(req.get("prompt") or "")
        ep = int(req.get("ep") or 1)
        if category not in CATEGORY_DIRS or not name or not prompt:
            self.send_json({"ok": False, "error": "category/name/prompt 缺失"}, 400)
            return
        base = name.rsplit(".", 1)[0] if "." in name else name
        ok = False
        _dbd = db_read_all()
        if not _dbd:
            self.send_json({"ok": False, "error": "数据库读取失败"}, 500)
            return
        data = _dbd
        if category == "character":
            for c in data.get("xiatang", {}).get("characters", []):
                if c.get("name") == base:
                    c["prompt"] = prompt; ok = True
        elif category == "identity":
            for c in data.get("xiatang", {}).get("characters", []):
                for idn in c.get("identities", []):
                    if f"{c.get('name')}-{idn.get('name')}" == base or idn.get("name") == base:
                        idn["prompt"] = prompt; ok = True
        elif category == "scene":
            for s in data.get("xiatang", {}).get("scenes", []):
                if s.get("name") == base:
                    s["prompt"] = prompt; ok = True
        elif category == "prop":
            for p in data.get("xiatang", {}).get("props", []):
                if p.get("name") == base:
                    p["prompt"] = prompt; ok = True
        elif category in ("sketch", "blocking"):
            key = {"sketch": "blocking_prompt", "blocking": "blocking_prompt"}[category]
            bn = base.replace("beat", "", 1)
            for e in data.get("xiajing", {}).get("episodes", []):
                if e.get("number") != ep:
                    continue
                for b in e.get("beats", []):
                    if str(b.get("beat_number", "")) == bn:
                        b[key] = prompt; ok = True
        elif category == "frame":
            # ★ 2026-08-21 兼容新旧：frame → firstframe_prompt（beats 与 shots 都查）
            bn = base.replace("beat", "", 1).replace("shot", "", 1)
            for e in data.get("xiajing", {}).get("episodes", []):
                if e.get("number") != ep:
                    continue
                for b in e.get("beats", []):
                    if str(b.get("beat_number", "")) == bn:
                        b["firstframe_prompt"] = prompt; ok = True
                for s in e.get("shots", []):
                    if str(s.get("shot_number", "")) == bn:
                        s["firstframe_prompt"] = prompt; ok = True
        elif category in ("firstframe", "tailframe", "video"):
            # ★ 2026-08-21 新版 shots 结构：shot{镜号} → shots[].{firstframe/tailframe/video}_prompt
            key = {"firstframe": "firstframe_prompt", "tailframe": "tailframe_prompt", "video": "video_prompt"}[category]
            sn = base.replace("shot", "", 1)
            # ★ 2026-08-24 单镜视频双模型：video 类别支持 model 参数，写 video_prompts[model]
            save_model = str(req.get("model") or "").strip()
            for e in data.get("xiajing", {}).get("episodes", []):
                if e.get("number") != ep:
                    continue
                for s in e.get("shots", []):
                    if str(s.get("shot_number", "")) == sn:
                        s[key] = prompt; ok = True
                        if category == "video" and save_model in ("seedance", "h3"):
                            if not isinstance(s.get("video_prompts"), dict):
                                s["video_prompts"] = {"seedance": "", "h3": ""}
                            s["video_prompts"][save_model] = prompt
        elif category == "space_map":
            # ★ 2026-09-10 3.5.14 虾镜拓扑图按场保存提示词：name=xj-space-map-{ep}-{idx} → space_maps[idx].prompt
            _xsm = _re.match(r'^xj-space-map-(\d+)-(\d+)$', base)
            for _e in data.get("xiajing", {}).get("episodes", []):
                if _xsm and int(_e.get("number", 0)) == int(_xsm.group(1)):
                    _xj_space_map_at(_e, int(_xsm.group(2)))["prompt"] = prompt
                    ok = True
        elif category == "tf_space_map":
            # ★ 2026-09-04 听风拓扑图按场集合保存提示词：name=tf-space-map-{ep}-{idx} → space_maps[idx].prompt；
            #   旧 name=tf-space-map-{ep} 兼容写 space_map_prompt（原缺口：该类别此前不在 save-prompt 支持列表，提示词保存会 400）
            _tfe = _re.match(r'^tf-space-map-(\d+)$', base)
            _tfm = _re.match(r'^tf-space-map-(\d+)-(\d+)$', base)
            for _te in data.get("tingfeng", {}).get("episodes", []):
                if _tfm and int(_te.get("number", 0)) == int(_tfm.group(1)):
                    _tf_space_map_at(_te, int(_tfm.group(2)))["prompt"] = prompt
                    ok = True
                elif _tfe and int(_te.get("number", 0)) == int(_tfe.group(1)):
                    _te["space_map_prompt"] = prompt; ok = True
        else:
            self.send_json({"ok": False, "error": f"不支持的类别 {category}（仅 character/identity/scene/prop/sketch/blocking/frame/firstframe/tailframe/video/space_map/tf_space_map）"}, 400)
            return
        if ok:
            db_upsert("xiatang", data["xiatang"]) if "xiatang" in data else None
            db_upsert("xiajing", data["xiajing"]) if "xiajing" in data else None
            db_upsert("tingfeng", data["tingfeng"]) if "tingfeng" in data else None   # ★ 2026-09-04 补 tingfeng 落库（§6.1 成对规则）
            log(f"💾 提示词已保存: {category} name={name} ({len(prompt)}字符)")
        self.send_json({"ok": ok, "category": category, "name": name}, code=200 if ok else 404)

    def handle_download_zip(self):
        """POST /download-zip：资产打包下载（★ 2026-08-22 顶部📥下载按钮）
        body: { items: [{path, name}, ...] } → zip 流返回（★ 2026-08-23 文件名=页面展示名称 name+原扩展名；
              兼容旧格式 { paths: [...] } 用原 basename）"""
        import zipfile
        import io as _bio
        try:
            length = int(self.headers.get("Content-Length", 0))
            req = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
        except Exception:
            self.send_json({"ok": False, "error": "JSON 解析失败"}, 400)
            return
        paths = req.get("paths") or []
        items = req.get("items") or []
        if not isinstance(paths, list):
            paths = []
        if not isinstance(items, list):
            items = []
        # 归一化：[(rel, 展示名或None)]；name 为 None 时用原 basename
        entries = []
        if items:
            for it in items:
                if not isinstance(it, dict):
                    continue
                p = it.get("path")
                if p:
                    entries.append((str(p), str(it.get("name") or "") or None))
        else:
            for p in paths:
                entries.append((str(p), None))
        if not entries:
            self.send_json({"ok": False, "error": "未选择任何图片"}, 400)
            return
        buf = _bio.BytesIO()
        added = 0
        names = {}   # ★ 2026-08-22 扁平打包：zip 内只留文件名（不要 assets/xxx 文件夹层级）；重名加序号
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for rel, nm in entries:
                rel = str(rel).lstrip("/").replace("\\", "/")
                fp = os.path.join(ROOT, rel)
                if os.path.isfile(fp):
                    ext = os.path.splitext(rel)[1]
                    stem = (nm or os.path.splitext(os.path.basename(rel))[0]).strip() or "图片"
                    base = stem + ext
                    arc = base
                    n = names.get(base, 0)
                    if n:
                        s2, e2 = os.path.splitext(base)
                        arc = f"{s2}({n}){e2}"
                    names[base] = n + 1
                    zf.write(fp, arc)
                    added += 1
        if not added:
            self.send_json({"ok": False, "error": "所选图片文件均不存在"}, 404)
            return
        data = buf.getvalue()
        self.send_response(200)
        self.send_header("Content-Type", "application/zip")
        self.send_header("Content-Disposition", f'attachment; filename="assets-{len(paths)}-{int(time.time())}.zip"')
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        try:
            self.wfile.write(data)
        except Exception:
            pass

    def handle_save_annotation(self):
        """POST /save-annotation：画面标注保存（2026-08-20 新增；★ 2026-08-22 适配虾镜 shots：shot_number 优先，兼容 beat_number）。
        body: { shot_number 或 beat_number, ep, data_url }
        → 解码 base64 → 写盘 assets/ep{NNN}/annotation/{shot|beat}{N}-annotated-{ms}.png（时间戳防缓存）
        → 清理同镜头旧 annotated 文件 → SQLite 更新 shot/beat.annotated_image（编辑稿优先）→ 返回 {ok, image, ts}
        """
        length = int(self.headers.get("Content-Length", 0))
        try:
            req = json.loads(self.rfile.read(length).decode("utf-8"))
        except Exception:
            self.send_json({"ok": False, "error": "JSON 解析失败"}, 400)
            return
        shot_number = req.get("shot_number")
        beat_number = req.get("beat_number")
        ident = shot_number if shot_number is not None else beat_number
        ep = int(req.get("ep") or 1)
        data_url = req.get("data_url") or ""
        if ident is None or not str(data_url).startswith("data:image/"):
            self.send_json({"ok": False, "error": "shot_number/beat_number/data_url 缺失"}, 400)
            return
        try:
            import base64 as _b64
            img_bytes = _b64.b64decode(str(data_url).split(",", 1)[1])
        except Exception:
            self.send_json({"ok": False, "error": "图片数据解码失败"}, 400)
            return
        # 目录 assets/ep{NNN}/annotation/
        rel_dir = os.path.join("assets", f"ep{ep:03d}", "annotation")
        prefix = "shot" if shot_number is not None else "beat"
        fname = f"{prefix}{ident}-annotated-{int(time.time() * 1000)}.png"
        try:
            target = safe_join(ROOT, rel_dir, fname)
        except Exception:
            self.send_json({"ok": False, "error": "非法路径"}, 400)
            return
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "wb") as f:
            f.write(img_bytes)
        # 清理同镜头旧 annotated 文件（防磁盘堆积；页面始终用最新 URL 不会命中缓存）
        try:
            for old in os.listdir(os.path.dirname(target)):
                if old.startswith(f"{prefix}{ident}-annotated-") and old != fname:
                    os.remove(os.path.join(os.path.dirname(target), old))
        except Exception:
            pass
        rel_path = f"{rel_dir}/{fname}".replace("\\", "/")
        # SQLite 更新 shot/beat.annotated_image（★ 编辑稿优先，与前端显示一致）
        ok = False
        _dbd = db_read_all()
        if _dbd and _dbd.get("xiajing"):
            xj = _dbd["xiajing"]
            for e in xj.get("episodes", []):
                if e.get("number") == ep:
                    if shot_number is not None:
                        for _arr_key in ("edited_shots", "shots"):
                            for s in e.get(_arr_key) or []:
                                if str(s.get("shot_number")) == str(shot_number):
                                    s["annotated_image"] = rel_path
                                    ok = True
                    else:
                        for b in e.get("beats", []):
                            if b.get("beat_number") == int(beat_number):
                                b["annotated_image"] = rel_path
                                ok = True
            if ok:
                db_upsert("xiajing", xj)
        # 同步磁盘 shots.json / beats.json（annotated_image 是附加产物，不污染分镜内容字段）
        try:
            if shot_number is not None:
                sj_path = os.path.realpath(os.path.join(ROOT, "..", "outputs", "xiajing", f"ep{ep:03d}", "shots.json"))
                if os.path.exists(sj_path):
                    sj = json.load(open(sj_path, encoding="utf-8"))
                    for s in sj.get("shots", []):
                        if str(s.get("shot_number")) == str(shot_number):
                            s["annotated_image"] = rel_path
                    json.dump(sj, open(sj_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            else:
                bj_path = os.path.realpath(os.path.join(ROOT, "..", "outputs", "xiajing", f"ep{ep:03d}", "beats.json"))
                if os.path.exists(bj_path):
                    bj = json.load(open(bj_path, encoding="utf-8"))
                    for b in bj.get("beats", []):
                        if b.get("beat_number") == int(beat_number):
                            b["annotated_image"] = rel_path
                    json.dump(bj, open(bj_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        except Exception:
            pass
        log(f"📌 标注保存: ep{ep} {prefix}{ident} → {rel_path} ({len(img_bytes)}B) sqlite={'✅' if ok else '❌'}")
        self.send_json({"ok": ok, "image": rel_path, "ts": int(time.time() * 1000)},
                       code=200 if ok else 500)

    def handle_scene_set_front(self):
        """POST /scene-set-front：把场景某张多角度图设为「正面」（2026-08-20 用户拍板）。
        body: { name: 场景名, view: 角度（如 左侧） }
        → 复制 场景名-{view}.png → 场景名-正面-{ms}.png（时间戳防缓存）→ views.正面 指向新文件
        → 原角度 views[view]/views_ready[view] 清空 → SQLite 更新 → 返回 {ok, image, cleared_view}
        """
        length = int(self.headers.get("Content-Length", 0))
        try:
            req = json.loads(self.rfile.read(length).decode("utf-8"))
        except Exception:
            self.send_json({"ok": False, "error": "JSON 解析失败"}, 400)
            return
        name = str(req.get("name") or "").strip()
        view = str(req.get("view") or "").strip()
        if not name or not view:
            self.send_json({"ok": False, "error": "name/view 缺失"}, 400)
            return
        dbd = db_read_all()
        if not dbd or not dbd.get("xiatang"):
            self.send_json({"ok": False, "error": "数据库为空"}, 404)
            return
        xt = dbd["xiatang"]
        s = next((x for x in xt.get("scenes", []) if x.get("name") == name), None)
        if not s:
            self.send_json({"ok": False, "error": f"场景不存在: {name}"}, 404)
            return
        views = s.setdefault("views", {})
        views_ready = s.setdefault("views_ready", {})
        if not views.get(view):
            self.send_json({"ok": False, "error": f"角度「{view}」未生成"}, 400)
            return
        if view == "正面":
            # 本身就是正面：无需处理
            self.send_json({"ok": True, "image": views["正面"], "cleared_view": ""})
            return
        src = str(views[view]).split("?")[0]
        src_path = os.path.join(ROOT, src)
        if not os.path.exists(src_path):
            self.send_json({"ok": False, "error": f"源图不存在: {src}"}, 404)
            return
        # 复制为正面命名（时间戳防浏览器缓存；沿用 {base}-{视角}-{ms}.png 惯例）
        fname = f"{name}-正面-{int(time.time() * 1000)}.png"
        scenes_dir = os.path.join(ROOT, "assets", "scenes")
        os.makedirs(scenes_dir, exist_ok=True)
        try:
            shutil.copy2(src_path, os.path.join(scenes_dir, fname))
        except Exception as e:
            self.send_json({"ok": False, "error": f"复制失败: {e}"}, 500)
            return
        rel = f"assets/scenes/{fname}"
        views["正面"] = rel
        views_ready["正面"] = True
        # 原角度清空（文件保留，重新生成该角度会覆盖）
        views.pop(view, None)
        views_ready[view] = False
        db_upsert("xiatang", xt)
        log(f"🔄 场景正面替换: {name} 原角度「{view}」→ 正面（{rel}）")
        self.send_json({"ok": True, "image": rel, "cleared_view": view, "src": src})

    def handle_scene_del_img(self):
        """POST /scene-del-img：删除场景某张图（文件 + 数据库）（2026-08-22 用户需求）。
        body: { scene: 场景名, key: image | view:正面 | plan | plan_sketch | dist:源标签|视距 }
        → 定位 SQLite xiatang.scenes[name] 对应字段 → 删除磁盘文件（safe_join 安全路径）
        → 清 SQLite 字段（views/dists 用 pop，image/plan 等清空 + ready false）→ 返回 {ok, cleared}
        """
        length = int(self.headers.get("Content-Length", 0))
        try:
            req = json.loads(self.rfile.read(length).decode("utf-8"))
        except Exception:
            self.send_json({"ok": False, "error": "JSON 解析失败"}, 400)
            return
        name = str(req.get("scene") or "").strip()
        key = str(req.get("key") or "").strip()
        if not name or not key:
            self.send_json({"ok": False, "error": "scene/key 缺失"}, 400)
            return
        dbd = db_read_all()
        if not dbd or not dbd.get("xiatang"):
            self.send_json({"ok": False, "error": "数据库为空"}, 404)
            return
        xt = dbd["xiatang"]
        s = next((x for x in xt.get("scenes", []) if x.get("name") == name), None)
        if not s:
            self.send_json({"ok": False, "error": f"场景不存在: {name}"}, 404)
            return
        rel_path = None
        cleared = key
        if key == "image":
            rel_path = s.get("image") or ""
            def clear():
                s.pop("image", None); s["image_ready"] = False
        elif key.startswith("view:"):
            v = key[5:]
            if not v or not (s.get("views") or {}).get(v):
                self.send_json({"ok": False, "error": f"视角「{v}」不存在"}, 404); return
            rel_path = (s.get("views") or {}).get(v) or ""
            cleared = v
            def clear():
                s.setdefault("views", {}).pop(v, None)
                s.setdefault("views_ready", {})[v] = False
        elif key == "plan":
            if not s.get("plan_ready"):
                self.send_json({"ok": False, "error": "平面布局未生成"}, 404); return
            rel_path = s.get("plan") or ""
            def clear():
                s.pop("plan", None); s["plan_ready"] = False
        elif key == "plan_sketch":
            if not s.get("plan_sketch_ready"):
                self.send_json({"ok": False, "error": "线稿未生成"}, 404); return
            rel_path = s.get("plan_sketch") or ""
            def clear():
                s.pop("plan_sketch", None); s["plan_sketch_ready"] = False
        elif key.startswith("dist:"):
            dk = key[5:]
            if not dk or not (s.get("dists") or {}).get(dk):
                self.send_json({"ok": False, "error": "视距图不存在"}, 404); return
            rel_path = (s.get("dists") or {}).get(dk) or ""
            cleared = dk.replace("|", "·")
            def clear():
                s.setdefault("dists", {}).pop(dk, None)
                s.setdefault("dists_ready", {})[dk] = False
        else:
            self.send_json({"ok": False, "error": f"未知 key: {key}"}, 400); return
        # 删除磁盘文件（仅 ROOT 内，safe_join 防路径穿越；文件已不存在时静默继续）
        if rel_path:
            try:
                fp = safe_join(ROOT, str(rel_path).split("?")[0].lstrip("/"))
                if os.path.isfile(fp):
                    os.remove(fp)
            except Exception:
                pass
        clear()
        db_upsert("xiatang", xt)
        log(f"🗑 场景图删除: {name} {cleared}（文件{'已删' if rel_path else '无'}）")
        self.send_json({"ok": True, "cleared": cleared})

    def handle_reuse_annotation(self):
        """POST /reuse-annotation：复用已有画面标注图到当前镜头（2026-08-22 用户需求）。
        body: {ep, shot_number, image}
        → SQLite xiajing edited_shots+shots 设 annotated_image = image（引用路径，不复制文件）
        → 磁盘 shots.json 同步（仅附加字段）→ 返回 {ok, image}
        """
        length = int(self.headers.get("Content-Length", 0))
        try:
            req = json.loads(self.rfile.read(length).decode("utf-8"))
        except Exception:
            self.send_json({"ok": False, "error": "JSON 解析失败"}, 400)
            return
        ep = int(req.get("ep") or 1)
        shot_number = req.get("shot_number")
        image = str(req.get("image") or "").strip()
        if shot_number is None or not image:
            self.send_json({"ok": False, "error": "shot_number/image 缺失"}, 400)
            return
        dbd = db_read_all()
        if not dbd or not dbd.get("xiajing"):
            self.send_json({"ok": False, "error": "数据库为空"}, 404)
            return
        xj = dbd["xiajing"]
        ok = False
        for e in xj.get("episodes", []):
            if e.get("number") == ep:
                for _arr_key in ("edited_shots", "shots"):
                    for s in e.get(_arr_key) or []:
                        if str(s.get("shot_number")) == str(shot_number):
                            s["annotated_image"] = image
                            ok = True
        if ok:
            db_upsert("xiajing", xj)
        # 同步磁盘 shots.json（annotated_image 为附加产物字段）
        try:
            sj_path = os.path.realpath(os.path.join(ROOT, "..", "outputs", "xiajing", f"ep{ep:03d}", "shots.json"))
            if os.path.exists(sj_path):
                sj = json.load(open(sj_path, encoding="utf-8"))
                for s in sj.get("shots", []):
                    if str(s.get("shot_number")) == str(shot_number):
                        s["annotated_image"] = image
                json.dump(sj, open(sj_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        except Exception:
            pass
        log(f"📋 复用标注: ep{ep} 镜{shot_number} ← {image} sqlite={'✅' if ok else '❌'}")
        self.send_json({"ok": ok, "image": image}, code=200 if ok else 500)

    def handle_storyboard_prompts_save(self):
        """POST /storyboard-prompts：保存故事板生视频提示词（★ 2026-08-24 双模型并存）
        body: {ep, idx, prompts: {seedance:[str...], h3:[str...]} 或 旧数组[str...], segments: [{first,last,total}...]}
        → SQLite xiajing episodes[].storyboards[idx].video_prompts（统一存为 {seedance,h3} 对象）/ video_segments"""
        length = int(self.headers.get("Content-Length", 0))
        try:
            req = json.loads(self.rfile.read(length).decode("utf-8"))
        except Exception:
            self.send_json({"ok": False, "error": "JSON 解析失败"}, 400)
            return
        ep = int(req.get("ep") or 1)
        idx = int(req.get("idx") or 0)
        prompts = req.get("prompts")
        # ★ 2026-08-24：prompts 支持 对象{seedance,h3} 或 旧数组（兼容）。统一归一为 {seedance,h3}
        if isinstance(prompts, dict):
            vp_obj = {
                "seedance": [str(p) for p in (prompts.get("seedance") or [])],
                "h3": [str(p) for p in (prompts.get("h3") or [])],
            }
        elif isinstance(prompts, list):
            # 旧格式：数组当作 seedance 文本，h3 暂留空（前端下次装填会自动补齐）
            vp_obj = {"seedance": [str(p) for p in prompts], "h3": []}
        else:
            self.send_json({"ok": False, "error": "prompts 需为对象或数组"}, 400)
            return
        segments = req.get("segments") if isinstance(req.get("segments"), list) else None
        dbd = db_read_all()
        if not dbd or not dbd.get("xiajing"):
            self.send_json({"ok": False, "error": "数据库为空"}, 404)
            return
        xj = dbd["xiajing"]
        ok = False
        for e in xj.get("episodes", []):
            if e.get("number") == ep:
                sb = next((s for s in (e.get("storyboards") or []) if s.get("idx") == idx), None)
                if sb is not None:
                    sb["video_prompts"] = vp_obj
                    if segments is not None:
                        sb["video_segments"] = segments
                    ok = True
                break
        if ok:
            db_upsert("xiajing", xj)
            log(f"🎬 故事板提示词保存: ep{ep} 板{idx} seedance {len(vp_obj['seedance'])} / h3 {len(vp_obj['h3'])} 条")
            self.send_json({"ok": True, "count": len(vp_obj["seedance"]) + len(vp_obj["h3"])})
        else:
            self.send_json({"ok": False, "error": "故事板不存在"}, 404)

    def handle_story_video_delete(self):
        """POST /story-video-delete：删除故事板某段视频（★ 2026-08-24）
        body: {ep, idx (gno), seg_idx}
        → 清 storyboards[gno].video_segments[seg_idx] 的 video/video_ready/video_result/_vt
          + 删除本地 mp4（assets/epNNN/videos/...）；记录与文件一起删。"""
        length = int(self.headers.get("Content-Length", 0))
        try:
            req = json.loads(self.rfile.read(length).decode("utf-8"))
        except Exception:
            self.send_json({"ok": False, "error": "JSON 解析失败"}, 400)
            return
        ep = int(req.get("ep") or 1)
        gno = int(req.get("idx") or 0)
        seg_idx = int(req.get("seg_idx") or 0)
        # ★ 2026-09-01 module 路由：xiajing（默认，兼容旧调用）/ tingfeng（清 episodes[].segments[seg_idx] 引用）
        module = (req.get("module") or "xiajing").strip() or "xiajing"
        dbd = db_read_all()
        if not dbd:
            self.send_json({"ok": False, "error": "数据库为空"}, 404)
            return
        target = None   # 待删本地文件相对路径
        ok = False
        if module == "tingfeng":
            tf = dbd.get("tingfeng") or {}
            target_ep = next((e for e in (tf.get("episodes") or []) if int(e.get("number", 0)) == int(ep)), None)
            if not target_ep:
                self.send_json({"ok": False, "error": "tingfeng 未找到该集"}, 404)
                return
            segs = target_ep.get("segments") or []
            if not (0 <= seg_idx < len(segs)):
                self.send_json({"ok": False, "error": "tingfeng 段位不存在"}, 404)
                return
            with _DB_WRITE_LOCK:
                seg = segs[seg_idx]
                target = seg.get("video") or ""
                seg["video"] = ""
                seg["video_ready"] = False
                seg["video_result"] = ""
                seg["_vt"] = 0
                ok = True
                db_upsert("tingfeng", tf)
            log(f"🗑 听风视频段已删: ep{ep} 段{seg_idx}")
            # 跳到公共删文件段（下面 if target 逻辑共用）
            if target:
                try:
                    fp = safe_join(ROOT, target)
                    if os.path.exists(fp):
                        os.remove(fp)
                        log(f"🗑 听风视频本地文件已删: {fp}")
                except Exception as e:
                    log(f"⚠️ 听风视频本地文件删除失败（记录已清）: {target} {e}")
            self.send_json({"ok": True})
            return
        xj = dbd["xiajing"]
        target = None   # 待删本地文件相对路径
        ok = False
        with _DB_WRITE_LOCK:
            for e in xj.get("episodes", []):
                if e.get("number") == ep:
                    sb = next((s for s in (e.get("storyboards") or []) if s.get("idx") == gno), None)
                    if sb is not None:
                        segs = sb.get("video_segments") or []
                        if 0 <= seg_idx < len(segs):
                            seg = segs[seg_idx]
                            target = seg.get("video") or ""
                            seg["video"] = ""
                            seg["video_ready"] = False
                            seg["video_result"] = ""
                            seg["_vt"] = 0
                            ok = True
                    break
        if not ok:
            self.send_json({"ok": False, "error": "故事板/段位不存在"}, 404)
            return
        # ★ 删本地 mp4（在锁外做 IO，避免阻塞其它写；路径用 safe_join 防穿越）
        if target:
            try:
                fp = safe_join(ROOT, target)
                if os.path.exists(fp):
                    os.remove(fp)
                    log(f"🗑 故事板视频本地文件已删: {fp}")
            except Exception as e:
                log(f"⚠️ 故事板视频本地文件删除失败（记录已清）: {target} {e}")
        db_upsert("xiajing", xj)
        log(f"🗑 故事板视频段已删: ep{ep} 板{gno} 段{seg_idx}")
        self.send_json({"ok": True})

    def handle_shots(self, action):
        """POST /shots/{save|reset|delete|add|reorder|reset_all}（★ 2026-08-22 编辑副本分离：原始 shots.json 永不动）
        body: { ep, idx, payload }
        - save:   payload=fields dict → 副本机制（首次编辑存 original_shot）
        - reset:  idx → 恢复 original_shot
        - delete: idx → 硬删并重排镜号
        - add:    idx+payload → 插入新行并重排
        - reorder:payload={ordered:[镜号...]} → 按序重排
        - reset_all: 删除本集编辑稿 → 回到原始定稿
        → 编辑结果只写入 ep.edited_shots + outputs/xiajing/ep{NNN}/shots.edited.json；原始 shots.json 永不覆盖"""
        length = int(self.headers.get("Content-Length", 0))
        try:
            req = json.loads(self.rfile.read(length).decode("utf-8"))
        except Exception:
            self.send_json({"ok": False, "error": "JSON 解析失败"}, 400)
            return
        ep = int(req.get("ep") or 1)
        idx = req.get("idx")
        payload = req.get("payload")
        _dbd = db_read_all()
        if not _dbd:
            self.send_json({"ok": False, "error": "数据库读取失败"}, 500)
            return
        episodes = _dbd.get("xiajing", {}).get("episodes", [])
        ep_obj = next((e for e in episodes if e.get("number") == ep), None)
        if ep_obj is None:
            self.send_json({"ok": False, "error": f"第{ep}集不存在"}, 404)
            return
        # ★ 2026-08-22 编辑稿分离：所有编辑 action 操作 edited_shots（首次编辑时从原始深拷贝一份）
        _orig = ep_obj.setdefault("shots", [])
        shots = ep_obj.get("edited_shots")
        if shots is None:
            shots = json.loads(json.dumps(_orig))
            # ★ 2026-08-22 uid 补齐：每镜给稳定唯一标识（拖动重排按 uid 传顺序；镜号是位置标识会重编号）
            for _sh in shots:
                if isinstance(_sh, dict) and not _sh.get("uid"):
                    _sh["uid"] = _uuid.uuid4().hex[:12]
            ep_obj["edited_shots"] = shots
        ok = False
        if action == "save" and isinstance(idx, int) and isinstance(payload, dict) and 0 <= idx < len(shots):
            s = shots[idx]
            if not s.get("is_edited"):
                s["original_shot"] = json.loads(json.dumps(s))
            for k, v in (payload or {}).items():
                if k not in ("is_edited", "original_shot", "shot_number"):
                    s[k] = v
            s["is_edited"] = True
            ok = True
        elif action == "reset" and isinstance(idx, int) and 0 <= idx < len(shots):
            s = shots[idx]
            if s.get("original_shot"):
                shots[idx] = s["original_shot"]
            else:
                s["is_edited"] = False
            ok = True
        elif action == "delete" and isinstance(idx, int) and 0 <= idx < len(shots):
            shots.pop(idx)
            for i, s in enumerate(shots):
                s["shot_number"] = str(i + 1)
            ok = True
        elif action == "add" and isinstance(payload, dict):
            shots.append(payload)
            for i, s in enumerate(shots):
                s["shot_number"] = str(i + 1)
            ok = True
        elif action == "reorder" and isinstance(payload, dict) and payload.get("ordered"):
            # ★ 2026-08-22 uid 优先匹配（镜号是位置标识会重编号，拖动顺序必须用稳定 uid 传）；
            #   旧数据无 uid 时降级镜号匹配（归一化兼容 "1"/"01"）
            _order = payload["ordered"]
            _s_by = {s.get("uid"): s for s in shots} if all(
                isinstance(x, str) and len(x) == 12 for x in _order if x is not None) else None
            if _s_by is None:
                def _zn(n):
                    s = str(n or "").strip()
                    return s.zfill(2) if s.isdigit() else s
                _s_by = {_zn(s.get("shot_number")): s for s in shots}
                _order = [_zn(n) for n in _order]
            new_shots = []
            for num in _order:
                s = _s_by.get(num)
                if s is None:
                    continue
                new_shots.append(s)
            if len(new_shots) == len(shots):
                # ★ 2026-08-22 必须原地替换编辑稿（shots 指向 edited_shots），禁写回原始 ep_obj["shots"]（会污染原始定稿且编辑稿不更新 → 刷新/重启"变回去"）
                shots[:] = new_shots
                for i, s in enumerate(new_shots):
                    s["shot_number"] = str(i + 1).zfill(2)
                ok = True
        elif action == "reset_all":
            # ★ 2026-08-22 整集重置分镜（编辑稿分离后简化）：删除本集编辑稿 → 自动回到原始定稿 shots
            ep_obj["edited_shots"] = None
            ok = True
        if not ok:
            self.send_json({"ok": False, "error": f"shots/{action} 执行失败（idx/数据不匹配）"}, 400)
            return
        db_upsert("xiajing", _dbd["xiajing"])
        ed = f"ep{ep:03d}"
        ep_dir = os.path.join(ROOT, "..", "outputs", "xiajing", ed)
        try:
            if ep_obj.get("edited_shots") is not None:
                # 有编辑稿 → 写 shots.edited.json（原始 shots.json 永不动）
                os.makedirs(ep_dir, exist_ok=True)
                with open(os.path.join(ep_dir, "shots.edited.json"), "w", encoding="utf-8") as fh:
                    json.dump({
                        "episode_title": ep_obj.get("title", f"第{ep}集"),
                        "shots": ep_obj["edited_shots"]
                    }, fh, ensure_ascii=False, indent=2)
            else:
                # reset_all → 删除编辑稿文件
                _f = os.path.join(ep_dir, "shots.edited.json")
                if os.path.exists(_f):
                    os.remove(_f)
        except Exception as e:
            log(f"⚠️ shots.edited.json 写回失败: {e}")
        log(f"🎬 shots/{action}: ep{ep}")
        self.send_json({"ok": True})

    def do_POST(self):
        parsed = urlparse(self.path)
        log(f"📨 POST {parsed.path}")  # 路由日志（调试用）
        if parsed.path == "/upload":
            self.handle_upload(parse_qs(parsed.query))
        elif parsed.path == "/save-prompt":
            self.handle_save_prompt()
            return
        elif parsed.path == "/xiaju/save":
            # ★ 2026-09-05 虾剧·剧本输出保存：body={episodes:[{number,title,body,updated_at}]} 全量写 xiaju 模块快照
            _len2 = int(self.headers.get("Content-Length", 0))
            try:
                _req2 = json.loads(self.rfile.read(_len2).decode("utf-8"))
                _eps2 = _req2.get("episodes")
                if not isinstance(_eps2, list):
                    raise ValueError("episodes 必须为数组")
                db_upsert("xiaju", {"episodes": _eps2})
                self.send_json({"ok": True, "count": len(_eps2)})
            except Exception as _e2:
                self.send_json({"ok": False, "error": str(_e2)}, 400)
            return
        elif parsed.path.startswith("/shots/"):
            self.handle_shots(parsed.path.split("/")[-1])
            return
        elif parsed.path == "/story-reset":
            # ★ 2026-08-21 故事板：重置指定集已生成的故事板图（清字段，历史图保留在目录）
            try:
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))).decode("utf-8") or "{}")
            except Exception:
                body = {}
            epn = int(body.get("ep", 0) or 0)
            data = self._load_data()
            ok = False
            for _e in data.get("xiajing", {}).get("episodes", []):
                if _e.get("number") == epn:
                    _e["storyboard_image"] = ""
                    _e["storyboard_ready"] = False
                    ok = True
                    break
            if ok:
                if "xiajing" in data:
                    db_upsert("xiajing", data["xiajing"])
                self.send_json({"ok": True})
            else:
                self.send_json({"ok": False, "error": f"未找到第 {epn} 集"}, 404)
            return
        elif parsed.path == "/set-current":
            self.handle_set_current(parse_qs(parsed.query))
        elif parsed.path == "/gen-image":
            self.handle_gen_image()
        elif parsed.path == "/gen-video":
            # ★ 2026-08-23 生视频：888 中转平台 海螺 H3 参考生
            self.handle_gen_video()
        elif parsed.path == "/gen-config":
            self.handle_gen_config_save()
        elif parsed.path == "/ann-tags":
            self.handle_ann_tags_save()
        elif parsed.path == "/gen-test":
            self.handle_gen_test()
        elif parsed.path == "/gen-fetch-models":
            self.handle_gen_fetch_models()
        elif parsed.path == "/agent-config":
            self.handle_agent_config_save()
            return
        elif parsed.path == "/agent-test":
            self.handle_agent_test()
            return
        elif parsed.path == "/agent-chat":
            self.handle_agent_chat()
            return
        elif parsed.path == "/styles/save":
            self.handle_style_save()
            return
        elif parsed.path == "/styles/confirm":
            self.handle_style_confirm(parse_qs(parsed.query))
            return
        elif parsed.path == "/styles/apply-library":
            self.handle_style_apply_library(parse_qs(parsed.query))
            return
        elif parsed.path == "/db/migrate":
            self.handle_db_migrate()
            return
        elif parsed.path == "/db/verify":
            self.handle_db_verify()
            return
        elif parsed.path == "/save-annotation":
            self.handle_save_annotation()
            return
        elif parsed.path == "/download-zip":
            self.handle_download_zip()
            return
        elif parsed.path == "/scene-set-front":
            self.handle_scene_set_front()
            return
        elif parsed.path == "/scene-del-img":
            self.handle_scene_del_img()
            return
        elif parsed.path == "/reuse-annotation":
            self.handle_reuse_annotation()
            return
        elif parsed.path == "/storyboard-prompts":
            self.handle_storyboard_prompts_save()
            return
        elif parsed.path == "/story-video-delete":
            self.handle_story_video_delete()
            return
        else:
            self.send_json({"ok": False, "error": "not found"}, 404)

    # ---------- 图片生成 ----------
    def handle_gen_config(self):
        """返回渠道列表（不含 apiKey）+ 尺寸列表 + 是否有可用渠道 + 各类别默认尺寸"""
        cfg = slot.load_img_config()
        channels = []
        for ch in (cfg or {}).get("channels", []):
            channels.append({
                "id": ch.get("id"),
                "name": ch.get("name"),
                "baseUrl": ch.get("baseUrl"),
                "apiFormat": ch.get("apiFormat"),
                "models": ch.get("models", []),
                "configured": bool(ch.get("baseUrl") and ch.get("apiKey")),
            })
        self.send_json({
            "ok": True,
            "configured": any(c["configured"] for c in channels),
            "channels": channels,
            "sizes": (cfg or {}).get("sizes", slot.DEFAULT_SIZES),
            "default_sizes": (cfg or {}).get("default_sizes", dict(DEFAULT_SIZE_MAP)),
            "video_model": (cfg or {}).get("video_model", "seedance"),  # ★ 2026-08-24 生视频模型选择：seedance / h3
            "storyboard_main_line": (cfg or {}).get("storyboard_main_line", "tingfeng"),  # ★ 2026-09-01 分镜主力线：xiajing / tingfeng（AI 开工判断依据）
        })

    def handle_ann_tags_get(self):
        """GET /ann-tags：标注提示词列表（★ 2026-08-23 持久化到 ROOT/ann_tags_config.json；无文件返回 tags:null，前端用默认）"""
        p = os.path.join(ROOT, "ann_tags_config.json")
        if os.path.exists(p):
            try:
                tags = json.load(open(p, encoding="utf-8"))
                self.send_json({"ok": True, "tags": tags if isinstance(tags, list) else None})
                return
            except Exception:
                pass
        self.send_json({"ok": True, "tags": None})

    def handle_ann_tags_save(self):
        """POST /ann-tags：保存标注提示词列表（body: {tags: [[标题, 内容], ...]} → 写 ROOT/ann_tags_config.json）"""
        length = int(self.headers.get("Content-Length", 0))
        try:
            req = json.loads(self.rfile.read(length).decode("utf-8"))
        except Exception:
            self.send_json({"ok": False, "error": "JSON 解析失败"}, 400)
            return
        tags = req.get("tags")
        if not isinstance(tags, list):
            self.send_json({"ok": False, "error": "tags 需为数组"}, 400)
            return
        clean = [[str(t[0] or ""), str(t[1] or "")] for t in tags if isinstance(t, list) and t and str(t[1] or "").strip()]
        try:
            with open(os.path.join(ROOT, "ann_tags_config.json"), "w", encoding="utf-8") as f:
                json.dump(clean, f, ensure_ascii=False, indent=2)
            log(f"📝 标注提示词已保存: {len(clean)} 条")
            self.send_json({"ok": True, "count": len(clean)})
        except Exception as e:
            self.send_json({"ok": False, "error": f"保存失败: {e}"}, 500)

    def handle_gen_config_save(self):
        """保存渠道配置：前端传 channels（apiKey 为空则保留旧值）；sizes 不传则保留原值。"""
        length = int(self.headers.get("Content-Length", 0))
        try:
            patch = json.loads(self.rfile.read(length).decode("utf-8")) if length > 0 else {}
        except Exception:
            self.send_json({"ok": False, "error": "JSON 解析失败"}, 400)
            return

        existing = slot.load_img_config() or {"channels": [], "sizes": slot.DEFAULT_SIZES}
        # 防御：若已有配置存在但读取失败（文件被锁/损坏），禁止静默覆盖成空配置
        if os.path.exists(slot.IMG_CONFIG_PATH) and not existing.get("channels"):
            self.send_json({"ok": False, "error": "无法读取现有 img_config.json（可能被其他程序锁定或损坏），已中止保存以免覆盖配置。请关闭占用该文件的程序后重试。"}, 409)
            return
        new_channels = slot.merge_channels(existing.get("channels"), patch.get("channels"), "ch_")
        # ★ 防御：前端未传 channels（只改 default_sizes 等其他字段）时保留现有渠道，禁止清空覆盖
        if patch.get("channels") is None:
            new_channels = existing.get("channels", [])
        sizes = patch.get("sizes") if isinstance(patch.get("sizes"), list) and patch["sizes"] else existing.get("sizes", slot.DEFAULT_SIZES)
        # ★ 2026-08-24 生视频模型选择（seedance / h3），不传则保留旧值
        vm = patch.get("video_model")
        if vm not in ("seedance", "h3"):
            vm = (existing.get("video_model") or "seedance")
        default_sizes = dict(existing.get("default_sizes") or DEFAULT_SIZE_MAP)
        if isinstance(patch.get("default_sizes"), dict):
            for k, v in patch["default_sizes"].items():
                if v:
                    default_sizes[k] = v
        # ★ 2026-09-01 分镜主力线：保留现有值，前端未传不覆盖（tingfeng 听风 / xiajing 虾镜）
        main_line = patch.get("storyboard_main_line")
        if main_line not in ("tingfeng", "xiajing"):
            main_line = existing.get("storyboard_main_line") or "tingfeng"
        cfg = {"channels": new_channels, "sizes": sizes, "default_sizes": default_sizes, "video_model": vm, "storyboard_main_line": main_line}
        err = slot.save_img_config(cfg)
        if err is not True:
            self.send_json({"ok": False, "error": str(err)}, 500)
            return
        self.send_json({"ok": True, "configured": any(slot.channel_configured(c) for c in new_channels)})

    def handle_gen_test(self):
        """测试渠道连通性：up_lk888 → /media/generate 极小任务（拿 task_id 即通）；
        openai/ark → GET /models；gemini → GET v1beta/models。
        入参：{channel_id 或 baseUrl+apiKey+apiFormat}"""
        length = int(self.headers.get("Content-Length", 0))
        try:
            patch = json.loads(self.rfile.read(length).decode("utf-8")) if length > 0 else {}
        except Exception:
            self.send_json({"ok": False, "error": "JSON 解析失败"}, 400)
            return
        cfg = slot.load_img_config()
        channel = None
        if patch.get("channel_id"):
            channel = slot.find_channel(cfg, patch["channel_id"])
        if not channel:
            channel = {
                "baseUrl": (patch.get("baseUrl") or "").strip(),
                "apiKey": (patch.get("apiKey") or "").strip(),
                "apiFormat": slot.normalize_protocol(patch.get("apiFormat")),
                "models": [],
            }
        if not channel.get("apiKey"):
            self.send_json({"ok": False, "error": "未提供 API Key"}, 400)
            return
        ok, payload = slot.test_img_channel(channel)
        if not ok:
            status = payload.get("status", 502)
            self.send_json({"ok": False, "error": payload.get("error", "测试失败")}, status)
            return
        self.send_json({"ok": True, "models": payload.get("models", []), "count": payload.get("count", 0), "note": payload.get("note", "")})

    def handle_gen_fetch_models(self):
        """拉取平台模型列表（渠道编辑器用）。openai / up_lk888 走 /v1/models，gemini 走 /v1beta/models。"""
        length = int(self.headers.get("Content-Length", 0))
        try:
            patch = json.loads(self.rfile.read(length).decode("utf-8")) if length > 0 else {}
        except Exception:
            self.send_json({"ok": False, "error": "JSON 解析失败"}, 400)
            return
        ok, payload = slot.fetch_models((patch.get("baseUrl") or "").strip(), (patch.get("apiKey") or "").strip(), patch.get("apiFormat"))
        if not ok:
            self.send_json({"ok": False, "error": payload.get("error", "拉取失败")}, 502)
            return
        self.send_json({"ok": True, "models": payload.get("models", []), "count": payload.get("count", 0)})

    # ---------- Agent（对话型 LLM · OpenAI Chat Completions 透传到 lk888）----------
    def handle_agent_config_get(self):
        """返回 Agent 配置（去敏：apiKey 隐藏成 ****）+ 默认模型 + 系统提示。"""
        cfg = slot.load_agent_config()
        channels = []
        for ch in (cfg.get("channels") or []):
            channels.append({
                "id": ch.get("id"),
                "name": ch.get("name"),
                "baseUrl": ch.get("baseUrl"),
                "apiFormat": ch.get("apiFormat"),
                "models": ch.get("models", []),
                "configured": bool(ch.get("baseUrl") and ch.get("apiKey")),
                "apiKeyMasked": ("****" + ch.get("apiKey", "")[-4:]) if ch.get("apiKey") else "",
            })
        self.send_json({
            "ok": True,
            "configured": any(c["configured"] for c in channels),
            "channels": channels,
            "default_model": cfg.get("default_model") or slot.DEFAULT_AGENT_MODEL,
            "system_prompt": cfg.get("system_prompt") or "",
        })

    def handle_agent_config_save(self):
        """保存 Agent 配置。前端 channels[*].apiKey 为空则保留旧值；models 同 img_config 兼容。"""
        length = int(self.headers.get("Content-Length", 0))
        try:
            patch = json.loads(self.rfile.read(length).decode("utf-8")) if length > 0 else {}
        except Exception:
            self.send_json({"ok": False, "error": "JSON 解析失败"}, 400)
            return
        existing = slot.load_agent_config() or {"default_model": slot.DEFAULT_AGENT_MODEL, "system_prompt": "", "channels": []}
        new_channels = slot.merge_channels(existing.get("channels"), patch.get("channels"), "agent_")
        cfg = {
            "default_model": (str(patch.get("default_model") or "")).strip() or existing.get("default_model") or slot.DEFAULT_AGENT_MODEL,
            "system_prompt": str(patch.get("system_prompt") or ""),
            "channels": new_channels,
        }
        ok = slot.save_agent_config(cfg)
        if ok is not True:
            self.send_json({"ok": False, "error": ok}, 500)
            return
        self.send_json({"ok": True, "configured": any(slot.channel_configured(c) for c in new_channels)})

    def handle_agent_test(self):
        """测试 Agent 连通：用最小请求试一次 chat 补全（不强制 stream）。"""
        length = int(self.headers.get("Content-Length", 0))
        try:
            patch = json.loads(self.rfile.read(length).decode("utf-8")) if length > 0 else {}
        except Exception:
            self.send_json({"ok": False, "error": "JSON 解析失败"}, 400)
            return
        cfg = slot.load_agent_config()
        channel = slot.find_agent_channel(cfg, patch.get("channel_id"))  # channel_id=None 时自动 fallback 到第一个已配置渠道
        if (not channel or not channel.get("apiKey")) and patch.get("apiKey") and patch.get("baseUrl"):
            # 允许前端临时透传（设置面板测试按钮用，未落盘的渠道）
            channel = {
                "baseUrl": (patch.get("baseUrl") or "").strip(),
                "apiKey": (patch.get("apiKey") or "").strip(),
                "apiFormat": "openai",
                "models": [],
            }
        if not channel or not channel.get("apiKey"):
            self.send_json({"ok": False, "error": "Agent 未配置渠道：请先在 ⚙ 设置 → Agent 中配置 API Key"}, 400)
            return
        ok, payload = slot.test_agent_channel(channel, patch.get("model"), cfg.get("default_model"))
        if not ok:
            status = payload.get("status", 502)
            self.send_json({"ok": False, "error": payload.get("error", "测试失败")}, status)
            return
        self.send_json({"ok": True, "echo": payload.get("echo", ""), "note": payload.get("note", "")})

    # ---------- 虾格：风格保存 / 确认 ----------
    def handle_style_save(self):
        """虾格：保存新风格 → outputs/styles/<style_id>.json（三要素必填）"""
        try:
            length = int(self.headers.get("Content-Length", 0))
            req = json.loads(self.rfile.read(length).decode("utf-8"))
            sid = str(req.get("style_id", "")).strip()
            if not sid or not re.match(r"^[\w\u4e00-\u9fff-]+$", sid):
                self.send_json({"ok": False, "error": "style_id 非法（仅中文/字母/数字/下划线/连字符）"}, 400); return
            for k in ("style_label", "style_tag", "style_instructions", "avoid_instructions"):
                if not str(req.get(k, "")).strip():
                    self.send_json({"ok": False, "error": f"{k} 不能为空"}, 400); return
            style = {
                "style_id": sid,
                "style_label": str(req.get("style_label", "")),
                "style_tag": str(req.get("style_tag", "")),
                "style_instructions": str(req.get("style_instructions", "")),
                "avoid_instructions": str(req.get("avoid_instructions", "")),
                "recommended_for": str(req.get("recommended_for", "")),
                # ★ v3.4.0-风格库：持久化展示图三件套，供 /api/export-style 导出完整库条目（缺省向后兼容）
                "family": str(req.get("family", "")),
                "keyframe": req.get("keyframe", {}),
                "preview_prompt": str(req.get("preview_prompt", "")),
                "is_preset": False,
                "confirmed_by_user": False,
            }
            styles_dir = os.path.join(PROJECT_ROOT, "outputs", "styles")
            os.makedirs(styles_dir, exist_ok=True)
            path = os.path.join(styles_dir, sid + ".json")
            if os.path.exists(path) and not req.get("overwrite"):
                self.send_json({"ok": False, "error": f"风格 {sid} 已存在，需 overwrite=true"}, 409); return
            with open(path, "w", encoding="utf-8") as f:
                json.dump(style, f, ensure_ascii=False, indent=2)
            log(f"🎨 虾格风格已保存: {sid} → outputs/styles/{sid}.json")
            db_sync_xiage()   # 同步 SQLite，前端刷新可见
            self.send_json({"ok": True, "style_id": sid, "path": f"outputs/styles/{sid}.json"})
        except Exception as e:
            self.send_json({"ok": False, "error": str(e)}, 500)

    def _find_library_entry(self, sid):
        """在 skill styles-library 各回退目录 + 用户级库中找 <sid>.json，返回 (json路径, 目录)。
        目录清单单一来源：style_library_paths.library_dirs()（★ v3.4.0-风格库 真合并，防与 build-data-js 漂移）。"""
        try:
            import sys as _sys
            _here = os.path.dirname(os.path.abspath(__file__))
            for _p in (_here,
                       os.path.expanduser("~/.qwenworkcn/skills/xia-boss/scripts"),
                       os.path.expanduser("~/.qwenworkcn/skills/xia-boss/templates")):
                if _p and _p not in _sys.path:
                    _sys.path.insert(0, _p)
            from style_library_paths import library_dirs
            _skill_dirs, _user_dir = library_dirs()
            dirs = list(_skill_dirs) + [_user_dir]
        except Exception:
            # 兜底：旧项目未同步 style_library_paths.py 时用内置等价清单（与共享模块保持一致）
            dirs = []
            env = os.environ.get("XIA_BOSS_SKILL_DIR", "")
            if env: dirs.append(os.path.join(env, "modules", "xiage-styles", "styles-library"))
            dirs.append(os.path.expanduser("~/.qwenworkcn/skills/xia-boss/modules/xiage-styles/styles-library"))
            dirs.append(os.path.expanduser("~/.workbuddy/skills/xia-boss/modules/xiage-styles/styles-library"))
            dirs.append(os.path.expanduser("~/.qwenworkcn/xiage-style-library"))
        for d in dirs:
            fp = os.path.join(d, sid + ".json")
            if os.path.isfile(fp):
                return fp, d
        return "", ""

    def handle_style_apply_library(self, query):
        """POST /styles/apply-library?style_id=<id>：把挂载库风格拷进项目并确认（★ v3.4.0-风格库）"""
        sid = (query.get("style_id", [""])[0] or "").strip()
        if not sid:
            self.send_json({"ok": False, "error": "style_id 缺失"}, 400); return
        src, sdir = self._find_library_entry(sid)
        if not src:
            self.send_json({"ok": False, "error": f"挂载库中找不到风格 {sid}"}, 404); return
        try:
            entry = json.load(open(src, encoding="utf-8"))
        except Exception as e:
            self.send_json({"ok": False, "error": f"库条目解析失败: {e}"}, 500); return
        styles_dir = os.path.join(PROJECT_ROOT, "outputs", "styles")
        os.makedirs(styles_dir, exist_ok=True)
        with open(os.path.join(styles_dir, sid + ".json"), "w", encoding="utf-8") as f:
            json.dump(entry, f, ensure_ascii=False, indent=2)
        # 预览图拷进项目 assets/styles/<id>.png（仅存在时）
        png = entry.get("preview_image") or (sid + ".png")
        src_png = os.path.join(sdir, png)
        if os.path.isfile(src_png):
            dst_dir = os.path.join(ROOT, "assets", "styles")
            os.makedirs(dst_dir, exist_ok=True)
            shutil.copy2(src_png, os.path.join(dst_dir, sid + ".png"))
        # 确认应用（与 handle_style_confirm 同款：写 pipeline-state + 同步 SQLite）
        ps = {}
        psp = os.path.join(PROJECT_ROOT, "pipeline-state.json")
        if os.path.exists(psp):
            try: ps = json.load(open(psp, encoding="utf-8"))
            except Exception: ps = {}
        ps.setdefault("modules", {})["xiage-styles"] = {
            "status": "confirmed",
            "handoff": f"outputs/styles/{sid}.json",
            "note": f"用户从挂载库应用风格: {sid}（tier={entry.get('tier','skill')}）",
        }
        ps["current"] = "style-confirmed"
        with open(psp, "w", encoding="utf-8") as f:
            json.dump(ps, f, ensure_ascii=False, indent=2)
        db_sync_xiage()
        log(f"🎨 从挂载库应用风格: {sid} → outputs/styles/{sid}.json")
        self.send_json({"ok": True, "style_id": sid, "source": entry.get("tier", "skill")})

    def handle_export_style(self, query):
        """GET /api/export-style?style_id=<id>：把虾格风格打包成可丢进 skill styles-library/ 的 zip
        （★ v3.4.0-风格库：含 <id>.json 库条目 + 预览图 + 定风格图；导出前剥离项目专有词）"""
        import zipfile, io as _bio, glob as _glob
        sid = (query.get("style_id", [""])[0] or "").strip()
        styles_dir = os.path.join(PROJECT_ROOT, "outputs", "styles")
        psp = os.path.join(PROJECT_ROOT, "pipeline-state.json")
        proj_name = ""
        try:
            _ps = json.load(open(psp, encoding="utf-8"))
            proj_name = str(_ps.get("project", ""))
            if not sid:
                _ho = (_ps.get("modules", {}).get("xiage-styles", {}) or {}).get("handoff", "")
                if _ho: sid = os.path.splitext(os.path.basename(_ho))[0]
        except Exception:
            _ps = {}
        if not sid:
            try:
                cd0 = json.load(open(os.path.join(PROJECT_ROOT, "outputs", "creation-direction.json"), encoding="utf-8"))
                sid = cd0.get("style_id", "")
            except Exception: pass
        if not sid:
            _js = sorted(_glob.glob(os.path.join(styles_dir, "*.json")))
            sid = os.path.splitext(os.path.basename(_js[0]))[0] if _js else ""
        spath = os.path.join(styles_dir, sid + ".json") if sid else ""
        if not sid or not os.path.exists(spath):
            self.send_json({"ok": False, "error": f"风格 {sid or '(未找到)'} 不存在于 outputs/styles/"}, 404); return
        try:
            s = json.load(open(spath, encoding="utf-8"))
        except Exception as e:
            self.send_json({"ok": False, "error": f"风格 JSON 解析失败: {e}"}, 500); return
        cd = {}
        try:
            cd = json.load(open(os.path.join(PROJECT_ROOT, "outputs", "creation-direction.json"), encoding="utf-8"))
        except Exception: pass
        entry = {
            "style_id": sid,
            "style_label": s.get("style_label", sid),
            "family": s.get("family", ""),
            "style_tag": s.get("style_tag", ""),
            "style_instructions": s.get("style_instructions", ""),
            "avoid_instructions": s.get("avoid_instructions", ""),
            "visual_references": cd.get("visual_references", s.get("visual_references", [])),
            "tonal_direction": cd.get("tonal_direction", s.get("tonal_direction", "")),
            "keyframe": s.get("keyframe", {}),
            "preview_prompt": s.get("preview_prompt", ""),
            "preview_image": f"{sid}.png",
            "is_library_entry": True,
            "tier": "skill",
            "source": s.get("source", f"项目导出 {datetime.now().strftime('%Y-%m-%d')}"),
            "confirmed_by_user": True,
        }
        # ★ 脱敏校验：项目名命中 → 拒绝导出，提示先通用化 keyframe/figure（禁项目数据最高纪律）
        blob = json.dumps(entry, ensure_ascii=False)
        if proj_name and proj_name in blob:
            self.send_json({"ok": False, "error": f"检测到项目专有词『{proj_name}』未脱敏，请先把 keyframe/figure 通用化再导出"}, 400); return
        buf = _bio.BytesIO()
        files = []
        pv = os.path.join(ROOT, "assets", "styles", f"{sid}.png")
        if os.path.isfile(pv): files.append((pv, f"{sid}.png"))
        kf = sorted(_glob.glob(os.path.join(ROOT, "assets", "styles", "style_keyframe*.png")))
        if kf: files.append((kf[-1], "style_keyframe.png"))
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(f"{sid}.json", json.dumps(entry, ensure_ascii=False, indent=2))
            for fp, arc in files:
                zf.write(fp, arc)
        data = buf.getvalue()
        self.send_response(200)
        self.send_header("Content-Type", "application/zip")
        self.send_header("Content-Disposition", f'attachment; filename="xiage-style-{sid}.zip"')
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        try:
            self.wfile.write(data)
        except Exception:
            pass
        log(f"📦 虾格风格导出: {sid}（含 {len(files)} 张图）")

    def handle_style_confirm(self, query):
        """虾格：确认应用某风格 → 更新 pipeline-state（xiage-styles=confirmed）"""
        sid = query.get("style_id", [""])[0]
        if not sid:
            self.send_json({"ok": False, "error": "style_id 缺失"}, 400); return
        path = os.path.join(PROJECT_ROOT, "outputs", "styles", sid + ".json")
        if not os.path.exists(path):
            self.send_json({"ok": False, "error": f"风格 {sid} 不存在"}, 404); return
        ps = {}
        psp = os.path.join(PROJECT_ROOT, "pipeline-state.json")
        if os.path.exists(psp):
            try: ps = json.load(open(psp, encoding="utf-8"))
            except Exception: ps = {}
        ps.setdefault("modules", {})["xiage-styles"] = {
            "status": "confirmed",
            "handoff": f"outputs/styles/{sid}.json",
            "note": f"用户在虾格页确认风格: {sid}",
        }
        ps["current"] = "style-confirmed"
        with open(psp, "w", encoding="utf-8") as f:
            json.dump(ps, f, ensure_ascii=False, indent=2)
        log(f"🎨 虾格风格确认: {sid}")
        db_sync_xiage()   # 同步 SQLite，前端刷新可见
        self.send_json({"ok": True, "style_id": sid})

    def handle_agent_chat(self):
        """Agent 主入口：POST /agent-chat
        入参：{messages: [{role,content}], model?, stream?, temperature?, max_tokens?, channel_id?, system?}
        - stream=false（默认）：返回完整 JSON
        - stream=true：以 SSE 透传到客户端（text/event-stream, data: [...], data: [DONE]）
        协议：OpenAI Chat Completions，鉴权 Bearer，目标端点 {baseUrl}/chat/completions。
        """
        length = int(self.headers.get("Content-Length", 0))
        try:
            req = json.loads(self.rfile.read(length).decode("utf-8"))
        except Exception:
            self.send_json({"ok": False, "error": "JSON 解析失败"}, 400)
            return
        cfg = slot.load_agent_config()
        channel = slot.find_agent_channel(cfg, req.get("channel_id"))
        if not slot.channel_configured(channel):
            log("❌ Agent 调用被拒：未配置渠道")
            self.send_json({"ok": False, "error": "Agent 未配置 API 渠道：请在 ⚙ 设置 → Agent 标签页中添加渠道"}, 501)
            return
        model = (str(req.get("model") or "")).strip() or cfg.get("default_model") or slot.DEFAULT_AGENT_MODEL
        messages = req.get("messages") or []
        log(f"🤖 Agent 调用: model={model} stream={bool(req.get('stream'))} 消息数={len(messages)} 首条={str(messages[0] if messages else '').replace(chr(10),' ')[:50]}")
        if not isinstance(messages, list) or not messages:
            self.send_json({"ok": False, "error": "messages 不能为空"}, 400)
            return
        ok, resp = slot.agent_chat_completion(
            channel, model, messages,
            system_prompt=req.get("system") if req.get("system") is not None else cfg.get("system_prompt"),
            stream=bool(req.get("stream")),
            temperature=req.get("temperature"), max_tokens=req.get("max_tokens"),
            default_model=cfg.get("default_model"))
        if not ok:
            self.send_json({"ok": False, "error": resp.get("error", "调用失败")}, resp.get("status", 502))
            return
        if not resp["stream"]:
            data = resp["body"]
            self.send_response(200)
            self.send_header("Content-Type", resp.get("content_type", "application/json; charset=utf-8"))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        # 流式：SSE 透传（上游连接对象由插槽返回，此处逐行转发）
        upstream = resp["upstream"]
        try:
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("X-Accel-Buffering", "no")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Connection", "close")
            self.end_headers()
            # SSE 必须逐行透传：urllib 的 read(n) 会等凑满 n 字节或 EOF 才返回，
            # 而 lk888 生成完不立即关闭连接 → read(4096) 会永久阻塞。readline() 读到 \n 即返回，可实时转发。
            total = 0
            while True:
                try:
                    line = upstream.readline()
                except Exception:
                    break
                if not line:
                    break
                total += len(line)
                try:
                    self.wfile.write(line)
                    self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError, OSError):
                    break
            log(f"🤖 Agent 流式完成: model={model} 透传 {total} 字节")
        finally:
            try:
                upstream.close()
            except Exception:
                pass
    def _save_generated_image(self, category, name, img_bytes, ep=1):
        """公共写盘：归档旧图 + 写新图 + mark_ready。返回 (rel_path, fname, hist_path)
        缓存策略（2026-08-19）：若已有同名主图，新文件改用「{name}-{毫秒时间戳}.png」——
        URL 变化，浏览器必取新图，杜绝刷新后命中缓存显示旧图。
        ★ 2026-08-20 分集：ep 参数决定 epNNN 目录（sketch/frame/blocking 按集存储）。"""
        ext = ".png"
        name = os.path.splitext(name)[0].strip()   # 防 name 带扩展名拼出 xxx.png.png
        dir_template = CATEGORY_DIRS[category]
        dir_part = dir_template.replace("epNNN", f"ep{int(ep):03d}")
        rel_dir = os.path.join("assets", dir_part)
        hist_path = None
        fname = f"{name}{ext}"
        target = safe_join(ROOT, rel_dir, fname)
        if os.path.exists(target):
            # 已有同名主图：旧图归档 history/，新图用时间戳文件名（防浏览器缓存）
            hist_path = self.archive_old(rel_dir, fname)
            fname = f"{name}-{int(time.time() * 1000)}{ext}"
            target = safe_join(ROOT, rel_dir, fname)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "wb") as f:
            f.write(img_bytes)
        self.mark_ready(category, fname, rel_dir, hist_path, ep=ep)
        return f"{rel_dir}/{fname}".replace("\\", "/"), fname, hist_path

    def handle_gen_image(self):
        """生图主入口：按渠道协议分叉。
        - up_lk888：异步任务式（/v1/media/generate 建任务 → 轮询 status → 下载 result_url）
        - openai：POST /v1/images/generations（b64_json）；垫图走 /v1/images/edits（multipart）
        - gemini：POST /v1beta/models/{m}:generateContent（inline_data）
        - ark：POST /api/v3/images/generations（JSON 内 image 数组垫图）
        入参：{category, name, prompt, model, size, image_b64, channel_id}
        """
        cfg = slot.load_img_config()
        if not cfg:
            self.send_json({"ok": False, "error": "未配置图片生成 API：请在 ⚙ 设置中添加渠道"}, 501)
            return

        length = int(self.headers.get("Content-Length", 0))
        try:
            req = json.loads(self.rfile.read(length).decode("utf-8"))
        except Exception:
            self.send_json({"ok": False, "error": "JSON 解析失败"}, 400)
            return

        category = req.get("category", "")
        name = req.get("name", "")
        prompt = req.get("prompt", "")
        model = req.get("model", "")
        size = req.get("size", "auto")
        images = req.get("images") or []
        log(f"🖼 收到生图请求: category={category} name={name} model={model} size={size}(→{slot.SIZE_TO_RATIO.get(size, '1:1')}) 垫图数={len(images)}")
        # 兼容旧字段 image_b64（单张）
        if not images and req.get("image_b64"):
            images = [req.get("image_b64")]
        if not isinstance(images, list):
            images = [images]
        images = [str(b) for b in images if b]
        images = images[:9]   # API 上限 9 张
        # 规范化参考图为两套：
        #  - image_datauris: data:image/...;base64,... 完整格式（lk888/ark 要求 data URI 或 URL）
        #  - image_b64s:     纯 base64（gemini inline_data / openai 解码用）
        image_datauris = []
        image_b64s = []
        for it in images:
            s = it.strip()
            if s.startswith("data:"):
                image_datauris.append(s)
                if ";base64," in s:
                    image_b64s.append(s.split(";base64,", 1)[1])
            elif s.startswith("http://") or s.startswith("https://"):
                # 公网 URL：lk888/ark 可直接用；gemini/openai 分支暂无法用 URL，跳过
                image_datauris.append(s)
            else:
                # 旧前端传的裸 base64，按 PNG 补前缀
                image_b64s.append(s)
                image_datauris.append("data:image/png;base64," + s)
        image_b64 = image_b64s[0] if image_b64s else ""
        if category not in CATEGORY_DIRS or not name or not prompt:
            self.send_json({"ok": False, "error": "category/name/prompt 缺失"}, 400)
            return
        # 剥掉扩展名（前端可能传 xxx.png），后续 _save_generated_image 会统一补 .png
        name = os.path.splitext(name)[0].strip()
        # 允许中文/字母数字/·/-/括号（全角半角）/角度符号°：角色名如"角色A(角色B)"、场景视角如"示例场景-45°俯视全景"；不含 / \ 冒号等路径/文件名非法字符
        if not re.match(r"^[\u4e00-\u9fff\w·\-（）()°]+$", name):
            self.send_json({"ok": False, "error": f"非法名称: {name}"}, 400)
            return

        channel = slot.find_channel(cfg, req.get("channel_id"))
        if not channel or not slot.channel_configured(channel):
            self.send_json({"ok": False, "error": "所选渠道未配置 baseUrl/API Key，请在 ⚙ 设置中完善"}, 501)
            return

        # ===== 任务队列：入队（★ 2026-08-20 统一排队上限 60，普通/批量一致；并发 5 由调度器控制）=====
        batch = bool(req.get("batch"))   # ★ 2026-08-19：批量生成标记（批量草图等）
        ep = int(req.get("ep") or 1)     # ★ 2026-08-20 分集：sketch/frame/blocking 按集存储
        task_id, queue_full = GEN_QUEUE.add_task(category, name, model, size, prompt, images,
                                                 req.get("channel_id"), batch=batch, ep=ep)
        if queue_full:
            stats = GEN_QUEUE.stats()
            limit = GEN_QUEUE.MAX_QUEUED
            log(f"⛔ 任务队列已满: running={stats['running']}/{limit} 拒绝 name={name}")
            self.send_json({"ok": False, "error": f"任务队列已满（{stats['running']}/{limit}），请等待…", "queue_full": True, "stats": stats}, 429)
            return

        # ===== 调度器模式：入队即返回，由 _dispatch_loop 按并发 5 调度执行 =====
        log(f"📥 任务已入队: {task_id} name={name} model={model} 队列占用={GEN_QUEUE.stats()['running']}/{GEN_QUEUE.MAX_QUEUED} batch={batch}")
        self.send_json({"ok": True, "task_id": task_id, "queued": True,
                        "category": category, "name": name, "model": model, "size": size,
                        "stats": GEN_QUEUE.stats()})
        return

    # ============================================================
    # ★ 2026-08-23 生视频接口（集成 888 中转平台 海螺 H3 参考生）
    # 与生图独立：长任务（5~60 分钟）不入 GEN_QUEUE 排队；独立任务字典 + 状态机 + 前端轮询
    # ============================================================
    def _save_generated_video(self, ep, idx, seg_idx, video_bytes, shot_num="", module="xiajing"):
        """公共写盘：写 mp4 到 assets/epNNN/videos/。
        ★ 2026-08-24：shot_num 非空 → 单镜视频文件名 shot-{ep}-{shot}.mp4（与故事板段位不冲突）；
                        否则 → storyboard-{ep}-{idx}-{seg_idx}.mp4。
        ★ 2026-09-01：module=tingfeng → assets/tingfeng/ep{ep}/videos/tingfeng-{ep}-{seg_idx}.mp4（听风独立目录）。
        返回 (rel_path, fname) 或 (None, err)"""
        if not video_bytes:
            return None, "视频字节为空"
        ext = ".mp4"
        if module == "tingfeng":
            rel_dir = f"assets/tingfeng/ep{int(ep):03d}/videos"
            fname = f"tingfeng-{int(ep):03d}-{int(seg_idx):03d}{ext}"
        else:
            rel_dir = f"assets/ep{int(ep):03d}/videos"
            if shot_num:
                fname = f"shot-{int(ep):03d}-{str(shot_num).replace('/', '_')}{ext}"
            else:
                fname = f"storyboard-{int(ep):03d}-{int(idx):03d}-{int(seg_idx):03d}{ext}"
        target = safe_join(ROOT, rel_dir, fname)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        try:
            with open(target, "wb") as f:
                f.write(video_bytes)
        except Exception as e:
            return None, f"写盘失败: {e}"
        return f"{rel_dir}/{fname}".replace("\\", "/"), fname

    def _mark_video_ready_in_db(self, ep, idx, seg_idx, rel_path, shot_num="", module="xiajing"):
        """在 SQLite 标记视频完成：
        ★ 2026-08-24：shot_num 非空 → 写回 shot.video（制作页单镜视频位）；
                        否则 → 写回 storyboards[idx].video_segments[seg_idx]（故事板多镜段位）。
        ★ 2026-08-23 加 _DB_WRITE_LOCK：读-改-写整段临界区串行化，避免多个并发视频任务同时
        读旧值→各自改→各自写回→互相覆盖（只剩最后一个生效，前 N-1 个视频资产位丢失）。"""
        try:
            with _DB_WRITE_LOCK:
                _dbd = db_read_all()
                if not _dbd:
                    return False, "数据库为空"
                data = _dbd
                # ★ 2026-09-01 tingfeng 路由：写回 tingfeng.episodes[ep].segments[seg_idx]
                if module == "tingfeng":
                    tf = data.get("tingfeng") or {}
                    target = next((e for e in (tf.get("episodes") or []) if int(e.get("number", 0)) == int(ep)), None)
                    if not target:
                        return False, f"tingfeng 未找到第 {ep} 集"
                    segs = target.get("segments") or []
                    if not (0 <= int(seg_idx) < len(segs)):
                        return False, f"tingfeng 段 {seg_idx} 不存在（共 {len(segs)} 段）"
                    segs[int(seg_idx)]["video"] = rel_path
                    segs[int(seg_idx)]["video_ready"] = True
                    db_upsert("tingfeng", tf)
                    return True, None
                xiajing = data.get("xiajing") or {}
                episodes = xiajing.get("episodes") or []
                target_ep = None
                for _e in episodes:
                    if int(_e.get("number", 0)) == int(ep):
                        target_ep = _e
                        break
                if not target_ep:
                    return False, f"未找到第 {ep} 集"
                # ★ 2026-08-24 单镜视频：写回 shot.video
                if shot_num:
                    shots = target_ep.get("shots") or []
                    s = next((x for x in shots if str(x.get("shot_number", "")) == str(shot_num)), None)
                    if not s:
                        return False, f"未找到镜 {shot_num}（该集共 {len(shots)} 镜）"
                    s["video"] = rel_path
                    s["video_ready"] = True
                    db_upsert("xiajing", xiajing)
                    return True, None
                # ★ 故事板多镜段位写回
                storyboards = target_ep.get("storyboards") or []
                # ★ 修复：按 idx 字段查找（与保存提示词 handler 一致），不能用列表下标——
                # 故事板可能因删除/重排导致 idx 与列表位置不一致（如 idx=3 但列表第 1 位）
                sb = next((s for s in storyboards if int(s.get("idx", -1)) == int(idx)), None)
                if not sb:
                    return False, f"故事板 idx={idx} 不存在（该集共 {len(storyboards)} 张）"
                # ★ 兜底补齐：历史故事板可能根本没有 video_segments 字段（老数据），
                # 或段数不足（前端按 prompts 推断段数渲染，但 DB 里数组为空/偏短）。
                # 不再直接报「段不存在」，而是按 seg_idx 自动 extend 到足够长（空 dict 占位）再写。
                segments = sb.get("video_segments")
                if not isinstance(segments, list):
                    segments = []
                    sb["video_segments"] = segments
                if int(seg_idx) >= len(segments):
                    while len(segments) <= int(seg_idx):
                        segments.append({})
                seg = segments[int(seg_idx)]
                seg["video"] = rel_path
                seg["video_ready"] = True
                db_upsert("xiajing", xiajing)
                return True, None
        except Exception as e:
            return False, f"标记 video_ready 失败: {e}"

    def _execute_video_task(self, task_id):
        """线程函数（由调度器按视频独立并发 3 分派）：跑 slot.generate_video，标记结果。
        ★ 2026-08-23 修复：images 元素是资产相对路径（如 assets/ep001/...png）或 http URL 或 data URI，
          需把本地相对路径读成真实 base64 字节内嵌（888 平台要求 data:image/...;base64,<真实字节>）。
        ★ 2026-08-23 重试：超时/失败且 retry < VIDEO_MAX_RETRY 时，自动重新入队（保留 video_meta/图像/提示词）。"""
        t = None
        with GEN_QUEUE._lock:
            t = GEN_QUEUE._tasks.get(task_id)
            if t:
                t = dict(t)
        if not t:
            return
        vm = t.get("video_meta") or {}
        retry = int(t.get("retry") or 0)
        GEN_QUEUE.mark_running(task_id)
        log(f"▶️ 视频任务开始(第{retry+1}次): {task_id} ep{t['ep']} storyboard{vm.get('idx')} seg{vm.get('seg_idx')} model={t['model']} duration={vm.get('duration')}s ratio={vm.get('aspect_ratio')} resolution={vm.get('resolution')} refs={len(t.get('images') or [])}")
        try:
            cfg = slot.load_img_config() or {}
            channel = slot.find_channel(cfg, t["channel_id"])
            if not channel or not slot.channel_configured(channel):
                self._video_fail_or_retry(task_id, t, vm, "渠道未配置", retry)
                return
            # ★ 规范化垫图：把本地相对路径 → 读真实字节 → data URI（888 要求合法 base64）
            image_b64s, image_datauris = [], []
            for s in (t.get("images") or []):
                s = str(s).strip()
                if not s:
                    continue
                try:
                    if s.startswith("data:"):
                        image_datauris.append(s)
                        if ";base64," in s:
                            image_b64s.append(s.split(";base64,", 1)[1])
                    elif s.startswith("http://") or s.startswith("https://"):
                        image_datauris.append(s)
                    else:
                        # 本地相对路径（assets/...）：读字节 → 真实 base64 内嵌
                        fpath = safe_join(ROOT, s) if not os.path.isabs(s) else s
                        if os.path.isfile(fpath):
                            b = open(fpath, "rb").read()
                            # 888 平台限制 10MB/张；超限跳过该图并告警
                            if len(b) > 10 * 1024 * 1024:
                                log(f"⚠️ 视频参考图超 10MB 跳过: {s} ({len(b)//1024//1024}MB)")
                            else:
                                ext = os.path.splitext(fpath)[1].lower().lstrip(".") or "png"
                                mime = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png",
                                        "webp": "webp", "gif": "gif", "bmp": "bmp"}.get(ext, "png")
                                b64 = base64.b64encode(b).decode("ascii")
                                image_b64s.append(b64)
                                image_datauris.append(f"data:image/{mime};base64,{b64}")
                        else:
                            log(f"⚠️ 视频参考图文件不存在，跳过: {s}")
                except Exception as e:
                    log(f"⚠️ 视频参考图处理失败，跳过: {s} {str(e)[:120]}")
            log(f"🎬 视频任务规范化参考图: {task_id} 有效 {len(image_datauris)} 张")
            video_bytes, err, meta = slot.generate_video(
                channel, t["model"], t["prompt"], image_b64s, image_datauris,
                vm.get("duration", 6), vm.get("aspect_ratio", "adaptive"), vm.get("resolution", "768P"),
                vm.get("video_urls") or [], vm.get("audio_urls") or []
            )
            if err or not video_bytes:
                # 超时/失败 → 重试或终态失败
                self._video_fail_or_retry(task_id, t, vm, str(err or "视频字节为空"), retry)
                return
            rel_path, fname_or_err = self._save_generated_video(
                t["ep"], vm.get("idx", 0), vm.get("seg_idx", 0), video_bytes, vm.get("shot", ""),
                module=vm.get("module", "xiajing")
            )
            if not rel_path:
                self._video_fail_or_retry(task_id, t, vm, str(fname_or_err), retry)
                return
            ok, mark_err = self._mark_video_ready_in_db(t["ep"], vm.get("idx", 0), vm.get("seg_idx", 0), rel_path, vm.get("shot", ""), module=vm.get("module", "xiajing"))
            if not ok:
                # 视频已写盘但 DB 标记失败——仍算成功（文件可用），仅 warning
                log(f"⚠️ 视频任务 DB 标记失败: {task_id} {mark_err}（视频已存 {rel_path}）")
            # ★ 结果存 result 字段（前端 /gen-video-status 读 t.get("result")）
            GEN_QUEUE.mark_done(task_id, True, result=rel_path)
            log(f"✅ 视频任务完成: {task_id} {rel_path} {len(video_bytes)}B")
        except Exception as e:
            self._video_fail_or_retry(task_id, t, vm, str(e), retry)

    def _video_fail_or_retry(self, task_id, t, vm, err_msg, retry):
        """视频任务失败统一处理：retry < VIDEO_MAX_RETRY 则重新入队（保留原参数），否则标记终态失败。"""
        if retry < GEN_QUEUE.VIDEO_MAX_RETRY:
            new_retry = retry + 1
            # 保留原始 video_meta / 图像 / 提示词 / 渠道，重新入队（并发仍受视频独立上限约束）
            # ★ 复用同一 task_id 原地重排（前端只需轮询一个 id，体验更顺）：
            # 把任务状态复位为 queued，递增 retry，调度器会再次取它执行
            requeued = GEN_QUEUE.requeue(task_id, retry=new_retry, error_hint=err_msg)
            if not requeued:
                # 队列满（排队上限 60）：本次放弃重试，退回终态失败
                GEN_QUEUE.mark_done(task_id, False, error=f"重试队列已满，放弃重试: {err_msg[:160]}")
                log(f"❌ 视频任务重试失败(队列满): {task_id} retry={retry} err={err_msg[:160]}")
            else:
                log(f"🔁 视频任务重试入队(原地): {task_id} 第{retry+1}次失败→重排第{new_retry+1}次 原因={err_msg[:140]} 视频并发={GEN_QUEUE.stats()['video_running']}/{GEN_QUEUE.VIDEO_MAX_CONCURRENT}")
        else:
            GEN_QUEUE.mark_done(task_id, False, error=f"重试{retry}次仍失败: {err_msg[:160]}")
            log(f"❌ 视频任务终态失败(已达重试上限): {task_id} retry={retry} err={err_msg[:160]}")

    def handle_gen_video(self):
        """生视频主入口（★ 2026-08-23 集成 888 中转平台）。
        入参：{ep, idx, seg_idx, model, size, prompt, images, channel_id,
               duration(必填4~15), aspect_ratio(选填), resolution(选填)}
        返回：{ok, task_id}，前端轮询 /gen-video-status?task_id= 拿结果
        """
        cfg = slot.load_img_config()
        if not cfg:
            self.send_json({"ok": False, "error": "未配置图片生成 API：请在 ⚙ 设置中添加渠道（视频走同渠道）"}, 501)
            return
        length = int(self.headers.get("Content-Length", 0))
        try:
            req = json.loads(self.rfile.read(length).decode("utf-8"))
        except Exception:
            self.send_json({"ok": False, "error": "JSON 解析失败"}, 400)
            return
        ep = int(req.get("ep") or 1)
        idx = int(req.get("idx") or 0)
        seg_idx = int(req.get("seg_idx") or 0)
        shot_num = str(req.get("shot") or "").strip()   # ★ 2026-08-24 单镜视频：shot_number（非空=单镜模式）
        # ★ 2026-09-01 模块路由：xiajing（默认，兼容旧调用）/ tingfeng（听风电影，写回 episodes[].segments[seg_idx]）
        module = (req.get("module") or "xiajing").strip() or "xiajing"
        model = (req.get("model") or "").strip() or slot.DEFAULT_VIDEO_MODEL
        size = req.get("size", "auto")
        prompt = (req.get("prompt") or "").strip()
        images = req.get("images") or []
        channel_id = req.get("channel_id") or ""
        # 视频参数（带合法值校验）
        try:
            duration = int(req.get("duration") or 6)
        except Exception:
            duration = 6
        if duration not in slot.VIDEO_DURATIONS:
            duration = min(slot.VIDEO_DURATIONS, key=lambda x: abs(x - duration))
        aspect_ratio = req.get("aspect_ratio") or "adaptive"
        if aspect_ratio not in slot.VIDEO_ASPECT_RATIOS:
            aspect_ratio = "adaptive"
        resolution = req.get("resolution") or "768P"
        if resolution not in slot.VIDEO_RESOLUTIONS:
            resolution = "768P"
        # 基础校验
        if not prompt:
            self.send_json({"ok": False, "error": "prompt 缺失"}, 400)
            return
        if not isinstance(images, list):
            images = [images]
        images = [str(b) for b in images if b]
        images = images[:9]   # API 上限 9 张（实际弹窗限制 5 张）
        # 渠道配置校验
        channel = slot.find_channel(cfg, channel_id)
        if not channel or not slot.channel_configured(channel):
            self.send_json({"ok": False, "error": "所选渠道未配置 baseUrl/API Key，请在 ⚙ 设置中完善"}, 501)
            return
        # 视频协议：minimax_h3（MiniMax 官方 H3）优先 / up_lk888（888 中转）回退
        api_format = channel.get("apiFormat") or slot.DEFAULT_PROTOCOL
        if api_format not in ("minimax_h3", "up_lk888"):
            self.send_json({"ok": False, "error": f"当前渠道协议 {api_format} 暂不支持视频生成（已集成：minimax_h3 / up_lk888）"}, 400)
            return
        # 注册任务（★ 2026-08-23 改造：并入 GEN_QUEUE，复用 60 上限 / 视频独立并发 3）
        # ★ 2026-08-24：单镜视频（shot_num 非空）写回 shot.video；多镜写回 storyboards 段位
        is_shot = bool(shot_num)
        if is_shot:
            name = f"单镜视频 ep{ep} 镜{shot_num}"
        elif module == "tingfeng":
            name = f"听风视频 ep{ep} 段{seg_idx}"
        else:
            name = f"视频 ep{ep} 故事板{idx} 段{seg_idx}"
        # ★ 2026-08-24 视频模型分支：【全能参考】可附带 video_urls / audio_urls（最多 3 数组），
        #   【参考生】忽略这两个字段。统一收进 video_meta，复用 _execute_video_task 透传给 generate_video。
        v_urls_raw = req.get("video_urls") or []
        a_urls_raw = req.get("audio_urls") or []
        v_urls = [str(s).strip() for s in v_urls_raw if str(s).strip()][:3]
        a_urls = [str(s).strip() for s in a_urls_raw if str(s).strip()][:3]
        video_meta = {
            "idx": int(idx), "seg_idx": int(seg_idx),
            "module": module,            # ★ 2026-09-01 写回路由：xiajing / tingfeng
            "shot": shot_num,            # ★ 单镜写回用
            "duration": int(duration), "aspect_ratio": aspect_ratio,
            "resolution": resolution,
            "video_urls": v_urls, "audio_urls": a_urls,
        }
        task_id, queue_full = GEN_QUEUE.add_task(
            category="video", name=name, model=model, size=size,
            prompt=prompt, images=images, channel_id=channel_id, ep=ep,
            video_meta=video_meta
        )
        if queue_full:
            self.send_json({"ok": False, "error": f"任务队列已满（{GEN_QUEUE.MAX_QUEUED}），请等待…",
                            "queue_full": True, "stats": GEN_QUEUE.stats()}, 429)
            return
        log(f"📥 视频任务已入队: {task_id} {name} model={model} duration={duration}s ratio={aspect_ratio} resolution={resolution} refs={len(images)} 队列占用={GEN_QUEUE.stats()['running']}/{GEN_QUEUE.MAX_QUEUED} 视频并发={GEN_QUEUE.stats()['video_running']}/{GEN_QUEUE.VIDEO_MAX_CONCURRENT}")
        self.send_json({"ok": True, "task_id": task_id, "queued": True,
                        "ep": ep, "idx": idx, "seg_idx": seg_idx,
                        "model": model, "duration": duration,
                        "aspect_ratio": aspect_ratio, "resolution": resolution,
                        "stats": GEN_QUEUE.stats()})
        return

    def handle_gen_video_status(self, query):
        """GET /gen-video-status?task_id=：返回单个视频任务状态（前端轮询用）"""
        task_id = (query.get("task_id") or [""])[0]
        if not task_id:
            self.send_json({"ok": False, "error": "task_id 缺失"}, 400)
            return
        t = None
        with GEN_QUEUE._lock:
            t = GEN_QUEUE._tasks.get(task_id)
            if t:
                t = dict(t)
        if not t:
            self.send_json({"ok": False, "error": "task_id 不存在或已过期"}, 404)
            return
        if t.get("category") != "video":
            self.send_json({"ok": False, "error": "该 task_id 不是视频任务"}, 400)
            return
        vm = t.get("video_meta") or {}
        out = {
            "ok": True,
            "task_id": t["task_id"],
            "status": t["status"],   # queued | running | success | failed
            "progress": t.get("progress") or "",
            "video": t.get("result") or "",   # ★ 视频路径存于 result（mark_done 写入）
            "error": t.get("error") or "",
            "ep": t.get("ep", 1), "idx": vm.get("idx", 0), "seg_idx": vm.get("seg_idx", 0),
            "retry": int(t.get("retry") or 0),   # ★ 2026-08-23 已尝试次数（前端可显示「第 N 次」）
            "max_retry": GEN_QUEUE.VIDEO_MAX_RETRY,
        }
        if t.get("started_at"):
            out["started_at"] = t["started_at"]
        if t.get("finished_at"):
            out["finished_at"] = t["finished_at"]
        if t.get("started_at") and t.get("finished_at"):
            out["duration_sec"] = round(t["finished_at"] - t["started_at"], 1)
        self.send_json(out)

    def _execute_task(self, task_id):
        """执行单个生图任务（由调度器按并发上限 spawn）。任务状态已在 take_next 置 running。"""
        item = GEN_QUEUE._tasks.get(task_id)   # 直接取任务数据（调度线程持有锁内已返回）
        if not item:
            return
        category, name, model, size = item["category"], item["name"], item["model"], item["size"]
        ep = item.get("ep", 1)           # ★ 2026-08-20 分集
        prompt = item["prompt"]
        channel_id = item["channel_id"]
        # 重建垫图列表（dataUrl → b64；裸 base64 → 补 PNG 前缀）
        image_b64s, image_datauris = [], []
        for s in (item.get("images") or []):
            if s.startswith("data:image"):
                image_b64s.append(s.split(",", 1)[1])
                image_datauris.append(s)
            else:
                image_b64s.append(s)
                image_datauris.append("data:image/png;base64," + s)
        log(f"▶️ 任务开始: {task_id} name={name} model={model} 队列占用={GEN_QUEUE.stats()['running']}/{GEN_QUEUE.MAX_CONCURRENT} 垫图={len(image_b64s)}")
        try:
            cfg = slot.load_img_config() or {}
            channel = slot.find_channel(cfg, channel_id)
            if not channel or not slot.channel_configured(channel):
                GEN_QUEUE.mark_done(task_id, False, error="渠道未配置")
                return
            img_bytes, err, meta = slot.generate_image(channel, model, prompt, image_b64s, image_datauris, size)
            if err:
                GEN_QUEUE.mark_done(task_id, False, error=err)
                log(f"❌ 任务失败: {task_id} name={name} err={str(err)[:200]}")
                return
            rel_path, fname, hist_path = self._save_generated_image(category, name, img_bytes, ep)
            GEN_QUEUE.mark_done(task_id, True, result=rel_path, hist_path=hist_path)
            log(f"✅ 任务完成: {task_id} name={name} 图片={len(img_bytes)}B → {rel_path}")
        except Exception as e:
            GEN_QUEUE.mark_done(task_id, False, error=str(e))
            log(f"❌ 任务异常: {task_id} name={name} err={str(e)[:200]}")

    def _dispatch_loop(self):
        """★ 2026-08-19 调度器：始终只并发执行 MAX_CONCURRENT 个，完成一个自动取下一个。
        ★ 2026-08-23 扩展：category=="video" 的任务分派到 _execute_video_task。"""
        log("🚀 任务调度器已启动")
        while True:
            item = GEN_QUEUE.take_next()
            if item:
                tid = item[0]
                cat = item[1].get("category")
                if cat == "video":
                    t = _threading.Thread(target=self._execute_video_task, args=(tid,), daemon=True)
                else:
                    t = _threading.Thread(target=self._execute_task, args=(tid,), daemon=True)
                t.start()
            else:
                time.sleep(0.3)
    # ---------- 上传 ----------
    def handle_upload(self, query):
        category = query.get("category", [""])[0]
        name = query.get("name", [""])[0]
        ep = int(query.get("ep", ["1"])[0] or 1)   # ★ 2026-08-20 分集：sketch/frame/blocking 按集上传
        if category not in CATEGORY_DIRS or not name:
            self.send_json({"ok": False, "error": "category 或 name 缺失"}, 400)
            return

        # 读取 multipart 或 raw body
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length > 0 else b""
        if not body:
            self.send_json({"ok": False, "error": "空文件"}, 400)
            return

        ext = os.path.splitext(name)[1].lower()
        if ext not in ALLOWED_EXT:
            self.send_json({"ok": False, "error": f"不支持的文件类型 {ext}，允许: png/jpg/jpeg/webp/gif"}, 400)
            return

        # 解析 multipart/form-data（简单实现）
        ctype = self.headers.get("Content-Type", "")
        if ctype.startswith("multipart/form-data"):
            boundary = ctype.split("boundary=")[-1].strip().strip('"')
            parts = body.split(("--" + boundary).encode())
            for part in parts:
                if b'filename="' in part[:2000] and b"\r\n\r\n" in part:
                    data = part.split(b"\r\n\r\n", 1)[1].rstrip(b"\r\n--")
                    body = data
                    break

        # 生成目标路径：category 目录 + 规范化文件名
        dir_template = CATEGORY_DIRS[category]
        dir_part = dir_template.replace("epNNN", f"ep{ep:03d}")   # ★ 2026-08-20 分集

        # 边界防御（先检查原始 name，再 sanitize——顺序不能反，否则穿越特征被替换后绕过）
        if not name or ".." in name or name.startswith("/") or name.startswith("\\") or ":" in name:
            self.send_json({"ok": False, "error": f"非法文件名: {name}"}, 400)
            return
        if not body.strip():
            self.send_json({"ok": False, "error": "文件内容为空"}, 400)
            return

        fname = re.sub(r'[\\/:*?"<>|\s]+', "_", name)
        fname = fname if fname.lower().endswith(tuple(ALLOWED_EXT)) else fname + ext

        rel_dir = os.path.join("assets", dir_part)
        target = safe_join(ROOT, rel_dir, fname)

        # 若已存在同文件：先归档旧图到 history/（时间戳前缀），并记录到 data.js 对应对象 history[]
        hist_path = None
        if os.path.exists(target):
            hist_path = self.archive_old(rel_dir, fname)

        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "wb") as f:
            f.write(body)

        # 更新 data.js：把匹配的 *_ready 置 true（若归档了旧图，历史路径一并写入）
        self.mark_ready(category, fname, rel_dir, hist_path, ep=ep)

        self.send_json({"ok": True, "path": f"{rel_dir}/{fname}".replace("\\", "/"), "file": fname,
                        "hist_path": hist_path})

    # ---------- 归档旧图（上传覆盖前） ----------
    def archive_old(self, rel_dir, fname):
        """把现有同名文件复制到 <dir>/history/<ts>-<fname>，返回相对路径（assets/...）"""
        target = safe_join(ROOT, rel_dir, fname)
        hist_rel = os.path.join(rel_dir, HIST_DIR)
        hist_abs = safe_join(ROOT, hist_rel)
        os.makedirs(hist_abs, exist_ok=True)
        hist_name = f"{int(time.time() * 1000)}-{fname}"
        shutil.copy2(target, os.path.join(hist_abs, hist_name))
        return f"{hist_rel}/{hist_name}".replace("\\", "/")

    # ---------- 历史图设为当前 ----------
    def handle_set_current(self, query):
        category = query.get("category", [""])[0]
        fname = query.get("name", [""])[0]          # 当前主文件名，如 角色A.png
        hist = query.get("hist", [""])[0]           # 历史相对路径，如 assets/characters/history/1712-角色A.png
        if category not in CATEGORY_DIRS or not fname or not hist:
            self.send_json({"ok": False, "error": "category/name/hist 缺失"}, 400)
            return
        if ".." in hist or ".." in fname or fname.startswith("/") or fname.startswith("\\") or ":" in fname:
            self.send_json({"ok": False, "error": "非法参数"}, 400)
            return

        # 历史文件必须存在于 assets 内
        try:
            hist_abs = safe_join(ROOT, hist)
        except ValueError:
            self.send_json({"ok": False, "error": "非法历史路径"}, 400)
            return
        if not os.path.isfile(hist_abs):
            self.send_json({"ok": False, "error": "历史文件不存在"}, 404)
            return

        dir_template = CATEGORY_DIRS[category]
        dir_part = dir_template.replace("epNNN", "ep001")
        rel_dir = os.path.join("assets", dir_part)
        base = os.path.splitext(fname)[0]
        # ★ 新文件名带时间戳：避免浏览器缓存旧图 + 与历史图区分（历史图应用为 名称-<时间戳>.png）
        new_fname = f"{base}-{int(time.time() * 1000)}.png"
        target = safe_join(ROOT, rel_dir, new_fname)

        # 当前图先归档为历史（用旧文件名归档）
        new_hist = None
        old_target = safe_join(ROOT, rel_dir, fname)
        if os.path.exists(old_target):
            new_hist = self.archive_old(rel_dir, fname)

        # 历史图复制为新文件名（当前位）
        os.makedirs(os.path.dirname(target), exist_ok=True)
        shutil.copy2(hist_abs, target)

        # 更新 SQLite：image 指向新文件名 + history 更新（路径统一正斜杠，浏览器 URL 才能加载）
        self.mark_ready(category, fname, rel_dir, new_hist, remove_hist=hist,
                        rename_to=f"{rel_dir}/{new_fname}".replace("\\", "/"))
        self.send_json({"ok": True, "path": f"{rel_dir}/{new_fname}".replace("\\", "/"), "file": new_fname,
                        "hist_path": new_hist})

    # ---------- 更新 data.js 就绪标记 ----------
    def mark_ready(self, category, fname, rel_dir, hist_path=None, remove_hist=None, rename_to=None, ep=None):
        # 数据源已切换为 SQLite(xiaji.db)：读库 → 标记 → 写回
        _dbd = db_read_all()
        if not _dbd:
            return
        data = _dbd
        # 基础名：去掉扩展名 + 一个或多个时间戳后缀（如 角色A-1787xxx-1787xxx.png → 角色A）
        import re as _re
        _TS_RE = _re.compile(r'(?:-\d{13})+$')
        base = _TS_RE.sub('', os.path.splitext(fname)[0])
        # 本次写盘的实际文件名（可能带时间戳）；mark_ready 由生图/上传调用时 fname 即最新文件名
        cur_fname = fname
        changed = False

        def apply(obj, img_key="image", extra_names=()):
            nonlocal changed
            obj_base = os.path.basename(obj.get(img_key) or "")
            obj_clean = _TS_RE.sub('', os.path.splitext(obj_base)[0])
            # ★ 2026-08-19 修复：image 为空（新资产首次生成，如「多角色群像」群像）时，
            #   按对象 name 字段匹配兜底（身份图支持「角色名-身份名」组合，extra_names 传入）
            obj_name = str(obj.get("name") or "")
            if obj_clean == base or (not obj_clean and (base == obj_name or base in extra_names)):
                if rename_to:
                    obj[img_key] = rename_to   # ★ set-current：image 指向新文件名（带时间戳）
                else:
                    obj[img_key] = f"{rel_dir}/{cur_fname}".replace("\\", "/")  # ★ 生图/上传：image 指向最新文件名
                obj[{"sketch": "sketch_ready", "frame": "frame_ready",
                     "audio": "audio_ready", "video": "video_ready"}.get(category, "image_ready")] = True
                obj.setdefault("history", [])
                if hist_path and hist_path not in obj["history"]:
                    obj["history"].insert(0, hist_path)   # 最新在前
                if remove_hist and remove_hist in obj["history"]:
                    obj["history"].remove(remove_hist)
                changed = True

        if category == "character":
            for c in data.get("xiatang", {}).get("characters", []):
                apply(c)
                for idn in c.get("identities", []):
                    # 身份图首次生成（无图）时前端传「角色名-身份名」，此处传入组合名兜底匹配
                    apply(idn, extra_names=(f"{c.get('name')}-{idn.get('name')}",))
                    # ★ 2026-08-21 四视图角色卡：name=「角色名-身份id-sheet」→ 写入 idn.sheet_image/sheet_ready（历史独立存 sheet_history，与定妆照 history 互不干扰）
                    if base == f"{c.get('name')}-{idn.get('identity_id')}-sheet":
                        if rename_to:
                            idn["sheet_image"] = rename_to
                        else:
                            idn["sheet_image"] = f"{rel_dir}/{cur_fname}".replace("\\", "/")
                        idn["sheet_ready"] = True
                        idn.setdefault("sheet_history", [])
                        if hist_path and hist_path not in idn["sheet_history"]:
                            idn["sheet_history"].insert(0, hist_path)
                        if remove_hist and remove_hist in idn["sheet_history"]:
                            idn["sheet_history"].remove(remove_hist)
                        changed = True
        elif category == "identity":
            # ★ 2026-08-21 身份定妆照：遍历 characters.identities 按 base 匹配（name 形如「角色名-身份id」）
            for c in data.get("xiatang", {}).get("characters", []):
                for idn in c.get("identities", []):
                    apply(idn, extra_names=(f"{c.get('name')}-{idn.get('name')}",))
        elif category == "scene":
            for s in data.get("xiatang", {}).get("scenes", []):
                apply(s)
                # ★ 2026-08-20 多视角：name=「场景名-视角」（正面/左侧/右侧/背面/斜侧/俯视/45°俯视全景）→ 写入 s.views
                #   （视角重生成**不写 history**——用户 2026-08-20 拍板：视角图是派生图，不进历史）
                for _view in ("正面", "左侧", "右侧", "背面", "斜侧", "俯视", "45°俯视全景"):
                    if base == f"{s.get('name')}-{_view}":
                        s.setdefault("views", {})[_view] = f"{rel_dir}/{cur_fname}".replace("\\", "/")
                        s.setdefault("views_ready", {})[_view] = True
                        changed = True
                        break
                # ★ 2026-08-20 上帝视角：平面布局（引用正面/背面/45°三图）→ s.plan；线稿（引用平面布局）→ s.plan_sketch（均不写 history）
                if base == f"{s.get('name')}-平面布局":
                    s["plan"] = f"{rel_dir}/{cur_fname}".replace("\\", "/")
                    s["plan_ready"] = True
                    changed = True
                elif base == f"{s.get('name')}-线稿":
                    s["plan_sketch"] = f"{rel_dir}/{cur_fname}".replace("\\", "/")
                    s["plan_sketch_ready"] = True
                    changed = True
                # ★ 2026-08-22 视距推拉/航拍：name=「场景名-源标签-前移X米/后移X米/航拍系」→ s.dists[源标签|视距]（不写 history）
                #   （前端 markReadyInMemory 只更新内存，必须在此写 SQLite，否则刷新丢——用户反馈）
                #   ★ 2026-09-01 扩展航拍系：航拍/45°航拍/高航拍/45°高航拍
                _dm = re.match(r"^(.*?)-([^-]+)-((?:前移|后移)\d+米|(?:45°)?高?航拍)$", base)
                if _dm and _dm.group(1) == s.get("name"):
                    _dk = f"{_dm.group(2)}|{_dm.group(3)}"
                    s.setdefault("dists", {})[_dk] = f"{rel_dir}/{cur_fname}".replace("\\", "/")
                    s.setdefault("dists_ready", {})[_dk] = True
                    changed = True
        elif category == "prop":
            for p in data.get("xiatang", {}).get("props", []):
                apply(p)
        elif category == "key_scene":
            # ★ 2026-08-21 关键场景素材（画面素材，非资产）：按 name 匹配 xiatang.key_scenes
            for k in data.get("xiatang", {}).get("key_scenes", []):
                apply(k)
        elif category == "space_map":
            # ★ 2026-08-31 空间拓扑图（按集单张）：写 xiajing episodes[ep].space_map_image/space_map_ready
            # ★ 2026-09-10 3.5.14 新增按场：name=xj-space-map-{ep}-{idx} → 写 space_maps[idx].image/ready
            #   （原缺口：虾镜只有按集单数形态，每场一张的拓扑图无处回填 → 用户无处上传、D2 长期红灯）
            _xjm = _re.match(r'^xj-space-map-(\d+)-(\d+)$', base)
            for _e in data.get("xiajing", {}).get("episodes", []):
                if _xjm and int(_e.get("number", 0)) == int(_xjm.group(1)):
                    _m0 = _xj_space_map_at(_e, int(_xjm.group(2)))
                    _m0["image"] = f"{rel_dir}/{cur_fname}".replace("\\", "/")
                    _m0["ready"] = True
                    _e.setdefault("history", [])
                    if hist_path and hist_path not in _e["history"]:
                        _e["history"].insert(0, hist_path)
                    changed = True
                    _xj_backfill_space_maps(_xjm.group(1), int(_xjm.group(2)),
                                            f"{rel_dir}/{cur_fname}".replace("\\", "/"))
                    continue
                if int(_e.get("number", 0)) == int(ep or 1):
                    _e["space_map_image"] = f"{rel_dir}/{cur_fname}".replace("\\", "/")
                    _e["space_map_ready"] = True
                    _e.setdefault("history", [])
                    if hist_path and hist_path not in _e["history"]:
                        _e["history"].insert(0, hist_path)
                    if remove_hist and remove_hist in _e["history"]:
                        _e["history"].remove(remove_hist)
                    changed = True
        elif category == "tingfeng":
            # ★ 2026-09-01 听风电影故事板（独立模块，与虾镜完全隔离）：name=tingfeng-{ep}-{idx} → 写 tingfeng.episodes[ep].storyboards[idx]
            _m = _re.match(r'^tingfeng-(\d+)-(\d+)$', base)
            for _e in data.get("tingfeng", {}).get("episodes", []):
                if _m and int(_e.get("number", 0)) == int(_m.group(1)):
                    _sbs = _e.setdefault("storyboards", [])
                    _sb = next((s for s in _sbs if int(s.get("idx", -1)) == int(_m.group(2))), None)
                    if not _sb:
                        _sb = {"idx": int(_m.group(2))}; _sbs.append(_sb)
                    _sb["image"] = f"{rel_dir}/{cur_fname}".replace("\\", "/")
                    _sb["ready"] = True
                    changed = True
        elif category == "tf_space_map":
            # ★ 2026-09-04 听风空间拓扑图按场集合（每场一张）：name=tf-space-map-{ep}-{idx} → 写 space_maps[idx].image/ready；
            #   旧 name=tf-space-map-{ep}（无 idx）兼容写 space_map_image/ready（旧项目数据原样不动）
            _tfe = _re.match(r'^tf-space-map-(\d+)$', base)
            _tfm = _re.match(r'^tf-space-map-(\d+)-(\d+)$', base)
            for _te in data.get("tingfeng", {}).get("episodes", []):
                if _tfm and int(_te.get("number", 0)) == int(_tfm.group(1)):
                    _m0 = _tf_space_map_at(_te, int(_tfm.group(2)))
                    _m0["image"] = f"{rel_dir}/{cur_fname}".replace("\\", "/")
                    _m0["ready"] = True
                    changed = True
                elif _tfe and int(_te.get("number", 0)) == int(_tfe.group(1)):
                    _te["space_map_image"] = f"{rel_dir}/{cur_fname}".replace("\\", "/")
                    _te["space_map_ready"] = True
                    changed = True
        elif category == "storyboard":
            # ★ 2026-08-22 故事板多张：name=story-{ep}-{idx} → 写 ep.storyboards[idx]（9 镜/张分组）；
            #   旧 name=story-{ep}（无 idx）兼容写 storyboard_image（按集单张）
            _sm = _re.match(r"^story-(\d+)-(\d+)$", base)
            for _e in data.get("xiajing", {}).get("episodes", []):
                if ep is not None and _e.get("number") != ep:
                    continue
                if _sm:
                    _sbs = _e.setdefault("storyboards", [])
                    _sb = next((s for s in _sbs if s.get("idx") == int(_sm.group(2))), None)
                    if _sb is None:
                        _sb = {"idx": int(_sm.group(2)), "image": "", "ready": False, "history": []}
                        _sbs.append(_sb)
                    if rename_to:
                        _sb["image"] = rename_to
                    else:
                        _sb["image"] = f"{rel_dir}/{cur_fname}".replace("\\", "/")
                    _sb["ready"] = True
                    _sb.setdefault("history", [])
                    if hist_path and hist_path not in _sb["history"]:
                        _sb["history"].insert(0, hist_path)
                    if remove_hist and remove_hist in _sb["history"]:
                        _sb["history"].remove(remove_hist)
                    changed = True
                else:
                    _e["storyboard_image"] = f"{rel_dir}/{cur_fname}".replace("\\", "/")
                    _e["storyboard_ready"] = True
                    _e.setdefault("history", [])
                    if hist_path and hist_path not in _e["history"]:
                        _e["history"].insert(0, hist_path)
                    if remove_hist and remove_hist in _e["history"]:
                        _e["history"].remove(remove_hist)
                    changed = True
        elif category in ("sketch", "frame", "blocking", "firstframe", "tailframe"):
            img_key = CUR_IMG_KEY[category]
            for _e in data.get("xiajing", {}).get("episodes", []):
                if ep is not None and _e.get("number") != ep:   # ★ 2026-08-20 分集：只匹配指定集
                    continue
                for b in _e.get("beats", []):
                    # ★ 按 beat_number 匹配（name 形如 beat1/beat2...），不依赖 sketch_image 字段存在
                    bn = base.replace("beat", "", 1)
                    if str(b.get("beat_number", "")) == bn:
                        b[img_key] = f"{rel_dir}/{cur_fname}".replace("\\", "/")   # ★ 指向最新文件名（带时间戳）
                        b[READY_KEY[category]] = True
                        b.setdefault("history", [])
                        if hist_path and hist_path not in b["history"]:
                            b["history"].insert(0, hist_path)
                        if remove_hist and remove_hist in b["history"]:
                            b["history"].remove(remove_hist)
                        changed = True
                for s in _e.get("shots", []):   # ★ 2026-08-21 新版 shots 结构（name 形如 shot1/shot2...）
                    sn = base.replace("shot", "", 1)
                    if str(s.get("shot_number", "")) == sn:
                        s[img_key] = f"{rel_dir}/{cur_fname}".replace("\\", "/")
                        s[READY_KEY[category]] = True
                        s.setdefault("history", [])
                        if hist_path and hist_path not in s["history"]:
                            s["history"].insert(0, hist_path)
                        if remove_hist and remove_hist in s["history"]:
                            s["history"].remove(remove_hist)
                        changed = True
        elif category == "video":
            for _e in data.get("xiajing", {}).get("episodes", []):
                if ep is not None and _e.get("number") != ep:
                    continue
                for b in _e.get("beats", []):
                    img = "assets/ep%03d/videos/beat%s.mp4" % (_e.get("number", 1), b.get("beat_number", 0))
                    if os.path.basename(img or "") == fname:
                        b["video_ready"] = True
                        b.setdefault("history", [])
                        if hist_path and hist_path not in b["history"]:
                            b["history"].insert(0, hist_path)
                        if remove_hist and remove_hist in b["history"]:
                            b["history"].remove(remove_hist)
                        changed = True
                for s in _e.get("shots", []):   # ★ 2026-08-21 新版 shots 结构
                    img = "assets/ep%03d/videos/shot%s.mp4" % (_e.get("number", 1), s.get("shot_number", 0))
                    if os.path.basename(img or "") == fname:
                        s["video_ready"] = True
                        s["video"] = f"assets/ep{_e.get('number', 1):03d}/videos/{fname}"
                        s.setdefault("history", [])
                        if hist_path and hist_path not in s["history"]:
                            s["history"].insert(0, hist_path)
                        if remove_hist and remove_hist in s["history"]:
                            s["history"].remove(remove_hist)
                        changed = True

        if changed:
            if "xiatang" in data:
                db_upsert("xiatang", data["xiatang"])
            if "xiajing" in data:
                db_upsert("xiajing", data["xiajing"])
            # ★ 2026-09-01 补 tingfeng 落库（漏写导致听风拓扑图/故事板图生成后 db 不更新——§6.1 成对规则）
            if "tingfeng" in data:
                db_upsert("tingfeng", data["tingfeng"])

        # ★ 全剧定风格图：style 类生成后重算 keyframe（mark_ready 无 style 分支，需重扫 assets/styles）
        if category == "style":
            try:
                db_sync_xiage()
            except Exception:
                pass

    # ---------- JSON 响应 ----------
    def send_json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    # ★ 2026-08-22 启动自愈：把磁盘编辑稿（shots.edited.json）同步进 SQLite——分镜编辑重启后不丢
    try:
        _dbd0 = db_read_all()
        if _dbd0:
            _eps0 = _dbd0.get("xiajing", {}).get("episodes", [])
            _changed0 = False
            for _ep0 in _eps0:
                _ed0 = f"ep{_ep0.get('number', 0):03d}"
                _p0 = os.path.join(ROOT, "..", "outputs", "xiajing", _ed0, "shots.edited.json")
                if os.path.exists(_p0):
                    try:
                        _d0 = json.load(open(_p0, encoding="utf-8"))
                        _s0 = _d0.get("shots") if isinstance(_d0, dict) else _d0
                        if isinstance(_s0, list) and _s0 and _ep0.get("edited_shots") != _s0:
                            _ep0["edited_shots"] = _s0
                            _changed0 = True
                    except Exception:
                        pass
            if _changed0:
                db_upsert("xiajing", _dbd0["xiajing"])
                log("↺ 已从磁盘恢复编辑稿（分镜编辑重启保留）")
    except Exception as _e0:
        log(f"⚠️ 编辑稿自愈失败: {_e0}")
    # 用 ThreadingHTTPServer，多生图请求并发处理（一个生图 1-2 分钟，不阻塞其他请求）
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    # ★ 2026-08-19：启动任务调度器（并发 5 执行，批量任务排队等待）。
    #   用 object.__new__ 创建未初始化实例（跳过 __init__ 的请求参数），方法内部只用全局变量
    _dispatch_inst = object.__new__(Handler)
    _threading.Thread(target=_dispatch_inst._dispatch_loop, daemon=True).start()
    print(f"{{项目名}}已启动: http://127.0.0.1:{PORT}")
    print(f"项目目录: {ROOT}")
    print(f"日志文件: {LOG_PATH}（生图/Agent 关键事件都会写入这里）")
    print("按 Ctrl+C 停止")
    log(f"🚀 项目台启动: http://127.0.0.1:{PORT} 目录={ROOT} 端口={PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止")
        server.server_close()
