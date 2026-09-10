# -*- coding: utf-8 -*-
"""从现有产出文件组装 project/data.js（HTML 项目管理台数据层）
用法: python build-data-js.py <项目根目录>
"""
import json, re, os, datetime, sys, shutil, glob
try:
    import sqlite3
except ImportError:
    sqlite3 = None

BASE = sys.argv[1] if len(sys.argv) > 1 else os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))

# ---------- 同步虾格预设到项目（风格 json + 预览图，仅缺失时复制；不覆盖项目已确认内容） ----------
def sync_xiage_presets(base):
    """把虾格模块 presets/ 的风格 json+png 同步到项目：
    json → <项目根>/outputs/styles/；png → <项目根>/project/assets/styles/
    仅当目标不存在时复制（新项目初始化自动带风格库与预览图）。
    回退链：XIA_BOSS_SKILL_DIR 环境变量 → 本机 xia-boss 包 modules/ → 外部独立安装 xiage-styles。"""
    cands = []
    env = os.environ.get("XIA_BOSS_SKILL_DIR", "")
    if env:
        cands.append(os.path.join(env, "modules", "xiage-styles", "presets"))
    cands.append(os.path.expanduser("~/.workbuddy/skills/xia-boss/modules/xiage-styles/presets"))
    cands.append(os.path.expanduser("~/.workbuddy/skills/xiage-styles/presets"))
    xg = next((c for c in cands if os.path.isdir(c)), "")
    if not xg:
        return 0
    cnt = 0
    for src in sorted([f for f in os.listdir(xg) if f.endswith(".json")]):
        dst = os.path.join(base, "outputs", "styles", src)
        if not os.path.exists(dst):
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(os.path.join(xg, src), dst); cnt += 1
    for src in sorted([f for f in os.listdir(xg) if f.endswith(".png")]):
        dst = os.path.join(base, "project", "assets", "styles", src)
        if not os.path.exists(dst):
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(os.path.join(xg, src), dst); cnt += 1
    return cnt

_synced = 0  # ★ 虾格预设库已废弃：不再把 presets 同步进项目 outputs/styles（每次按剧情新做风格）
if _synced:
    print(f"[xiage] 已同步虾格预设 {_synced} 个文件到项目")

# ---------- 挂载风格库（★ v3.4.0-风格库：skill 种子层 + 用户级库合并，供虾格 Tab 候选；只读不污染 outputs/styles） ----------
def load_style_library():
    """扫 skill styles-library/*.json + 用户级 ~/.qwenworkcn/xiage-style-library/*.json，
    按 style_id 合并（用户层覆盖 skill 层）→ 预览图拷进项目 assets/styles/library/ 供前端显示。
    只读、不写项目 outputs/styles（不动当前风格权威链）。回退链同 sync_xiage_presets。"""
    # 目录清单单一来源：style_library_paths.library_dirs()（★ v3.4.0-风格库 真合并，防与 server 漂移）
    try:
        import sys as _sys
        _here = os.path.dirname(os.path.abspath(__file__))
        for _p in (_here,
                   os.path.expanduser("~/.qwenworkcn/skills/xia-boss/scripts"),
                   os.path.expanduser("~/.qwenworkcn/skills/xia-boss/templates")):
            if _p and _p not in _sys.path:
                _sys.path.insert(0, _p)
        from style_library_paths import library_dirs
        skill_dirs, user_dir = library_dirs()
    except Exception as _e:
        print(f"[xiage] ⚠ 未找到 style_library_paths.py（旧项目未同步），跳过挂载库加载: {_e}")
        return []
    merged = {}
    for d in skill_dirs + [user_dir]:
        if not os.path.isdir(d):
            continue
        tier = "user" if os.path.abspath(d) == os.path.abspath(user_dir) else "skill"
        for fp in sorted(glob.glob(os.path.join(d, "*.json"))):
            try:
                e = json.load(open(fp, encoding="utf-8"))
            except Exception:
                continue
            sid = e.get("style_id") or os.path.splitext(os.path.basename(fp))[0]
            if not sid:
                continue
            e.setdefault("style_id", sid)
            e["_tier"], e["_dir"] = tier, d
            merged[sid] = e   # 后到的 user 覆盖 skill
    out = []
    for sid, e in sorted(merged.items()):
        png = e.get("preview_image") or (sid + ".png")
        src_png = os.path.join(e["_dir"], png)
        dst_png = os.path.join(BASE, "project", "assets", "styles", "library", f"{sid}.png")
        ready = False
        if os.path.exists(src_png):
            os.makedirs(os.path.dirname(dst_png), exist_ok=True)
            if not os.path.exists(dst_png):
                shutil.copy2(src_png, dst_png)
            ready = True
        out.append({
            "style_id": sid,
            "style_label": e.get("style_label", ""),
            "family": e.get("family", ""),
            "style_tag": e.get("style_tag", ""),
            "style_instructions": e.get("style_instructions", ""),
            "avoid_instructions": e.get("avoid_instructions", ""),
            "tonal_direction": e.get("tonal_direction", ""),
            "visual_references": e.get("visual_references", []),
            "keyframe": e.get("keyframe", {}),
            "preview_prompt": e.get("preview_prompt", ""),
            "image": f"assets/styles/library/{sid}.png",
            "image_ready": ready,
            "tier": e.get("tier", e.get("_tier", "skill")),
            "source": e.get("source", ""),
        })
    return out

_style_library = load_style_library()
if _style_library:
    print(f"[xiage] 挂载风格库加载 {len(_style_library)} 个风格（skill 种子 + 用户级合并）")

# ---------- 读取产出（扫描所有 ep，支持多集） ----------
try:
    ingest = json.load(open(os.path.join(BASE, "outputs/ingest/ingest-result.json"), encoding="utf-8"))
except (FileNotFoundError, json.JSONDecodeError):
    # ★ 大纲入口流程：虾剧先于虾料，成稿剧本尚未被虾料摄入时给安全空默认值（前端按空渲染，不 crash）
    print("[xialiao] outputs/ingest/ingest-result.json 不存在（虾料未运行），使用空默认——虾剧成稿仍会入库")
    ingest = {"format_check": {}, "chapters": [], "scene_blocks": [], "total_chars": 0,
              "billable_chars": 0, "spine_template": "",
              "knowledge_graph": {"node_count": 0, "edge_count": 0, "nodes": [], "edges": []}}
