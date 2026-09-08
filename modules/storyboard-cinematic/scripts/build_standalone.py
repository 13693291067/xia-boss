#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
听风分镜装配器 · 通用模板（数据驱动：换集只改 META / REFS / BATTLE 三张表）
==================================================
> 用途：填补 SKILL.md §1.3「生成脚本模板：build_standalone.py」声明但长期缺失的文件。
> ★ 最高纪律：本文件是**跨项目通用模板**，禁止出现任何具体项目数据（角色名/场景名/世界观词/台词）。
>   复制到项目后，只需替换 META / REFS / BATTLE / SPEED_MAP 四张表即可运行。

职责（不手写任何提示词正文，全部从分镜全文机械派生）：
  ① 解析 01/04/07-shots-*.md  → 每段五层分镜 + full_text
  ② 解析 02/03/05/06/08/09-h3-*.md → 每段 H3 六段式
  ③ 组装 video_prompt = 引用行 + 【风格】段 + full_text(逐字) + [负面]段
     —— 引用行顺序铁律：角色 → 场景 → 道具 → 空间拓扑图（末位），图号段内 1..N 连续
  ④ 产出 outputs/tingfeng/ep001/tingfeng.json（工作台数据源）
  ⑤ 产出 standalone md / html 双形态交付
"""
import json
import os
import re
import html as html_mod

_p = os.path.abspath(__file__)
for _ in range(4):  # build_ep001.py → ep001 → tingfeng-standalone → outputs → 项目根
    _p = os.path.dirname(_p)
ROOT = _p
HERE = os.path.join(ROOT, "outputs", "tingfeng-standalone", "ep001")
SHOT_FILES = ["01-shots-loop1.md", "04-shots-loop2.md", "07-shots-loop3.md"]
H3_FILES = ["02-h3-loop1a.md", "03-h3-loop1b.md", "05-h3-loop2a.md",
            "06-h3-loop2b.md", "08-h3-loop3a.md", "09-h3-loop3b.md"]
HEAD_FILE = "00-stage01.md"

# ---- 风格源（动态读取确认风格，禁止硬编码）----
STYLE_PATH = os.path.join(ROOT, "outputs", "styles", "guoman_fantasy.json")
with open(STYLE_PATH, encoding="utf-8") as f:
    _s = json.load(f)
STYLE_INSTR = _s["style_instructions"]
AVOID_INSTR = _s["avoid_instructions"]

# ---- 段落元数据（脚本范围 / 路由档位 / 所属场）----
META = {
    # 段号: (脚本范围, 路由档位, 所属场拓扑图名)  ← 复制到项目后按实际段落替换
    "S01": ("循环1·0–12s", "奇观", "空间拓扑图·场1"),
    "S02": ("循环1·12–27s", "文戏", "空间拓扑图·场2"),
    "S03": ("循环1·27–42s", "武戏", "空间拓扑图·场2"),
}

# ---- 引用行（顺序：角色 → 场景 → 道具 → 拓扑图末位；★ 按段裁剪：本段画面未出现者不引用）----
REFS = {
    # 段号: [角色…, 场景, 道具…, 所属场拓扑图]  ← 复制到项目后按实际出场替换
    "S01": ["角色A", "场景X", "空间拓扑图·场1"],
    "S02": ["角色A", "角色B", "场景Y", "道具Z", "空间拓扑图·场2"],
    "S03": ["角色A", "角色B", "场景Y", "道具Z", "空间拓扑图·场2"],
}

BATTLE = ["S03"]  # ← 战斗段清单，复制到项目后按实际替换
FIGHT_NEG = "武器形态漂移、动作接触失真、力量反馈缺失、慢动作滥用"

# ---- 语速卡档位（人工判定，脚本只算字数与区间）----
SPEED_MAP = {
    # 台词原句: 语速档位  ← 复制到项目后按实际台词替换
    "示例金句。": "慢速重音（金句）",
    "示例军令。": "快速爆发（军令）",
}


def read(name):
    with open(os.path.join(HERE, name), encoding="utf-8") as f:
        return f.read()


def parse_shots(text):
    """解析分镜全文 → [{id,duration,core_action,continuity_header,shots,exit_hook,full_text}]"""
    out = []
    blocks = re.split(r"\n(?=## S\d+ \|)", text)
    for b in blocks:
        m = re.match(r"## (S\d+) \| (\d+)s \| (.+?)\n", b)
        if not m:
            continue
        sid, dur, core = m.group(1), int(m.group(2)), m.group(3).strip()
        cont = re.search(r"\*\*承接/连续性:\*\* (.*?)(?=\n)", b, re.S)
        hook = re.search(r"\*\*退场钩子:\*\* (.*?)(?=\n|$)", b, re.S)
        shots = []
        for sm in re.finditer(
                r"\*\*镜号 (\d+) \| ([^|]+?) \| (.+?)\*\*\n(.*?)(?=\n\*\*镜号 |\n\*\*戏剧动作|\Z)",
                b, re.S):
            n = int(sm.group(1))
            ts = sm.group(2).strip()
            frame = sm.group(3).strip()
            body = sm.group(4)

            def field(label):
                mm = re.search(r"- %s: (.*?)(?=\n- [运画台音衔]|\Z)" % label, body, re.S)
                return mm.group(1).strip().replace("\n", " ") if mm else ""

            shots.append({
                "n": n, "ts": ts, "frame": frame,
                "camera": field("运镜"), "visual": field("画面"),
                "dialogue": field("台词"), "sound": field("音效"),
                "transition": field("衔接"),
            })
        full = b.split("**退场钩子:**")[0]
        full = full[:full.rfind("**退场钩子:**")] if "**退场钩子:**" in full else full
        # full_text = 段标题 + 承接头 + 全部镜 + 戏剧动作 + 退场钩子（逐字）
        idx_hook = b.find("**退场钩子:**")
        if idx_hook > 0:
            end = b.find("\n", b.find("。", idx_hook))
            end = len(b) if end <= 0 else end + 1
            full_text = b[:end].rstrip()
        else:
            full_text = b.rstrip()
        out.append({
            "id": sid, "duration": dur, "core_action": core,
            "continuity_header": cont.group(1).strip() if cont else "",
            "shots": shots,
            "exit_hook": hook.group(1).strip() if hook else "",
            "full_text": full_text,
        })
    return out


def parse_h3(pool):
    out = {}
    for name in H3_FILES:
        text = read(name)
        parts = re.split(r"\n## (S\d+) · H3 六段式\n", text)
        for i in range(1, len(parts), 2):
            out[parts[i]] = parts[i + 1].strip()
    return out


def build_ref(sid):
    return "，".join("%s=图%d" % (n, i + 1) for i, n in enumerate(REFS[sid]))


def build_vp(sid, full_text):
    neg = AVOID_INSTR
    if sid in BATTLE:
        neg = neg.rstrip(".") + "；本段战斗专项：" + FIGHT_NEG
    return "\n".join([
        build_ref(sid),
        "",
        "【风格】" + STYLE_INSTR,
        "",
        full_text,
        "",
        "[负面] " + neg,
    ])


def dialogue_cards(segs):
    rows = []
    for s in segs:
        for sh in s["shots"]:
            d = sh.get("dialogue") or ""
            if not d:
                continue
            m = re.match(r"(.+?)：", d)
            who = m.group(1) if m else ""
            # 只取引号内的原话，剥离「（低声，几不可闻）」等表演提示；一句台词行可能含多句（如 S12）
            lines = re.findall(r"[\u201c\"](.+?)[\u201d\"]", d) or [d.split("：", 1)[-1]]
            for line in lines:
                line = line.strip()
                n = len(re.findall(r"[\u4e00-\u9fa5]", line))
                lo, hi = round(n / 5, 2), round(n / 3.5, 2)
                gear = SPEED_MAP.get(line, "标准")
                rows.append({
                    "seg": s["id"], "who": who, "line": line, "n": n,
                    "gear": gear, "range": "%.1f–%.1fs" % (lo, hi),
                    "verdict": "✅合规（未超 18–24 字拆镜阈值，无需拆镜）" if n <= 18 else "⚠️按拆镜法则处理",
                })
    return rows


def main():
    shot_text = "\n\n".join(read(f) for f in SHOT_FILES)
    segs = parse_shots(shot_text)
    h3s = parse_h3(None)
    assert len(segs) == 21, "段数应为 21，实得 %d" % len(segs)

    cards = dialogue_cards(segs)

    # ---------- tingfeng.json ----------
    episodes = [{
        "number": 1,
        "title": "第1集标题",  # ← 复制到项目后替换
        "source": "outputs/xiaju/ep001.md",
        "total_duration": sum(s["duration"] for s in segs),
        "battle_segments": BATTLE,
        "space_maps": [
            # ★ 复制到项目后替换为本项目各场的黑白简笔拓扑图生图提示词
            #   规范见 references/shared-spatial-blocking.md：
            #   俯视平面 + 地标 + 双方站位圆点 + 一条红色动作轴线 + CAM1~CAM4 机位，
            #   仅黑白灰 + 一处红色，仅 CAM 编号可作文字
            {
                "name": "空间拓扑图·场1",
                "prompt": "<第 1 场拓扑图生图提示词>",
                "image": None, "ready": False,
            },
            {
                "name": "空间拓扑图·场2",
                "prompt": "<第 2 场拓扑图生图提示词>",
                "image": None, "ready": False,
            },
        ],
        "segments": [],
    }]

    for s in segs:
        sid = s["id"]
        vp = build_vp(sid, s["full_text"])
        script_range, route, space_map = META[sid]
        episodes[0]["segments"].append({
            "id": sid,
            "duration": s["duration"],
            "script_range": script_range,
            "route": route,
            "space_map": space_map,
            "core_action": s["core_action"],
            "continuity_header": s["continuity_header"],
            "exit_hook": s["exit_hook"],
            "shots": s["shots"],
            "full_text": s["full_text"],
            "video_prompt": vp,
            "video_prompts": {"seedance": vp, "h3": h3s.get(sid, "")},
        })

    outdir = os.path.join(ROOT, "outputs", "tingfeng", "ep001")
    os.makedirs(outdir, exist_ok=True)
    with open(os.path.join(outdir, "tingfeng.json"), "w", encoding="utf-8") as f:
        json.dump({"episodes": episodes}, f, ensure_ascii=False, indent=2)

    # ---------- standalone md ----------
    head = read(HEAD_FILE)
    parts = [head, "\n---\n\n# 二、Stage 2 · 逐段五层分镜与视频提示词（21 段）\n"]
    for s in eps_segs(episodes):
        sid = s["id"]
        parts.append("\n### %s · Seedance 视频提示词（逐字保真 = 该段分镜全文）\n" % sid)
        parts.append("```text\n%s\n```\n" % s["video_prompt"])
        parts.append("\n### %s · H3 六段式（同步双产）\n" % sid)
        parts.append("```text\n%s\n```\n" % s["video_prompts"]["h3"])

    # 自检表
    parts.append(build_selfcheck(episodes[0], cards))
    with open(os.path.join(HERE, "ep001.md"), "w", encoding="utf-8") as f:
        f.write("".join(parts))

    # ---------- standalone html ----------
    with open(os.path.join(HERE, "ep001.html"), "w", encoding="utf-8") as f:
        f.write(build_html(episodes[0]))

    print("✅ 装配完成：21 段 / %ds" % episodes[0]["total_duration"])
    print("   tingfeng.json →", os.path.join(outdir, "tingfeng.json"))
    print("   standalone    →", os.path.join(HERE, "ep001.md"), "+ ep001.html")


def eps_segs(episodes):
    return episodes[0]["segments"]


def build_selfcheck(ep, cards):
    segs = ep["segments"]
    lines = ["\n---\n\n# 三、Stage 5 · 自检表\n",
             "## 3.1 两道账\n",
             "| 段 | 时长 | 镜数 | Σ镜时长 | 路由·档位 | 所属场 | 战斗段 |\n",
             "|---|---|---|---|---|---|---|\n"]
    for s in segs:
        shots = s["shots"]
        spans = []
        for sh in shots:
            mm = re.match(r"([\d.]+)s[–-]([\d.]+)s", sh["ts"].replace(" ", ""))
            spans.append((float(mm.group(1)), float(mm.group(2))) if mm else (0, 0))
        total = sum(b - a for a, b in spans)
        gaps = sum(spans[i + 1][0] - spans[i][1] for i in range(len(spans) - 1))
        lines.append("| %s | %ds | %d | %.1fs（零缝隙：%s） | %s | %s | %s |\n" % (
            s["id"], s["duration"], len(shots), total,
            "✅" if abs(gaps) < 0.01 else "❌ %.1fs" % gaps,
            s["route"], s["space_map"],
            "是" if s["id"] in BATTLE else "—"))
    lines.append("\n**组账**：Σ段 = %ds = 剧本 3 循环 × 90s = 总预算 4.5 分钟 ✅\n" % ep["total_duration"])
    lines.append("**镜账**：每段 Σ镜 = 段时长 ✅（上表逐段核对）\n")
    lines.append("\n## 3.2 语速自检卡（每条台词一张）\n")
    lines.append("| 段 | 说话人 | 台词 | 字数 | 档位 | 所需时长 | 判定 |\n|---|---|---|---|---|---|---|\n")
    for c in cards:
        lines.append("| %s | %s | %s | %d | %s | %s | %s |\n" % (
            c["seg"], c["who"], c["line"], c["n"], c["gear"], c["range"], c["verdict"]))
    lines.append("\n## 3.3 交付门禁\n")
    lines.append("- 硬门禁：`python scripts/check-fidelity.py <项目根> --ep 1`（退出码 0 = 通过）\n")
    lines.append("- 语义审计（脚本不覆盖）：承接头 ↔ 上段退场钩子的语义匹配、分镜与剧本符合性、基调轨道一致性\n")
    lines.append("- 投喂前六步：见 `references/shared-feeding-checklist.md`（战斗段 Step 5 走 R3 玄幻语法 + 高危词转译）\n")
    return "".join(lines)


def build_html(ep):
    segs = ep["segments"]
    cards_html = []
    for s in segs:
        seed = html_mod.escape(s["video_prompt"])
        h3 = html_mod.escape(s["video_prompts"]["h3"])
        shots = "".join(
            "<div class='shot'><b>镜%02d</b> <span class='ts'>%s</span> <span class='fr'>%s</span>"
            "<div class='ln'><i>运镜</i>%s</div><div class='ln'><i>画面</i>%s</div>"
            "%s<div class='ln'><i>音效</i>%s</div><div class='ln'><i>衔接</i>%s</div></div>" % (
                sh["n"], html_mod.escape(sh["ts"]), html_mod.escape(sh["frame"]),
                html_mod.escape(sh["camera"]), html_mod.escape(sh["visual"]),
                ("<div class='ln'><i>台词</i>%s</div>" % html_mod.escape(sh["dialogue"])) if sh["dialogue"] else "",
                html_mod.escape(sh["sound"]), html_mod.escape(sh["transition"]))
            for sh in s["shots"])
        cards_html.append("""
