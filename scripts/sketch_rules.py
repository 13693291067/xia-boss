# -*- coding: utf-8 -*-
"""
草图提示词规则引擎（sketch_rules.py）
======================================
规范正本 = `modules/xiajing-episodes/references/sketch-prompt-spec.md`；本模块只负责把其中的
词表与判据**代码化一份供复用**，供两个调用方共用，避免规则出现第二副本：
  · scripts/gen-sketch-prompts.py   —— 按规则从 shots.json 派生 sketch_prompt
  · scripts/check-script-fidelity.py —— E 项按规则逐镜校验

纪律：本文件禁止出现任何具体项目数据（角色名/场景名/剧名），词表一律通用。
"""

import io
import re

HEAD = u"黑白草图，"
TAIL = u"。；快速铅笔线条，未完成感，干净纸面。"
MIN_LEN = 20
MAX_LEN = 160

# ── §3.1 姿态动作（保留：构图骨架必须可画）──
POSE_WORDS = [
    u"跪", u"蹲", u"坐", u"站", u"立", u"俯身", u"弯腰", u"转身", u"回头", u"抬手", u"伸手", u"指",
    u"抱拳", u"拱手", u"揪", u"拧", u"推", u"拉", u"拽", u"递", u"接", u"端", u"捧", u"提", u"拎",
    u"抓", u"按", u"剁", u"切", u"撒", u"舀", u"搅", u"拨", u"挑", u"掀", u"跑", u"冲", u"奔",
    u"走", u"跨", u"绊", u"踉跄", u"倚", u"靠", u"扑", u"挡", u"护", u"叉腰", u"掸", u"拍", u"抹",
    u"探头", u"背身", u"侧身", u"低头", u"抬头", u"蹲下", u"站起", u"揉", u"擦", u"看", u"望",
    u"环视", u"扫视", u"举", u"拿", u"放", u"趴", u"躺", u"侧卧", u"凑近", u"逼近", u"退步",
    u"闪", u"避", u"扑", u"甩", u"拢", u"拽住", u"扑空", u"扫过",
]

# ── §3.2 剥离词表（命中即违规）──
BAN_EXPRESSION = [u"震惊", u"愣住", u"瞪大", u"嘴角", u"似笑非笑", u"目光", u"眼神", u"神色", u"神情",
                  u"面色", u"脸红", u"冷笑", u"含泪", u"怨毒", u"媚", u"挑眉", u"眯眼", u"眉", u"嘴唇"]
BAN_MIND = [u"心想", u"暗想", u"意识到", u"明白", u"脑海", u"记忆灌入", u"回忆", u"内心", u"OS",
            u"想起", u"认出", u"心里"]
# 一律多字：单字「说/道/哗」会误伤「道具/村道/知道/哗然」（dry-run 实测踩到）
BAN_SPEECH = [u"说道", u"答道", u"喊道", u"骂道", u"沉声", u"冷声", u"低语", u"画外音", u"台词",
              u"自语", u"呢喃", u"刺啦", u"哐", u"轰然", u"话音"]
BAN_DEGREE = [u"猛地", u"缓缓", u"轻描淡写", u"仿佛", u"似乎", u"一瞬间", u"时间静止", u"慢了一拍",
              u"仿佛静止", u"下一秒"]
BAN_METAPHOR = [u"像", u"如", u"似的", u"般"]
# 非入画标记：这些角色/注记不进草图画面
NON_VISUAL_MARKS = [u"画外", u"OS", u"背景", u"远景", u"未入画", u"仅眼", u"不见人", u"（远"]

ALL_BAN = {
    u"表情神态": BAN_EXPRESSION,
    u"心理活动": BAN_MIND,
    u"台词声音": BAN_SPEECH,
    u"程度节奏": BAN_DEGREE,
}

# ── §2 要素5 可画的场景特效物 ──
FX_NOUNS = [u"水汽", u"蒸汽", u"尘土", u"光束", u"浮尘", u"浮渣", u"散落", u"湿痕", u"草屑",
            u"烟", u"火苗", u"灰烬", u"阴影", u"雨", u"雪"]