# ★ 2026-08-19 数据契约校验：scene_blocks 必须是数组（前端 renderXialiao 用 .map 遍历）；
# 曾误写成计数数字导致虾料页 TypeError: (x.scene_blocks||[]).map is not a function
if not isinstance(ingest.get("scene_blocks"), list):
    print("[xialiao] ⚠ scene_blocks 不是数组（契约要求 list[{episode,scene,location,time_of_day,interior_exterior,header_line,dialogue_lines,action_lines,characters}]），已置空避免前端崩溃；请检查 outputs/ingest/ingest-result.json")
    ingest["scene_blocks"] = []
try:
    registry = json.load(open(os.path.join(BASE, "outputs/xiatang/assets-registry.json"), encoding="utf-8"))
except (FileNotFoundError, json.JSONDecodeError):
    # ★ 大纲入口流程：虾剧先于虾塘，资产库未建时给安全空默认值（前端按空列表渲染，不 crash）
    registry = {"characters": [], "scenes": [], "props": [], "props_merged_into_characters": []}
# 风格文件：优先 pipeline-state.json 的 xiage-styles.handoff（用户确认的定稿），否则自动扫描 styles 目录（不硬编码具体风格）
# _all_styles = outputs/styles/ 下全部风格文件（供 data.js 的 xiage.styles 列表，HTML 虾格页展示用）
_style_path = None
_all_styles = []
_ps_path2 = os.path.join(BASE, "pipeline-state.json")
if os.path.exists(_ps_path2):
    try:
        _ps2 = json.load(open(_ps_path2, encoding="utf-8"))
        _ho = (_ps2.get("modules", {}).get("xiage-styles", {}) or {}).get("handoff", "")
        # 只接受指向 styles JSON 的 handoff（旧格式 handoff-xiage.md 会跳过，走扫描兜底）
        if _ho and str(_ho).endswith(".json"):
            _cand = os.path.join(BASE, str(_ho))
            if os.path.exists(_cand):
                _style_path = _cand
    except Exception:
        pass
if not _style_path:
    # ★ 权威源优先：creation-direction.json 的 style_id（虾格三步向导用户拍板结果），防止字母序兜底选错
    _cd_path = os.path.join(BASE, "outputs", "creation-direction.json")
    if os.path.exists(_cd_path):
        try:
            _cd = json.load(open(_cd_path, encoding="utf-8"))
            _sid = _cd.get("style_id", "")
            if _sid:
                _cand2 = os.path.join(BASE, "outputs", "styles", f"{_sid}.json")
                if os.path.exists(_cand2):
                    _style_path = _cand2
        except Exception:
            pass
if not _style_path:
    _style_files = [f for f in sorted(os.listdir(os.path.join(BASE, "outputs/styles"))) if f.endswith(".json")]
    if _style_files:
        _style_path = os.path.join(BASE, "outputs/styles", _style_files[0])
if _style_path:
    style = json.load(open(_style_path, encoding="utf-8"))
else:
    style = {}
# 全部风格（供虾格页列表）：按文件名排序读全部 json
_style_dir = os.path.join(BASE, "outputs/styles")
if os.path.isdir(_style_dir):
    for _sf in sorted(os.listdir(_style_dir)):
        if _sf.endswith(".json"):
            try:
                _all_styles.append(json.load(open(os.path.join(_style_dir, _sf), encoding="utf-8")))
            except Exception:
                pass
try:
    asset_prompts_md = open(os.path.join(BASE, "outputs/xiatang/asset-prompts.md"), encoding="utf-8").read()
except FileNotFoundError:
    # ★ 大纲入口流程：虾塘资产提示词未生成时为空（不影响 xiaju/ingest/world 已入库）
    asset_prompts_md = ""

# 世界观与知识图谱（权威源 outputs/world.json，取自 docs；存在则覆盖 ingest 默认）
world_data = None
_wp = os.path.join(BASE, "outputs", "world.json")
if os.path.exists(_wp):
    world_data = json.load(open(_wp, encoding="utf-8"))

# ★ 创作方向（三步向导产出：视觉参考/影片基调）；存在则读取，缺失则空
creation_dir = None
_cd_path = os.path.join(BASE, "outputs", "creation-direction.json")
if os.path.exists(_cd_path):
    try:
        creation_dir = json.load(open(_cd_path, encoding="utf-8"))
    except Exception:
        creation_dir = None

# ★ 关键场景素材（2026-08-21：独立资产类别，可含人物，素材定位）
key_scenes = []
_ks_dir = os.path.join(BASE, "outputs", "key-scenes")
if os.path.isdir(_ks_dir):
    for _ksf in sorted(os.listdir(_ks_dir)):
        if _ksf.endswith(".json"):
            try:
                key_scenes.append(json.load(open(os.path.join(_ks_dir, _ksf), encoding="utf-8")))
            except Exception:
                pass

PROJECT_DIR = os.path.join(BASE, "project")
def asset_exists(*rel):
    return os.path.exists(os.path.join(PROJECT_DIR, "assets", *rel))

def latest_versioned(rel_dir, base_name):
    """assets/<rel_dir>/ 下 {base_name}-<数字>.png 最新文件（set-current 换名生成的版本图）；
    无版本图则返回 {base_name}.png。"""
    d = os.path.join(PROJECT_DIR, "assets", rel_dir)
    if not os.path.isdir(d):
        return base_name + ".png"
    pat = re.compile(r"^" + re.escape(base_name) + r"-\d+\.png$")
    cands = [f for f in os.listdir(d) if pat.match(f)]
    if cands:
        return sorted(cands)[-1]
    return base_name + ".png"


def keyframe_info():
    """全剧定风格图 assets/styles/style_keyframe*.png 最新一张 → (相对路径, 是否存在)。"""
    fn = latest_versioned("styles", "style_keyframe")
    ok = asset_exists("styles", fn)
    return (f"assets/styles/{fn}" if ok else "", ok)


def asset_history(rel_dir, fname):
    """扫描 assets/<rel_dir>/history/ 下归档文件，返回匹配 fname 的历史相对路径列表。
    命名约定：<时间戳>-<原文件名>（如 1787062663232-角色名.png）；全量重建不丢历史。"""
    hdir = os.path.join(PROJECT_DIR, "assets", rel_dir, "history")
    if not os.path.isdir(hdir):
        return []
    hist = []
    for f in sorted(os.listdir(hdir)):
        if f.endswith("-" + fname):
            hist.append(f"assets/{rel_dir}/history/{f}")
    return hist