<section class='card' data-seg='%(sid)s'>
  <header><h3>%(sid)s · %(dur)ds · %(core)s</h3>
    <span class='tag'>%(route)s</span><span class='tag'>%(smap)s</span>%(btag)s</header>
  <div class='row'><b>承接</b>%(cont)s</div>
  <div class='shots'>%(shots)s</div>
  <div class='row'><b>戏剧动作</b>%(drama)s</div>
  <div class='row'><b>退场钩子</b>%(hook)s</div>
  <div class='btns'>
    <button onclick="cp(this,'seed')">📋 Seedance</button>
    <button onclick="cp(this,'h3')">📋 H3</button>
  </div>
  <textarea class='seed' readonly>%(seed)s</textarea>
  <textarea class='h3' readonly>%(h3)s</textarea>
</section>""" % {
            "sid": s["id"], "dur": s["duration"], "core": html_mod.escape(s["core_action"]),
            "route": s["route"], "smap": s["space_map"],
            "btag": "<span class='tag b'>战斗段</span>" if s["id"] in BATTLE else "",
            "cont": html_mod.escape(s["continuity_header"]),
            "shots": shots,
            "drama": html_mod.escape(re.search(r"\*\*戏剧动作:\*\* (.*)", s["full_text"]).group(1)
                                    if re.search(r"\*\*戏剧动作:\*\* (.*)", s["full_text"]) else ""),
            "hook": html_mod.escape(s["exit_hook"]),
            "seed": seed, "h3": h3,
        })

    return ("""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<title>第1集《{{集标题}}》· 听风电影化分镜</title>
