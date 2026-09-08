#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
听风分镜交付保真校验器（check-fidelity · ★ 2026-09-03 P0-1）
=============================================================
用途：把听风最核心的"视频提示词 = 分镜全文逐字"铁律从 AI 自查升级为机械校验，
作为该集交付的硬门禁（不通过 = 该集交付未完成）。独立于 AI 自查（第三方账本思想）。

检查项（五类 + ★ 2026-09-06 新增 ⑥-⑪）：
  ① 保真：segment.full_text 规范化空白后 100% 连续包含于 video_prompt（非前缀、非抽样；
     引用行/STYLE段/负面词环绕在前后属正常结构；★ D4 追加的 [执行约束] 区在全文之后，不影响本项）。
  ② 段规则：duration ≤ 15s；shots 2-4 个（★ D7 route=武戏 时为 4-6）；非首段 continuity_header 非空、
     **全部段（含末段）exit_hook 非空**——末段钩子 = Stage 0「系列位置说明」要求留给下集的出段钩子。
     ★ D7 新增 ②路由：route 必填（文戏/武戏/奇观/收束），按路由查镜数与单镜时长，收束段禁 ≥5s 静帧。
  ③ 引用行：video_prompt 首行 name=图N 解析——「空间拓扑图」必须存在、只出现一次且在最后，图号必须连续。
     ★ D1 附带修复：引用名带「{{角色:」「{{拓扑:」等类型前缀时先剥离再判（历史事故：带前缀导致 ③/⑥ 误判）。
     ★ D6 新增：本段画面中未出现的角色不得出现在引用行（防模型自行加人）。
  ④ H3 契约：video_prompts.h3 非空且六段标记齐全有序。h3_dual_product=false 时跳过本项。
  ⑤ 一致性：video_prompts.seedance 与 video_prompt 并存时必须逐字一致。
  ⑥ 拓扑图场一致性：seg.space_map 与引用行拓扑图名必须在 space_maps 场集合中登记。
  ⑦ 战斗段附加质检（★ D1 修正；★ 2026-09-07 v3 重构）：战斗段清单统一读 ep.battle_segments，缺失时回退
     ep.combat_design[].段，两者皆无则用战斗词探测 core_action，命中即报错——**禁止静默跳过**。
     ★ v3：battle_segments 登记段 = seedance-combat-prompt 外协提示词整段回流，走早退分支——
     只查 ①保真 + 诱因词 + 负面四禁 + ⑪合规扫描，豁免 ②镜数/③引用行/④H3/⑧camera/⑨执行约束
     （契约见 references/shared-fight-dispatch.md）。
  ⑧ 镜头规格（★ D3）：每镜 camera 必须四段式「景别·视角+角度·运镜·跟随目标」。
  ⑨ 执行块（★ D4）：收束段的 [执行约束] 追加区必须存在且含「位置锁」与「机位」（战斗段豁免，v3）。
  ⑩ 母题锚点（★ D5）：母题「出现段」含本段 → 其「进词片段」必须出现在 video_prompt。
  ⑪ 合规扫描（★ D8）：按 references/shared-compliance-lexicon.md 四维高危词表扫正文，
     命中 → 回改分镜源重跑（禁止直接手改 video_prompt）。
  ③ 引用行：video_prompt 首行 name=图N 解析——「空间拓扑图」（★ 2026-09-04 兼容每场一张的
     场标识变体，如「空间拓扑图·场1」）必须存在、只出现一次且在最后，图号必须连续
     ⚠ 诚实声明：本脚本文档曾声明"本段场景引用检查归 check-scenes.py"，但**该文件从未实现**
     （2026-09-06 核验：scripts/ 下不存在）。故"本段是否引用了所属场景资产"目前**无机械校验**，
     归人工与 Stage 5 审计——这是已知缺口，不是已覆盖项。
  ④ H3 契约：video_prompts.h3 非空且六段标记齐全有序（subject_definitions / summary /
     retention_analysis / detailed_description / overall_soundscape / non_diegetic_music，
     标记格式取自项目台 buildTfVideoPromptH3 实际产出）。h3_dual_product=false 时跳过本项。
  ⑤ 一致性：video_prompts.seedance 与 video_prompt 并存时必须逐字一致。
  （故事板不跨板检查：板位数据在工作台运行时/SQLite，不在 tingfeng.json，暂不入脚本——诚实声明。）

边界（诚实声明）：本脚本只校验"结构与逐字保真"，抓不到"分镜文本与原文剧本语义不符"——
语义归 Stage 5 三重审计与基调追踪表。脚本是门禁，不是裁判。

用法：
  python check-fidelity.py <项目根> [--ep N] [--file tingfeng.json路径] [--out 报告.md]
数据源（三选一优先级）：--file > 项目根/outputs/tingfeng/{epNNN:03d}/tingfeng.json (--ep 指定) > 该目录全部集。
兼容结构：{"episodes":[{number,segments:[...]}]} / [{number,segments}] / 单 ep dict。
H3 开关：项目 project/img_config.json 的 h3_dual_product（缺省 true）。

注意：通用模板，禁止写入任何具体项目数据。
"""
import argparse
import glob
import json
import os
import re
import sys

# H3 六段标记（★ 2026-09-06 兼容两种写法：`[name]` 段头 与 `name:` 字段式，
# 历史事故：只认 `name:` 导致 27 段 × 5 标记 = 135 条误报）
H3_MARKERS = ["subject_definitions", "summary", "retention_analysis",
              "detailed_description", "overall_soundscape", "non_diegetic_music"]
TOPO_NAME = "空间拓扑图"
REF_PAIR_RE = re.compile(r"([^\s=，,、]+)=图(\d+)")

# ★ D1 附带修复（2026-09-06）：引用名可能带「{{角色:」「{{拓扑:」等类型前缀，
# 解析时必须先剥离，否则 ③引用行 / ⑥拓扑图 会把带前缀的名字判为不认识（历史事故：门禁误判）。
TYPE_PREFIX_RE = re.compile(r"^(?:角色|场景|道具|拓扑|空间拓扑图|场)\s*[:：]\s*")

# ★ D3：camera 四段式「景别·视角+角度·运镜·跟随目标」
CAM4_RE = re.compile(r"^(ECU|CU|MCU|MS|WS|ELS)\s*·\s*[^·]{2,}\s*·\s*[^·]{2,}\s*·\s*跟随[^·]{2,}$")

# ★ D7：段落路由 → (最少镜, 最多镜, 单镜最小时长, 单镜最大时长)
ROUTE_RULES = {"文戏": (2, 3, 3.0, 6.0), "武戏": (4, 6, 1.5, 3.0),
               "奇观": (2, 3, 4.0, 7.0), "收束": (3, 4, 2.0, 4.0)}

# ★ D1：未登记战斗段清单时的战斗词探测（只报疑似段，文戏集不误伤）
BATTLE_HINT_RE = re.compile(r"(打斗|对决|交手|厮杀|血战|追杀|突围|掩杀|冲杀|斩|劈|砍|刺|格挡|闪避|拳|刀|剑|枪|刃|战场)")

# ★ D7：时码解析 "0.0s–5.0s" / "0.0-5.0"
TS_RE = re.compile(r"([\d.]+)\s*s?\s*[–—\-~至]\s*([\d.]+)\s*s?")

# ★ D1：段号区间展开 "S07-S08" → ["S07","S08"]（保留零填充宽度）
SEG_RANGE_RE = re.compile(r"^([A-Za-z]*)(\d+)\s*[-–—~]\s*([A-Za-z]*)(\d+)$")


def _ref_name(n):
    """剥离 {{ 与 类型: 前缀，返回纯资产名（★ D1 附带修复）"""
    n = str(n or "").strip()
    n = re.sub(r"^\{\{", "", n)
    n = TYPE_PREFIX_RE.sub("", n)
    n = re.sub(r"^\{\{", "", n)
    return n.strip()


def _is_role_ref(n):
    """判定该引用项是否显式标注为角色（如「{{角色:甲」）——用于 D6 引用行裁剪检查。
    未标类型的裸名不判，避免误伤历史数据。"""
    s = re.sub(r"^\{\{", "", str(n or "").strip()).strip()
    return s.startswith("角色") and bool(TYPE_PREFIX_RE.match(s))


def _is_topo_name(n):
    """★ 2026-09-04 每场一张：拓扑图名兼容场标识变体（「空间拓扑图」/「空间拓扑图·场1」）"""
    n = _ref_name(n)
    return n == TOPO_NAME or n.startswith(TOPO_NAME + "·") or n.startswith(TOPO_NAME + "-")


def _expand_seg_ids(raw):
    """段号区间展开：'S07-S08' → ['S07','S08']；'S03' → ['S03']；支持 、, / 分隔"""
    out = []
    for part in re.split(r"[、,，/\s]+", str(raw or "").strip()):
        part = part.strip()
        if not part:
            continue
        m = SEG_RANGE_RE.match(part)
        if m:
            p1, a, p2, b = m.group(1), int(m.group(2)), (m.group(3) or m.group(1)), int(m.group(4))
            if b >= a and p1 == p2:
                w = len(m.group(2))
                out += [f"{p1}{i:0{w}d}" for i in range(a, b + 1)]
                continue
        out.append(part)
    return out


def battle_segments(ep):
    """★ D1：战斗段清单统一读取。返回 (段号列表, 来源) —— 来源为空表示两者皆无。
    优先 ep.battle_segments；缺失回退 ep.combat_design[].段（兼容历史产出）。"""
    if isinstance(ep, dict):
        bl = ep.get("battle_segments")
        if isinstance(bl, list) and bl:
            ids = []
            for x in bl:
                ids += _expand_seg_ids(x)
            return ids, "battle_segments"
        cd = ep.get("combat_design")
        if isinstance(cd, list) and cd:
            ids = []
            for c in cd:
                if isinstance(c, dict):
                    ids += _expand_seg_ids(c.get("段") or c.get("segment") or "")
            if ids:
                return ids, "combat_design"
    return [], ""


def motifs_of(ep):
    """★ D5：取集级母题表（兼容 stage1.motif_table / ep.motif_table 等落位）"""
    if not isinstance(ep, dict):
        return []
    holders = [ep]
    if isinstance(ep.get("stage1"), dict):
        holders.append(ep["stage1"])
    for h in holders:
        for key in ("motif_table", "motifs", "母题表"):
            v = h.get(key)
            if isinstance(v, list) and v and isinstance(v[0], dict):
                return v
    return []


def load_high_risk_words():
    """★ D8：高危拦截词从横切单源 references/shared-compliance-lexicon.md 动态读取（无硬编码项目词）"""
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    p = os.path.join(base, "references", "shared-compliance-lexicon.md")
    words = []
    try:
        with open(p, encoding="utf-8") as f:
            for line in f:
                s = line.strip()
                if not s.startswith("|"):
                    continue
                cells = [c.strip() for c in s.strip("|").split("|")]
                if len(cells) < 2:
                    continue
                if any(d in cells[0] for d in ("击打受力", "面部创伤", "致命打击", "环境破坏")):
                    words += [w for w in re.split(r"[、,，/]", cells[1]) if w]
    except OSError:
        pass
    return words


def _shot_seconds(ts):
    """从时码串取单镜时长（秒）；无法解析返回 None"""
    m = TS_RE.search(str(ts or ""))
    if not m:
        return None
    try:
        return float(m.group(2)) - float(m.group(1))
    except ValueError:
        return None

def norm(t):
    """规范化空白：任意空白串折叠为单空格（不改内容，只消换行/缩进/多空格差异）"""
    return re.sub(r"\s+", " ", str(t or "")).strip()

def load_eps(path):
    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
    except json.JSONDecodeError as e:
        sys.exit(f"❌ {path} 不是合法 JSON（{e}）——请检查文件是否被手工编辑损坏")
    except OSError as e:
        sys.exit(f"❌ 无法读取 {path}：{e}")
    if isinstance(d, dict) and isinstance(d.get("episodes"), list):
        return d["episodes"]
    if isinstance(d, list):
        return d
    if isinstance(d, dict):
        return [d]
    sys.exit(f"❌ {path} 结构不识别（应为 episodes 数组 / ep 数组 / 单 ep）")

def h3_enabled(root):
    """读 project/img_config.json 的 h3_dual_product（缺省 true，P2-2 契约）"""
    try:
        p = os.path.join(root, "project", "img_config.json")
        if os.path.exists(p):
            cfg = json.load(open(p, encoding="utf-8"))
            return bool(cfg.get("h3_dual_product", True))
    except Exception:
        pass
    return True

def check_segment(seg, idx, ep_label, h3_on, problems, ep=None,
                  battle_list=None, battle_soft=None, motifs=None, high_risk=None):
    sid = str(seg.get("id") or f"段{idx+1}")
    tag = f"[{ep_label} {sid}]"
    battle_list = battle_list or []
    battle_soft = battle_soft or []
    motifs = motifs or []
    high_risk = high_risk or []
    vp = str(seg.get("video_prompt") or "").strip()
    vp2 = ""
    vps = seg.get("video_prompts")
    if isinstance(vps, dict):
        vp2 = str(vps.get("seedance") or "").strip()
    h3 = str(vps.get("h3") or "").strip() if isinstance(vps, dict) else ""

    # ---- ① 保真（full_text ⊆ video_prompt）----
    ft = str(seg.get("full_text") or "").strip()
    targets = [v for v in {vp, vp2} if v]
    if not ft:
        if targets:
            problems.append(f"{tag} ①保真 缺 full_text 字段（契约要求存分镜全文，缺失即无法机械校验）")
    else:
        if not targets:
            problems.append(f"{tag} ①保真 有 full_text 但无 video_prompt（未产出视频提示词）")
        for label, v in (("video_prompt", vp), ("video_prompts.seedance", vp2)):
            if not v:
                continue
            if norm(ft) not in norm(v):
                problems.append(f"{tag} ①保真 {label} 未完整包含分镜全文（截断/改写/总结——触发原文再生成协议）")

    text_all = " ".join(x for x in (ft, vp, vp2) if x)

    # ---- ⑦v3 战斗段早退分支（★ 2026-09-07：battle_segments 登记段 = seedance 外协提示词整段回流）----
    # 只查：诱因词 + 负面四禁 + 合规扫描；豁免 ②镜数/③引用行/④H3/⑧camera/⑨执行约束/⑩母题。
    # 契约：references/shared-fight-dispatch.md
    if sid in battle_list:
        for w in ("对穿错位", "错位定格", "迎头撞上"):
            if w in text_all:
                problems.append(f"{tag} ⑦战斗 越轴/无锚定诱因词「{w}」→ 修订调度单重新外协（见 shared-fight-dispatch.md）")
        m_neg = (re.search(r"\[负面\]\s*(.+)", vp) or re.search(r"\[负面\]\s*(.+)", vp2)
                 or re.search(r"负面提示词[:：]\s*(.+)", vp2 or vp))
        neg = m_neg.group(1) if m_neg else ""
        for w in ("武器形态漂移", "动作接触失真", "力量反馈缺失", "慢动作滥用"):
            if w not in neg:
                problems.append(f"{tag} ⑦战斗 负面提示词缺战斗四禁「{w}」（外协回流契约见 shared-fight-dispatch.md）")
        for w in high_risk:
            if w and w in text_all:
                problems.append(f"{tag} ⑪合规 战斗段正文含高危拦截词「{w}」→ 合规转译后回流"
                                f"（转译表见 references/shared-compliance-lexicon.md）")
        return

    # ---- ② 段规则 ----
    dur_raw = seg.get("duration")
    try:
        dur = float(re.sub(r"[^\d.]", "", str(dur_raw)) or 0)
        if dur <= 0:
            raise ValueError
        if dur > 15.0:
            problems.append(f"{tag} ②段规则 时长 {dur}s 超上限 15s")
    except ValueError:
        problems.append(f"{tag} ②段规则 duration 无效（≤0 或无法解析）：{dur_raw!r}")
    shots = seg.get("shots")
    shots = shots if isinstance(shots, list) else []
    # ★ D7 段落路由：先定 route，再定镜数与时长（废"默认三镜"）
    route = str(seg.get("route") or "").strip()
    rkey = ""
    for k in ROUTE_RULES:
        if k in route:
            rkey = k
            break
    if not route:
        problems.append(f"{tag} ②路由 缺 route 字段（文戏/武戏/奇观/收束）——无路由即默认三镜，密度无规则")
    elif not rkey:
        problems.append(f"{tag} ②路由 route={route!r} 非四选一（文戏/武戏/奇观/收束）")
    if rkey:
        lo, hi, smin, smax = ROUTE_RULES[rkey]
        if not lo <= len(shots) <= hi:
            problems.append(f"{tag} ②路由 {rkey} 段镜数 {len(shots)} 不在 {lo}-{hi} 区间")
        for sh in shots:
            d = _shot_seconds(sh.get("ts"))
            if d is None:
                continue
            if d < smin - 0.01 or d > smax + 0.01:
                problems.append(f"{tag} ②路由 {rkey} 段镜{sh.get('n')} 时长 {d:.1f}s 超出 {smin}-{smax}s")
            if rkey == "收束" and d >= 5.0:
                problems.append(f"{tag} ②路由 收束段镜{sh.get('n')} 时长 {d:.1f}s ≥5s 静帧（每 2 秒须有信息或运动变化）")
    elif not 2 <= len(shots) <= 4:
        problems.append(f"{tag} ②段规则 镜数 {len(shots)} 不在 2-4 区间")
    if idx > 0 and not str(seg.get("continuity_header") or "").strip():
        problems.append(f"{tag} ②段规则 非首段缺承接头 continuity_header")
    if not str(seg.get("exit_hook") or "").strip():
        problems.append(f"{tag} ②段规则 缺退场钩子 exit_hook（末段亦须留余味钩子）")

    # ---- ③ 引用行（拓扑图存在、唯一且最后 + 图号连续；★ 2026-09-04 兼容场标识拓扑图名）----
    if vp:
        first_line = vp.split("\n")[0]
        pairs = REF_PAIR_RE.findall(first_line)
        if not pairs:
            problems.append(f"{tag} ③引用行 首行未解析到 name=图N 引用（引用行缺失）")
        else:
            names = [n for n, _ in pairs]
            nums = [int(x) for _, x in pairs]
            topo_idx = [i for i, n in enumerate(names) if _is_topo_name(n)]
            if not topo_idx:
                problems.append(f"{tag} ③引用行 首行缺「{TOPO_NAME}」引用（空间锚缺失；每场一张后拓扑图名可带场标识，如「{TOPO_NAME}·场1」）")
            elif len(topo_idx) > 1 or topo_idx[0] != len(names) - 1:
                problems.append(f"{tag} ③引用行 顺序错误：{TOPO_NAME}（含场标识变体）应只出现一次且在最后（角色→场景→道具→拓扑图）")
            # ★ 2026-09-06b 再放宽：图号须「严格递增」，允许断号——D6 引用裁剪后集级连续图号
            #   必然缺号（删图87 → 85,86,88…），垫图链路只依赖顺序不依赖连续；连续性由资产表保证
            if any(nums[i + 1] <= nums[i] for i in range(len(nums) - 1)):
                problems.append(f"{tag} ③引用行 图号非严格递增：{nums}（须递增；允许断号——D6 裁剪后缺号属正常）")
            # ★ D6 引用行按段裁剪：本段画面未出现的角色不得引用（防模型自行加人）
            visual_all = " ".join(str(sh.get("visual") or "") for sh in shots)
            for raw_n in names:
                if not _is_role_ref(raw_n):
                    continue
                nm = _ref_name(raw_n)
                if nm and nm not in visual_all:
                    problems.append(f"{tag} ③引用行 角色「{nm}」未出现在本段任一镜画面中（引用行须按段裁剪）")

    # ---- ④ H3 契约 ----
    if h3_on:
        if not h3:
            problems.append(f"{tag} ④H3 缺 video_prompts.h3（同步双产纪律：禁止事后补转化）")
        else:
            hl = h3.lower()
            last = -1
            for m in H3_MARKERS:
                mm = re.search(r"\[\s*%s\s*\]|%s\s*[:：]" % (re.escape(m), re.escape(m)), hl)
                i = mm.start() if mm else -1
                if i < 0:
                    problems.append(f"{tag} ④H3 缺六段标记「{m}」")
                else:
                    if i < last:
                        problems.append(f"{tag} ④H3 六段标记顺序错误：「{m}」位置倒置")
                    last = i

    # ---- ⑤ 一致性 ----
    if vp and vp2 and norm(vp) != norm(vp2):
        problems.append(f"{tag} ⑤一致性 video_prompt 与 video_prompts.seedance 不一致")

    # ---- ⑥ 拓扑图场一致性（★ 2026-09-04 每场一张；仅当 ep 带 space_maps 集合时检查，旧数据自动跳过）----
    smaps = ep.get("space_maps") if isinstance(ep, dict) else None
    if isinstance(smaps, list) and smaps:
        map_names = [str(m.get("name") or "") for m in smaps if isinstance(m, dict)]
        seg_map_key = str(seg.get("space_map") or "").strip()
        if seg_map_key and map_names and not any(seg_map_key in n for n in map_names):
            problems.append(f"{tag} ⑥拓扑图 seg.space_map={seg_map_key!r} 在 space_maps 场集合中找不到（集合：{map_names}）——段所属场标注与集合命名需一致")
        if vp:
            first_line = vp.split("\n")[0]
            for tr in [_ref_name(n) for n, _ in REF_PAIR_RE.findall(first_line) if _is_topo_name(n)]:
                if map_names and not any(tr == n for n in map_names):
                    problems.append(f"{tag} ⑥拓扑图 引用行拓扑图名 {tr!r} 未在 space_maps 集合精确登记（集合：{map_names}）——每场一张，引用名须与集合条目名一致，先在 Stage 1 产出并写入集合")

    # ---- ⑦ 收束段简化门禁（★ D2；★ 2026-09-07 v3：战斗段本体已走 §开头早退分支，此处只剩收束段）----
    # battle_soft = 紧接战斗段之后的收束段（走简化门禁：诱因词 + 执行块）
    if sid in battle_soft:
        # 诱因词仅查战斗系段（叙事段"迎头撞上"可为字面撞怀合法用法，避免误伤）
        for w in ("对穿错位", "错位定格", "迎头撞上"):
            if w in text_all:
                problems.append(f"{tag} ⑦战斗 越轴/无锚定诱因词「{w}」→ 改位置锁/碰撞空间锚定写法（见 shared-fight-dispatch.md）")

    # ---- ⑧ 镜头规格（★ D3：camera 四段式「景别·视角+角度·运镜·跟随目标」）----
    bad_cam = []
    for sh in shots:
        cam = str(sh.get("camera") or "").strip()
        if not CAM4_RE.match(cam):
            bad_cam.append((sh.get("n"), cam or "<空>"))
    if bad_cam:
        n0, c0 = bad_cam[0]
        problems.append(f"{tag} ⑧镜头规格 {len(bad_cam)}/{len(shots)} 镜 camera 未用四段式"
                        f"「景别·视角+角度·运镜·跟随目标」（首例 镜{n0}: {c0[:36]}）")

    # ---- ⑨ 执行块（★ D4：收束段须有 [执行约束] 追加区，含机位重申与位置锁；战斗段 v3 豁免）----
    if sid in battle_soft or rkey == "收束":
        blk = re.search(r"\[执行约束\]\s*(.+)", vp, re.S) or re.search(r"\[执行约束\]\s*(.+)", vp2, re.S)
        b = blk.group(1) if blk else ""
        if not b:
            problems.append(f"{tag} ⑨执行块 缺 [执行约束] 追加区（video_prompt = 引用行+STYLE+分镜全文逐字+[执行约束]）")
        else:
            for w in ("位置锁", "机位"):
                if w not in b:
                    problems.append(f"{tag} ⑨执行块 [执行约束] 缺「{w}」（必带机位重申与位置锁）")

    # ---- ⑩ 母题锚点（★ D5：出现段含本段 → 进词片段必须进 video_prompt）----
    for m in motifs:
        if not isinstance(m, dict):
            continue
        appear = str(m.get("出现段") or m.get("出现") or "")
        if sid not in [x.strip() for x in re.split(r"[、,，]", appear)]:
            continue
        name = str(m.get("母题") or m.get("标准名") or "?")
        kw = str(m.get("进词片段") or "").strip()
        if not kw:
            problems.append(f"{tag} ⑩母题 母题「{name}」出现段含本段但缺『进词片段』字段（无法机械校验锚点是否进词）")
        elif kw not in text_all:
            problems.append(f"{tag} ⑩母题 母题「{name}」出现段含本段，video_prompt 未含进词片段「{kw}」")

    # ---- ⑪ 合规扫描（★ D8：命中高危词 → 回改分镜源重跑，禁手改 video_prompt）----
    for w in high_risk:
        if w and w in text_all:
            problems.append(f"{tag} ⑪合规 正文含高危拦截词「{w}」→ 回改分镜源重跑"
                            f"（转译表见 references/shared-compliance-lexicon.md）")


def main():
    ap = argparse.ArgumentParser(description="听风分镜交付保真校验器（通用模板）")
    ap.add_argument("root", help="项目根目录")
    ap.add_argument("--ep", type=int, default=0, help="只校验第 N 集（默认全部集）")
    ap.add_argument("--file", default="", help="直接指定 tingfeng.json 路径（优先于项目根推导）")
    ap.add_argument("--out", default="", help="报告输出路径（可选）")
    a = ap.parse_args()

    files = []
    if a.file:
        files = [a.file]
    else:
        pat = os.path.join(a.root, "outputs", "tingfeng", "*", "tingfeng.json")
        files = sorted(glob.glob(pat))
        if a.ep:
            files = [f for f in files if f"ep{a.ep:03d}" in f.replace("\\", "/")]
        if not files:
            sys.exit(f"❌ 未找到 tingfeng.json（查找 {pat}）。请确认该集已按 §1.3 双形态交付产出工作台数据。")

    h3_on = h3_enabled(a.root)
    high_risk = load_high_risk_words()
    problems = []
    seg_total = 0
    for fp in files:
        eps = load_eps(fp)
        rel = os.path.relpath(fp, a.root)
        for e in eps:
            # ★ D1 同族修复（2026-09-06）：集号兼容 number / ep 两种落法，
            #   否则 --ep 过滤会把整集静默跳过（历史事故：段总数 0 却显示通过）。
            num = e.get("number", e.get("ep", "?"))
            elabel = str(num) if str(num).lower().startswith("ep") else f"ep{num}"
            if num == "?":
                problems.append(f"{os.path.relpath(fp, a.root)} ⓪集数据 缺 number/ep 字段（按集匹配/交付定位依赖它；缺字段会导致『段总数 0』误通过事故）")
            if a.ep and num not in (a.ep, f"ep{a.ep:03d}", f"{a.ep:03d}"):
                continue
            segs = e.get("segments") if isinstance(e.get("segments"), list) else []
            seg_total += len(segs)
            # ★ D1：战斗段清单统一解析；两者皆无 → 战斗词探测（门禁禁止静默跳过）
            bl, src = battle_segments(e)
            if not src:
                hits = [str(s.get("id") or i + 1) for i, s in enumerate(segs)
                        if BATTLE_HINT_RE.search(str(s.get("core_action") or ""))]
                if hits:
                    problems.append(f"[{elabel}] ⑦战斗 未登记战斗段清单（battle_segments / combat_design 均无），"
                                    f"但 {len(hits)} 段 core_action 命中战斗词（如 {hits[0]}）"
                                    f"——⑦ 战斗质检无法生效（历史事故：字段名不一致导致门禁空转）")
            mt = motifs_of(e)
            # ★ ⑫ 拓扑图生图提示词校验（2026-09-06b 新增）：规范单源 shared-spatial-blocking §十
            #   三硬规则（blueprint sketch + no photorealism / 站位图标特征 / 文字白名单）+ 回填提醒。
            #   背景：苍澜关 ep001 三张拓扑图全员违规——规范文档早已存在，但 space_maps 是校验盲区
            #   （文档≠执行的第三次复现），把规范变成闸门。
            smaps = e.get("space_maps") if isinstance(e.get("space_maps"), list) else []
            if smaps:
                for sm in smaps:
                    if not isinstance(sm, dict):
                        continue
                    nm = str(sm.get("name") or "未命名拓扑图")
                    pp = str(sm.get("prompt") or "")
                    if "blueprint sketch" not in pp.lower():
                        problems.append(f"[{elabel}] ⑫拓扑 「{nm}」生图提示词缺 blueprint sketch 风格词"
                                        f"——未按 shared-spatial-blocking §十书写（防画成写实鸟瞰）")
                    if "no photorealism" not in pp.lower():
                        problems.append(f"[{elabel}] ⑫拓扑 「{nm}」生图提示词缺 no photorealism"
                                        f"——未按 shared-spatial-blocking §十书写")
                    if "icon" not in pp.lower() and "小图标" not in pp:
                        problems.append(f"[{elabel}] ⑫拓扑 「{nm}」生图提示词缺站位区分图标"
                                        f"（主角方/对手方 icon 特征，防无差别圆点）——§十硬规则 3")
                    if not ("no text labels" in pp.lower() or "only cam" in pp.lower()
                            or "仅 cam" in pp or "CAM 编号" in pp or "CAM 编号" in pp.replace("CAM", "CAM")):
                        problems.append(f"[{elabel}] ⑫拓扑 「{nm}」生图提示词缺文字白名单声明"
                                        f"（仅 CAM1~4 与『主轴』二字可作文字）——§十硬规则 1")
                    # ★ 2026-09-06d CAM 同侧铁律（第四次文档≠执行事故后固化）：
                    #   §十 模板要求「轴线同侧布置 CAM1~4 + 细弧线调度弧」——CAM 若画到轴线两侧，
                    #   成图即废（同侧原则是拓扑图存在的意义）。检查对象词：same side / 同侧
                    if "same side" not in pp.lower() and "同侧" not in pp:
                        problems.append(f"[{elabel}] ⑫拓扑 「{nm}」生图提示词缺 CAM 同侧声明"
                                        f"（all CAM icons on the same side of the axis + 细弧线调度弧）"
                                        f"——§十 模板要素，缺则机位可能画到轴线两侧，成图即废")
                    img = sm.get("image")
                    if not img or sm.get("ready") is not True:
                        problems.append(f"[{elabel}] ⑫拓扑 「{nm}」未回填成图（image 空或 ready≠true）"
                                        f"——生成后须回填才算该场空间资产就绪")
                    # ★ 双语双产（2026-09-06b 契约 v2.10.0）：EN prompt 已产出则 prompt_cn 必须成对
                    if pp.strip() and not str(sm.get("prompt_cn") or "").strip():
                        problems.append(f"[{elabel}] ⑫拓扑 「{nm}」EN 提示词缺配对 prompt_cn"
                                        f"（双语双产契约：CN=理解层，需结构化对译回补）")
            # ★ D2 机械化：紧接战斗段之后、route 标为收束的段自动纳入（简化门禁）
            bl_soft = list(bl)
            ids = [str(s.get("id") or "") for s in segs]
            for i2 in range(1, len(ids)):
                if ids[i2 - 1] in bl and "收束" in str(segs[i2].get("route") or ""):
                    bl_soft.append(ids[i2])
            for i, seg in enumerate(segs):
                check_segment(seg, i, elabel, h3_on, problems, e, bl, bl_soft, mt, high_risk)

    lines = [
        "# 听风保真校验报告（check-fidelity）",
        "",
        f"- 校验文件：{len(files)} 个 / 段总数：{seg_total}",
        f"- H3 契约检查：{'启用' if h3_on else '跳过（h3_dual_product=false）'}",
        f"- 问题总数：{len(problems)}",
        f"- 高危词表：加载 {len(high_risk)} 条（源 references/shared-compliance-lexicon.md）",
        "",
    ]
    if problems:
        lines.append("## 问题清单（硬门禁：清零前该集交付视为未完成）")
        lines += [f"- {p}" for p in problems]
    else:
        lines.append("## ✅ 全部通过（保真 / 段规则 / 路由 / 引用行 / H3 / 一致性 / 拓扑图 / 战斗 / 镜头规格 / 执行块 / 母题锚点 / 合规）")
        lines.append("")
        lines.append("> 注意：本脚本只校验「结构与逐字保真」；分镜与原文剧本的语义符合性归 Stage 5 三重审计与基调追踪表。")
    report = "\n".join(lines)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"报告已写入：{a.out}")
    print(report)
    sys.exit(1 if problems else 0)

if __name__ == "__main__":
    main()
