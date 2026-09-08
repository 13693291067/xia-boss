#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
backfill-pipeline-xiaju-first.py — 把存量旧项目的流水线断点回填为"剧本先行"。

背景：xia-boss 自 v3.1.0 起统一"剧本先行"（虾剧=流程第 1 步、虾料之前），新项目的
pipeline-state.json 初始 current=xiaju-script。但**已存在的旧项目**里 current 可能仍停在
"xialiao-ingest" / "chapter-1"（旧口径：虾料先、最后写第一章），且还没跑到虾格。本脚本把这类
项目安全地回填为 current=xiaju-script，并把 modules 里 xiaju-script 前置。

判定"可回填"（必须同时满足，避免把已推进的项目打回）：
  - current ∈ {xialiao-ingest, chapter-1, confirm-xialiao}（或为空）
  - modules.xiaju-script.status != completed（虾剧还没做完）
  - modules.xiage-styles.status ∈ {缺失, "", not_started}（还没进虾格，说明没越过剧本先行阶段）

安全：默认 dry-run 只打印将做的改动；`--apply` 才写盘；写盘前对 pipeline-state.json 生成一次 .bak；
若项目目录存在 xiaji.db，则同步改其 snapshots 表 module='pipeline' 的 current/顺序。

用法：
  python backfill-pipeline-xiaju-first.py <项目目录 或 pipeline-state.json> [...] [--apply]
  传目录会递归找 pipeline-state.json；也可一次传多个。