_xj_dir = os.path.join(BASE, "outputs/xiajing")
ep_dirs = sorted([d for d in os.listdir(_xj_dir) if re.match(r"^ep\d+$", d)]) if os.path.isdir(_xj_dir) else []
all_episodes = []
for ed in ep_dirs:
    ep_num = int(ed.replace("ep", ""))
    # ★ 2026-08-21 数据契约：优先 shots.json（新版 11 字段+制作产物+副本），兼容 beats.json（旧版映射）
    _shots_path = os.path.join(BASE, "outputs/xiajing", ed, "shots.json")
    _ep_shots = []
    if os.path.exists(_shots_path):
        try:
            _sd = json.load(open(_shots_path, encoding="utf-8"))
            _ep_shots = _sd.get("shots", []) if isinstance(_sd, dict) else _sd
            _title = (_sd.get("episode_title") if isinstance(_sd, dict) else "") or f"第{ep_num}集"
            _tone = (_sd.get("tone_palette", {}) if isinstance(_sd, dict) else {})
            _status = (_sd.get("episode_status", {}) if isinstance(_sd, dict) else {})
            _sb_img = (_sd.get("storyboard_image", "") if isinstance(_sd, dict) else "")
            _sb_rd = bool((_sd.get("storyboard_ready", False) if isinstance(_sd, dict) else False))
            # ★ 2026-08-22 SC 编号 → 场景资产名映射（shots.json 顶层 scene_map）；每镜补 scene_name（制作页显示资产名）
            _scene_map = (_sd.get("scene_map", {}) if isinstance(_sd, dict) else {}) or {}
            # ★ 2026-08-22 CH 编号 → 角色资产名映射（shots.json 顶层 ch_map；角色引用解析 CH-01/02 等编号用）
            _ch_map = (_sd.get("ch_map", {}) if isinstance(_sd, dict) else {}) or {}
            # ★ 2026-09-08 战斗段登记透传（虾镜纪律 17·方案 A）：shots.json 顶层 battle_segments → 项目台可见
            _battle_segments = (_sd.get("battle_segments", []) if isinstance(_sd, dict) else []) or []
            # ★ 2026-09-09 同源段稿透传：build_prompts 产的每板 ≤15s 段生视频提示词 + 分段配置（离线为唯一源）
            _sbvps = (_sd.get("storyboard_video_prompts", []) if isinstance(_sd, dict) else []) or []
            _sbcfg = (_sd.get("storyboard_config", {}) if isinstance(_sd, dict) else {}) or {}
            # ★ 2026-09-09 空间拓扑图透传：build_prompts 从 space_maps.json 写入 ep 级 space_maps
            _spmaps = (_sd.get("space_maps", []) if isinstance(_sd, dict) else []) or []
            # ★ 2026-08-22 镜号归一化：统一 zfill(2)（消除 "1"/"01" 混用，避免拖动 reorder 匹配失败）
            def _zn(n):
                s = str(n or "").strip()
                return s.zfill(2) if s.isdigit() else s
            for _sh in _ep_shots:
                if isinstance(_sh, dict) and _sh.get("shot_number") is not None:
                    _sh["shot_number"] = _zn(_sh.get("shot_number"))
                # ★ 2026-08-22 scene_name：SC 编号 → 场景资产名（制作页/生图引用用）
                if isinstance(_sh, dict):
                    _sh["scene_name"] = _scene_map.get(str(_sh.get("scene_tag") or ""), "") or _sh.get("scene_name", "")
            # ★ 2026-08-22 uid 补齐：每镜给稳定唯一标识（拖动重排按 uid 传顺序，镜号会重编号）
            import uuid as _uuid
            for _sh in _ep_shots:
                if isinstance(_sh, dict) and not _sh.get("uid"):
                    _sh["uid"] = _uuid.uuid4().hex[:12]
            # ★ 2026-08-22 编辑稿分离：原始 shots.json 永不动；页面编辑稿单独存 shots.edited.json → 读入 edited_shots
            _edited_shots = None
            _edited_path = os.path.join(BASE, "outputs/xiajing", ed, "shots.edited.json")
            if os.path.exists(_edited_path):
                try:
                    _ed = json.load(open(_edited_path, encoding="utf-8"))
                    _edited_shots = _ed.get("shots", []) if isinstance(_ed, dict) else _ed
                    for _sh in (_edited_shots or []):
                        if isinstance(_sh, dict) and _sh.get("shot_number") is not None:
                            _sh["shot_number"] = _zn(_sh.get("shot_number"))
                        if isinstance(_sh, dict) and not _sh.get("uid"):
                            _sh["uid"] = _uuid.uuid4().hex[:12]
                        # ★ 2026-08-22 编辑稿也补 scene_name（旧编辑稿深拷贝缺少该字段 → 场景显示/注入失效）
                        if isinstance(_sh, dict):
                            _sh["scene_name"] = _scene_map.get(str(_sh.get("scene_tag") or ""), "") or _sh.get("scene_name", "")
                except Exception:
                    _edited_shots = None
        except Exception:
            _ep_shots, _title, _tone, _status, _sb_img, _sb_rd, _edited_shots = [], f"第{ep_num}集", {}, {}, "", False, None
            _scene_map, _ch_map = {}, {}
            _battle_segments = []
            _sbvps, _sbcfg = [], {}
            _spmaps = []
    else:
        _beats_path = os.path.join(BASE, "outputs/xiajing", ed, "beats.json")
        _title, _tone, _status, _sb_img, _sb_rd, _edited_shots = f"第{ep_num}集", {}, {}, "", False, None
        _scene_map, _ch_map = {}, {}
        _battle_segments = []
        _sbvps, _sbcfg = [], {}
        _spmaps = []
        if os.path.exists(_beats_path):
            try:
                _beats = json.load(open(_beats_path, encoding="utf-8"))
                _title = _beats.get("episode_title", f"第{ep_num}集")
                _tone = _beats.get("tone_palette", {})
                _status = _beats.get("episode_status", {})
                for _b in _beats.get("beats", []):
                    _n = _b.get("beat_number", "")
                    _ep_shots.append({
                        "shot_number": str(_n), "duration": "",
                        "shot_type": "", "visual": _b.get("visual_description", ""),
                        "dialogue": _b.get("narration_segment", ""), "composition": "",
                        "scene_tag": _b.get("scene", ""), "characters": "",
                        "camera": "", "action": "", "movement": "",
                        "sound": _b.get("sfx", ""), "narrative": "",
                        "firstframe_prompt": _b.get("firstframe_prompt", ""),
                        "firstframe_image": f"assets/ep{ep_num:03d}/frames/beat{_n}.png",
                        "tailframe_prompt": "", "tailframe_image": "",
                        "video_prompt": _b.get("video_prompt", ""),
                        "video": f"assets/ep{ep_num:03d}/video/beat{_n}.mp4",
                        "is_edited": False, "original_shot": None
                    })
            except Exception:
                pass
    # 归一化 shots：缺字段补默认，asset 路径按新目录
    _norm = []
    # ★ 2026-08-22 画面标注反推：assets/ep{NNN}/annotation/shot{N}-annotated-*.png 最新一张
    def _find_annotated(_epn, _shotnum):
        _ad = os.path.join(PROJECT_DIR, "assets", f"ep{_epn:03d}", "annotation")
        try:
            _files = [f for f in os.listdir(_ad) if f.startswith(f"shot{_shotnum}-annotated-") and f.endswith(".png")]
        except Exception:
            return ""
        if not _files:
            return ""
        _files.sort()
        return f"assets/ep{_epn:03d}/annotation/{_files[-1]}"
    for i, _s in enumerate(_ep_shots):
        _nn = str(_s.get("shot_number") or (i + 1))
        _norm.append({
            "shot_number": _nn,
            "annotated_image": _find_annotated(ep_num, _nn),
            "duration": _s.get("duration", ""),
            "shot_type": _s.get("shot_type", ""),
            "visual": _s.get("visual", ""),
            "dialogue": _s.get("dialogue", ""),
            "composition": _s.get("composition", ""),
            "scene_tag": _s.get("scene_tag", ""),
            "scene_name": _s.get("scene_name", ""),
            "characters": _s.get("characters", ""),
            "camera": _s.get("camera", ""),
            "action": _s.get("action", ""),
            "movement": _s.get("movement", ""),
            "sound": _s.get("sound", ""),
            "narrative": _s.get("narrative", ""),
            # ★ 2026-09-09 剧本秒段出处透传（check-script-fidelity 依赖，缺则项目台静默丢出处）
            "source": _s.get("source", ""),
            # ★ 2026-09-09 镜级章节透传（前端按 chapter_range 选当前剧情身份，缺则身份选择退化）
            "chapter": _s.get("chapter", ""),
            # ★ 2026-09-09 镜级空间拓扑图资产名（引用行末位/垫图对应场）
            # ★ 2026-09-10 3.5.16 草图提示词透传：白名单装配器不透传＝前端永远拿不到（同 voice_desc 坑）
            "sketch_prompt": _s.get("sketch_prompt", ""),
            # ★ 2026-09-10 3.5.17 草图位：仅当文件真在盘上才给路径（否则前端会显示破图而非"未生成"）
            "sketch_image": _s.get("sketch_image") or (
                f"assets/ep{ep_num:03d}/sketches/shot{_nn}.png"
                if asset_exists(f"ep{ep_num:03d}/sketches", f"shot{_nn}.png") else ""),
            "space_map": _s.get("space_map", ""),
            # ★ 2026-08-22 分镜大纲字段（Tab1 7 列）：大纲生成器写回，缺省回退完整字段
            "outline_visual": _s.get("outline_visual") or _s.get("visual", ""),
            "outline_dialogue_sound": _s.get("outline_dialogue_sound") or (_s.get("dialogue", "") + ((" · " + _s.get("sound", "")) if _s.get("sound") else "")),
            "outline_function": _s.get("outline_function") or _s.get("narrative", ""),
            "firstframe_prompt": _s.get("firstframe_prompt", ""),
            "firstframe_image": _s.get("firstframe_image", f"assets/ep{ep_num:03d}/frames/shot{_nn}.png"),
            "tailframe_prompt": _s.get("tailframe_prompt", ""),
            "tailframe_image": _s.get("tailframe_image", f"assets/ep{ep_num:03d}/frames/tail-{_nn}.png"),
            "video_prompt": _s.get("video_prompt", ""),
            "video": _s.get("video", f"assets/ep{ep_num:03d}/video/shot{_nn}.mp4"),
            "is_edited": bool(_s.get("is_edited", False)),
            "original_shot": _s.get("original_shot"),
            # ★ 2026-09-09 同源双模型逐镜稿透传（离线产 {seedance,h3}，缺 h3 留空）
            "video_prompts": _s.get("video_prompts") or ({"seedance": _s.get("video_prompt",""), "h3": ""} if _s.get("video_prompt") else None),
        })
    # ★ 2026-08-22 故事板多张（9 镜/张自动分组）：反推 assets/ep{NNN}/storyboards/story-{集}-{idx}.png
    #   （命名与 name=story-{集}-{idx} 一致，如 story-1-1.png）
    _storyboards = []
    _sbd = os.path.join(PROJECT_DIR, "assets", f"ep{ep_num:03d}", "storyboards")
    if os.path.isdir(_sbd):
        for _i in range(1, 60):
            _sf = f"story-{ep_num}-{_i}.png"
            if os.path.exists(os.path.join(_sbd, _sf)):
                _storyboards.append({
                    "idx": _i,
                    "image": f"assets/ep{ep_num:03d}/storyboards/{_sf}",
                    "ready": True,
                    "history": asset_history(f"ep{ep_num:03d}/storyboards", _sf),
                })
    # ★ 2026-09-09 离线同源段稿权威合并：按板号写入 _storyboards[].video_prompts（无图的板建桩），
    #   使前端故事板直接读离线稿、不再自行拼装；此步在"merge 旧快照"之后执行 → 离线覆盖旧前端稿。
    _sb_by_idx = {sb.get("idx"): sb for sb in _storyboards}
    for _b in _sbvps:
        _bi = _b.get("idx")
        if _bi is None: continue
        _sb = _sb_by_idx.get(_bi)
        if _sb is None:
            _sb = {"idx": _bi, "ready": False}
            _storyboards.append(_sb); _sb_by_idx[_bi] = _sb
        _sb["video_prompts"] = _b.get("video_prompts", {"seedance": [], "h3": []})
        _sb["seg_ranges"] = _b.get("seg_ranges", [])
    _storyboards.sort(key=lambda s: s.get("idx") or 0)
    all_episodes.append({
        "number": ep_num,
        "title": _title,
        "status": _status,
        "tone_palette": _tone,
        "storyboard_image": _sb_img,
        "storyboard_ready": _sb_rd,
        "storyboards": _storyboards,
        "storyboard_config": _sbcfg,
        "storyboard_video_prompts": _sbvps,
        "space_maps": _spmaps,
        "scene_map": _scene_map,
        "ch_map": _ch_map,
        "battle_segments": _battle_segments,
        "edited_shots": _edited_shots,
        "shots": _norm
    })
