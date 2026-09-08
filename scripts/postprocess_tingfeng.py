#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
postprocess_tingfeng.py —— 听风 tingfeng.json 契约后处理器（skill 契约可执行件）
================================================================================
★ 2026-09-06 新增。背景：项目本地生成脚本（gen_tingfeng_*.py）不读 skill 模板文档，
  只抄名词不抄制度，导致 camera 四段式 / 执行约束块 / 母题进词 / 引用裁剪 / route /
  高危词转译全部缺席（实战项目 ep001 实测 224 条）。本脚本把契约变成「任何项目
  生成脚本跑完后必跑的一道闸」。

功能（按执行序）：
  1. route 推断写入（战斗词>奇观词>收束词>默认文戏）
  2. 镜重拆（--camera-map 提供 reshard 时按新镜表替换 shots；内容设计由人/AI 提供，
     本脚本不做机械切分）
  3. camera 四段式回填（--camera-map 按 段→镜号 匹配；缺 map 的镜列入待设计清单）
  4. 设计注记剥离：visual 中「（A·B·C）」标签式括号移出正文，存 seg['_design_notes']
  5. 高危词转译：visual/dialogue/exit_hook/continuity_header 同步转译（与
     references/shared-compliance-lexicon.md 同步；语义降级处写报告待人工复核）
  6. 引用行重建：剥 {{类型:}} 包裹 → 按本段实际出现裁剪（场景/拓扑保留，角色/道具按出现）
  7. 母题进词：stage1.motif_table 出现于本段的规格 → 执行约束块；并回填「进词片段」字段
  8. full_text 重建（shots 派生）→ video_prompt 重建（引用行+STYLE+全文+[执行约束]+[AVOID]）
  9. H3 六段重建（标准序；英文骨架+画面原文直嵌）
 10. 自动复验：调 check-fidelity.py 输出残留问题分类

用法：
  python postprocess_tingfeng.py <项目根> --ep 1 [--camera-map map.json]
      [--dry-run] [--out report.md] [--script <check-fidelity.py 路径>]
