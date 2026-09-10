#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
拓扑图生图投喂清单生成器（gen-topology-feedlist.py）
====================================================
读项目自己的 `outputs/xiajing/ep{NNN}/space_maps.json`（单一真源），产出一份可直接投喂的
「空间拓扑图·生图清单」md：每场一张图的英文执行稿 + 中文理解稿 + 出图验收项 + 回填步骤。

为什么要有它：三场拓扑图未回填是 `check-scenes` D2 的 P0，但提示词散在 json 里、验收项写在
规范正文里，用户生图时要自己拼——拼错一次就白跑一轮。本脚本把「读真源 → 排清单」固化，
**不复制规范正文、不写死任何项目数据**（场名/场景名一律来自该项目的 json）。

用法：
  python gen-topology-feedlist.py <项目根> --ep 1 [--out <路径>] [--require-doorway]
  # 默认输出 <项目根>/outputs/xiajing/ep{NNN}/拓扑图生图投喂清单.md

纪律：只读 space_maps.json，绝不写回；改词一律改 json 再重跑本脚本。
"""

import argparse
import io
import json
import os
import sys

# 通用验收项（与具体项目无关；规范正本 = references/shared-spatial-blocking.md §十 / §十六·一）
GENERIC_CHECKS = [
    u"**黑白简笔俯视**，无写实光影、无人物造型、无材质纹理；线条干净，像手绘蓝图",
    u"**图上除 CAM 编号（及规范允许的轴标签）外不得出现任何文字**，尤其不得出现角色名/场景名",
    u"**轴线两端不得带箭头**；朝向箭头只贴在站位圆点上，不贴在轴线上",
    u"**机位全部落在轴线同侧**（`same side`），跨侧即越轴",
    u"左右站位须与该项目 `shots.json` 的侧别锁一致（侧别按机位朝向推，见 §十六·一）",
    u"幅面与提示词首行声明一致（现行规范：16:9 白底）",
]

BACKFILL_STEPS = [
    u"图片存入 `project/assets/` 下合适子目录，建议命名 `拓扑图·场N.png`",
    u"把 `space_maps.json` 中对应条目的 `image` 填成 `assets/.../<文件名>`、`ready` 改为 `true`",
    u"**注意双份拷贝**：`shots.json` 顶层内嵌一份 `space_maps`，改完须以 `space_maps.json` 为源"
    u"单向回同步进 `shots.json`，否则读内嵌那份的门禁仍报空",
    u"跑 `modules/scene-consistency/scripts/check-scenes.py --shots <shots.json> --scenes <registry>`"
    u" → D2 问题数应下降至 0",
    u"跑 `scripts/build-data-js.py <项目根>` 重建项目台并校验拓扑图入库",
]


def load_maps(root, ep):
    p = os.path.join(root, "outputs", "xiajing", "ep%03d" % ep, "space_maps.json")
    if not os.path.exists(p):
        print(u"❌ 未找到 %s" % p)
        sys.exit(1)
    return p, json.load(io.open(p, encoding="utf-8"))


def build(path, data, require_doorway=False):
    maps = data.get("space_maps") or []
    o = io.StringIO()
    o.write(u"# 空间拓扑图·生图投喂清单\n\n")
    o.write(u"> 单一真源：`%s`（本文件由 `gen-topology-feedlist.py` 生成，**手改无效**，改词请改 json）。\n"
            % os.path.relpath(path, os.path.dirname(os.path.dirname(os.path.dirname(path)))).replace("\\", "/"))
    o.write(u"> 规范：`references/shared-spatial-blocking.md` §十 黑白简笔 / §十六·一 侧别推导律。\n")
    o.write(u"> 门禁：`check-scenes.py` D2 —— 被引用的拓扑图必须 `image` 非空且 `ready=true`，否则该集交付未完成（P0）。\n\n")
    if not maps:
        o.write(u"⚠️ 该集 `space_maps` 为空：没有拓扑图可生。若分镜引用行已指向拓扑图，属登记缺失，先补登记。\n")
        return o.getvalue()
    o.write(u"## 投喂参数（各场一致）\n\n")
    o.write(u"- 只用英文执行稿投喂；中文理解稿**只读**，用于核对语义，不要进提示词\n")
    o.write(u"- **一张一张跑**，不要用批量/组图（组图会把多场几何互相污染）\n\n")
    for m in maps:
        name = m.get(u"name") or u"(未命名)"
        o.write(u"---\n\n## %s\n\n" % name)
        if m.get(u"scene"):
            o.write(u"- 对应场景：%s\n" % m[u"scene"])
        o.write(u"- 当前状态：`image`=%s ｜ `ready`=%s\n\n"
                % (m.get(u"image") or u"空", m.get(u"ready")))
        o.write(u"**英文执行稿（复制去生图）**\n\n```text\n%s\n```\n\n" % (m.get(u"prompt") or u""))
        if m.get(u"prompt_cn"):
            o.write(u"**中文理解稿（只读）**\n\n> %s\n\n" % m[u"prompt_cn"])
    o.write(u"---\n\n## 出图验收（逐张过，任一不过＝重跑）\n\n")
    for i, c in enumerate(GENERIC_CHECKS, 1):
        o.write(u"%d. %s\n" % (i, c))
    if require_doorway:
        o.write(u"%d. 若本场的 A2 layout 图尚未 ready：场景空镜图须自带 `Doorway relation:` 声明"
                u"（条款正本 = xiatang `scene-assets.md` A2·5），否则门通向无人交代，生图会自行补全\n"
                % (len(GENERIC_CHECKS) + 1))
    o.write(u"\n## 回填步骤（全部出图后）\n\n")
    for i, s in enumerate(BACKFILL_STEPS, 1):
        o.write(u"%d. %s\n" % (i, s))
    return o.getvalue()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--ep", type=int, required=True)
    ap.add_argument("--out", default="")
    ap.add_argument("--require-doorway", action="store_true",
                    help="追加 A2·5 缺位兜底验收项（layout 未 ready 的项目建议加）")
    args = ap.parse_args()
    path, data = load_maps(os.path.abspath(args.root), args.ep)
    md = build(path, data, args.require_doorway)
    out = args.out or os.path.join(os.path.dirname(path), u"拓扑图生图投喂清单.md")
    io.open(out, "w", encoding="utf-8", newline="").write(md)
    n = len(data.get("space_maps") or [])
    print(u"已生成：%s（%d 场）" % (out, n))
    print(u"下一步：按清单逐张生图 → 回填 space_maps.json 的 image/ready → 复跑 check-scenes D2")


if __name__ == "__main__":
    main()
