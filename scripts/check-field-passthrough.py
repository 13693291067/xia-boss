#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
字段透传差集检查（check-field-passthrough.py）
==============================================
为什么要它：`build-data-js.py` 是**白名单装配**——只有显式列出的键才会进 SQLite 快照，
数据文件里多出来的字段会被**静默丢弃**。本批次连着踩了两次（`voice_desc`、`sketch_prompt`
写进 registry/shots 后重建为 None），且此前没有任何检查能发现。

原理：比对「数据源里的键集合」与「db 快照里的键集合」，
      源里有、db 里没有 = 被白名单吞掉（P1）；已知有意不落库的键走豁免表。

用法：
  python check-field-passthrough.py <项目根> [--ep N]
  python check-field-passthrough.py --selftest      # 投毒对照，证明不空转

退出码：0=无问题；1=有 P1。
"""

import argparse
import io
import json
import os
import sqlite3
import sys

# 有意不落库的键（改了要在这里说明理由，否则视为漏放行）
EXEMPT = {
    "shots": {
        "uid",            # 前端行内稳定 id，由工作台自管
        "is_edited",      # 编辑态标记，运行时产物
        "annotated_image",
        "original_shot",
    },
    "characters": set(),
    "scenes": set(),
    "props": set(),
    "episodes": set(),
}

# shots.json 顶层元数据：由 build-data-js 自行推导（episode→ep 号、total_duration→Σ镜、notes 仅文档），
# 前端不消费，故有意不落库
TOPLEVEL_EXEMPT = {"episode", "notes", "total_duration"}


def _keys(items):
    out = set()
    for it in items or []:
        if isinstance(it, dict):
            out.update(it.keys())
    return out


def compare(root, ep=None):
    issues = []
    dbp = os.path.join(root, "project", "xiaji.db")
    if not os.path.exists(dbp):
        return [("P1", "xiaji.db", u"未找到项目台数据库，无法比对（先跑 build-data-js.py）")]
    con = sqlite3.connect(dbp)
    try:
        def snap(mod):
            row = con.execute("select data from snapshots where module=?", (mod,)).fetchone()
            return json.loads(row[0]) if row and row[0] else {}
        regp = os.path.join(root, "outputs", "xiatang", "assets-registry.json")
        if os.path.exists(regp):
            reg = json.load(io.open(regp, encoding="utf-8"))
            xt = snap("xiatang")
            for kind in ("characters", "scenes", "props", "key_scenes"):
                src = _keys(reg.get(kind))
                dst = _keys(xt.get(kind))
                lost = sorted((src - dst) - EXEMPT.get(kind, set()))
                if lost:
                    issues.append(("P1", "assets-registry:%s" % kind,
                                   u"源有、快照无（被 build-data-js 白名单丢弃）：%s" % u"、".join(lost)))
        sp = None
        if ep is not None:
            sp = os.path.join(root, "outputs", "xiajing", "ep%03d" % ep, "shots.json")
        else:
            base = os.path.join(root, "outputs", "xiajing")
            if os.path.isdir(base):
                subs = sorted(os.listdir(base))
                for sub in subs:
                    cand = os.path.join(base, sub, "shots.json")
                    if os.path.exists(cand):
                        sp = cand
                        break
        if sp and os.path.exists(sp):
            doc = json.load(io.open(sp, encoding="utf-8"))
            xj = snap("xiajing")
            eps = xj.get("episodes") or []
            dst_shot = _keys(eps[0].get("shots") if eps else [])
            lost = sorted((set(doc.keys()) - set(eps[0].keys() if eps else {})) - EXEMPT["episodes"] - TOPLEVEL_EXEMPT) \
                if eps else []
            if lost:
                issues.append(("P1", "shots.json:顶层", u"源有、快照无：%s" % u"、".join(lost)))
            lost2 = sorted((_keys(doc.get("shots")) - dst_shot) - EXEMPT["shots"])
            if lost2:
                issues.append(("P1", "shots.json:shots[]",
                               u"源有、快照无（被白名单丢弃，前端拿不到）：%s" % u"、".join(lost2)))
    finally:
        con.close()
    return issues


def selftest():
    """投毒对照：合成数据必须报、一致必须不报。"""
    print(u"=== check-field-passthrough --selftest：投毒对照 ===")
    src = {u"characters": [{u"name": u"A", u"voice_desc": u"x", u"prompt": u"y"}]}
    dst_ok = {u"characters": [{u"name": u"A", u"voice_desc": u"x", u"prompt": u"y"}]}
    dst_bad = {u"characters": [{u"name": u"A", u"prompt": u"y"}]}

    def diff(src, dst, exempt):
        s = _keys(src.get("characters"))
        d = _keys(dst.get("characters"))
        return sorted((s - d) - exempt)

    cases = [
        (u"投毒·快照少 voice_desc", diff(src, dst_bad, set()), [u"voice_desc"]),
        (u"干净·键一致", diff(src, dst_ok, set()), []),
        (u"豁免·少 exempted", diff({u"characters": [{u"uid": u"1"}]}, {u"characters": [{}]}, {u"uid"}), []),
    ]
    failed = 0
    for name, got, want in cases:
        ok = got == want
        if not ok:
            failed += 1
        print(u"  [%s] %-22s 期望=%s 实际=%s" % (u"OK" if ok else u"❌ 空转/误报", name, want or u"无", got or u"无"))
    return 1 if failed else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", nargs="?")
    ap.add_argument("--ep", type=int)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        sys.exit(selftest())
    if not args.root:
        print(u"用法：check-field-passthrough.py <项目根> [--ep N]")
        sys.exit(2)
    issues = compare(os.path.abspath(args.root), args.ep)
    for sev, where, msg in issues:
        print(u"[%s] %s :: %s" % (sev, where, msg))
    n_p1 = len([i for i in issues if i[0] == "P1"])
    print(u"字段透传差集：P1 %d" % n_p1)
    if not issues:
        print(u"✅ 数据源字段与项目台快照键一致（无被白名单吞掉的字段）")
    else:
        print(u"→ 修法：在 build-data-js.py 对应装配处显式放行该字段，并同步 scripts/ 与 templates/ 两份副本，"
              u"再跑 build-data-js.py 复验")
    sys.exit(1 if n_p1 else 0)


if __name__ == "__main__":
    main()
