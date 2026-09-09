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
import json
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
    if has_vp:
        for i, s in enumerate(shots):
            vp = str(s.get("video_prompt") or "").strip()
            if not vp:
                continue
            num = str(s.get("shot_number") or (i + 1))
            scene = str(s.get("scene_name") or s.get("scene_tag") or "")
            first_line = vp.split("\n")[0]
            import re as _re
            ref_names = _re.findall(r"([^=\s]+)=图\d+", first_line)
            if "空间拓扑图" not in ref_names:
                problems.append(f"[D引用行] 镜{num} 提示词首行缺「空间拓扑图」引用（空间锚缺失）")
            elif ref_names[-1] != "空间拓扑图":
                problems.append(f"[D引用行] 镜{num} 引用顺序错误：空间拓扑图应在最后（角色→场景→道具→拓扑图），当前在第 {ref_names.index('空间拓扑图')+1} 位")
            if scene and scene not in first_line:
                problems.append(f"[D引用行] 镜{num} 提示词首行缺本段场景图引用「{scene}」（单条提示词必须自包含场景锚）")

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

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="分镜场景一致性矛盾扫描器（通用模板）")
    ap.add_argument("--shots", required=True, help="shots.json 路径（顶层含 shots 数组，或直接是数组）")
    ap.add_argument("--scenes", default="", help="场景资产清单：json 文件路径 或 逗号分隔场景名列表")
    ap.add_argument("--scene-names", default="", help="逗号分隔场景名（与 --scenes 二选一）")
    ap.add_argument("--out", default="", help="报告输出路径（可选）")
    args = ap.parse_args()

    names = load_scene_names(args.scenes) if args.scenes else load_scene_names(args.scene_names)
    n = check(args.shots, names, args.out)
    sys.exit(1 if n else 0)