all_episodes.sort(key=lambda e: e["number"])

# ★ 2026-08-23 merge SQLite 旧快照的 storyboards.video_prompts/video_segments（build 从文件反推时无此数据，
#   不 merge 会丢故事板生视频提示词）
if sqlite3 is not None:
    try:
        _db2 = sqlite3.connect(os.path.join(PROJECT_DIR, "xiaji.db"))
        _row2 = _db2.execute("SELECT data FROM snapshots WHERE module='xiajing'").fetchone()
        if _row2:
            _old2 = json.loads(_row2[0])
            _old_eps = {e.get("number"): e for e in _old2.get("episodes", [])}
            for _ep in all_episodes:
                _oe = _old_eps.get(_ep.get("number"))
                if not _oe:
                    continue
                _old_sbs = {s.get("idx"): s for s in (_oe.get("storyboards") or [])}
                for _sb in _ep.get("storyboards", []):
                    _osb = _old_sbs.get(_sb.get("idx"))
                    if _osb:
                        if _osb.get("video_prompts") is not None and _sb.get("video_prompts") is None:
                            _sb["video_prompts"] = _osb["video_prompts"]
                        if _osb.get("video_segments") is not None and _sb.get("video_segments") is None:
                            _sb["video_segments"] = _osb["video_segments"]
                # ★ 2026-08-31 空间拓扑图（按集单张，db 有、build 文件反推无）：merge 回来
                if _oe.get("space_map_image"):
                    _ep["space_map_image"] = _oe["space_map_image"]
                    _ep["space_map_ready"] = True
                # ★ 2026-09-01 每集独立拓扑图提示词 merge
                if _oe.get("space_map_prompt") and not _ep.get("space_map_prompt"):
                    _ep["space_map_prompt"] = _oe["space_map_prompt"]
                # ★ 2026-09-10 3.5.14 按场集合 merge：db 里的 space_maps[].image/ready 是运行时上传产物，
                #   全量重建必须回灌，否则"上传完一重建就没了"（同 db_sync_xiage 覆盖丢字段一类事故）
                _old_sms = _oe.get("space_maps")
                if isinstance(_old_sms, list) and _old_sms:
                    _new_sms = _ep.setdefault("space_maps", [])
                    for _oi, _os in enumerate(_old_sms):
                        if not isinstance(_os, dict):
                            continue
                        _nm = str(_os.get("name") or "")
                        _tgt = next((x for x in _new_sms if isinstance(x, dict) and str(x.get("name") or "") == _nm), None)
                        if _tgt is None and _oi < len(_new_sms):
                            _tgt = _new_sms[_oi]
                        if _tgt is None:
                            _new_sms.append(dict(_os))
                            continue
                        for _k in ("image", "prompt", "prompt_cn"):
                            if _os.get(_k) and not _tgt.get(_k):
                                _tgt[_k] = _os[_k]
                        if _os.get("image"):
                            _tgt["ready"] = True
        _db2.close()
    except Exception:
        pass

