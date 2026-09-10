#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
场景一致性矛盾扫描器（scene-consistency 子 skill 产物③）
==========================================================
用途：扫描分镜 shots.json，输出三类机械矛盾——
  A. 矛盾词：画面文本含内景信号词但 scene 是外景（或反之）
  B. 资产缺失：scene 不在场景资产清单中
  C. 换景无据：相邻镜 scene 变化但 narrative 无转场词

边界（诚实声明）：本脚本只抓"内部矛盾"，抓不到"与原文事实不符"（语义判断
归原文-场景对照表 + 人工审核）。脚本是兜底，不是裁判。

用法（三种入参组合）：
  python check-scenes.py --shots <shots.json> --scenes <scenes.json> [--out report.md]
  python check-scenes.py --shots <shots.json> --scene-names <逗号分隔场景名> [--out report.md]
  python check-scenes.py --shots <shots.json>                 # 仅矛盾词/换景检查，跳过资产校验

注意：本脚本为通用模板，禁止写入任何具体项目数据。词表可按剧本语境增补。
"""

import argparse
import io
import json
import os
import re
import sys

# ===== 可配置词表（按剧本语境增补，增补时保持"通用词"定位）=====
# 内景信号词：画面文本出现这些词 → scene 应为内景
INDOOR_WORDS = [
    "屋顶", "房梁", "横梁", "屋内", "堂屋", "卧房", "里屋", "内室",
    "床", "炕", "灶台", "火塘", "窗台", "窗户", "厅堂", "门槛内",
    "屋檐下", "房内", "室内", "墙内", "帘",
]
# 外景信号词：画面文本出现这些词 → scene 应为外景
OUTDOOR_WORDS = [
    "院子", "院中", "院墙", "门外", "石阶", "墙头", "晒架", "晒鱼架",
    "空地", "露天", "海风", "巷道", "街", "码头", "田", "操场", "广场",
]
# 合法例外（不报警）：从内景看外部（"望向屋外大海""从窗外看去"）
LOOKOUT_EXCEPTIONS = ["屋外", "窗外", "门外", "墙外", "院外"]
# 转场词：相邻镜 scene 变化时，narrative 含这些词视为"有转场依据"
TRANSITION_WORDS = [
    "走向", "走出", "来到", "推开", "进入", "迈过", "跨过", "退回",
    "跑到", "移动到", "移至", "转身进", "进屋", "出院", "走到", "回到",
    "转场", "切至", "门口", "门槛", "穿过", "沿着", "步入",
    "推入", "切回", "切入", "推进", "折返", "闪回至",
]

def load_shots(path):
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    shots = d.get("shots") if isinstance(d, dict) else d
    if not shots:
        sys.exit(f"❌ {path} 中未找到 shots 数组（顶层应为 {{shots:[...]}} 或直接数组）")
    return d if isinstance(d, dict) else {}, shots

def load_scene_names(scenes_arg):
    """场景资产清单：json 文件（scenes:[{name}...] 或 [\"name\"...]）或逗号分隔字符串"""
    names = set()
    if not scenes_arg:
        return names
    try:
        with open(scenes_arg, encoding="utf-8") as f:
            data = json.load(f)
        arr = data.get("scenes") if isinstance(data, dict) else data
        for s in arr or []:
            if isinstance(s, str):
                names.add(s)
            elif isinstance(s, dict) and s.get("name"):
                names.add(s["name"])
    except (json.JSONDecodeError, OSError):
        # 不是 json 文件 → 当作逗号分隔的场景名列表
        for n in re.split(r"[,，]", scenes_arg):
            n = n.strip()
            if n:
                names.add(n)
    return names

def scene_type_from_name(name):
    """由场景名粗判内外景：含 院/场/巷/街/码头/田/海/空地 等 → 外景；含 屋/房/堂/厅/室/楼/阁/洞/密 等 → 内景"""
    name = name or ""
    if any(w in name for w in ["院", "广场", "空地", "巷道", "街道", "码头", "田", "海面", "操场", "街"]):
        return "outdoor"
    if any(w in name for w in ["屋", "房", "堂", "厅", "室", "楼", "阁", "洞", "窑", "帐", "殿", "馆", "铺", "坊"]):
        return "indoor"
    return None

def scene_base(scene, scene_names):
    """'母版 › 分区' → 母版：优先返回资产清单中作为 scene 前缀/子串的母版全名，
       否则退化为 ' › ' 之前部分。同一母版不同分区视为同一空间（机位移动，非换景）。"""
    scene = scene or ""
    for a in (scene_names or []):
        if a and a in scene:
            return a
    return scene.split(" › ")[0].split("›")[0].strip() or scene

def scene_in_assets(scene, scene_names):
    return any(a and a in (scene or "") for a in (scene_names or []))

def _ref_line_problems(txt, num, scene, field):
    """单条提示词的顶部资产引用行完整性（★ 2026-09-10 3.5.12 抽成函数：
    video_prompt 与 firstframe_prompt 同一口径。旧版只跑 video_prompt，
    渔村 ep001 因此出现「首帧 51/51 缺引用行、门禁全绿」的静默缺口）。"""
    out = []
    tag = u"首帧" if field == "firstframe_prompt" else u"视频"
    first_line = txt.split("\n")[0]
    ref_names = re.findall(r"([^=\s]+)=图\d+", first_line)
    if not ref_names:
        out.append(u"[D引用行] 镜%s %s提示词缺顶部资产引用行（首行应为「【资产引用】 名=图N …」）——垫图无编号表" % (num, tag))
        return out
    topo = [j for j, n in enumerate(ref_names) if n.startswith(u"空间拓扑图")]
    if not topo:
        out.append(u"[D引用行] 镜%s %s提示词首行缺「空间拓扑图」引用（空间锚缺失）" % (num, tag))
    elif not ref_names[-1].startswith(u"空间拓扑图"):
        out.append(u"[D引用行] 镜%s %s引用顺序错误：空间拓扑图应在最后（角色→场景→道具→拓扑图），当前末位=%s"
                   % (num, tag, ref_names[-1]))
    if scene and scene not in first_line:
        out.append(u"[D引用行] 镜%s %s提示词首行缺本段场景图引用「%s」（单条提示词必须自包含场景锚）" % (num, tag, scene))
    return out


def _board_label_problems(boards):
    """段稿镜头标识（★ 2026-09-10 3.5.12 新增；规范正本 = seedance-stylock.md §39-40，
    此处不重述条款，只做机械校验）：每镜须写「【镜头N · 景别 · …约Xs·软参考】」，
    段内序号从 1 连续，且正文须带「景别」。"""
    out = []
    if not isinstance(boards, list):
        return out
    for b in boards:
        if not isinstance(b, dict):
            continue
        segs = (b.get("video_prompts") or {}).get("seedance") or []
        for si, seg in enumerate(segs):
            if not isinstance(seg, str) or u"【" not in seg:
                continue
            nums = [int(x) for x in re.findall(u"【镜头(\\d+) · ", seg)]
            if not nums:
                out.append(u"[D3镜头标识] 板%s段%d 无「【镜头N · 景别 · …】」标签——段稿未按官方镜头序号组织"
                           % (b.get("idx"), si))
                continue
            if nums != list(range(1, len(nums) + 1)):
                out.append(u"[D3镜头标识] 板%s段%d 段内镜头序号未从 1 连续：%s" % (b.get("idx"), si, nums))
            for line in seg.split("\n"):
                m = re.search(u"【镜头(\\d+) · ([^·]+?) · ", line)
                if m and u"景别" not in line:
                    out.append(u"[D3镜头标识] 板%s段%d 镜头%s 正文缺「景别」（stylock §40 要求镜头设计含 shot size）"
                               % (b.get("idx"), si, m.group(1)))
            if u"软参考" not in seg:
                out.append(u"[D3镜头标识] 板%s段%d 逐镜秒数未标「软参考」（分镜层秒数须声明为参考值，见 duration-control §三）"
                           % (b.get("idx"), si))
    return out


def check(path, scene_names, out_path):
    meta, shots = load_shots(path)
    problems = []
    scene_names = set(scene_names)

    for i, s in enumerate(shots):
        num = str(s.get("shot_number") or (i + 1))
        scene = str(s.get("scene_name") or s.get("scene_tag") or "")
        text = " ".join([
            str(s.get("visual") or ""),
            str(s.get("action") or ""),
            str(s.get("dialogue") or ""),
            str(s.get("narrative") or ""),
        ])

        # ---- A. 矛盾词 ----
        if scene:
            st = scene_type_from_name(scene)
            for w in INDOOR_WORDS:
                if w in text and st == "outdoor":
                    problems.append(f"[A矛盾词] 镜{num} scene=`{scene}`(外景) 但画面含内景词「{w}」")
                    break
            for w in OUTDOOR_WORDS:
                if w in text and st == "indoor":
                    # 例外：从内景看外部（屋外/窗外/门外/墙外/院外）
                    if any(ex in text for ex in LOOKOUT_EXCEPTIONS):
                        continue
                    problems.append(f"[A矛盾词] 镜{num} scene=`{scene}`(内景) 但画面含外景词「{w}」")
                    break

        # ---- B. 资产缺失（'母版 › 分区' 含母版全名前缀即命中）----
        if scene_names and scene and not scene_in_assets(scene, scene_names):
            problems.append(f"[B资产缺失] 镜{num} scene=`{scene}` 不在场景资产清单中")

    # ---- C. 换景无据（相邻镜 scene 变化但 narrative 无转场词）----
    for i in range(1, len(shots)):
        a = shots[i - 1]
        b = shots[i]
        sa = str(a.get("scene_name") or a.get("scene_tag") or "")
        sb = str(b.get("scene_name") or b.get("scene_tag") or "")
        # 只在「母版」层判换景：同母版不同分区=机位移动，不算换景（守 母版 › 分区 规范）
        ba, bb = scene_base(sa, scene_names), scene_base(sb, scene_names)
        if ba and bb and ba != bb:
            narr = str(b.get("narrative") or "") + " " + str(b.get("action") or "") + " " + str(b.get("visual") or "")
            if not any(w in narr for w in TRANSITION_WORDS):
                num = str(b.get("shot_number") or (i + 1))
                problems.append(f"[C换景无据] 镜{num} 从 `{sa}` → `{sb}`（跨母版 {ba}→{bb}）但 narrative 无转场词")

    # ---- D. 引用行完整性（★ 2026-09-01 新增：shot 带 video_prompt 时校验首行引用行）----
    # 规则：每段视频独立投喂 → 单条提示词必须自包含：
    #   ① 首行引用行含「空间拓扑图」且在最后（顺序定稿：角色→场景→道具→拓扑图）
    #   ② 首行含本镜 scene_name（场景图引用）
    has_vp = any(str(s.get("video_prompt") or "").strip() for s in shots)
    for i, s in enumerate(shots):
        num = str(s.get("shot_number") or (i + 1))
        scene = str(s.get("scene_name") or s.get("scene_tag") or "")
        for field in ("video_prompt", "firstframe_prompt"):
            txt = str(s.get(field) or "").strip()
            if txt:
                problems += _ref_line_problems(txt, num, scene, field)

    # ---- D2. 引用的拓扑图必须已登记且成图已回填（★ 2026-09-10 补：防「引用齐全而图全空」静默绿灯）----
    if has_vp:
        refs = set()
        for s in shots:
            vp = str(s.get("video_prompt") or "").strip()
            if not vp:
                continue
            for nm in re.findall(r"([^=\s]+)=图\d+", vp.split("\n")[0]):
                if nm.startswith("空间拓扑图"):
                    refs.add(nm)
        smaps = meta.get("space_maps") if isinstance(meta, dict) else None
        if smaps is None and refs:
            alt = os.path.join(os.path.dirname(os.path.abspath(path)), "space_maps.json")
            if os.path.exists(alt):
                try:
                    with open(alt, encoding="utf-8") as f:
                        smaps = (json.load(f) or {}).get("space_maps")
                except (json.JSONDecodeError, OSError):
                    smaps = None
        known = {m.get("name"): m for m in (smaps or []) if isinstance(m, dict)}
        for nm in sorted(refs):
            m = known.get(nm)
            if m is None:
                problems.append(f"[D2拓扑图未登记] 有镜引用 `{nm}`，但 space_maps 集合里没有这一场"
                                f"（已登记：{sorted(known) or '空'}）——引用悬空，垫图取不到")
                continue
            if not str(m.get("image") or "").strip() or m.get("ready") is not True:
                problems.append(f"[D2拓扑图未回填] `{nm}` 被引用但成图缺失"
                                f"（image={'空' if not str(m.get('image') or '').strip() else '有'}"
                                f"/ready={m.get('ready')}）——P0：引用行指向不存在的图，空间约束在生成时失效")

    # ---- D3. 段稿镜头标识（★ 2026-09-10 3.5.12 补）----
    if isinstance(meta, dict):
        problems += _board_label_problems(meta.get("storyboard_video_prompts"))

    # ---- 输出 ----
    lines = [
        f"# 场景一致性矛盾扫描报告",
        "",
        f"- 扫描文件：`{path}`",
        f"- 镜头总数：{len(shots)}",
        f"- 场景资产清单：{'已提供（' + str(len(scene_names)) + ' 个）' if scene_names else '未提供（跳过 B 类检查）'}",
        f"- 问题总数：{len(problems)}",
        "",
    ]
    if problems:
        lines.append("## 问题清单")
        for p in problems:
            lines.append(f"- {p}")
        lines.append("")
        lines.append("> 处理要求：逐条给出结论（修正 scene / 修正画面词 / 补转场依据 / 补引用行 / 确认为合法例外），问题清零后本报告才视为通过。")
    else:
        lines.append("## ✅ 未发现机械矛盾（矛盾词 / 资产缺失 / 换景无据 / 引用行完整性 均为 0）")
        lines.append("")
        lines.append("> 注意：本报告只覆盖机械矛盾；与原文事实不符的语义问题需对照「原文-场景对照表」人工审核。")

    report = "\n".join(lines)
    if out_path:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"报告已写入：{out_path}")
    print(report)
    return len(problems)