# ── 景别与机位高度映射（草图不写焦段/运镜/时长）──
FRAME_CN = [(u"特写", u"特写"), (u"近景", u"近景"), (u"中近", u"中近景"), (u"中全", u"中全景"),
            (u"中景", u"中景"), (u"全景", u"全景"), (u"远景", u"远景"), (u"大远", u"大远景")]
ANGLE_WORDS = [u"低机位", u"高机位", u"顶视", u"过肩", u"平视", u"略俯", u"略仰", u"俯", u"仰"]
SIDE_WORDS = [u"画面左", u"画面右", u"画面上", u"画面下", u"居中", u"前景", u"背景",
              u"下缘", u"上缘", u"左缘", u"右缘", u"深处", u"门口入画"]


def cn_frame(shot_type):
    st = shot_type or u""
    for key, cn in FRAME_CN:
        if key in st:
            return cn
    return u"中景"


def cn_angle(camera):
    cam = camera or u""
    hits = [w for w in ANGLE_WORDS if w in cam]
    return hits[0] if hits else u"平视"


def extract_side(text):
    for w in SIDE_WORDS:
        if w in (text or u""):
            return w
    return u""


def strip_banned(clause):
    """按 §3.2 丢弃违规子句用的判断：命中任一剥离类即视为不可入画面描述。"""
    for cat, words in ALL_BAN.items():
        for w in words:
            if w in clause:
                return True
    return False


def has_pose(clause):
    return any(w in clause for w in POSE_WORDS)


def build_desc(scene_name, characters, action, visual, composition, shot_type, camera):
    """按 §五 派生 {画面描述}。返回 (desc, 缺失要素列表)。不臆造：侧别取不到就记缺失。"""
    missing = []
    parts = []

    parts.append(scene_name or u"（缺场景）")
    if scene_name is None or not str(scene_name).strip():
        missing.append(u"场景")

    src = (action or u"").strip() or (visual or u"").strip()
    # 动作链用「→」连接，必须一并切开：否则一个 banned 词会连坐整句（实测"揉拧耳朵→眼神发怔"）
    clauses = [c.strip() for c in re.split(u"[，。；、,→]+", src) if c.strip()]
    # ① 无剥离词即保留（姿态白名单只用于排序，不作准入闸门——白名单永远不全）
    clean = [c for c in clauses if not strip_banned(c)]
    clean.sort(key=lambda c: (0 if has_pose(c) else 1), )
    kept = clean[:2]
    if not kept:
        # ② 整句都带剥离词：剥掉违规片段，剩余够画就保留
        for c in clauses[:2]:
            residue = c
            for words in ALL_BAN.values():
                for w in words:
                    residue = residue.replace(w, u"")
            residue = residue.strip(u"，、 ")
            if len(residue) >= 3:
                kept.append(residue)
        kept = kept[:2]
    # 角色名清洗：去括号注记，再剔除"画外/OS/背景/远景/未入画"等非入画标记（不进画面描述）
    # 先按原始 token 判非入画标记（含括号注记），再剥括号——否则「角色B（画外·不见人）」会被剥成「角色B」画进草图（草图只画可见物）
    _toks = [t0 for t0 in re.split(u"[、,，]", characters or u"")
             if t0.strip() and not any(x in t0 for x in NON_VISUAL_MARKS)]
    who = u"、".join([re.sub(u"[（(][^）)]*[）)]", u"", x).strip() for x in _toks]).strip()
    if kept:
        seg = who + u" " + u"，".join(kept) if who else u"，".join(kept)
        parts.append(seg)
    elif who:
        # 有角色却无可画动词：草稿仍出全四段，但显式留占位——不臆造、不静默降级成空镜
        parts.append(u"【待人工补姿态】" + who)
        missing.append(u"姿态动作")
    else:
        parts.append(u"空镜无人物")

    # composition 二级切分：按「、」再切，只丢违规子项（"近景居中、画外音留白" 不该整段丢）
    first = (composition or u"").split(u"；")[0].strip()
    subs = [x.strip() for x in re.split(u"[、,，]", first) if x.strip()]
    # 违规片段只删词不删段（"近景眼神定住特写" → "近景定住特写"），避免整段连坐丢构图
    _clean_subs = []
    for x in subs:
        if strip_banned(x):
            residue = x
            for words in ALL_BAN.values():
                for w in words:
                    residue = residue.replace(w, u"")
            x = residue.strip(u"，、 ")
        if x:
            _clean_subs.append(x)
    comp = u"、".join(_clean_subs)
    side = extract_side(composition)
    if comp and side and side not in comp:
        comp = comp + u"，" + side
    if comp:
        parts.append(u"构图 " + comp if not comp.startswith(u"构图") else comp)
        if not side:
            missing.append(u"侧别断言")
    else:
        missing.append(u"构图")

    parts.append(cn_frame(shot_type) + u"·" + cn_angle(camera))

    fx = [w for w in FX_NOUNS if w in (visual or u"")][:2]
    if fx:
        parts.append(u"环境物 " + u"、".join(fx))

    return u"；".join([p for p in parts if p]), missing