# ---------- 解析 asset-prompts.md 提取各资产提示词 ----------
# ============================================================
# 身份图锁脸（★ 强制，xiatang-characters 铁律）
# 身份图 prompt 必须含锁脸指令；build-data-js 自动校验/追加
# ============================================================
LOCK_FACE_SUFFIX = (
    "\n\n【锁脸·强制】严格保持参考图中人物的面部五官与主图完全一致"
    "（眼型/鼻形/唇形/脸型/骨骼/发际线零差异）；"
    "only change outfit / accessories / environment / pose, NOT face. "
    "Same face as the reference image, identical facial features."
)

def _ensure_lock_face(prompt):
    """身份图 prompt 自动追加锁脸指令（已含则跳过）。"""
    p = (prompt or "").rstrip()
    pl = p.lower()
    if ("same face as the reference" in pl) or ("same face as the" in pl) or ("锁脸" in p):
        return p
    return p + LOCK_FACE_SUFFIX

def extract_code_blocks(md):
    """返回 [(section_title, [code_block, ...]), ...]"""
    sections = []
    cur_title, cur_blocks = None, []
    for line in md.split("\n"):
        m = re.match(r"^#{2,3}\s+(.+)$", line.strip())
        if m:
            if cur_title:
                sections.append((cur_title, cur_blocks))
            cur_title = m.group(1).strip()
            cur_blocks = []
        elif line.strip().startswith("```"):
            pass
        elif cur_title and line.strip():
            cur_blocks.append(line.rstrip())
    if cur_title:
        sections.append((cur_title, cur_blocks))
    return sections

sections = extract_code_blocks(asset_prompts_md)
prompt_map = {}  # 标题 -> 完整提示词文本
for title, blocks in sections:
    if blocks:
        prompt_map[title] = "\n".join(blocks)

# ---------- 组装角色（从注册表+提示词；禁止硬编码任何项目角色数据，防跨项目污染） ----------
characters = []
for reg in registry["characters"]:
    name = reg["name"]
    # 主图提示词：★ 优先直接用 registry.prompt（2026-08-21 修复：md 标题格式不匹配时主图提示词丢失）；md 解析兜底
    prompt = str(reg.get("prompt") or "")
    if not prompt:
        for title, p in prompt_map.items():
            # 标题以"数字."开头（兼容 1.1 与 1. 两种编号）+ 名字在"（"前出现
            if name in title.split("（")[0] and re.match(r"^\d+\.\d*\s*", title.split("（")[0]):
                prompt = p
                break
    characters.append({
        "name": name,
        "role": reg.get("role", ""),
        "desc": reg.get("desc", ""),
        "aliases": reg.get("aliases", []),
        "identity": " / ".join([str(idn.get("identity_name", "")) for idn in reg.get("identities", [])]),
        "is_main": reg.get("is_main", False),
        "image": f"assets/characters/{latest_versioned('characters', name)}",
        "image_ready": asset_exists("characters", latest_versioned('characters', name)),
        "prompt": prompt,
        "prompt_cn": str(reg.get("prompt_cn") or ""),
        # ★ 2026-09-10 3.5.13 声线域契约（xiatang SKILL.md「声线域契约」）：未知字段会被本装配器丢弃，必须显式放行前端才拿得到
        "voice_desc": str(reg.get("voice_desc") or ""),
        "voice_ready": bool(reg.get("voice_ready")) or asset_exists("voices", f"{name}.mp3"),
        "history": asset_history("characters", f"{name}.png"),
        "identities": [{"identity_id": idn["identity_id"], "name": idn["identity_name"], "image": f"assets/characters/{latest_versioned('characters', name + '-' + idn['identity_id'])}", "image_ready": asset_exists("characters", latest_versioned('characters', name + '-' + idn['identity_id'])), "prompt": _ensure_lock_face(idn.get("prompt", "")), "prompt_cn": str(idn.get("prompt_cn", "")), "sheet_prompt": idn.get("sheet_prompt", ""), "sheet_prompt_cn": str(idn.get("sheet_prompt_cn", "")), "sheet_image": f"assets/characters/{latest_versioned('characters', name + '-' + idn['identity_id'] + '-sheet')}", "sheet_ready": asset_exists("characters", latest_versioned('characters', name + '-' + idn['identity_id'] + '-sheet')), "history": asset_history("characters", f"{name}-{idn['identity_id']}.png"), "sheet_history": asset_history("characters", f"{name}-{idn['identity_id']}-sheet.png"), "chapter_range": idn.get("chapter_range", ""), "evidence": idn.get("evidence", "")} for idn in reg.get("identities", [])]
    })