# ===== --selftest：投毒对照（★ 2026-09-10 3.5.12）=====
def _synth_doc():
    """造一份「全部合规」的最小 shots 结构（通用占位名，零项目数据）。"""
    ref = u"【资产引用】 角色A=图1 场甲 › 区1=图2 空间拓扑图·场1=图3"
    seg = (ref + u"\n  【镜头1 · 近景 · 约3秒·软参考｜原镜号001】镜头设计：景别 近景；平视；构图 居中。"
                     u"画面剧情（开场→随后→结尾）：站立→抬手。\n")
    return {
        "shots": [{
            "shot_number": "001", "scene_tag": "SC-01", "scene_name": u"场甲 › 区1",
            "visual": u"角色A 站在区1", "narrative": u"开场",
            "video_prompt": ref + u"\n正文", "firstframe_prompt": ref + u"\n① 风格与质感： x",
        }],
        "space_maps": [{"name": u"空间拓扑图·场1", "image": "assets/scenes/x.png", "ready": True}],
        "storyboard_video_prompts": [{"idx": 0, "video_prompts": {"seedance": [seg]}}],
    }


def selftest():
    import copy
    import contextlib
    import json as _json
    import tempfile
    print(u"=== check-scenes --selftest：投毒对照（门禁必须报，干净必须不报）===")
    cases = []
    d = _synth_doc()
    cases.append((u"干净模板", copy.deepcopy(d), False, u"[D"))
    d1 = copy.deepcopy(d)
    d1["shots"][0]["firstframe_prompt"] = u"① 风格与质感： x\n正文"
    cases.append((u"首帧删引用行", d1, True, u"缺顶部资产引用行"))
    d2 = copy.deepcopy(d)
    d2["storyboard_video_prompts"][0]["video_prompts"]["seedance"][0] = (
        d2["storyboard_video_prompts"][0]["video_prompts"]["seedance"][0]
        .replace(u"【镜头1 · 近景 · 约3秒·软参考｜原镜号001】", u"【镜001 · 近景 · 约3秒·软参考】"))
    cases.append((u"段稿退回全局镜号", d2, True, u"D3镜头标识"))
    d3 = copy.deepcopy(d)
    d3["shots"][0]["video_prompt"] = (u"【资产引用】 角色A=图1 场甲 › 区1=图2 空间拓扑图·场1=图3\n正文")
    d3["space_maps"][0]["image"] = ""
    d3["space_maps"][0]["ready"] = False
    cases.append((u"拓扑图未回填", d3, True, u"D2拓扑图未回填"))
    d4 = copy.deepcopy(d)
    d4["storyboard_video_prompts"][0]["video_prompts"]["seedance"][0] = (
        d4["storyboard_video_prompts"][0]["video_prompts"]["seedance"][0].replace(u"景别 近景；", u""))
    cases.append((u"段稿正文缺景别", d4, True, u"正文缺「景别」"))

    failed = 0
    tmp = tempfile.mkdtemp(prefix="cs_selftest_")
    for name, doc, expect_hit, needle in cases:
        p = os.path.join(tmp, "shots.json")
        open(p, "w", encoding="utf-8").write(_json.dumps(doc, ensure_ascii=False))
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            check(p, [u"场甲"], "")
        rep = buf.getvalue()
        hit = needle in rep
        got = hit if expect_hit else (not hit)
        flag = "OK" if got else u"❌ 门禁空转/误报"
        if not got:
            failed += 1
        print(u"  [%s] %-14s 期望=%s 实际=%s 探针=%s" % (flag, name,
              (u"报 " + needle) if expect_hit else u"不报 [D", got, needle in rep))
    print(u"  临时目录：%s" % tmp)
    return 1 if failed else 0

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="分镜场景一致性矛盾扫描器（通用模板）")
    ap.add_argument("--shots", default="", help="shots.json 路径（顶层含 shots 数组，或直接是数组）")
    ap.add_argument("--scenes", default="", help="场景资产清单：json 文件路径 或 逗号分隔场景名列表")
    ap.add_argument("--scene-names", default="", help="逗号分隔场景名（与 --scenes 二选一）")
    ap.add_argument("--out", default="", help="报告输出路径（可选）")
    ap.add_argument("--selftest", action="store_true", help="投毒对照自检（不读项目数据）")
    args = ap.parse_args()
    if args.selftest:
        sys.exit(selftest())

    if not args.shots:
        ap.error("--shots 必填（或使用 --selftest）")
    names = load_scene_names(args.scenes) if args.scenes else load_scene_names(args.scene_names)
    n = check(args.shots, names, args.out)
    sys.exit(1 if n else 0)
