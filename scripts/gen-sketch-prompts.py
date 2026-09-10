#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
草图提示词派生器（gen-sketch-prompts.py）
========================================
按 `modules/xiajing-episodes/references/sketch-prompt-spec.md`（正本）与 `scripts/sketch_rules.py`
（规则引擎）从项目的 `shots.json` **派生** `sketch_prompt`。

为什么要有它：批量交付物不接受 AI 即兴撰写——同一批 51 条手写必然前后不一致、不可复现、
下一集又变一套。规则化后由脚本派生，AI 只做抽检与人工修订。

幂等策略：只补空、只修违规；已合规的人工修订原样保留。

用法：
  python gen-sketch-prompts.py <项目根> --ep 1 [--dry-run] [--force]
"""

import argparse
import io
import json
import os
import shutil
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sketch_rules as SR   # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--ep", type=int, required=True)
    ap.add_argument("--dry-run", action="store_true", help="只打印将要生成的内容，不落盘")
    ap.add_argument("--force", action="store_true", help="连已合规的也重新派生（默认保留人工修订）")
    args = ap.parse_args()

    d = os.path.join(os.path.abspath(args.root), "outputs", "xiajing", "ep%03d" % args.ep)
    p = os.path.join(d, "shots.json")
    if not os.path.exists(p):
        print(u"❌ 未找到 %s" % p)
        sys.exit(1)
    doc = json.load(io.open(p, encoding="utf-8"))
    shots = doc.get("shots") or []
    if not shots:
        print(u"❌ shots 为空")
        sys.exit(1)

    added = fixed = kept = 0
    warns = []
    for s in shots:
        sn = s.get("shot_number") or "?"
        chars = s.get("characters") or u""
        has_char = bool(chars.strip()) and (u"空镜" not in chars)
        cur = (s.get("sketch_prompt") or u"").strip()
        if cur and not args.force:
            bad = SR.validate(cur, has_character=has_char)
            if not bad:
                kept += 1
                continue
        new, missing = SR.make(s.get("scene_name"), chars, s.get("action"), s.get("visual"),
                               s.get("composition"), s.get("shot_type"), s.get("camera"))
        bad = SR.validate(new, has_character=has_char)
        if bad:
            warns.append((sn, bad, missing))
        if cur:
            fixed += 1
        else:
            added += 1
        if not args.dry_run:
            s["sketch_prompt"] = new

    print(u"共 %d 镜｜新增 %d｜修复违规 %d｜保留人工修订 %d" % (len(shots), added, fixed, kept))
    if warns:
        print(u"⚠️ 派生后仍不合规则 %d 镜（需人工补，脚本不臆造）：" % len(warns))
        for sn, bad, missing in warns[:12]:
            print(u"   镜%s ｜ %s" % (sn, u"；".join(bad)))
    else:
        print(u"✅ 全部派生结果通过 sketch_rules.validate")

    if args.dry_run:
        print(u"（--dry-run 未写盘）示例：")
        for s in shots[:3]:
            print(u"   镜%s：%s" % (s.get("shot_number"), s.get("sketch_prompt") or u"(未生成)"))
        return

    if added == 0 and fixed == 0:
        print(u"无需写盘。")
        return
    bak = os.path.join(d, "shots.json.bak-sketch-%s" % time.strftime("%Y%m%d%H%M%S"))
    shutil.copy2(p, bak)
    io.open(p, "w", encoding="utf-8", newline="").write(json.dumps(doc, ensure_ascii=False, indent=2))
    print(u"已写盘（备份 %s）" % os.path.basename(bak))
    print(u"下一步：跑 check-script-fidelity.py <项目根> --ep %d 复验 E 项，再跑 build-data-js.py 同步项目台" % args.ep)


if __name__ == "__main__":
    main()
