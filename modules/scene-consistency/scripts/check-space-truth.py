#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check-space-truth.py —— 空间真理图（space-truth.json）门禁，单源契约 space-truth/1

定位：真理图是「出处与校验层」，不进模型、不出图。本脚本是它唯一的机械执行器。
并存声明：本脚本不改动 check-assets.py / check-scenes.py / check-fidelity.py 的任何既有行为，
          只读 space-truth.json，独立可跑。

七道门禁：
  G1 锚点出处必填        —— 每个 anchor 要有 source；标 INFER 的必须给 basis
  G2 围合/边界四面必填   —— enclosed 必须 N/E/S/W 齐；linear|open 必须声明 sides
  G3 海（主地标）方位可达 —— sea_bearing 那一面不得是实墙/房屋，否则看不见
  G4 方位词表合法        —— bearing 只能取八方位 + C
  G5 基准光不携带时段    —— reference_lighting.no_time_signature 必须为 true
  G6 物件白名单闭合      —— 出 layout 图的母版必须有 object_whitelist，且 anchors 全部在册
  G7 确认门              —— approved=true 时不得存在 blocking 的未决矛盾
  G8 同名锚点跨母版自洽  —— 同 id 锚点方位冲突时，必须登记在 open_issues 里

用法：
  python check-space-truth.py --check <space-truth.json>
  python check-space-truth.py --selftest          # 投毒对照：坏样本必须被逐条抓到
  python check-space-truth.py --objects <json> --master SC-02
