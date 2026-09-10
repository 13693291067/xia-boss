#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
模板卫生门禁（check-template-hygiene.py）

堵两类静默事故：
  A. 占位符被项目数据顶掉 —— 项目→模板反向复制时忘了还原，导致 `{{项目名}}` 计数归零，
     而既有验收「grep {{项目名}} 应为空才算替换完成」在模板上天然通过 → 污染随每次复制传染。
  B. 模板/脚本/正文里残留具体项目数据（剧名/角色名）—— 违反全流程最高纪律。

零硬编码：B 类的项目词表一律从「被检查项目自己的 xiaji.db 快照 meta.name + 资产名」动态取，
          脚本内不出现任何具体项目词。

用法：
  python check-template-hygiene.py                      # 只查 A 类（占位符功能位）+ D 类（bat/ps1 卫生）
  python check-template-hygiene.py --project-root <根>  # 追加 B 类：用该项目词表扫包
  python check-template-hygiene.py --selftest           # 投毒对照，证明门禁不空转

退出码：0 = 无 P0/P1；1 = 有 P0；2 = 有 P1（无 P0）。
"""
import argparse
import io
import json
import os
import re
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)

# ── A 类：占位符功能位清单（期望计数）。注释性提及不计入，故按"功能位锚点"精确匹配 ──
PLACEHOLDER_SLOTS = [
    ("templates/index.html", "{{项目名}}", 3,
     ["<title>", "sb-prof-name", 'id="title"']),
    ("templates/server.py", "{{项目名}}", 3,
     ["本地服务（上传 + 静态托管）", '"project":', "已启动"]),
    # gen.js：1 处功能位（P.meta?.name 兜底）+ 1 处注释性提及（防字面残留说明）= 2
    ("templates/js/gen.js", "{{项目名}}", 2,
     ["P.meta?.name"]),
    # bat：1 处功能位（echo）+ 1 处 REM 注释说明 = 2
    ("templates/启动项目台.bat", "{{TITLE}}", 2,
     ["echo "]),
]

# ── B 类豁免：锚定示例/风格库/变更留痕（SKILL.md 纪律 1 白名单）──
EXEMPT_PATTERNS = [
    re.compile(r"modules/[^/]+/references/[^/]*(example|锚定示例)[^/]*\.md$"),
    re.compile(r"modules/xiage-styles/styles-library/"),
    re.compile(r"(^|/)CHANGELOG\.md$"),
]

SCAN_SUFFIXES = (".md", ".py", ".json", ".html", ".js", ".css", ".bat", ".ps1")


def is_exempt(rel):
    return any(p.search(rel) for p in EXEMPT_PATTERNS)


def check_placeholders():
    """A 类：占位符功能位计数。少了=被项目数据顶掉；多了=复制方向搞反/占位符被复制扩散。"""
    issues = []
    for rel, token, expect, anchors in PLACEHOLDER_SLOTS:
        path = os.path.join(PKG, rel.replace("/", os.sep))
        if not os.path.exists(path):
            issues.append(("P0", rel, "模板文件不存在"))
            continue
        txt = io.open(path, encoding="utf-8", errors="replace").read()
        got = txt.count(token)
        if got != expect:
            issues.append(("P0", rel, "%s 计数 %d ≠ 功能位 %d（少=被项目数据顶掉，多=复制方向反了）"
                           % (token, got, expect)))
        for a in anchors:
            if a not in txt:
                issues.append(("P0", rel, "功能位锚点缺失：%s（占位符位置被改动）" % a))
    return issues


def project_words(project_root):
    """B 类词表：从项目自己的 xiaji.db 动态取剧名 + 角色/场景/道具名。零硬编码。"""
    db = os.path.join(project_root, "project", "xiaji.db")
    words = set()
    if not os.path.exists(db):
        return words, "缺 xiaji.db（跳过 B 类扫描）"
    con = sqlite3.connect(db)
    try:
        meta = con.execute("select data from snapshots where module='meta'").fetchone()
        if meta:
            name = json.loads(meta[0]).get("name") or ""
            for cand in {name, name.strip("《》")}:
                if len(cand) >= 4:
                    words.add(cand)
        for mod, key in (("xiatang", "characters"), ("xiatang", "scenes"), ("xiatang", "props")):
            row = con.execute("select data from snapshots where module=?", (mod,)).fetchone()
            if not row:
                continue
            for it in (json.loads(row[0]).get(key) or []):
                nm = (it.get("name") or "").strip()
                if len(nm) >= 3 and nm not in ("无", "系统"):
                    words.add(nm)
    finally:
        con.close()
    return words, ""


def check_project_leak(words):
    issues = []
    for root, dirs, files in os.walk(PKG):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git", "assets", "node_modules")]
        for fn in files:
            if not fn.endswith(SCAN_SUFFIXES):
                continue
            full = os.path.join(root, fn)
            rel = os.path.relpath(full, PKG).replace(os.sep, "/")
            if is_exempt(rel):
                continue
            txt = io.open(full, encoding="utf-8", errors="replace").read()
            hits = sorted({w for w in words if w in txt})
            if hits:
                sev = "P0" if rel.startswith(("templates/", "scripts/")) else "P1"
                issues.append((sev, rel, "残留项目词：" + "、".join(hits[:6])))
    return issues


def check_launcher_hygiene():
    """D 类：模板 bat/ps1 必须纯 ASCII + CRLF（纪律 8 ⑦⑧）。"""
    issues = []
    for rel in ("templates/启动项目台.bat", "templates/启动项目台.ps1"):
        path = os.path.join(PKG, rel.replace("/", os.sep))
        if not os.path.exists(path):
            issues.append(("P0", rel, "启动器缺失"))
            continue
        b = open(path, "rb").read()
        lf, crlf = b.count(b"\n"), b.count(b"\r\n")
        if lf - crlf:
            issues.append(("P0", rel, "存在 %d 行纯 LF（cmd.exe 会行边界崩坏）" % (lf - crlf)))
        if any(x > 127 for x in b):
            issues.append(("P0", rel, "含非 ASCII 字节（跨代码页会乱码）"))
    return issues



# ── 双副本正本（★ 2026-09-10 自查固化：同一批次内我分叉过两次，此前零机械兜底）──
# 同一份代码被两个入口引用时，改一份必须同步另一份；逐字节比对（忽略 CRLF 差异）
DUAL_COPIES = [
    ("scripts/check-assets.py", "modules/xiatang-characters/scripts/check-assets.py"),
    ("scripts/build-data-js.py", "templates/build-data-js.py"),
]


def _norm(p):
    return io.open(p, "rb").read().replace(b"\r\n", b"\n")


def check_dual_copies():
    out = []
    for a_rel, b_rel in DUAL_COPIES:
        a = os.path.join(PKG, *a_rel.split("/"))
        b = os.path.join(PKG, *b_rel.split("/"))
        if not os.path.exists(a) or not os.path.exists(b):
            miss = a_rel if not os.path.exists(a) else b_rel
            out.append(("P0", a_rel, u"双副本缺文件：%s" % miss))
            continue
        if _norm(a) != _norm(b):
            out.append(("P0", a_rel, u"与 %s 内容不一致——同一代码两个入口会得出不同结论；"
                                     u"改任一份后必须 cp 同步并复跑本门禁" % b_rel))
    return out


def run_all(project_root=None, text=None):
    """text: 覆盖 index.html 内容（自检用）；返回问题列表。"""
    issues = check_placeholders() + check_launcher_hygiene() + check_dual_copies()
    if project_root:
        words, note = project_words(project_root)
        if note:
            print("[skip] B 类：%s" % note)
        elif words:
            issues += check_project_leak(words)
        else:
            print("[skip] B 类：项目词表为空")
    return issues


def selftest():
    """投毒对照：证明 A 类门禁真的会报，而不是无条件打印 PASS。"""
    print("=== 自检：投毒对照（门禁必须报出问题，否则=空转）===")
    path = os.path.join(PKG, "templates", "index.html")
    orig = io.open(path, encoding="utf-8").read()
    cases = []
    # 用例1：把一处占位符换成任意剧名（模拟项目→模板反向复制）→ 应报 P0
    poisoned = orig.replace("{{项目名}}", "《某某剧名》", 1)
    cases.append(("污染一处占位符", poisoned, True))
    # 用例2：占位符被复制扩散成 4 处 → 应报 P0
    extra = orig.replace('<title>{{项目名}} · 项目台</title>',
                         '<title>{{项目名}} · 项目台</title><!--{{项目名}}-->')
    cases.append(("占位符多余一处", extra, True))
    # 用例3：原样（干净）→ 不应因占位符报错
    cases.append(("干净模板", orig, False))
    failed = 0
    global PLACEHOLDER_SLOTS
    keep = PLACEHOLDER_SLOTS
    for name, content, expect_hit in cases:
        io.open(path, "w", encoding="utf-8", newline="").write(content)
        hits = [i for i in check_placeholders() if "index.html" in i[1]]
        got = bool(hits)
        flag = "OK" if got == expect_hit else "❌ 门禁空转"
        if got != expect_hit:
            failed += 1
        print("  [%s] %-14s 期望报=%s 实际报=%s %s" % (flag, name, expect_hit, got,
                                                    (hits[0][2][:60] if hits else "")))
    io.open(path, "w", encoding="utf-8", newline="").write(orig)
    same = io.open(path, encoding="utf-8").read() == orig
    print("  还原模板：%s" % ("一致" if same else "❌ 不一致，请 git checkout"))
    return 1 if (failed or not same) else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-root")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        sys.exit(selftest())
    issues = run_all(args.project_root)
    p0 = [i for i in issues if i[0] == "P0"]
    p1 = [i for i in issues if i[0] == "P1"]
    for sev, rel, msg in issues:
        print("[%s] %s :: %s" % (sev, rel, msg))
    print("模板卫生门禁：P0 %d / P1 %d" % (len(p0), len(p1)))
    if not issues:
        print("✅ 占位符功能位完整、启动器编码达标" +
              ("、包内无项目词残留" if args.project_root else "（未做项目词扫描）"))
    sys.exit(1 if p0 else (2 if p1 else 0))


if __name__ == "__main__":
    main()
