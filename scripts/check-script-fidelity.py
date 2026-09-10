#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""虾镜·剧本保真机械门禁（check-script-fidelity）
来源：2026-09-09 事故固化——虾镜 shots 凭记忆/大纲拆镜导致"自创拍、台词改写、漏拍"，
本门禁把「按剧本来」变成机械可查的四查（缺一即 FAIL）：
  A 秒段覆盖   ：剧本 ep{NNN}.md 的每个秒段（循环N·X—Y秒）至少被 1 个镜头的 source 引用；
  B 出处合法   ：每镜 source 必须精确指向剧本中真实存在的秒段（禁自造出处）；
  C 台词逐字   ：C1 剧本每条台词必须逐字出现在某镜 dialogue；C2 每镜 dialogue 中的每句
                台词必须逐字来自剧本（双向夹击，抓"改写台词"与"自创台词"）。
  D 符号越界   ：dialogue 含 {} 台词标记却无「」引号 → C2 会静默致盲，报错（{} 只属 video_prompt）。
用法：
  python scripts/check-script-fidelity.py <项目根> --ep N
  python scripts/check-script-fidelity.py <项目根> --script <md路径> --shots <json路径>   # 便于投毒对照
退出码：0 = 通过；1 = 存在问题。
纪律：本脚本零硬编码项目词，通用解析；配套纪律见 modules/xiajing-episodes/SKILL.md 纪律14⑦。"""
import argparse, io, json, os, re, sys

def read(p):
    return io.open(p, encoding="utf-8").read()

def norm(s):
    """统一引号/空白，供逐字比对（「」『』与弯引号互转，去空白）。"""
    s = s.replace("「", "\u201c").replace("」", "\u201d")
    s = s.replace("『", "\u201c").replace("』", "\u201d")
    return re.sub(r"\s+", "", s)

def extract_quote_bodies(text):
    """兼容三种引号制式：ASCII "..."、弯引号 “...”、直角 「...」。返回引号内文本列表。"""
    t = text.replace("「", "\u201c").replace("」", "\u201d").replace("『", "\u201c").replace("』", "\u201d")
    out = []
    for m in re.finditer(r"\u201c([^\u201d\n]+)\u201d", t):
        out.append(m.group(1))
    for m in re.finditer(r'"([^"\n]+)"', t):
        out.append(m.group(1))
    return out

def script_segments_and_quotes(md):
    """解析剧本：返回 (秒段集合, 台词引文列表)。引文取『台词』字段内成对引号内容。"""
    segs = set()
    for m in re.finditer(r"^###\s*(循环\d+·\d+—\d+秒)\s*$", md, re.M):
        segs.add(m.group(1))
    quotes = []
    for line in md.splitlines():
        if "【台词】" not in line:
            continue
        body = line.split("【台词】", 1)[1]
        for q in extract_quote_bodies(body):
            nq = norm(q)
            if len(nq) >= 2:
                quotes.append(nq)
    return segs, quotes

def shot_quotes(dialogue):
    return [norm(q) for q in extract_quote_bodies(dialogue) if len(norm(q)) >= 2]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--ep", type=int)
    ap.add_argument("--script")
    ap.add_argument("--shots")
    args = ap.parse_args()
    root = os.path.abspath(args.root)
    ep = args.ep
    script_path = args.script or os.path.join(root, "outputs", "xiaju", "ep%03d.md" % ep)
    shots_path = args.shots or os.path.join(root, "outputs", "xiajing", "ep%03d" % ep, "shots.json")
    for p in (script_path, shots_path):
        if not os.path.exists(p):
            print("❌ 文件不存在:", p); sys.exit(1)
    md = read(script_path)
    doc = json.loads(read(shots_path))
    shots = doc.get("shots", [])
    segs, script_quotes = script_segments_and_quotes(md)
    problems = []

    # ---- A. 秒段覆盖：每个剧本秒段至少被 1 镜 source 引用 ----
    used = set()
    missing_source = []
    for i, s in enumerate(shots):
        src = str(s.get("source") or "").strip()
        if not src:
            missing_source.append(str(s.get("shot_number") or (i + 1)))
            continue
        used.add(src)
    for seg in sorted(segs):
        if seg not in used:
            problems.append("[A秒段未覆盖] 剧本秒段「%s」没有任何镜头引用（漏拍）" % seg)
    if missing_source:
        problems.append("[A秒段未覆盖] %d 镜缺 source 字段（镜号：%s）" % (len(missing_source), "、".join(missing_source[:10])))

    # ---- B. 出处合法：每镜 source 必须是剧本真实秒段 ----
    for s in shots:
        src = str(s.get("source") or "").strip()
        if src and src not in segs:
            problems.append("[B出处非法] 镜%s source=「%s」在剧本中不存在（自造出处/笔误）" % (s.get("shot_number"), src))

    # ---- C. 台词逐字（双向）----
    script_qset = "\n".join("\x00" + q for q in script_quotes)  # 用哨兵做包含判定
    # C1 剧本台词 → 必须逐字出现在某镜 dialogue
    all_dia_norm = [norm(str(s.get("dialogue") or "")) for s in shots]
    for q in script_quotes:
        if not any(q in d for d in all_dia_norm):
            problems.append("[C1台词丢失] 剧本台词「%s…」未逐字出现在任何镜头 dialogue（漏/改写）" % q[:24])
    # C2 镜头台词 → 必须逐字来自剧本
    script_norm_all = norm("\n".join(script_quotes))  # 剧本引文合集（用于包含判定）
    for s in shots:
        num = s.get("shot_number")
        for q in shot_quotes(str(s.get("dialogue") or "")):
            if q not in script_norm_all and q not in script_qset:
                # 容错：合并镜可能把两条剧本引文拼进同一句——按“任一剧本引文是它的子串”判定
                if not any(qq in q for qq in script_quotes if len(qq) >= 2):
                    problems.append("[C2台词自创/改写] 镜%s 台词「%s…」不是剧本原文（凭记忆改写）" % (num, q[:24]))

    # ---- D. 符号越界：{} 误入分镜 dialogue 且无「」→ C2 静默致盲 ----
    for s in shots:
        dia = str(s.get("dialogue") or "")
        if re.search(r"\{[^{}]{2,}\}", dia) and not shot_quotes(dia):
            problems.append("[D符号越界] 镜%s dialogue 含 {} 台词标记却无「」引号——本门禁只从「」/引号提台词，此镜 C2「防自创台词」已静默失效。分镜台词须用「」、{} 只进 video_prompt" % (s.get("shot_number") or "?"))


    # ---- E. 草图层存在性与模板合规（★ 2026-09-10 3.5.12 新增）----
    # 条款正本 = xiajing-episodes SKILL.md 纪律 15：sketch_prompt 用中文固定模板
    #   「黑白草图，{画面描述}。；快速铅笔线条，未完成感，干净纸面。」
    # 为什么放在保真门禁：旧版 A/B/C/D 全在查「已有字段对不对」，渔村 ep001 因此出现
    #   「sketch_prompt 0/51 整层缺失、门禁仍 PASS」——协作约定要求草图/首帧/视频逐项给全。
    _sk_has = [s for s in shots if str(s.get("sketch_prompt") or "").strip()]
    if shots and not _sk_has:
        problems.append("[E草图层] 整层缺失：%d/%d 镜无 sketch_prompt——草图是低成本验构图/站位/机位的前置层，"
                        "跳过它等于每镜直接从文字跳到成品级首帧；协作约定要求草图/首帧/视频逐项给全"
                        % (len(shots), len(shots)))
    else:
        _miss = [str(s.get("shot_number") or "?") for s in shots if not str(s.get("sketch_prompt") or "").strip()]
        if _miss:
            problems.append("[E草图层] %d/%d 镜缺 sketch_prompt：%s"
                            % (len(_miss), len(shots), "、".join(_miss[:10])))
        # 逐镜按规则引擎校验（规则正本 = xiajing-episodes/references/sketch-prompt-spec.md，
        # 引擎 = scripts/sketch_rules.py；本门禁不另立判据，避免规则出现第二副本）
        try:
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            import sketch_rules as _SR
        except Exception as e:
            _SR = None
            problems.append("[E草图规则] 无法载入 sketch_rules（%s）——E 项已降级为仅查框架" % e)
        for s in shots:
            sp = str(s.get("sketch_prompt") or "").strip()
            if not sp:
                continue
            if _SR is not None:
                _chars = str(s.get("characters") or u"")
                _hc = bool(_chars.strip()) and (u"空镜" not in _chars)
                bad = _SR.validate(sp, has_character=_hc)
                for b in bad:
                    problems.append("[E草图规则] 镜%s %s ｜%s" % (s.get("shot_number"), b, sp[:36]))
            elif not (sp.startswith(u"黑白草图，") and u"快速铅笔线条" in sp and u"干净纸面" in sp):
                problems.append("[E草图模板] 镜%s 不合固定模板框架" % s.get("shot_number"))

    print("剧本秒段: %d | 剧本台词引文: %d | 镜头: %d" % (len(segs), len(script_quotes), len(shots)))
    if problems:
        print("❌ 剧本保真门禁 FAIL：%d 处问题" % len(problems))
        for p in problems[:40]:
            print("  -", p)
        if len(problems) > 40:
            print("  ……（其余 %d 条略）" % (len(problems) - 40))
        sys.exit(1)
    print("✅ 剧本保真门禁 PASS：秒段全覆盖 / 出处全部合法 / 台词双向逐字一致 / 草图层齐备")


def selftest():
    """投毒对照：临时造最小项目（剧本 + shots），证明 E 项真会报、干净时不误报。"""
    import contextlib
    import os as _os
    import shutil
    import tempfile
    print("=== check-script-fidelity --selftest：投毒对照 ===")
    tmp = tempfile.mkdtemp(prefix="csf_selftest_")
    _os.makedirs(_os.path.join(tmp, "outputs", "xiaju"))
    _os.makedirs(_os.path.join(tmp, "outputs", "xiajing", "ep001"))
    md = ("### 循环1\u00b70\u20143\u79d2\n\n- **\u3010\u753b\u9762\u3011 \u89d2\u8272A \u7ad9\u7acb\uff0c\u8bf4\uff1a"
          "\u300c\u53f0\u8bcd\u7532\u3002\u300d\n")
    io.open(_os.path.join(tmp, "outputs", "xiaju", "ep001.md"), "w", encoding="utf-8").write(md)

    def build(mode):
        shot = {"shot_number": "001", "source": u"循环1\u00b70\u20143\u79d2",
                "scene_name": u"场甲 \u00b7 区1", "dialogue": u"\u89d2\u8272A\uff1a\u300c\u53f0\u8bcd\u7532\u3002\u300d",
                "duration": 3}
        if mode == "clean":
            shot["sketch_prompt"] = (u"黑白草图，场甲 · 区1；角色A 站立于区1 右侧，抬手推开门，角色B 蹲在门内侧；"
                                 u"构图 双人对角、门框占右三分之一，画面右；中近景·平视。；"
                                 u"快速铅笔线条，未完成感，干净纸面。")
        elif mode == "bad_template":
            shot["sketch_prompt"] = u"角色A 站立，彩色效果图。"
        elif mode == "bad_rule":
            # 框架齐、内容违规：神态未剥离 + 缺侧别断言（证明 §3.2 剥离表与 §四 侧别硬规则在生效）
            shot["sketch_prompt"] = (u"黑白草图，场甲 · 区1；角色A 眼神震惊地望向门口，神色僵住；"
                                     u"构图 双人对角；中近景·平视。；"
                                     u"快速铅笔线条，未完成感，干净纸面。")
        doc = {"shots": [shot]}
        io.open(_os.path.join(tmp, "outputs", "xiajing", "ep001", "shots.json"), "w", encoding="utf-8").write(
            json.dumps(doc, ensure_ascii=False))

    cases = [(u"投毒\u00b7整层缺失", "missing", True),
             (u"投毒\u00b7模板不符", "bad_template", True),
             (u"投毒\u00b7神态未剥离缺侧别", "bad_rule", True),
             (u"干净\u00b7草图齐备", "clean", False)]
    failed = 0
    for label, mode, expect in cases:
        build(mode)
        sys.argv = ["check-script-fidelity.py", tmp, "--ep", "1"]
        buf = io.StringIO()
        old = sys.stdout
        sys.stdout = buf
        try:
            try:
                main()
            except SystemExit:
                pass
        finally:
            sys.stdout = old
        rep = buf.getvalue()
        hit = "[E草图" in rep
        ok = (hit == expect)
        if not ok:
            failed += 1
        print("  [%s] %-16s 期望报=%s 实际=%s" % ("OK" if ok else "\u274c 空转/误报", label, expect, hit))
    shutil.rmtree(tmp, ignore_errors=True)
    return 1 if failed else 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.argv = [a for a in sys.argv if a != "--selftest"]
        sys.exit(selftest())
    main()