# ---------- 场景 ----------
scenes = []
for s in registry["scenes"]:
    prompt = ""
    # 优先匹配场景段标题（形如 "黑市（黑市·夜·内景）"：标题=场景名开头且含 ·），
    # 避免误匹配角色标题（如 "老李（黑市商人·经济线搭档）" 里也含场景名"黑市"）
    for title, p in prompt_map.items():
        t0 = title.split("（")[0].strip()
        if t0 == s["name"] and "·" in title:
            prompt = p
            break
    if not prompt:
        for title, p in prompt_map.items():
            if s["name"] in title:
                prompt = p
                break
    scenes.append({
        "name": s["name"],
        "header": s.get("header") or f"{s.get('episode','')}-{s.get('scene','')} {s['name']} {s.get('time','')} {s.get('interior','')}",
        "time": s.get("time", ""), "interior": s.get("interior", False),
        "image": f"assets/scenes/{latest_versioned('scenes', s['name'])}", "image_ready": asset_exists("scenes", latest_versioned('scenes', s['name'])),
        "prompt": prompt, "prompt_cn": str(s.get("prompt_cn") or ""), "usage_count": s.get("usage_count", 0),
        # ★ 2026-09-10 3.5.13 A2 空间基准图承载字段（scene-assets.md A2·2·补）：未登记时按约定路径探测，探测到即视为 ready（不依赖没人写的布尔位）
        "layout_image": str(s.get("layout_image") or (
            f"assets/scenes/{latest_versioned('scenes', s['name'] + '-layout')}"
            if asset_exists("scenes", latest_versioned("scenes", s["name"] + "-layout")) else "")),
        "layout_ready": bool(s.get("layout_ready")) or asset_exists("scenes", s["name"] + "-layout")
    })

# ★ 2026-08-20：merge SQLite 现有 xiatang 快照的运行时字段（views/views_ready/plan/plan_ready/
#   plan_sketch/plan_sketch_ready/dists/dists_ready）——多视角/上帝视角/设为正面/视距推拉是运行时产物，
#   registry 无此数据，不 merge 的话 build 重建会丢（#47）。prompt/image 等静态字段仍以 registry + 文件为准。
if sqlite3 is not None:
    try:
        _db = sqlite3.connect(os.path.join(PROJECT_DIR, "xiaji.db"))
        _row = _db.execute("SELECT data FROM snapshots WHERE module='xiatang'").fetchone()
        if _row:
            _old = json.loads(_row[0])
            _old_scenes = {x.get("name"): x for x in _old.get("scenes", [])}
            for _sc in scenes:
                _o = _old_scenes.get(_sc.get("name"))
                if _o:
                    for _k in ("views", "views_ready", "plan", "plan_ready", "plan_sketch", "plan_sketch_ready", "dists", "dists_ready"):
                        if _k in _o:
                            _sc[_k] = _o[_k]
        _db.close()
    except Exception:
        pass

# ---------- 道具 ----------
props = []
for p in registry["props"]:
    prompt = ""
    for title, pp in prompt_map.items():
        if p["name"] in title:
            prompt = pp
            break
    props.append({
        "name": p["name"], "owner": p.get("character", ""), "reason": p.get("reason", ""),
        "image": f"assets/props/{latest_versioned('props', p['name'])}", "image_ready": asset_exists("props", latest_versioned('props', p['name'])), "prompt": prompt,
        # ★ 2026-09-10 3.5.17 道具契约字段放行（纪律 19③：识别锚点 + 剧情锁定状态）——此前被白名单静默丢弃，前端拿不到（check-field-passthrough 首跑抓出）
        "continuity_anchors": p.get("continuity_anchors") or [],
        "story_state": p.get("story_state", ""),
        "priority": p.get("priority", ""),
        "prompt_cn": str(p.get("prompt_cn") or ""),
        "history": asset_history("props", f"{p['name']}.png")
    })

# ---------- 听风电影（tingfeng，★ 2026-09-01 独立模块，不影响 xiajing）----------
tingfeng_eps = []
_tf_dir = os.path.join(BASE, "outputs", "tingfeng")
if os.path.isdir(_tf_dir):
    for _tf_sub in sorted(os.listdir(_tf_dir)):
        _tfj = os.path.join(_tf_dir, _tf_sub, "tingfeng.json")
        if os.path.exists(_tfj):
            try:
                _tf_data = json.load(open(_tfj, encoding="utf-8"))
                # 兼容两种结构：{"episodes":[...]}（解包）或直接数组/单集对象
                if isinstance(_tf_data, dict) and "episodes" in _tf_data:
                    for _e in _tf_data["episodes"]:
                        tingfeng_eps.append(_e)
                elif isinstance(_tf_data, list):
                    tingfeng_eps.extend(_tf_data)
                else:
                    tingfeng_eps.append(_tf_data)
            except Exception as _e:
                print("tingfeng 解析失败:", _tf_sub, _e)
# ★ 2026-09-06 字段契约兜底：tingfeng.json 可能仅用 ep 字段（如 "ep001"），
# 前端 tingfeng.js 全程依赖 e.number 渲染/查找/打开单集。此处统一补全 number，
# 避免「听风第一集打不开」（e.number 为 undefined → 找不到集）。
for _e in tingfeng_eps:
    if not _e.get("number"):
        _eid = str(_e.get("ep") or _e.get("id") or "")
        _digits = "".join(ch for ch in _eid if ch.isdigit())
        _e["number"] = int(_digits) if _digits else 0