"""
import sys, os, json, glob, shutil, datetime

OLD_CURRENTS = {"xialiao-ingest", "chapter-1", "confirm-xialiao", ""}


def _now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _eligible(state):
    cur = state.get("current", "")
    mods = state.get("modules", {}) or {}
    xj = (mods.get("xiaju-script") or {}).get("status", "")
    xg = (mods.get("xiage-styles") or {}).get("status", "")
    if cur not in OLD_CURRENTS:
        return False, f"current={cur!r} 不在旧值集合，跳过"
    if xj == "completed":
        return False, "虾剧已 completed，勿打回，跳过"
    if xg not in ("", "not_started", None):
        return False, f"已推进到虾格(status={xg!r})，越过剧本先行阶段，跳过"
    return True, f"current {cur!r} → 'xiaju-script'（虾剧 status={xj or 'not_started'}）"


def _reorder_modules(mods):
    """把 xiaju-script 提到 xialiao-ingest 之前（仅当两者都在且顺序相反）。"""
    if not isinstance(mods, dict):
        return mods, False
    keys = list(mods.keys())
    if "xiaju-script" not in keys or "xialiao-ingest" not in keys:
        return mods, False
    if keys.index("xiaju-script") < keys.index("xialiao-ingest"):
        return mods, False
    # 重建：xiaju-script 插到 xialiao-ingest 前
    out = {}
    moved = False
    for k in keys:
        if k == "xiaju-script":
            continue  # 稍后在 xialiao-ingest 前重建
        if k == "xialiao-ingest" and not moved:
            out["xiaju-script"] = mods["xiaju-script"]
            moved = True
        out[k] = mods[k]
    return out, True


def process(path, apply_changes):
    try:
        raw = open(path, encoding="utf-8").read()
        state = json.loads(raw)
    except Exception as e:
        print(f"[跳过] 读取/解析失败 {path}: {e}")
        return 0
    if not isinstance(state, dict):
        print(f"[跳过] 非预期结构 {path}")
        return 0

    ok, why = _eligible(state)
    print(f"\n=== {path} ===\n  {why}")
    if not ok:
        return 0

    new_state = dict(state)
    new_state["current"] = "xiaju-script"
    mods, reordered = _reorder_modules(dict(state.get("modules", {}) or {}))
    # 保证 xiaju-script 键存在（老项目可能压根没登记这个模块）
    if "xiaju-script" not in mods:
        mods = {"xiaju-script": {"status": "not_started", "handoff": "", "finished_at": ""}, **mods}
        reordered = True
    new_state["modules"] = mods
    hist = list(new_state.get("history", []) or [])
    hist.append({"module": "xiaju-script", "action": "backfill-xiaju-first", "time": _now()})
    new_state["history"] = hist
    new_state["updated_at"] = _now()
    print(f"  → current='xiaju-script'；modules xiaju 前置={reordered}；追加 history 标记")

    if not apply_changes:
        print("  [dry-run] 未写盘（加 --apply 生效）")
        return 1

    bak = path + ".bak"
    if not os.path.exists(bak):
        shutil.copy2(path, bak)
        print(f"  已备份 → {os.path.basename(bak)}")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(new_state, f, ensure_ascii=False, indent=2)
    print(f"  ✓ 已写回 pipeline-state.json")

    # 同步 SQLite 快照 module='pipeline'（真实布局：db 在 <项目根>/project/xiaji.db，其次同级）
    root = os.path.dirname(path)
    db = next((p for p in (os.path.join(root, "project", "xiaji.db"),
                           os.path.join(root, "xiaji.db")) if os.path.exists(p)), None)
    print("  提示：回填后建议重跑 `python scripts/build-data-js.py <项目根>` 以刷新 resume_guide。")
    if db:
        try:
            import sqlite3
            conn = sqlite3.connect(db)
            row = conn.execute("SELECT data FROM snapshots WHERE module='pipeline'").fetchone()
            if row:
                try:
                    pdata = json.loads(row[0])
                    pdata["current"] = "xiaju-script"
                    pmods, _ = _reorder_modules(dict(pdata.get("modules", {}) or {}))
                    if "xiaju-script" not in pmods:
                        pmods = {"xiaju-script": {"status": "not_started", "handoff": "", "finished_at": ""}, **pmods}
                    pdata["modules"] = pmods
                    conn.execute("INSERT OR REPLACE INTO snapshots(module,data,updated_at) VALUES(?,?,?)",
                                 ("pipeline", json.dumps(pdata, ensure_ascii=False), _now()))
                    conn.commit()
                    print(f"  ✓ 已同步 {os.path.relpath(db, root)} 的 pipeline 快照")
                except Exception as e:
                    print(f"  ⚠ {os.path.basename(db)} 更新跳过（可后续重跑 build-data-js.py）：{e}")
            conn.close()
        except Exception as e:
            print(f"  ⚠ 打开 {os.path.basename(db)} 失败：{e}")
    else:
        print("  （未发现 xiaji.db，仅改了 pipeline-state.json）")
    return 1


def collect_targets(args):
    files = []
    for a in args:
        if os.path.isfile(a) and os.path.basename(a) == "pipeline-state.json":
            files.append(a)
        elif os.path.isdir(a):
            direct = os.path.join(a, "pipeline-state.json")
            if os.path.isfile(direct):
                files.append(direct)
            files.extend(sorted(glob.glob(os.path.join(a, "**", "pipeline-state.json"), recursive=True)))
        else:
            print(f"[warn] 不是目录也不是 pipeline-state.json：{a}")
    # 去重保序
    seen, uniq = set(), []
    for f in files:
        rp = os.path.realpath(f)
        if rp not in seen:
            seen.add(rp); uniq.append(f)
    return uniq


def main():
    argv = sys.argv[1:]
    apply_changes = "--apply" in argv
    paths = [a for a in argv if not a.startswith("--")]
    if not paths:
        print(__doc__); sys.exit(2)
    targets = collect_targets(paths)
    if not targets:
        print("未找到任何 pipeline-state.json。"); sys.exit(1)
    print(f"模式：{'APPLY（写盘）' if apply_changes else 'DRY-RUN（只预览）'}；扫描到 {len(targets)} 个 pipeline-state.json")
    changed = sum(process(t, apply_changes) for t in targets)
    print(f"\n合计{'回填' if apply_changes else '待回填'}：{changed} 个项目。")
    if changed and not apply_changes:
        print("确认无误后，加 --apply 执行。")


if __name__ == "__main__":
    main()
