#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen-layout-prompt.py —— 从 space-truth.json 派生「layout 空间基准图」双语提示词

定位：真理图（唯一写入点）→ 本脚本 → layout 基准图提示词（EN 出图 / CN 审稿）。
      锚点段、围合段、光源段、白名单段全部逐字取自 json，禁止手抄删改。
并存声明：本脚本只新增产物，不改写任何既有生图内容（场景主图 / §A 鸟瞰 / B 九宫格 /
          C 总览 / 上帝视角 plan_sketch 全部保持原样）。

确认门：space-truth.json 的 approved 不为 true 时默认拒绝出词（--allow-unapproved 可强制，
        仅用于草稿预览）。理由：未拍板的布局不该进入出图环节。

用法：
  python gen-layout-prompt.py --truth <space-truth.json> --out <layout-prompts.md> \
         [--fs-from-keyscene <key-scene.json>] [--master SC-02] [--allow-unapproved]
  python gen-layout-prompt.py --truth <space-truth.json> --topology-band --master SC-02
退出码：0 成功 / 2 被确认门或校验拦下 / 3 用法错误
"""

import argparse
import importlib.util
import io
import json
import os
import sys

_GATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "check-space-truth.py")


def _load_gates():
    """门禁单源：按路径动态加载同目录 check-space-truth.py（文件名含连字符，不能直接 import）。"""
    spec = importlib.util.spec_from_file_location("check_space_truth", _GATE_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.run_gates


run_gates = _load_gates()

BEAR_EN = {
    "N": "far side, upper centre of frame",
    "S": "near side, bottom of frame",
    "E": "right side of frame",
    "W": "left side of frame",
    "NE": "upper right corner",
    "NW": "upper left corner",
    "SE": "lower right area",
    "SW": "lower left area",
    "C": "centre of the space",
}
BEAR_CN = {
    "N": "远端·画面中上",
    "S": "近端·画面下缘",
    "E": "画面右侧",
    "W": "画面左侧",
    "NE": "右上角",
    "NW": "左上角",
    "SE": "右下",
    "SW": "左下",
    "C": "空间中央",
}
ENC_EN = {
    "wall_solid": "a solid rammed-earth wall with no opening",
    "wall_low": "a LOW rammed-earth wall, its top edge at about the chest height of a standing adult, clearly lower than the eaves and the door lintel, with a wide flat worn top a person could sit on; the interior stays visible from outside over it",
    "fence": "a low weathered wooden fence with a broken gate frame and two half-open thin-slat gate leaves",
    "house": "the house itself, its full inner facade facing the space",
    "door": "a doorway",
    "window": "a small window",
    "open": "open ground, no boundary",
    "edge_low": "a low field edge",
    "landmark": "a landmark element",
    "none": "nothing",
}
ENC_CN = {
    "wall_solid": "整面无开口的夯土实墙",
    "wall_low": "低矮夯土墙：顶缘约在站立成人的胸口高，明显低于屋檐与门楣，顶面磨平可坐可靠，从院外可越过它看见院内",
    "fence": "低旧木篱笆，带破木院门框与两扇半开细木条门",
    "house": "正房本体，其内侧立面完整朝向空间",
    "door": "一处门口",
    "window": "一扇小窗",
    "open": "开敞，无边界",
    "edge_low": "低矮田埂边缘",
    "landmark": "地标要素",
    "none": "无",
}
SIDE_NAME_EN = {"N": "NORTH", "E": "EAST", "S": "SOUTH", "W": "WEST"}
SIDE_NAME_CN = {"N": "北", "E": "东", "S": "南", "W": "西"}

FIXED_VIEW_EN = ("Scene spatial-reference sheet, 3/4 oblique axonometric view from about 55 degrees above, "
                 "camera positioned high over the SOUTH side looking NORTH, so the whole ground plane and the "
                 "inner faces of all four boundaries are readable at once. 16:9, aspect independent of the "
                 "finished film's ratio.")
FIXED_VIEW_CN = ("场景空间基准图，3/4 斜俯视轴测、约 55 度俯角，机位位于南侧上空朝北俯看，"
                 "使整个地面与四面边界的内侧一次读全。16:9，画幅与成片比例解耦。")

FIXED_LIGHT_EN = ("Neutral reference lighting: soft diffused daylight from an open overcast sky, plus a gentle "
                  "brighter wash entering from the south edge. Lighting carries no time-of-day signature: a soft "
                  "single-sided light is acceptable, but no low-angle long shadows, no golden-hour warmth, no "
                  "backlit rim. Materials fully readable, no dead black, no lifted white, no source-less rim light. "
                  "This image defines geometry and material identity only; time of day and light direction are set "
                  "per shot elsewhere.")
FIXED_LIGHT_CN = ("中性基准光：开阔阴天的柔和散射天光，加一道自南缘透入的较亮漫射。光照不携带时段特征：允许柔和"
                  "单侧光，但不得出现低角度长影、黄金暖调或逆光轮廓。材质完全可读，无死黑、无漂浮发白、无无来源"
                  "轮廓光。本图只定义几何与材质身份；时段与光向由镜次另定。")

FIXED_ANTI_EN = ("Reproduce exactly the listed structures and objects and no others. Do not add barrels, extra "
                 "baskets, plants, shrubs, trees, posts, columns, rocks, coastline, animals, vehicles, laundry, "
                 "tools or furniture. An empty corner is preferable to an invented object.")
FIXED_ANTI_CN = ("只复现上面列出的结构与物件，不得增补。禁止添加木桶、额外的筐、植物、灌木、树、柱子、立柱、礁石、"
                 "海岸线、动物、车辆、晾晒物、工具或家具。宁可空着一角，也不要凭空造一件。")

FIXED_EXCL_EN = ("No people, no animals, no text, no watermark, no arrows, no diagram lines, no labels, no UI "
                 "marks. This image is a LAYOUT AND MATERIAL REFERENCE ONLY: it does not prescribe camera angle, "
                 "shot size or time of day; actual camera positions and framing are defined by the shot list and "
                 "the blocking diagram.")
FIXED_EXCL_CN = ("无人物、无生物、无文字、无水印、无箭头、无图示线、无标注、无 UI 记号。本图仅作布局与材质参考，"
                 "不规定机位角度、景别与时段；实际机位以文字镜次与调度拓扑图为准。")


def load_json(path):
    with io.open(path, encoding="utf-8") as f:
        return json.load(f)


def fs_from_keyscene(path):
    """逐字取合同 FS 段：读 key-scene json 的 prompt 字段里「风格质感：」那一行，不做任何删减。"""
    d = load_json(path)
    for line in (d.get("prompt") or "").splitlines():
        t = line.strip()
        if t.startswith("风格质感："):
            return t[len("风格质感："):].strip()
    raise SystemExit("[ERR] %s 里找不到「风格质感：」行" % path)


def enclosure_lines(m):
    en, cn = [], []
    enc = m.get("enclosure") or {}
    for side in ("N", "E", "S", "W"):
        cell = enc.get(side) or {}
        ty = cell.get("type", "none")
        en.append("%s = %s" % (SIDE_NAME_EN[side], ENC_EN.get(ty, ty)))
        cn.append("%s（%s）= %s" % (SIDE_NAME_CN[side], SIDE_NAME_EN[side], ENC_CN.get(ty, ty)))
    return en, cn


def anchor_lines(m):
    en, cn, skipped = [], [], []
    for a in m.get("anchors", []):
        b = a.get("bearing", "C")
        nm = a.get("name", a.get("id"))
        if a.get("role") in ("light_feature", "boundary_only"):
            skipped.append("%s（%s）" % (nm, a.get("role")))
            continue
        extra = ""
        if a.get("state_at_open"):
            extra = ", %s" % a["state_at_open"]
        en.append("%s at the %s%s" % (nm, BEAR_EN.get(b, b), extra))
        cn.append("%s 位于%s%s" % (nm, BEAR_CN.get(b, b), extra))
    if skipped:
        en.append("(excluded from this reference by design: %s)" % ", ".join(skipped))
        cn.append("（按设计排除于基准图：%s）" % "、".join(skipped))
    return en, cn


def sea_clause(truth):
    sea = truth.get("sea_bearing")
    if sea not in SIDE_NAME_EN:
        return "", ""
    en = ("The sea lies ONLY to the %s, beyond that edge: show it as a DISTANT water surface with a clear "
          "horizontal horizon line and a narrow strip of shore, several tens of metres away, never as water, ice "
          "or a puddle on the ground. Nothing on the other edges reveals sea, shoreline, rocks or hills."
          % SIDE_NAME_EN[sea])
    cn = ("海只在%s：越过那一侧边缘呈现为远处的水面，有清晰水平海平线与一条窄岸线，距几十米，不得像地面上的水、"
          "冰或水洼。其余三面一律不得出现海、岸、礁石或丘陵。" % SIDE_NAME_CN[sea])
    return en, cn


def build_prompt(truth, m, fs_slot):
    enc_en, enc_cn = enclosure_lines(m)
    anc_en, anc_cn = anchor_lines(m)
    sea_en, sea_cn = sea_clause(truth)
    wl = m.get("object_whitelist", [])
    ev = m.get("env_evidence", [])

    en_blocks = [
        "[视角·固定] " + FIXED_VIEW_EN,
        "[风格槽·逐字取合同] " + (fs_slot or "{{FS_SLOT_UNRESOLVED}}"),
        ("[围合结构·四面必填] The space is enclosed by: " + "; ".join(enc_en) + "."),
        ("[锚点段·来自 space-truth，禁止增删] " + "; ".join(anc_en) + "."),
        "[纵深边界·方位钉死] " + (sea_en or "No external landmark bearing declared."),
        ("[环境证据段] Few and causal only: " + ("; ".join(ev) if ev else "none declared") + "."),
        "[光源段·中性基准] " + FIXED_LIGHT_EN,
        ("[反增殖·白名单闭合] Allowed objects: " + ", ".join(wl) + ". " + FIXED_ANTI_EN),
        "[排除与声明·固定] " + FIXED_EXCL_EN,
    ]
    cn_blocks = [
        "[视角·固定] " + FIXED_VIEW_CN,
        "[风格槽·逐字取合同] （见上方英文段，中文审稿以同一 FS 编号为准）",
        ("[围合结构·四面必填] 本空间围合为：" + "；".join(enc_cn) + "。"),
        ("[锚点段·来自 space-truth] " + "；".join(anc_cn) + "。"),
        "[纵深边界·方位钉死] " + (sea_cn or "未声明外部地标方位。"),
        ("[环境证据段] 少量有因果的痕迹：" + ("；".join(ev) if ev else "无") + "。"),
        "[光源段·中性基准] " + FIXED_LIGHT_CN,
        ("[反增殖·白名单闭合] 允许出现的物件仅限：" + "、".join(wl) + "。" + FIXED_ANTI_CN),
        "[排除与声明·固定] " + FIXED_EXCL_CN,
    ]
    return en_blocks, cn_blocks


def topology_band(m):
    """给拓扑图用的锚点带（同一来源，两条链不再各写一遍）。"""
    enc_en, _ = enclosure_lines(m)
    anc_en, _ = anchor_lines(m)
    return ("[固定锚点带·与空间真理图同源] " + "; ".join(enc_en) + ". " + "; ".join(anc_en) + ".")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--truth", required=True)
    ap.add_argument("--out")
    ap.add_argument("--fs")
    ap.add_argument("--fs-from-keyscene")
    ap.add_argument("--master")
    ap.add_argument("--topology-band", action="store_true")
    ap.add_argument("--allow-unapproved", action="store_true")
    args = ap.parse_args()

    truth = load_json(args.truth)

    bad = run_gates(truth)
    if bad:
        print("[FAIL] space-truth 门禁未过，拒绝派生：")
        for g, msg in bad:
            print("  %s | %s" % (g, msg))
        return 2

    if truth.get("approved") is not True and not args.allow_unapproved:
        print("[BLOCKED] approved=false —— 布局尚未拍板，不进出图环节。"
              "确认无误后把 space-truth.json 的 approved 改为 true，或用 --allow-unapproved 出草稿。")
        return 2

    fs_slot = args.fs
    if args.fs_from_keyscene:
        fs_slot = fs_from_keyscene(args.fs_from_keyscene)

    masters = [m for m in truth.get("masters", []) if not args.master or m.get("id") == args.master]
    if not masters:
        print("[ERR] 找不到母版 %s" % args.master)
        return 3

    if args.topology_band:
        print(topology_band(masters[0]))
        return 0

    out = args.out
    if not out:
        print("[ERR] 需要 --out 指定输出文件（新文件名，勿覆盖既有 asset-prompts.md）")
        return 3

    lines = []
    lines.append("# 空间基准图（layout）提示词 · %s" % truth.get("episode", ""))
    lines.append("")
    lines.append("> 派生自 `%s`（唯一写入点）。**本文件由 gen-layout-prompt.py 生成，手改视为污染**；"
                 "改布局请改 space-truth.json 后重跑本脚本。" % os.path.basename(args.truth))
    lines.append("> 与既有场景资产（主图 / §A 全景鸟瞰 / B 九宫格 / C 总览 / 上帝视角）**并存**，不替代、不改写它们。")
    lines.append("> **单张不可采信**：同一条提示词出 3~4 张，取共同出现的物件为事实，只出现在一张里的判为幻觉。")
    lines.append("> 垫图时槽位语义为 `role=layout`（仅提供几何与材质，不规定机位与时段）。")
    lines.append("")
    for m in masters:
        en_b, cn_b = build_prompt(truth, m, fs_slot)
        lines.append("## %s %s" % (m.get("id"), m.get("name")))
        lines.append("")
        lines.append("prompt（英文·生图执行）")
        lines.append("")
        lines.append("```text")
        lines.extend(en_b)
        lines.append("```")
        lines.append("")
        lines.append("prompt_cn（中文·理解审稿）")
        lines.append("")
        lines.append("```text")
        lines.extend(cn_b)
        lines.append("```")
        lines.append("")

    with io.open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    print("[ OK ] 已生成 %s（%d 个母版）" % (out, len(masters)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