tingfeng_eps.sort(key=lambda e: int(e.get("number", 0) or 0))
# ★ 2026-09-01 merge db 旧快照的 tingfeng storyboards/space_map（build 从 tingfeng.json 组装无此运行时数据，不 merge 会丢）
if sqlite3 is not None:
    try:
        _db3 = sqlite3.connect(os.path.join(PROJECT_DIR, "xiaji.db"))
        _row3 = _db3.execute("SELECT data FROM snapshots WHERE module='tingfeng'").fetchone()
        if _row3:
            _old3 = json.loads(_row3[0])
            _old_tf = {e.get("number"): e for e in (_old3.get("episodes") or [])}
            for _te in tingfeng_eps:
                _ote = _old_tf.get(_te.get("number"))
                if _ote and _ote.get("storyboards"):
                    _te["storyboards"] = _ote["storyboards"]
                # ★ 2026-09-01 听风空间拓扑图（db 有、tingfeng.json 无）：merge 回来
                if _ote and _ote.get("space_map_image"):
                    _te["space_map_image"] = _ote["space_map_image"]
                    _te["space_map_ready"] = True
                # ★ 2026-09-01 每集独立拓扑图提示词 merge
                if _ote and _ote.get("space_map_prompt") and not _te.get("space_map_prompt"):
                    _te["space_map_prompt"] = _ote["space_map_prompt"]
                # ★ 2026-09-04 拓扑图按场集合 merge（每场一张；db 有、tingfeng.json 无）：集合优先，旧单数字段兜底归一化
                if _ote and _ote.get("space_maps") and not _te.get("space_maps"):
                    _te["space_maps"] = _ote["space_maps"]
                elif _ote and (_ote.get("space_map_image") or _ote.get("space_map_prompt")) and not _te.get("space_maps"):
                    _te["space_maps"] = [{"name": "空间拓扑图", "prompt": _ote.get("space_map_prompt", ""), "image": _ote.get("space_map_image", ""), "ready": bool(_ote.get("space_map_image"))}]
        _db3.close()
    except Exception as _e3:
        print("tingfeng merge 失败:", _e3)

# ---------- 组装 PROJECT ----------
# 项目名/ID 从 pipeline-state.json 读取（title/project），兜底用目录名；禁止硬编码具体项目
_pipeline_meta = {}
_ps_path = os.path.join(BASE, "pipeline-state.json")
if os.path.exists(_ps_path):
    try:
        _pipeline_meta = json.load(open(_ps_path, encoding="utf-8"))
    except Exception:
        _pipeline_meta = {}
_proj_id = str(_pipeline_meta.get("project") or os.path.basename(os.path.normpath(BASE)))
_proj_title = str(_pipeline_meta.get("title") or _proj_id)
episode_count = len(all_episodes)
latest_ep = all_episodes[-1] if all_episodes else None
project = {
    "meta": {
        "name": _proj_title,
        "project_id": _proj_id,
        "source": _pipeline_meta.get("source") or "",
        "style_id": style.get("style_id") or style.get("id", "chinese_period_drama"),
        "style_label": style.get("style_label") or style.get("label", "中文古装剧写实风"),
        "style_tag": style.get("style_tag", "CINEMATIC FILMIC REALISM"),
        "mode": _pipeline_meta.get("mode", "production"),
        "updated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "episode_count": episode_count
    },
    "xialiao": {
        "format_check": ingest["format_check"],
        "chapters": ingest["chapters"],
        "scene_blocks": ingest["scene_blocks"],
        "total_chars": ingest["total_chars"],
        "billable_chars": ingest["billable_chars"],
        "spine_template": ingest["spine_template"],
        "world": world_data["world"] if world_data else None,
        "knowledge_graph": (world_data["knowledge_graph"] if world_data and world_data.get("knowledge_graph")
                            else {"node_count": ingest["knowledge_graph"]["node_count"], "edge_count": ingest["knowledge_graph"]["edge_count"], "nodes": ingest["knowledge_graph"]["nodes"]})
    },
    "xiatang": {
        "characters": characters,
        "scenes": scenes,
        "key_scenes": [dict(k,
            image=k.get("image") or f"assets/key-scenes/{latest_versioned('key-scenes', k.get('name') or '')}",
            image_ready=k.get("image_ready", asset_exists("key-scenes", latest_versioned('key-scenes', k.get('name') or '')))
        ) for k in key_scenes],
        "props": props,
        "props_merged": [{"prop": x.get("prop", ""), "merged_into": x.get("merged_into", ""), "reason": x.get("reason", "")} for x in (registry.get("props_merged_into_characters") or [])]
    },
    "xiajing": {
        "episodes": all_episodes
    },
    "tingfeng": {
        "episodes": tingfeng_eps
    },
    "xiage": {
        "styles": [{
            "style_id": s.get("style_id", ""),
            "style_label": s.get("style_label", ""),
            "style_tag": s.get("style_tag", ""),
            "style_instructions": s.get("style_instructions", ""),
            "avoid_instructions": s.get("avoid_instructions", ""),
            "recommended_for": s.get("recommended_for", ""),
            "is_preset": bool(s.get("is_preset", False)),
            "confirmed_by_user": bool(s.get("confirmed_by_user", False)),
            "image": f"assets/styles/{s.get('style_id', '')}.png",
            # 兼容两种命名：style_id.png（规范）或 style_tag.png（用户常按风格标签命名）
            "image_ready": (asset_exists("styles", f"{s.get('style_id', '')}.png")
                            or asset_exists("styles", f"{s.get('style_tag', '')}.png"))
        } for s in _all_styles],
        "current": style.get("style_id", ""),
        # ★ 创作方向三件套（三步向导产出：视觉参考/影片基调）
        "visual_references": (creation_dir or {}).get("visual_references", []),
        "tonal_direction": (creation_dir or {}).get("tonal_direction", ""),
        # ★ FS 固定风格库（虾格产出 outputs/fs-library.md，读入供虾镜按 FS-XX 引用与项目台展示）
        "fs_library": (open(os.path.join(BASE, "outputs", "fs-library.md"), encoding="utf-8").read()
                       if os.path.exists(os.path.join(BASE, "outputs", "fs-library.md")) else ""),
        # ★ 2026-09-10 3.5.15 全剧情绪曲线 + 色调总表（虾格产出 creation-direction.json 字段）：白名单装配器会丢弃未知字段，必须显式放行前端才拿得到
        "emotion_curve": (creation_dir or {}).get("emotion_curve", {}),
        "global_tone_table": (creation_dir or {}).get("global_tone_table", {}),
        # ★ 全剧定风格图（美术圣经锚）：assets/styles/style_keyframe*.png 最新一张
        "keyframe": keyframe_info()[0],
        "keyframe_ready": keyframe_info()[1],
        # ★ 挂载风格库（v3.4.0-风格库）：skill 种子层 + 用户级库合并的候选风格，供虾格 Tab 展示/应用/导出
        "style_library": _style_library
    }
}

