#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""check-style-library.py — 虾格风格库（种子层/用户层）脱敏与结构校验

为什么存在：最高纪律"禁止项目数据污染"的锚定示例白名单只覆盖 modules/<模块>/references/，
而 v3.4.0-风格库 新增的 modules/xiage-styles/styles-library/ 不在名单内。库的设计前提是
"条目入库前必须剥离剧名/角色/专有世界观词"，此前只靠人自觉、无机械校验。本脚本把这条
变成可复跑的硬门禁（词表从项目真实数据动态取，脚本内零硬编码项目词）。

用法：
    python scripts/check-style-library.py                     # 只跑结构校验（脱敏校验 SKIP）
    python scripts/check-style-library.py --project <项目根>  # 结构 + 脱敏（词表取自该项目）
    python scripts/check-style-library.py --layer seed        # 只校 skill 种子层
    python scripts/check-style-library.py --word 某角色名 --word 某地名   # 追加人工词

退出码：0=通过（含 SKIP 计数）；1=有 P0/P1 问题。
纪律：输出禁 emoji（Windows GBK 控制台会 UnicodeEncodeError）。
"""
import argparse
import io
import json
import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)                      # xia-boss 包根
SEED_DIR = os.path.join(ROOT, "modules", "xiage-styles", "styles-library")
USER_DIR = os.path.expanduser(os.path.join("~", ".qwenworkcn", "xiage-style-library"))

REQUIRED = ["style_id", "style_label", "family", "style_tag",
            "style_instructions", "avoid_instructions"]
# 疑似剧名/专名的硬标记：中文书名号
TITLE_MARKS = ("\u300a", "\u300b")


def iter_strings(obj, trail):
    """递归产出 (字段路径, 字符串值)。"""
    if isinstance(obj, dict):
        for k, v in obj.items():
            for item in iter_strings(v, trail + "." + str(k)):
                yield item
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            for item in iter_strings(v, trail + "[%d]" % i):
                yield item
    elif isinstance(obj, str):
        yield trail, obj


def project_words(project_root):
    """从项目真实数据动态取"项目特定词"（零硬编码）：项目名 + 资产名称。
    数据源优先级：project/xiaji.db 快照（唯一权威数据源）> pipeline-state.json 的 project 字段。
    返回 (词表, 来源说明列表)。"""
    words, src = set(), []
    db = os.path.join(project_root, "project", "xiaji.db")
    if not os.path.exists(db):
        alt = os.path.join(project_root, "xiaji.db")
        db = alt if os.path.exists(alt) else None
    if db:
        src.append(os.path.relpath(db, project_root))
        con = sqlite3.connect(db)
        try:
            rows = con.execute("select module, data from snapshots").fetchall()
        except sqlite3.Error as e:
            rows = []
            src.append("(读取失败: %s)" % e)
        finally:
            con.close()
        for module, data in rows:
            try:
                obj = json.loads(data) if data else None
            except ValueError:
                continue
            for trail, val in iter_strings(obj, module):
                leaf = trail.rsplit(".", 1)[-1]
                if module == "meta" and leaf in ("name", "project_id", "style_label"):
                    words.add(val.strip())
                elif leaf in ("name", "title", "location", "label"):
                    words.add(val.strip())
    state = os.path.join(project_root, "pipeline-state.json")
    if os.path.exists(state):
        src.append("pipeline-state.json")
        try:
            st = json.load(io.open(state, encoding="utf-8"))
            if st.get("project"):
                words.add(str(st["project"]).strip())
        except ValueError:
            pass
    words.discard("")
    return sorted(w for w in words if len(w) >= 2), src


def check_entry(path, words, problems):
    name = os.path.basename(path)
    try:
        data = json.load(io.open(path, encoding="utf-8"))
    except ValueError as e:
        problems.append(("P0", name, "JSON 解析失败: %s" % e))
        return
    for f in REQUIRED:
        if not data.get(f):
            problems.append(("P0", name, "缺必填字段 %s" % f))
    sid = str(data.get("style_id", ""))
    if sid and sid + ".json" != name:
        problems.append(("P1", name, "style_id=%s 与文件名不一致" % sid))
    if str(data.get("family", "")) not in ("A", "B", "C", ""):
        problems.append(("P1", name, "family 应为 A/B/C（当前 %r）" % data.get("family")))
    if not data.get("confirmed_by_user"):
        problems.append(("P1", name, "confirmed_by_user 缺失/为假（入库条目须用户拍板）"))
    tag = str(data.get("style_tag", ""))
    if tag and (tag != tag.upper() or " " in tag.strip() and tag.islower()):
        problems.append(("P2", name, "style_tag 建议全大写标签纯净性（当前 %r）" % tag[:40]))

    hits = []
    for trail, val in iter_strings(data, "$"):
        v = val.strip()
        if not v:
            continue
        if any(mk in v for mk in TITLE_MARKS):
            problems.append(("P1", name, "字段 %s 含书名号，疑似剧名/专名未剥离: %s" % (trail, v[:60])))
        for w in words:
            if w and w in v:
                hits.append((trail, w, v[:60]))
    for trail, w, v in hits:
        problems.append(("P0", name, "脱敏失败：字段 %s 命中项目特定词「%s」（片段: %s）" % (trail, w, v)))


def main():
    ap = argparse.ArgumentParser(description="虾格风格库脱敏与结构校验")
    ap.add_argument("--project", help="项目根（用于动态取项目词表；缺省则脱敏校验 SKIP）")
    ap.add_argument("--layer", choices=["seed", "user", "all"], default="all")
    ap.add_argument("--dir", dest="extra_dir", help="额外要校的目录（如某项目的 outputs/styles）")
    ap.add_argument("--word", action="append", default=[], help="追加项目词（可重复）")
    args = ap.parse_args()

    words, src = [], []
    if args.project:
        words, src = project_words(args.project)
    words = sorted(set(words) | set(w.strip() for w in args.word if w.strip()))

    targets = []
    if args.layer in ("seed", "all"):
        targets.append(("seed", SEED_DIR))
    if args.layer in ("user", "all"):
        targets.append(("user", USER_DIR))
    if args.extra_dir:
        targets.append(("extra", args.extra_dir))

    problems = []
    scanned = 0
    for layer, d in targets:
        if not os.path.isdir(d):
            print("[skip-layer] %s 目录不存在: %s" % (layer, d))
            continue
        files = sorted(f for f in os.listdir(d) if f.endswith(".json"))
        print("[%s] %s（条目 %d）" % (layer, d, len(files)))
        for f in files:
            scanned += 1
            check_entry(os.path.join(d, f), words, problems)

    p0 = [p for p in problems if p[0] == "P0"]
    p1 = [p for p in problems if p[0] == "P1"]
    p2 = [p for p in problems if p[0] == "P2"]
    for lvl, name, msg in problems:
        print("%s %s: %s" % (lvl, name, msg))
    if src:
        word_origin = "（来源: " + ", ".join(src) + "）"
    elif words:
        word_origin = "（来源: --word 手工词）"
    else:
        word_origin = "（无词表，脱敏校验 SKIP）"
    print("-" * 56)
    print("扫描条目 %d | 项目词表 %d 项%s | P0=%d P1=%d P2=%d"
          % (scanned, len(words), word_origin, len(p0), len(p1), len(p2)))
    if not words:
        print("提示：未给 --project 时脱敏校验处于 SKIP 状态（只校结构）。入库验收前必须带 --project 复跑。")
    verdict = "FAIL" if (p0 or p1) else "PASS"
    print("VERDICT %s" % verdict)
    return 1 if (p0 or p1) else 0


if __name__ == "__main__":
    sys.exit(main())