退出码：0 通过 / 2 门禁不过 / 3 用法或文件错误 / 4 自检失败
"""

import argparse
import copy
import io
import json
import sys

BEARINGS = {"N", "NE", "E", "SE", "S", "SW", "W", "NW", "C"}
ENCLOSED_TYPES = {"wall_solid", "wall_low", "fence", "house", "door", "window", "open", "edge_low", "landmark", "none"}
SIDES_TYPES = ENCLOSED_TYPES | {"n/a"}
SEA_VISIBLE_TYPES = {"open", "fence", "edge_low", "landmark", "window"}


def _fail(out, gate, msg):
    out.append((gate, msg))


def run_gates(data):
    """返回 [(门禁号, 说明)]，空列表 = 全过。"""
    bad = []

    if not isinstance(data, dict):
        return [("G0", "顶层不是对象")]

    # ---------- G1 锚点出处 ----------
    for m in data.get("masters", []):
        mid = m.get("id", "?")
        for a in m.get("anchors", []):
            src = (a.get("source") or "").strip()
            if not src:
                _fail(bad, "G1", "%s 锚点 %r 无 source（出处缺失）" % (mid, a.get("name")))
                continue
            if src.upper().startswith("INFER") and not (a.get("basis") or "").strip():
                _fail(bad, "G1", "%s 锚点 %r 标 INFER 但未给 basis 依据" % (mid, a.get("name")))

    # ---------- G2 围合/边界必填 ----------
    for m in data.get("masters", []):
        mid = m.get("id", "?")
        kind = m.get("kind")
        if kind == "enclosed":
            enc = m.get("enclosure") or {}
            for side in ("N", "E", "S", "W"):
                cell = enc.get(side)
                if not isinstance(cell, dict) or not (cell.get("type") or "").strip():
                    _fail(bad, "G2", "%s 围合 %s 面未声明（留空=交给生图模型自己补墙，权威旁落）" % (mid, side))
                elif cell["type"] not in ENCLOSED_TYPES:
                    _fail(bad, "G2", "%s 围合 %s 面 type %r 不在枚举" % (mid, side, cell["type"]))
        elif kind in ("linear", "open"):
            sides = m.get("sides") or {}
            if len(sides) < 2:
                _fail(bad, "G2", "%s kind=%s 但 sides 不足两面（线性/开放空间也要声明边界）" % (mid, kind))
            for side, cell in sides.items():
                if not isinstance(cell, dict) or cell.get("type") not in SIDES_TYPES:
                    _fail(bad, "G2", "%s sides %s 面 type 非法：%r" % (mid, side, cell))
        else:
            _fail(bad, "G2", "%s kind 缺失或非法：%r" % (mid, kind))

    # ---------- G3 海方位可达 ----------
    sea = data.get("sea_bearing")
    if sea not in ("N", "E", "S", "W"):
        _fail(bad, "G3", "sea_bearing 非法：%r（必须 N/E/S/W 之一）" % (sea,))
    else:
        for m in data.get("masters", []):
            if m.get("kind") != "enclosed":
                continue
            cell = (m.get("enclosure") or {}).get(sea)
            if isinstance(cell, dict) and cell.get("type") not in SEA_VISIBLE_TYPES:
                _fail(bad, "G3", "%s 的 %s 面是 %s，海在该向却看不见（围合与 sea_bearing 冲突）"
                      % (m.get("id"), sea, cell.get("type")))

    # ---------- G4 方位词表 ----------
    for m in data.get("masters", []):
        for a in m.get("anchors", []):
            if a.get("bearing") not in BEARINGS:
                _fail(bad, "G4", "%s 锚点 %r bearing 非法：%r" % (m.get("id"), a.get("name"), a.get("bearing")))

    # ---------- G5 基准光不携带时段 ----------
    rl = data.get("reference_lighting") or {}
    if rl.get("no_time_signature") is not True or rl.get("mode") != "neutral":
        _fail(bad, "G5", "reference_lighting 必须 mode=neutral 且 no_time_signature=true（基准图不得锁死影子方向/时段）")

    # ---------- G6 物件白名单闭合 ----------
    for m in data.get("masters", []):
        wl = m.get("object_whitelist")
        if not isinstance(wl, list) or not wl:
            _fail(bad, "G6", "%s 缺 object_whitelist（无白名单则无法机械判定生图增殖物件）" % m.get("id"))
            continue
        for a in m.get("anchors", []):
            role = a.get("role")
            if role in ("light_feature", "boundary_only"):
                continue          # 光态与纵深边界不是「画得出的物件」，不进白名单、不进基准图
            if role not in (None, "object", "prop"):
                _fail(bad, "G6", "%s 锚点 %r role 非法：%r（可用 object/prop/light_feature/boundary_only）"
                      % (m.get("id"), a.get("name"), role))
            nm = (a.get("name") or "").strip()
            if nm and not any(nm in w or w in nm for w in wl):
                _fail(bad, "G6", "%s 锚点 %r 未登记进 object_whitelist" % (m.get("id"), nm))

    # ---------- G7 确认门 ----------
    unresolved_blocking = [i.get("id") for i in data.get("open_issues", [])
                           if i.get("status") != "resolved" and i.get("blocking")]
    if data.get("approved") is True and unresolved_blocking:
        _fail(bad, "G7", "approved=true 但仍有未决阻断矛盾：%s" % ",".join(map(str, unresolved_blocking)))

    # ---------- G8 同名锚点跨母版自洽 ----------
    seen = {}
    for m in data.get("masters", []):
        for a in m.get("anchors", []):
            aid = a.get("id")
            if not aid:
                continue
            seen.setdefault(aid, []).append((m.get("id"), a.get("bearing")))
    issues_blob = json.dumps(data.get("open_issues", []), ensure_ascii=False)
    for aid, occ in seen.items():
        bearings = set(b for _, b in occ if b)
        if len(occ) > 1 and len(bearings) > 1 and aid not in issues_blob:
            _fail(bad, "G8", "锚点 %r 跨母版方位冲突 %s，却未登记在 open_issues（隐性矛盾不许静默通过）" % (aid, occ))

    return bad


# ---------------- 投毒对照（证明门禁不是空转） ----------------

def _clean_payload():
    return {
        "schema": "space-truth/1",
        "approved": False,
        "sea_bearing": "S",
        "reference_lighting": {"mode": "neutral", "no_time_signature": True},
        "masters": [
            {
                "id": "M1", "kind": "enclosed",
                "enclosure": {
                    "N": {"type": "house", "source": "x"},
                    "E": {"type": "wall_low", "source": "INFER", "basis": "对称"},
                    "S": {"type": "fence", "source": "L13"},
                    "W": {"type": "wall_low", "source": "INFER", "basis": "对称"},
                },
                "anchors": [{"id": "stove", "name": "土灶", "bearing": "E", "source": "INFER", "basis": "L53 动作链"}],
                "object_whitelist": ["土灶", "院心"],
            },
            {"id": "M2", "kind": "linear",
             "sides": {"N": {"type": "edge_low", "source": "INFER", "basis": "沉默"},
                       "S": {"type": "open", "source": "sea_bearing"}},
             "anchors": [{"id": "track", "name": "土路", "bearing": "C", "source": "S051"}],
             "object_whitelist": ["土路"]},
        ],
        "open_issues": [],
    }


POISONS = [
    ("G1", "锚点无出处", lambda d: d["masters"][0]["anchors"][0].pop("source")),
    ("G1", "INFER 无依据", lambda d: d["masters"][0]["anchors"][0].pop("basis")),
    ("G2", "围合少一面", lambda d: d["masters"][0]["enclosure"].pop("W")),
    ("G2", "线性空间无 sides", lambda d: d["masters"][1].pop("sides")),
    ("G3", "海向被实墙堵死", lambda d: d["masters"][0]["enclosure"].__setitem__("S", {"type": "wall_solid", "source": "x"})),
    ("G4", "方位词非法", lambda d: d["masters"][0]["anchors"][0].__setitem__("bearing", "上边")),
    ("G5", "基准光带时段", lambda d: d["reference_lighting"].__setitem__("no_time_signature", False)),
    ("G6", "白名单缺失", lambda d: d["masters"][0].pop("object_whitelist")),
    ("G6", "锚点未入白名单", lambda d: d["masters"][0].__setitem__("object_whitelist", ["院心"])),
    ("G7", "带矛盾却已确认", lambda d: (d.__setitem__("approved", True),
                                        d.__setitem__("open_issues", [{"id": "X1", "status": "unresolved", "blocking": True}]))),
    ("G8", "同名锚点冲突未登记", lambda d: d["masters"][1]["anchors"].append(
        {"id": "stove", "name": "土灶", "bearing": "W", "source": "L09"})),
]


def selftest():
    ok = True
    base = _clean_payload()
    clean = run_gates(copy.deepcopy(base))
    if clean:
        print("[FAIL] 干净样例被误报：%s" % clean)
        ok = False
    else:
        print("[ OK ] 干净样例通过（证明门禁不是永远报错）")

    for gate, label, mut in POISONS:
        d = copy.deepcopy(base)
        try:
            mut(d)
        except Exception as exc:                      # noqa: BLE001
            print("[FAIL] %s/%s 投毒构造失败：%s" % (gate, label, exc))
            ok = False
            continue
        hits = run_gates(d)
        caught = [g for g, _ in hits if g == gate]
        if not caught:
            print("[FAIL] %s/%s 未被抓到（门禁空转）→ 实际报出：%s" % (gate, label, [g for g, _ in hits]))
            ok = False
        else:
            print("[ OK ] %s/%s 被抓到（共 %d 条报警）" % (gate, label, len(hits)))

    print("")
    print("自检结论：%s（%d 个投毒样本 / 1 个干净样例）" % ("全部命中，门禁不空转" if ok else "存在空转，须修", len(POISONS)))
    return 0 if ok else 4


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--objects")
    ap.add_argument("--master")
    args = ap.parse_args()

    if args.selftest:
        return selftest()

    path = args.check or args.objects
    if not path:
        print("用法见文件头 docstring")
        return 3
    try:
        with io.open(path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as exc:                          # noqa: BLE001
        print("[ERR] 读取失败 %s: %s" % (path, exc))
        return 3

    if args.objects:
        for m in data.get("masters", []):
            if args.master and m.get("id") != args.master:
                continue
            print("%s %s" % (m.get("id"), m.get("name")))
            for w in m.get("object_whitelist", []):
                print("  - %s" % w)
        return 0

    bad = run_gates(data)
    if bad:
        print("[FAIL] space-truth 门禁未通过，共 %d 条：" % len(bad))
        for gate, msg in bad:
            print("  %s | %s" % (gate, msg))
        return 2

    state = "已确认" if data.get("approved") else "待你确认（approved=false，下游不得派生出图）"
    print("[ OK ] space-truth 七道门禁全过 —— %s / %s" % (data.get("episode", "?"), state))
    return 0


if __name__ == "__main__":
    sys.exit(main())