# ---------- 虾剧（xiaju）：剧本输出模块（★ 2026-09-05 新增） ----------
# 来源 outputs/xiaju/ep{NNN}.md（AI 按剧本写作规范产出的分集剧本）；db 已有 xiaju（前端编辑版）优先
_xju_eps = []
_xju_dir = os.path.join(BASE, "outputs", "xiaju")
if os.path.isdir(_xju_dir):
    for _fp in sorted(glob.glob(os.path.join(_xju_dir, "ep*.md"))):
        _xm = re.search(r"ep(\d+)", os.path.basename(_fp))
        if not _xm:
            continue
        _xnum = int(_xm.group(1))
        _xbody = open(_fp, encoding="utf-8").read()
        _xtm = re.search(r"#\s*第\s*\d+\s*集[《\s]*([^《\n]*)", _xbody)
        _xtitle = _xtm.group(1).strip().rstrip("》").strip() if _xtm else ""
        _xju_eps.append({"number": _xnum, "title": _xtitle, "body": _xbody, "source": "md",
                         "updated_at": datetime.datetime.fromtimestamp(os.path.getmtime(_fp)).strftime("%Y-%m-%d %H:%M:%S")})
_xju_db = None
try:
    import sqlite3 as _sq3
    _cdb = _sq3.connect(os.path.join(PROJECT_DIR, "xiaji.db"))
    _xrow = _cdb.execute("SELECT data FROM snapshots WHERE module='xiaju'").fetchone()
    _cdb.close()
    _xju_db = json.loads(_xrow[0]).get("episodes") if _xrow else None
except Exception:
    _xju_db = None
if isinstance(_xju_db, list) and _xju_db:
    # ★ 2026-09-05 修复：仅 source=='frontend'（用户在项目台前端编辑保存）的条目优先于 md；
    #   source=='md' 的旧条目一律以当前 md 内容为准——否则 AI 改 md 后永远覆盖不进去（同步事故）
    _xju_map = {e.get("number"): e for e in _xju_db if isinstance(e, dict)}
    for _me in _xju_eps:
        _xold = _xju_map.get(_me["number"])
        if _xold is None or _xold.get("source") != "frontend":
            _xju_map[_me["number"]] = _me
    _xju_eps = sorted(_xju_map.values(), key=lambda e: e.get("number", 0))
project["xiaju"] = {"episodes": _xju_eps}


# ---------- 读取流水线状态（pipeline-state.json，若存在） ----------
pipeline = {}
ps_path = os.path.join(BASE, "pipeline-state.json")
if os.path.exists(ps_path):
    pipeline = json.load(open(ps_path, encoding="utf-8"))
project["pipeline"] = {
    "mode": pipeline.get("mode", "production"),
    "current": pipeline.get("current", ""),
    "modules": {k: {"status": v.get("status", ""), "handoff": v.get("handoff", "")} for k, v in pipeline.get("modules", {}).items()},
    "history": pipeline.get("history", [])
}

# ---------- 续集引导（任何 AI 工具读取此字段即可续集） ----------
proj_name = project["meta"]["name"]
cur = project.get("pipeline", {}).get("current", "xiaju-script")
next_step_desc = {
    "user-generation": "资产图/草图/首帧/视频由用户在外部生成后放入 project/assets/ 对应目录（改 data.js 中 *_ready 为 true 即登记）；全部就绪后可继续下一集或合成导出。",
    "xiaju-script": "流程第 1 步（剧本先行）：虾剧 xiaju-script 把大纲/小说/单章/已有成稿写成或规范化为虾剧格式 outputs/xiaju/ep{NNN}.md（五阶门控→90s 情绪循环→台词七维）。",
    "confirm-xiaju": "剧本成稿待确认，下一步：确认后进虾料摄入成稿，再进虾格三步向导。",
    "xialiao-ingest": "虾剧成稿已确认，下一步：虾料 xialiao-ingest 摄入成稿，梳理世界观/知识图谱/生产事实。",
    "xiage-styles": "成稿 + 世界观就绪，下一步：虾格 xiage-styles 三步向导确认创作方向。",
    "xiatang-characters": "创作方向已确认，下一步：虾塘 xiatang-characters 从剧本反推建立资产库。",
    "xiajing-episodes": "资产就绪，下一步：虾镜 xiajing-episodes 生成脚本与镜头。",
}.get(cur, "见 pipeline-state.json 的 current 字段。")
project["resume_guide"] = {
    "how_to_resume": f"1) 读项目根 SQLite(xiaji.db) 获得全部产出与状态；2) 读项目根 pipeline-state.json 获得权威断点（current={cur}）；3) 按 pipeline.history 了解已执行步骤；4) 当前断点说明：{next_step_desc} 5) 确认后继续。",
    "asset_tag_convention": "{{角色名}} / {{场景·名}} / {{道具·名}}，分镜/视频提示词直接引用标签",
    "style": f"{project['meta']['style_label']}（style_tag={project['meta']['style_tag']}）",
    "prompt_convention": "AI 不生成图片但产出所有图片的提示词（资产定妆/草图/首帧/视频逐项全量交付，纯净单段可复制）；执行生成归用户；执行归用户≠提示词可省略。"
}

# ---------- 输出：直写 SQLite（项目根/xiaji.db），前端唯一数据源（替代原 data.js） ----------
import sqlite3 as _sq
_db = os.path.join(BASE, "project", "xiaji.db")
_conn = _sq.connect(_db)
_conn.execute("CREATE TABLE IF NOT EXISTS snapshots (module TEXT PRIMARY KEY, data TEXT NOT NULL, updated_at TEXT NOT NULL)")
for _k, _v in project.items():
    _conn.execute("INSERT OR REPLACE INTO snapshots(module, data, updated_at) VALUES (?,?,?)",
                  (_k, json.dumps(_v, ensure_ascii=False), datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
_conn.commit(); _conn.close()
print(f"SQLite written: {_db} ({len(project)} modules)")
# ★ 2026-08-22 虾镜改 shots 后统计修正：兼容 beats（旧）与 shots（新）
print("characters:", len(characters), "| scenes:", len(scenes), "| props:", len(props), "| shots:", sum(len(e.get("shots", []) or []) for e in all_episodes))
print("pipeline.current:", project.get("pipeline", {}).get("current", ""))
missing = [c["name"] for c in characters if not c["prompt"]]
print("角色提示词缺失:", missing if missing else "无")
print("场景提示词缺失:", [s["name"] for s in scenes if not s["prompt"]] or "无")
print("道具提示词缺失:", [p["name"] for p in props if not p["prompt"]] or "无")