"""
import argparse
import collections
import json
import os
import re
import subprocess
import sys

# ================= 转译表（★ 与 references/shared-compliance-lexicon.md 同步） =================
TRANSLATE_PAIRS = [
    # (高危词, 转译) —— 执行时按长度降序，长词优先
    # —— 首批（词典 base）
    ("挑落数十骑", "挑翻数十骑"),
    ("挑落", "挑翻"),
    ("斩落", "扫落马下"),
    ("毙命", "失去战力倒地"),
    ("毙敌", "击溃"),
    ("挑起首级", "挑飞兜鍪"),
    ("割下头颅", "挑飞兜鍪"),
    ("渗血", "甲缝暗色洇开"),
    ("流血", "暗色浸痕"),
    ("出血", "暗色浸痕"),
    ("血线", "暗色凝痕"),
    ("淌血", "暗色凝痕滑下"),
    ("血流", "暗色凝痕"),
    ("血滴", "暗色液滴断续坠落"),
    ("血珠", "暗色凝珠"),
    ("滴血", "暗红点滴"),
    ("血迹", "暗色浸痕"),
    ("鲜血", "暗色液体"),
    ("首级", "兜鍪"),
    # —— 2026-09-06 实战项目 ep001 追加（与词典 md 同步）
    ("劈成两半", "连人带盾砸飞"),
    ("血溅", "暗色液沫溅上"),
    ("血自甲缝涌出", "暗色浸痕自甲缝洇开"),
    ("半身是血", "半身染满暗色浸痕"),
    ("刀自前胸穿出", "刀锋贯入前胸甲缝"),
    ("血线喷在", "暗色凝痕溅在"),
    ("尸山", "倒伏甲士垒成的高坡"),
    ("尸横处", "倒伏处"),
    ("尸堆", "倒伏甲士堆"),
    ("尸身", "倒地士卒"),
    ("首次杀人", "初阵迎敌"),
    ("浴血浴火立于", "携一身火光立于"),
    ("气绝", "再无动静"),
]

# route 推断关键词（优先级：战斗 > 奇观 > 收束 > 文戏）
# ★ 强战斗词：命中 1 个即武戏；★ 弱战斗词：需 ≥2 个不同命中（单字武器词过宽——
#   「枪痕裂地」「枪立如林」这类收束段画面也会含"枪"，单字命中即判武戏会大面积误判）
RE_BATTLE_STRONG = re.compile(r"(打斗|对决|交手|厮杀|血战|追杀|突围|掩杀|冲杀|缠斗|突袭|反击|白刃|格挡|挑翻|斩|劈|砍)")
RE_BATTLE_WEAK = re.compile(r"(刺|扫|扎|挡|箭|刃|拳)")
RE_SPECTACLE = re.compile(r"(法阵|异象|天降|祭坛|祭台|魔相|爆发|崩断|撕裂|冲天|轰然|绽放)")
RE_WRAP = re.compile(r"(回望|清点|残员|收兵|风过|余烬|静立|凝滞|对峙|尘落|落定|硝烟散)")

# 设计注记（标签式括号）：内容含 ≥2 个 · 分隔片段即视为注记
NOTE_RE = re.compile(r"（([^（）]*·[^（）]*)）")

CAM4_RE = re.compile(r"^(ECU|CU|MCU|MS|WS|ELS)\s*·\s*[^·]{2,}\s*·\s*[^·]{2,}\s*·\s*跟随[^·]{2,}$")
TS_RE = re.compile(r"([\d.]+)\s*s?\s*[–—\-~至]\s*([\d.]+)\s*s?")
TOPO_NAME = "空间拓扑图"
TYPE_PREFIX_RE = re.compile(r"^(?:角色|场景|道具|拓扑|空间拓扑图|场)\s*[:：]\s*")
REF_PAIR_RE = re.compile(r"([^\s=，,、]+)=图(\d+)")

# ROUTE_RULES 与 check-fidelity.py 保持一致
ROUTE_RULES = {"文戏": (2, 3, 3.0, 6.0), "武戏": (4, 6, 1.5, 3.0),
               "奇观": (2, 3, 4.0, 7.0), "收束": (3, 4, 2.0, 4.0)}

FRAME_EN = {"ECU": "extreme close-up", "CU": "close-up", "MCU": "medium close-up",
            "MS": "medium shot", "WS": "full shot", "ELS": "extreme long shot"}


def translate_text(t):
    """高危词转译；返回 (新文本, 命中列表)。长词优先替换。"""
    hits = []
    if not t:
        return t, hits
    out = t
    for bad, good in sorted(TRANSLATE_PAIRS, key=lambda p: -len(p[0])):
        if bad in out:
            hits.append(f"{bad}→{good}")
            out = out.replace(bad, good)
    return out, hits


SENT_SPLIT_RE = re.compile(r"(?<=[。；！？])")


def balance_parens(t):
    """清理孤立的未闭合括号段（原文括号跨句切分点时产生）"""
    t = re.sub(r"（[^（）]*$", "", t)          # 尾部未闭合
    t = re.sub(r"^[^（）]*）", "", t) if t.startswith("）") else t  # 头部孤立闭合
    return t


def split_sentences(visual):
    return [p.strip() for p in SENT_SPLIT_RE.split(str(visual or "")) if p.strip()]


def resolve_take(ref, orig_shots_by_key):
    """take 引用："段:原镜号:句索引" → 原文句子（零抄写误差）"""
    parts = str(ref).split(":")
    if len(parts) != 3:
        return None
    sid, n, idx = parts[0], int(parts[1]), int(parts[2])
    sh = orig_shots_by_key.get((sid, n))
    if not sh:
        return None
    sents = split_sentences(sh.get("visual"))
    return sents[idx] if 0 <= idx < len(sents) else None


def strip_notes(visual):
    """剥离标签式设计注记括号；返回 (纯画面, 注记列表)"""
    notes = []

    def _grab(m):
        inner = m.group(1)
        if inner.count("·") >= 1 and len(inner) <= 60:
            notes.append(inner)
            return ""
        return m.group(0)

    cleaned = NOTE_RE.sub(_grab, visual)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
    cleaned = re.sub(r"。，", "。", cleaned)
    return cleaned, notes


def infer_route(seg):
    text = " ".join([str(seg.get("core_action") or "")] +
                    [str(sh.get("visual") or "") for sh in seg.get("shots", [])])
    if RE_BATTLE_STRONG.search(text) or len(set(RE_BATTLE_WEAK.findall(text))) >= 2:
        return "武戏"
    if RE_SPECTACLE.search(text):
        return "奇观"
    if RE_WRAP.search(text):
        return "收束"
    return "文戏"


def appearing_set(seg, names, aliases=None):
    """资产出现判定：全名或任一别名命中（★ 随身武器常以简称入文——
    「赤铜长枪岿然」在画面里写作「枪/红缨」，全名判定会过裁）"""
    aliases = aliases or {}
    text = " ".join([str(sh.get("visual") or "") + str(sh.get("dialogue") or "")
                     for sh in seg.get("shots", [])])
    out = set()
    for n in names:
        if n and (n in text or any(a in text for a in aliases.get(n, []))):
            out.add(n)
    return out


def rebuild_refline(seg, chars, prop_names, seg_index, prop_aliases=None):
    """重建引用行：★ 集级连续图号 base=(段序-1)*7（槽位=角色×4+场景+道具+拓扑），
    与既有垫图编号兼容（S13→85-91、S08→50-56 实测吻合）；裁剪跳号保严格递增"""
    base = seg_index * 7
    appear = appearing_set(seg, chars + prop_names, prop_aliases)
    items, dropped = [], []
    for i, c in enumerate(chars):
        if c in appear:
            items.append((c, base + i + 1))
        else:
            dropped.append(c)
    scene_nm = str(seg.get("scene") or "").strip()
    if scene_nm:
        items.append((scene_nm, base + 5))
    for p in prop_names:
        if p in appear:
            items.append((p, base + 6))
    topo_nm = str(seg.get("space_map") or "").strip()
    if topo_nm:
        items.append((topo_nm, base + 7))
    parts = [f"{nm}=图{pic}" for nm, pic in items]
    return " ".join(parts), dropped


def fmt_ts_start(ts):
    m = TS_RE.search(str(ts or ""))
    if not m:
        return None
    v = float(m.group(1))
    mm, ss = int(v // 60), v % 60
    return f"{mm:02d}:{ss:06.3f}"


def rebuild_full_text(seg):
    """从 shots 派生分镜全文（与 v2 生成格式一致）"""
    lines = [f"## {seg['id']} | {seg.get('duration')}s | {seg.get('core_action')}"]
    ch = str(seg.get("continuity_header") or "").strip()
    if ch:
        lines += ["", f"**承接/连续性：** {ch}"]
    for sh in seg.get("shots", []):
        lines += ["", f"**镜号 {int(sh.get('n', 0)):02d} | {sh.get('ts')} | {sh.get('camera')}**"]
        if str(sh.get("visual") or "").strip():
            lines.append(f"- 画面：{sh['visual']}")
        if str(sh.get("sound") or "").strip():
            lines.append(f"- 音效：{sh['sound']}")
        if str(sh.get("dialogue") or "").strip():
            lines.append(f"- 对白：{sh['dialogue']}")
    eh = str(seg.get("exit_hook") or "").strip()
    if eh:
        lines += ["", f"**退场钩子：** {eh}"]
    return "\n".join(lines)


def build_exec_block(seg, motif_rows, exec_notes):
    """构建 [执行约束] 块（追加区，不改写分镜文本 → 保真零破坏）"""
    lines = ["[执行约束]",
             "1. 位置锁：各出场人物首镜确立的左右站位全程不变，不换边、不越轴。",
             "2. 机位重申：各镜运镜与机位按镜号行声明执行，每镜开始时重申景别与角度，中途不得漂移为俯瞰或环绕。",
             "3. 接触锚定：每次攻击/受击必须落在具体身体部位或物件上并给出受力反馈；未写明接触点的动作不得自由发挥成打空。",
             "4. 外观锁定：不变脸、不换装、武器形态与握持手全程固定；禁止第三人凭空入镜。"]
    if motif_rows:
        lines.append("5. 母题锚点（本段必须呈现的资产规格）：" + "；".join(motif_rows) + "。")
    if exec_notes:
        lines.append("6. 本段专属负面：" + "；".join(exec_notes) + "。")
    return "\n".join(lines)


def build_h3(seg, assets, style_txt):
    """H3 全参考六段式重建（标准序；英文骨架 + 画面原文直嵌）"""
    refs = []
    m = re.search(r"\[引用行\]\s*(.+)", seg.get("video_prompt", ""))
    if m:
        refs = [(TYPE_PREFIX_RE.sub("", re.sub(r"^\{\{|\}\}$", "", n.strip())), int(p))
                for n, p in REF_PAIR_RE.findall(m.group(1))]
    topo = [(n, p) for n, p in refs if n == TOPO_NAME or n.startswith(TOPO_NAME + "·") or n.startswith(TOPO_NAME + "-")]
    subj = [(n, p) for n, p in refs if (n, p) not in topo]
    roles = {str(a.get("名")): str(a.get("type")) for a in assets}

    defs = []
    for i, (nm, pic) in enumerate(subj, 1):
        r = roles.get(nm, "道具")
        if r == "角色":
            defs.append(f"<Subject {i}> is the character {nm} referenced from the character reference sheet <Picture {pic}>, with fixed appearance, costume, and hairstyle to be preserved exactly.")
        elif r == "场景":
            defs.append(f"<Subject {i}> is the scene {nm} referenced from <Picture {pic}>.")
        else:
            defs.append(f"<Subject {i}> is the prop {nm} referenced from <Picture {pic}>.")
    if topo:
        n, p = topo[0]
        defs.append(f"<Picture {p}> is a spatial-planning reference (a top-down floor plan of the set) for [Shot 1] to [Shot {max(1, len(seg.get('shots', [])))}], defining relative positions, movement directions, and character blocking; on-screen spatial relationships must strictly follow this plan.")

    subj_labels = ", ".join(f"<Subject {i}>" for i in range(1, len(subj) + 1)) or "the referenced subjects"
    summary = (f"[reference generation] The target video shows {subj_labels} in a cinematic scene. "
               f"Character identity, costume, and appearance are locked to the referenced sheets"
               + (f"; spatial blocking follows the floor-plan reference <Picture {topo[0][1]}>" if topo else "") + ".")

    retain = []
    shots = seg.get("shots", [])
    for i, (nm, pic) in enumerate(subj, 1):
        hits = [f"[Shot {k}]" for k, sh in enumerate(shots, 1)
                if nm in (str(sh.get("visual") or "") + str(sh.get("dialogue") or ""))]
        where = f" (appears in {', '.join(hits)})" if hits else ""
        retain.append(f"<Subject {i}>{where}: fully_preserved - the referenced identity, costume, and key features are retained.")
    if topo:
        retain.append(f"<Picture {topo[0][1]}>: the spatial relationships, movement directions, and character blocking defined in the plan are followed in all shots above.")

    style_line = (style_txt.strip().rstrip(";") +
                  " ; This look applies only to the rendering medium, materials, lighting, and finish, "
                  "and must never be used to infer or change faces, ages, genders, body proportions, clothing, "
                  "accessories, props, or environments, which always follow the reference pictures and the on-script descriptions.")
    body = [style_line]
    for k, sh in enumerate(shots, 1):
        frame = str(sh.get("frame") or "").strip()
        fr = FRAME_EN.get(frame, "medium shot")
        at = "" if k == 1 else f" At {fmt_ts_start(sh.get('ts')) or f'{(k-1)*3:02d}:00.000'},"
        cam = str(sh.get("camera") or "")
        head = f"[Shot {k}]{at} A {fr} ({frame or 'MS'}) is declared"
        parts = [head + f" (on-script camera: {cam})."]
        if str(sh.get("visual") or "").strip():
            parts.append(f"On screen: {sh['visual']}")
        d = str(sh.get("dialogue") or "").strip()
        if d:
            mm = re.match(r"^([^：:]{1,20})[：:]\s*(.+)$", d)
            spk, quote = (mm.group(1), mm.group(2)) if mm else ("", d)
            parts.append(f"{spk + ' ' if spk else ''}(S1) says: <d>[Chinese] {quote}</d>")
        if str(sh.get("sound") or "").strip():
            parts.append(f"Diegetic sound: {sh['sound']}.")
        if topo:
            parts.append(f"Spatial blocking follows the floor plan in <Picture {topo[0][1]}>.")
        body.append(" ".join(parts))

    snds = []
    for sh in shots:
        t = str(sh.get("sound") or "").strip()
        if t and t not in snds:
            snds.append(t)
    soundscape = ("Diegetic ambience and effects throughout the scene include: " +
                  "; ".join(snds[:3]) + ("; and more." if len(snds) > 3 else ".") +
                  " Dialogue appears with its shots above.") if snds else "Ambient diegetic sound continues throughout the scene."

    return "\n".join([
        "subject_definitions:", *defs, "",
        "summary:", summary, "",
        "retention_analysis:", *retain, "",
        "detailed_description:", "\n".join(body), "",
        "overall_soundscape:", soundscape, "",
        "non_diegetic_music:", "N/A",
    ])


def extract_style(vp):
    m = re.search(r"\[STYLE\]\s*([\s\S]*?)(?=\n## |\[AVOID\]|$)", vp or "")
    return m.group(1).strip() if m else "CINEMATIC FILMIC REALISM, live-action, grounded historical realism."


def extract_avoid(vp):
    m = re.search(r"\[AVOID\]\s*([\s\S]*)$", vp or "")
    return m.group(1).strip() if m else ("FORBIDDEN: anime, cartoon, illustration, plastic skin, AI artifacts, "
                                          "extra limbs, mutated hands, deformed faces, text, watermarks, labels;")


def expand_battle_ids(combat_design):
    """combat_design[].段 展开为段号集合（区间写法 S07-S08 拆两段）"""
    ids = set()
    for row in combat_design or []:
        raw = str(row.get("段") or row.get("id") or "")
        m = re.match(r"^([A-Za-z]*)(\d+)\s*[-–—~]\s*([A-Za-z]*)(\d+)$", raw)
        if m:
            pre, a, _, b = m.group(1), int(m.group(2)), m.group(3), int(m.group(4))
            w = len(m.group(2))
            ids.update(f"{pre}{i:0{w}d}" for i in range(a, b + 1))
        elif raw:
            ids.update(x.strip() for x in raw.split("、") if x.strip())
    return ids


def process_segment(seg, assets, motif_table, cam_map, seg_map, rep, battle_ids=frozenset(),
                    chars=None, prop_names=None, seg_index=0, prop_aliases=None):
    sid = seg["id"]
    changed = []

    # 1. route（★ 登记优先：combat_design 登记的段 = 设计判断的战斗段，强制武戏；
    #    推断只兜底未登记段——与 check-fidelity ⑦/D2「登记即生效」同源）
    old_route = seg.get("route")
    if seg["id"] in battle_ids:
        seg["route"] = seg_map.get(seg["id"], {}).get("route", "武戏")
    else:
        seg["route"] = seg_map.get(seg["id"], {}).get("route") or old_route or infer_route(seg)
    if seg["route"] != old_route:
        changed.append(f"route {old_route!r}→{seg['route']!r}")

    # ★ 2026-09-07 v3：战斗登记段 = seedance-combat-prompt 外协提示词整段回流，
    #   跳过文戏重建管线（不 reshard/不重建 full_text/不产 H3/不追加执行块）。
    #   契约：references/shared-fight-dispatch.md。唯一动作：负面四禁缺失时并入负面提示词行。
    if sid in battle_ids:
        ft_b = str(seg.get("full_text") or "").strip()
        if ft_b:
            if "武器形态漂移" not in ft_b:
                four = ("禁止武器形态漂移：兵器形态与握持全程固定；禁止动作接触失真：每次接触"
                        "必须落在声明的接触点，不得打空或先击飞；禁止力量反馈缺失：受击必须给出位移或"
                        "形变反馈；禁止慢动作滥用：不出现慢镜/定格/时间延展")
                m_neg = re.search(r"(负面提示词[:：][^\n]*)", ft_b)
                if m_neg:
                    ft_b = ft_b[:m_neg.end()] + "；" + four + ft_b[m_neg.end():]
                else:
                    ft_b = ft_b + "\n负面提示词：" + four
                changed.append("战斗段负面四禁并入")
            seg["full_text"] = ft_b
            seg["video_prompt"] = ft_b
            seg.setdefault("video_prompts", {})["seedance"] = ft_b
        else:
            rep["reshard_needed"].append(f"{sid}（battle_segments 登记段缺 full_text——seedance 外协提示词未回流）")
        return changed

    # 2. reshard（内容设计层提供；take=引原文句，visual=显式文本，二者必有其一）
    rm = seg_map.get(sid, {}).get("reshard")
    if rm:
        orig_by_key = {(seg["id"], int(sh.get("n", 0))): sh for sh in seg.get("shots", [])}
        new_shots = []
        for k, item in enumerate(rm, 1):
            vis = item.get("visual")
            if not vis and item.get("take"):
                parts = [resolve_take(t, orig_by_key) for t in item["take"]]
                vis = "".join(p for p in parts if p)
            vis = balance_parens(str(vis or ""))
            new_shots.append({"n": k, "ts": item.get("ts"), "frame": item.get("frame", ""),
                              "camera": item.get("camera", ""), "visual": vis,
                              "dialogue": item.get("dialogue", ""), "sound": item.get("sound", "")})
        seg["shots"] = new_shots
        changed.append(f"重拆 {len(new_shots)} 镜")

    # 3. camera 回填（无 reshard 时按镜号匹配）
    cm = cam_map.get(sid, {})
    for sh in seg["shots"]:
        v = cm.get(str(sh.get("n"))) or cm.get(int(sh.get("n", 0)))
        if v and not CAM4_RE.match(str(sh.get("camera") or "")):
            sh["camera"] = v
            changed.append(f"镜{sh['n']} camera 四段式")

    # 4/5. 注记剥离 + 高危词转译（visual/dialogue/exit_hook/continuity_header）
    all_hits, all_notes = [], []
    for sh in seg["shots"]:
        v, notes = strip_notes(str(sh.get("visual") or ""))
        if notes:
            all_notes += notes
            sh["visual"] = v
        t, hits = translate_text(str(sh.get("visual") or ""))
        if hits:
            sh["visual"] = t
        t2, hits2 = translate_text(str(sh.get("dialogue") or ""))
        if hits2:
            sh["dialogue"] = t2
        all_hits += hits + hits2
    eh, eh_notes = strip_notes(str(seg.get("exit_hook") or ""))
    if eh_notes:
        all_notes += eh_notes
        seg["exit_hook"] = eh
    for key in ("exit_hook", "continuity_header"):
        t, hits = translate_text(str(seg.get(key) or ""))
        if hits:
            seg[key] = t
            all_hits += hits
    if all_notes:
        seg["_design_notes"] = all_notes
        changed.append(f"剥离设计注记 {len(all_notes)} 条")
    if all_hits:
        changed.append("转译 " + "、".join(sorted(set(all_hits))))

    # 6. 引用行重建（★ 真实集级图号：资产清单从 stage1.asset_ref 类级说明解析）
    new_ref, dropped = rebuild_refline(seg, chars or [], prop_names or [], seg_index, prop_aliases)
    if dropped:
        changed.append("引用裁剪 " + "、".join(dropped))
    used_chars = [c for c in chars if c not in dropped]
    seg["_assets_used"] = [{"type": "角色", "名": c} for c in used_chars] + \
                          [{"type": "场景", "名": str(seg.get("scene") or "")}] + \
                          [{"type": "道具", "名": p} for p in prop_names if p in appearing_set(seg, prop_names, prop_aliases)]

    # 7. 母题进词
    vis_all = " ".join(str(sh.get("visual") or "") for sh in seg["shots"])
    motif_rows = []
    for mrow in motif_table:
        nm = str(mrow.get("母题") or "")
        spec = str(mrow.get("规格") or mrow.get("进词片段") or "")
        appear = str(mrow.get("出现段") or "")
        if (nm and nm in vis_all) or sid in re.findall(r"S\d+", appear):
            motif_rows.append(spec or nm)
            if not mrow.get("进词片段") and spec:
                mrow["进词片段"] = spec
    if motif_rows:
        changed.append(f"母题进词 {len(motif_rows)} 条")

    # 8. full_text / video_prompt 重建（★ seedance 同步：门禁⑤检查两字段一致性）
    ft = rebuild_full_text(seg)
    seg["full_text"] = ft
    style = extract_style(seg.get("video_prompt", ""))
    avoid = extract_avoid(seg.get("video_prompt", ""))
    exec_block = build_exec_block(seg, motif_rows, seg_map.get(sid, {}).get("negative", []))
    seg["video_prompt"] = (f"[引用行] {new_ref}\n[STYLE] {style}\n\n{ft}\n\n{exec_block}\n\n[AVOID] {avoid}")
    # ★ ⑦战斗四禁：门禁在 [负面] 标记段检查四个 fight 关键词（负面区追加不破保真）。
    #   适用 = route 武戏/收束 或 combat_design 登记段（登记含蓄力/收尾段，四禁对其无害有益）
    if seg.get("route") in ("武戏", "收束") or sid in battle_ids:
        seg["video_prompt"] = seg["video_prompt"].replace(
            "[AVOID]",
            "[负面] 禁止武器形态漂移：枪斧刀形态与握持全程固定；禁止动作接触失真：每次接触"
            "必须落在声明的接触点，不得打空或先击飞；禁止力量反馈缺失：受击必须给出位移或"
            "形变反馈；禁止慢动作滥用：慢镜仅限分镜声明的时码段。\n[AVOID]")
    seg.setdefault("video_prompts", {})["seedance"] = seg["video_prompt"]

    # 9. H3 重建
    seg.setdefault("video_prompts", {})["h3"] = build_h3(seg, assets, style)

    # 10. 镜数/时长合规预检（报告用）
    lo, hi, tlo, thi = ROUTE_RULES.get(seg["route"], (2, 4, 1.5, 7.0))
    n = len(seg["shots"])
    if not lo <= n <= hi:
        rep["reshard_needed"].append(f"{sid}（route={seg['route']} 需 {lo}-{hi} 镜，现 {n} 镜）")
    for sh in seg["shots"]:
        m = TS_RE.search(str(sh.get("ts") or ""))
        if m and not tlo <= float(m.group(2)) - float(m.group(1)) <= thi:
            rep["reshard_needed"].append(f"{sid} 镜{sh.get('n')} 单镜 {float(m.group(2)) - float(m.group(1)):.1f}s 超出 {seg['route']} 档 {tlo}-{thi}s")
            break
    return changed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--ep", type=int, default=None)
    ap.add_argument("--file", default=None)
    ap.add_argument("--camera-map", default=None)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true",
                    help="允许对已后处理的文件重复运行（默认拒绝：take 引用会错位污染数据）")
    ap.add_argument("--out", default=None)
    ap.add_argument("--script", default=None)
    a = ap.parse_args()

    here = os.path.dirname(os.path.abspath(__file__))
    fidelity = a.script or os.path.join(here, "check-fidelity.py")

    if a.file:
        files = [a.file if os.path.isabs(a.file) else os.path.join(a.root, a.file)]
    else:
        base = os.path.join(a.root, "outputs", "tingfeng")
        files = []
        for d in sorted(os.listdir(base)):
            fp = os.path.join(base, d, "tingfeng.json")
            if os.path.isfile(fp):
                files.append(fp)
    if a.ep:
        files = [f for f in files if f"ep{a.ep:03d}" in f or f"ep{a.ep}" in f]

    cam_map, seg_map, data = {}, {}, {}
    if a.camera_map and os.path.isfile(a.camera_map):
        data = json.load(open(a.camera_map, encoding="utf-8"))
        cam_map = data.get("camera", {})
        seg_map = data.get("segments", {})
    elif a.camera_map:
        # ★ 自检修正（2026-09-06b）：设计映射传了但文件不存在 = 静默跳过的坏失败
        #   （内容设计项会全部缺失而脚本照常产出），必须显式报错退出
        sys.exit(f"✗ --camera-map 文件不存在：{a.camera_map}（设计映射是内容设计项，缺失即停，禁止静默跳过）")

    rep = {"changed": [], "reshard_needed": [], "dropped_all": []}
    for fp in files:
        d = json.load(open(fp, encoding="utf-8"))
        # ★ 自检修正（2026-09-06b）：防重复运行污染——take 引用按「原始镜号」解析，
        #   对已后处理文件二次运行会从新镜表错位抓句。检测 generator 标记即拒，--force 逃生
        if "postprocess@" in str(d.get("generator") or "") and not a.force:
            sys.exit(f"✗ {fp} 已经过后处理（generator 含 postprocess 标记）。二次运行会因 take 引用错位污染数据；"
                     f"如确需重跑：先由生成脚本重建 tingfeng.json，或加 --force 自担风险")
        assets = d.get("stage1", {}).get("asset_ref") or []
        motif_table = d.get("stage1", {}).get("motif_table") or []
        battle_ids = expand_battle_ids(d.get("combat_design"))
        # ★ 2026-09-07 v3：battle_segments 直读（ep 级段号数组，兼容区间写法）——与 check-fidelity 同源
        for raw in (d.get("battle_segments") or []):
            for piece in re.split(r"[、,，]", str(raw)):
                piece = piece.strip()
                m2 = re.match(r"^([A-Za-z]*)(\d+)\s*[-–—~]\s*([A-Za-z]*)(\d+)$", piece)
                if m2:
                    pre, aa, _, bb = m2.group(1), int(m2.group(2)), m2.group(3), int(m2.group(4))
                    w2 = len(m2.group(2))
                    battle_ids.update(f"{pre}{i:0{w2}d}" for i in range(aa, bb + 1))
                elif piece:
                    battle_ids.add(piece)
        # ★ 资产清单解析：asset_ref 是类级说明（名含斜杠组合），拆成段级可用清单
        chars, prop_names = [], []
        for ar in assets:
            names = [x.strip() for x in str(ar.get("名") or "").split("/")]
            if ar.get("类型") == "角色":
                chars = names
            elif ar.get("类型") == "道具":
                prop_names = names
        prop_aliases = data.get("prop_aliases", {}) if a.camera_map else {}
        if not assets:
            print(f"⚠ {fp} 无 stage1.asset_ref，引用重建跳过")
        for idx, seg in enumerate(d.get("segments", [])):
            ch = process_segment(seg, assets, motif_table, cam_map, seg_map, rep, battle_ids,
                                 chars=chars, prop_names=prop_names, seg_index=idx,
                                 prop_aliases=prop_aliases)
            if ch:
                rep["changed"].append(f"{seg['id']}: " + "; ".join(ch))
        if not a.dry_run:
            d["generator"] = d.get("generator", "") + " +postprocess@2.9.0"
            json.dump(d, open(fp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    lines = ["# 听风后处理报告", "", f"- 文件：{len(files)} 个", f"- 有改动段数：{len(rep['changed'])}", ""]
    lines += ["## 改动明细"] + [f"- {c}" for c in rep["changed"]] + [""]
    if rep["reshard_needed"]:
        lines += ["## ⚠ 待重拆镜（内容设计项，脚本不越权）"] + [f"- {x}" for x in rep["reshard_needed"]]
    report = "\n".join(lines)
    print(report[:3000])
    if a.out:
        open(a.out, "w", encoding="utf-8").write(report)

    # 11. 自动复验
    if not a.dry_run:
        cmd = [sys.executable, fidelity, a.root] + (["--ep", str(a.ep)] if a.ep else [])
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        tail = (r.stdout or "").splitlines()
        keep = [l for l in tail if ("段总数" in l or "问题总数" in l or "高危词表" in l)]
        print("\n===== check-fidelity 复验 =====")
        print("\n".join(keep) or "(无输出)")
        sys.exit(r.returncode)


if __name__ == "__main__":
    main()