def make(scene_name, characters, action, visual, composition, shot_type, camera):
    desc, missing = build_desc(scene_name, characters, action, visual, composition, shot_type, camera)
    return HEAD + desc + TAIL, missing


def validate(text, has_character=True):
    """E 项用：返回违规说明列表（空＝合规）。"""
    out = []
    t = (text or u"").strip()
    if not t:
        return [u"缺 sketch_prompt"]
    if not (t.startswith(HEAD) and t.endswith(TAIL)):
        out.append(u"框架不符（须「%s{画面描述}%s」）" % (HEAD, TAIL))
    body = t[len(HEAD):len(t) - len(TAIL)] if (t.startswith(HEAD) and t.endswith(TAIL)) else t
    n = len(re.findall(u"[一-鿿]", body))
    if n < MIN_LEN:
        out.append(u"画面描述过短（%d 字 < %d）" % (n, MIN_LEN))
    if n > MAX_LEN:
        out.append(u"画面描述过长（%d 字 > %d）" % (n, MAX_LEN))
    for cat, words in ALL_BAN.items():
        hit = [w for w in words if w in body]
        if hit:
            out.append(u"%s未剥离：%s" % (cat, u"/".join(hit[:3])))
    segs = [x for x in body.split(u"；") if x.strip()]
    if len(segs) < 4:
        out.append(u"五要素不足（实得 %d 段，须≥场景/人物动作/构图/镜头 4 段）" % len(segs))
    if has_character and not extract_side(body):
        out.append(u"缺侧别断言（画面左/画面右/居中/前景/背景）")
    if re.search(u"\d+\s*(mm|秒|s\b)", body, re.I):
        out.append(u"草图不得写焦段/时长")
    if u"【待人工补" in body:
        out.append(u"含待人工补占位（脚本不臆造，需人补姿态动作后重跑校验）")
    return out


def selftest():
    """断言：本模块词表 == 规范正本 §3.2 表格（双向逐词）。防止「正本落后于实现」。"""
    import os as _os
    import re as _re
    spec = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..",
                         "modules", "xiajing-episodes", "references", "sketch-prompt-spec.md")
    t = io.open(spec, encoding="utf-8").read()
    pairs = [(u"表情神态", BAN_EXPRESSION), (u"心理活动", BAN_MIND),
             (u"台词与声音", BAN_SPEECH), (u"程度与节奏", BAN_DEGREE)]
    bad = 0
    print(u"=== sketch_rules --selftest：规范词表漂移检查 ===")
    for cat, words in pairs:
        m = _re.search(u"\\| " + cat + u".*?\\| (.*?) \\|", t)
        if not m:
            print(u"  [\u274c] 规范缺类别：%s" % cat)
            bad += 1
            continue
        listed = [x for x in m.group(1).split(u"／") if x.strip()]
        only_spec = [w for w in listed if w not in words]
        only_code = [w for w in words if w not in listed]
        ok = not only_spec and not only_code
        if not ok:
            bad += 1
        print(u"  [%s] %-8s 规范多:%s 代码多:%s" % (u"OK" if ok else u"\u274c 漂移", cat,
                                                only_spec or u"—", only_code or u"—"))
    return 1 if bad else 0


if __name__ == u"__main__":
    import sys as _sys
    if u"--selftest" in _sys.argv:
        import io as _io
        _sys.exit(selftest())