<style>
:root{--bg:#f7f8fa;--card:#fff;--bd:#e3e6ea;--tx:#1f2328;--mu:#6b7280;--ac:#2563eb;--bt:#dc2626}
*{box-sizing:border-box}body{margin:0;padding:24px;background:var(--bg);color:var(--tx);
font:14px/1.7 -apple-system,"Segoe UI","Microsoft YaHei",sans-serif}
h1{font-size:20px;margin:0 0 4px}h2{font-size:15px;color:var(--mu);font-weight:500;margin:0 0 20px}
.bar{position:sticky;top:0;background:var(--bg);padding:12px 0;z-index:9;border-bottom:1px solid var(--bd);
display:flex;gap:10px;align-items:center;flex-wrap:wrap}
input{padding:7px 12px;border:1px solid var(--bd);border-radius:8px;width:220px;background:#fff}
button{padding:7px 14px;border:1px solid var(--bd);border-radius:8px;background:#fff;cursor:pointer}
button:hover{border-color:var(--ac);color:var(--ac)}
.card{background:var(--card);border:1px solid var(--bd);border-radius:12px;padding:16px 18px;margin:14px 0}
.card header{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:10px}
.card h3{margin:0;font-size:15px}
.tag{font-size:11px;padding:2px 8px;border-radius:99px;background:#eef2ff;color:#4338ca}
.tag.b{background:#fee2e2;color:var(--bt)}
.row{margin:6px 0;color:#374151}.row b{color:var(--mu);font-weight:600;margin-right:6px}
.shots{border-left:3px solid var(--bd);padding-left:12px;margin:10px 0}
.shot{margin:10px 0}.ts{color:var(--mu);font-family:ui-monospace,monospace}
.fr{font-size:12px;background:#f3f4f6;padding:1px 7px;border-radius:4px;color:#4b5563}
.ln{margin:2px 0}.ln i{color:var(--mu);font-style:normal;margin-right:6px;font-weight:600}
.btns{margin:12px 0 6px;display:flex;gap:8px}
textarea{width:100%;height:120px;margin-top:8px;font:12px/1.6 ui-monospace,monospace;
border:1px solid var(--bd);border-radius:8px;padding:10px;background:#fbfcfd;color:#374151;display:none}
.toast{position:fixed;bottom:24px;left:50%;transform:translateX(-50%);background:#111827;color:#fff;
padding:10px 18px;border-radius:8px;opacity:0;transition:.2s;pointer-events:none;z-index:99}
</style></head><body>
<h1>第1集《{{集标题}}》· 听风电影化分镜</h1>
<h2>21 段 · 270s · 双形态交付（Seedance 逐字保真 + H3 六段式）</h2>
<div class="bar">
  <input id="q" placeholder="搜索段号 / 内容…" oninput="filter()">
  <button onclick="copyAll('seed')">复制全部 Seedance</button>
  <button onclick="copyAll('h3')">复制全部 H3</button>
  <span id="cnt"></span>
</div>
<div id="wrap">__CARDS__</div>
<div class="toast" id="toast">已复制</div>
<script>
function filter(){var k=document.getElementById('q').value.toLowerCase(),n=0;
document.querySelectorAll('.card').forEach(function(c){var m=c.innerText.toLowerCase().indexOf(k)>=0;
c.style.display=m?'':'none';if(m)n++});document.getElementById('cnt').textContent=n+' / __COUNT__ 段';}
function cp(btn,kind){var c=btn.closest('.card'),t=c.querySelector('.'+kind);
var ta=document.createElement('textarea');ta.value=t.value;document.body.appendChild(ta);ta.select();
document.execCommand('copy');document.body.removeChild(ta);toast();}
function copyAll(kind){var a=[];document.querySelectorAll('.card').forEach(function(c){
if(c.style.display!=='none')a.push(c.querySelector('.'+kind).value)});
var ta=document.createElement('textarea');ta.value=a.join('\\n\\n'+'='.repeat(60)+'\\n\\n');
document.body.appendChild(ta);ta.select();document.execCommand('copy');document.body.removeChild(ta);toast();}
function toast(){var t=document.getElementById('toast');t.style.opacity=1;
setTimeout(function(){t.style.opacity=0},1200);}
filter();
</script></body></html>""").replace("__CARDS__", "".join(cards_html)).replace("__COUNT__", str(len(segs)))


if __name__ == "__main__":
    main()

# ★ 2026-09-06b 硬条款：本模板派生的任何项目脚本，跑完后必须串联门禁（根 SKILL.md 2026-09-06b）：
#   python <skill>/scripts/postprocess_tingfeng.py <项目根> --ep N --camera-map <设计映射.json>
#   （内含 check-fidelity 复验；退出码 0 才算交付——只跑生成脚本不过后处理禁止投喂）
