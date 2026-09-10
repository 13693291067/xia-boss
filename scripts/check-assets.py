# -*- coding: utf-8 -*-
"""
资产提示词合规自检脚本（跨项目通用，★ 虾塘产出后强制运行）
用法: python check_assets.py <项目根>
检查 4 项：
 ① 英文纯净：所有资产提示词（主图/身份图/场景/道具）不得含中文长串（>6字），中文仅允许锚点名/色调
 ② 主图证件照规格：9 要素（3:4 portrait / ID-passport / head-and-shoulders / head centered /
    neutral expression / plain solid background / even studio lighting / no pose / 85mm f/1.8）
    且不得含 full body / standing pose / dark gradient background / side view / three-quarter
 ③ 身份图两图制（★ 2026-08-21 用户拍板：①定妆照 prompt + ②四视图角色卡 sheet_prompt）：
    定妆照（prompt 字段）= 正面全身定妆照基准（★ 2026-08-21 拍板：按 02 全身定义，主图证件照锚脸、身份定妆照锚完整造型），
      查英文纯净 + 正面要素（front-facing / facing camera / frontal view / front view）+ 全身要素（full body / full-length / full standing / full outfit / standing pose）
    四视图卡（sheet_prompt 字段）= 上下两段式定妆参考板：
      固定中文模板（含「请基于参考人物」特征词）→ 豁免英文纯净，查结构特征（上下两段式/正脸特写/侧脸特写/正面服装展示/背面全身）
      英文兜底模板 → 查 7 要素（2x2 grid / close-up facial portrait / side profile / full body / back view / plain solid background / rim light）
      + 不得误用证件照词（ID/passport / 3:4 portrait）
 ④ 场景空镜：场景提示词不得含人物词
 ⑤ 道具五宫格（★ 2026-08-21）：道具提示词（产品特写写法，含中文段，豁免英文纯净）必须含
    五宫格布局描述（五宫格/上2下3/5-panel 等）+ 五个视图（正面/背面/左侧面/右侧面/材质特写）
 ⑥ 三要素内联（指纹句整句内联 + avoid 前两条禁令 + 视觉参考注入标记）；★ v3.2.0 CG 风另查：
    主图介质锚走 CG_ANCHOR_ANY 集合（覆盖国漫CG/2D赛璐璐，防非国漫 CG 项目被写死字面量误报），
    且剥 STYLE_HEAD 首句后正向 body 必含主动风格化锚 CG_STRONG_STYLE（治"指纹在但被写实人像词淹没致风格漂"的假校验）
 ⑧ 依赖门禁 + 道具锚点（★ 2026-09-03 集成，前半程方法论蒸馏）：
    角色 dependencies.upstream 必须指向 registry 内真实资产名；下游提示词已产出而上游
    主图/提示词未定稿 → 报错（有向依赖门禁，见 xiatang references/character-dependency.md）
    道具 continuity_anchors 登记的识别锚点必须逐条写入提示词（跨镜连续性锚点）
 ⑩ 双语成对（★ 2026-09-06 双语双产契约 v2.10.0）：凡 prompt（或 portrait_prompt/sheet_prompt，
    四视图卡固定中文模板除外）/prompt_cn 成对存在——EN 有而 CN 缺 → 报错提醒回补；
    CN 有而 EN 缺 → 报错（EN 是生图主字段，缺即不可生成）；两者皆空跳过
退出码 0=全部通过；1=有问题（逐条打印）
"""
import io
import json, os, re, sys

def load_registry(project_root):
    p = os.path.join(project_root, "outputs", "xiatang", "assets-registry.json")
    if os.path.exists(p):
        return json.load(open(p, encoding="utf-8"))
    # 回退：从 SQLite 读取
    dbp = os.path.join(project_root, "project", "xiaji.db")
    if os.path.exists(dbp):
        import sqlite3
        db = sqlite3.connect(dbp)
        row = db.execute("SELECT data FROM snapshots WHERE module='xiatang'").fetchone()
        if row:
            return json.loads(row[0])
    return None

CN_RE = re.compile(r'[\u4e00-\u9fff]{4,}')

# ★ 2026-09-06c 身份锚定句式：EN 提示词中「男/女·称号·身份」锚点允许以中文出现（英文语法槽位内嵌中文专名）。
#   这些中文落在固定身份锚句式（aged about X岁 / The XX look of 角色名 / 男·XX·XX 并列称号），
#   是"锚点名/色调"豁免范畴（脚本头注）。检查时先剥离锚点句再扫中文，防误报。
IDN_ANCHOR_SENT_RE = re.compile(
    r"(?:male|female|man|woman)?\s*aged\s*about\s*[^.;;\n]{0,120}"
    r"|[男女][\u00b7·][^.;;\n]{0,120}"
    r"|the\s+[\u4e00-\u9fff]{2,12}\s+look\s+of\s+[\u4e00-\u9fff]{2,8}[^.;;\n]{0,80}"
    r"|look\s+of\s+[\u4e00-\u9fff]{2,8}\s*[,，][^.;;\n]{0,80}",
    re.I)

def strip_idn_anchor(text):
    """剥离身份锚定句式段（中文专名允许区），返回剩余文本"""
    return IDN_ANCHOR_SENT_RE.sub("", str(text or ""))

# ★ 2026-08-27 风格感知：证件照 9 要素分两类
# 写实风格（默认/旧）：含 85mm f/1.8 相机参数
ID_KEYS_REAL = ["3:4 portrait", "ID/passport", "head-and-shoulders", "head centered", "neutral expression",
                "plain solid background", "even studio lighting", "no pose", "85mm f/1.8"]
# 动画/CG 风格（国漫幻想等）：禁写实相机，改查 3D CG 角色渲染介质
ID_KEYS_CG = ["3:4 portrait", "ID/passport", "head-and-shoulders", "head centered", "neutral expression",
              "plain solid background", "even studio lighting", "no pose"]   # ★ v3.2.0 去掉写死的第9项介质锚，改由 CG_ANCHOR_ANY 集合查
# ★ v3.2.0 主图 CG 介质锚可接受集合（覆盖族A 国漫CG / 族C 2D赛璐璐，防非国漫 CG 项目被写死字面量误报）
CG_ANCHOR_ANY = ["guoman cg character render", "3d cg character render", "cg character render",
                 "2d cel-shaded anime render", "cel-shaded anime render", "animated-feature render"]
# ★ v3.2.0 CG 风 body 主动风格化锚（剥 STYLE_HEAD 首句后正向 body 必含其一，治"指纹在但被写实人像词淹没致风格漂"）
CG_STRONG_STYLE = ["cel-influenced", "cel-shaded", "cel shaded", "flat cel", "line art",
                   "toon shader", "toon-shaded", "not photographic", "non-photographic",
                   "anime-styled", "anime styled", "2.5d", "animated-feature", "animated feature",
                   "stylized painterly", "painterly 3d", "painterly cg"]
# 动画/CG 风格额外禁止的写实词（写实风格不查，避免误伤）
ID_REALISM_BAN = ["photorealistic", "live-action", "realistic skin pores", "film grain", "85mm", "sony a7r", "f/1.8"]
# ★ v3.4.0-风格库 写实族（is_cg=False）反向禁磨皮网红词（事故：主图写 porcelain skin→磨皮AI脸；配套 render-medium-library 族B 真人皮肤锚）
#   故意不含 "beauty retouch"——族B STYLE_HEAD 合法含 "no beauty retouching"，含之会误伤
SKIN_BAN_REAL = ["porcelain skin", "flawless", "airbrushed", "glass skin", "baby skin", "ultra-smooth skin"]

ID_VIOL = ["full body", "standing pose", "dark gradient background", "side view", "three-quarter",
           "dynamic action pose", "busy background"]
# ★ 2026-08-21 身份图两图制：定妆照（prompt）+ 四视图角色卡（sheet_prompt）
FRONT_KEYS = ["front-facing", "facing camera", "frontal view", "front view"]   # 定妆照正面要素（任一命中即可）
IDN_FULL_KEYS = ["full body", "full-length", "full standing", "full outfit", "standing pose"]   # ★ 2026-08-21 身份定妆照=正面全身基准（02 定义），查全身要素（任一命中即可）
SHEET_KEYS = ["2x2 grid", "close-up facial portrait", "side profile",
              "full body", "back view", "plain solid background", "rim light"]
SHEET_WRONG = ["ID/passport", "3:4 portrait"]   # 四视图卡禁证件照词（head-and-shoulders 允许：上排特写即此构图）
# ★ 2026-08-21 用户钦定固定模板（中文）：含特征词即豁免英文纯净，只查结构特征
SHEET_FIXED_MARK = "请基于参考人物"
SHEET_FIXED_KEYS = ["上下两段式", "正脸特写", "侧脸特写", "正面服装展示", "背面全身"]
PERSON_WORDS = ["man", "woman", "person", "people", "crowd", "student", "teacher", "walking", "standing",
                "gathering", "boy", "girl", "disciple", "cultivator", "ninja standing"]
# ★ 2026-08-21 道具五宫格（产品特写写法含中文段，豁免英文纯净；中英文关键词统一查小写）
PROP_LAYOUT_KEYS = ["五宫格", "上2下3", "上 2 下 3", "2 rows", "3 columns", "5-panel", "five-panel",
                    "five views", "five panels", "5 宫格", "五个视图"]
PROP_VIEW_KEYS = {
    "正面": ["正面", "front view", "front side"],
    "背面": ["背面", "back view", "back side"],
    "左侧面": ["左侧面", "left side"],
    "右侧面": ["右侧面", "right side"],
    "材质特写": ["材质", "material", "texture", "特写", "close-up"],
}

def pos_part(p):
    """剥离负面段（Negative prompt / negative: / FORBIDDEN 之后的内容）"""
    for sep in ("Negative prompt", "negative:", "Negative:", "FORBIDDEN", "forbidden:"):
        i = p.find(sep)
        if i >= 0:
            return p[:i]
    return p

def cn_in_pos(p):
    """检查正向段是否含中文"""
    return CN_RE.findall(pos_part(p))

def detect_style(root):
    """读取当前确认的风格（pipeline-state → xiage-styles.handoff），判断是否为动画/CG 风格。
    返回 (is_cg, style_tag) —— is_cg=True 时证件照改用 3D CG 介质、禁写实词。
    ★ 2026-09-06c 修复：handoff 为 .md 时，解析其中「风格类型」行定位真实 preset json
    （历史事故：handoff-xiage.md 非 json 路径 → 静默回退字母序第一个 anime.json，
    导致按 ANIME 检查 chinese_period_drama 项目，产生 130+ 误报）。"""
    try:
        ps = os.path.join(root, "pipeline-state.json")
        handoff = None
        if os.path.exists(ps):
            st = json.load(open(ps, encoding="utf-8"))
            handoff = st.get("modules", {}).get("xiage-styles", {}).get("handoff")
        if handoff and str(handoff).endswith(".md"):
            # 从 handoff md 中解析「风格类型」行：`chinese_period_drama` → outputs/styles/<名>.json
            fp_md = handoff if os.path.isabs(handoff) else os.path.join(root, handoff)
            if os.path.exists(fp_md):
                md = open(fp_md, encoding="utf-8").read()
                m = re.search(r"风格类型\*{0,2}[：:]\s*`?([\w\-]+)`?", md)
                if m:
                    cand = os.path.join(root, "outputs", "styles", m.group(1) + ".json")
                    if os.path.exists(cand):
                        sd = json.load(open(cand, encoding="utf-8"))
                        tag = str(sd.get("style_tag", "") + " " + str(sd.get("visual_references", ""))).lower()
                        is_cg = any(k in tag for k in ("guoman", "3d", "cg", "anime", "cartoon", "cel-shad", "二维", "三维"))
                        return is_cg, sd.get("style_tag", "")
        # 兜底：取 outputs/styles/ 字母序第一个
        if not handoff or not handoff.endswith(".json"):
            sdir = os.path.join(root, "outputs", "styles")
            if os.path.isdir(sdir):
                js = sorted(f for f in os.listdir(sdir) if f.endswith(".json"))
                handoff = os.path.join("outputs", "styles", js[0]) if js else None
        if handoff:
            fp = os.path.join(root, handoff) if not os.path.isabs(handoff) else handoff
            if os.path.exists(fp):
                sd = json.load(open(fp, encoding="utf-8"))
                tag = str(sd.get("style_tag", "") + " " + str(sd.get("visual_references", ""))).lower()
                is_cg = any(k in tag for k in ("guoman", "3d", "cg", "anime", "cartoon", "cel-shad", "二维", "三维"))
                return is_cg, sd.get("style_tag", "")
    except Exception:
        pass
    return False, ""

def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    d = load_registry(root)
    if d is None:
        print("❌ 未找到资产数据（outputs/xiatang/assets-registry.json 或 xiaji.db）"); sys.exit(1)
    is_cg, style_tag = detect_style(root)
    ID_KEYS = ID_KEYS_CG if is_cg else ID_KEYS_REAL
    problems = 0

    # ① ② ③ 角色层
    for c in d.get("characters", []):
        name = c.get("name", "?")
        is_group = bool(c.get("group"))   # ★ 群像资产（如多角色群像）：只查英文纯净，跳过证件照/身份图检查
        pp = str(c.get("portrait_prompt") or c.get("prompt") or "")
        # 分离正向段（违规词/中文只查正向段；Negative/FORBIDDEN 后为负面词豁免区）
        pos = pos_part(pp)
        # ① 中文（正向段；★ 2026-09-06c 剥离身份锚定句后再扫，防把「男·示例称号·身份」等专名锚误报）
        cn = CN_RE.findall(strip_idn_anchor(pos))
        if is_group:
            # ★ 群像资产允许顶部中文引用行（如 角色A=图1，角色B=图2），检查前剥离第一行
            pp_no_ref = "\n".join(pp.split("\n")[1:]) if "\n" in pp else pp
            cn = CN_RE.findall(strip_idn_anchor(pos_part(pp_no_ref)))
        if cn:
            print(f"❌ [{name}] 主图正向段含中文: {cn[:3]}"); problems += 1
        if is_group:
            continue
        # ② 证件照要素（正向段查；大小写不敏感 ★ 2026-08-19：句首大写 Character reference 等写法需兼容）
        pos_l = pos.lower()
        miss = [k for k in ID_KEYS if k.lower() not in pos_l]
        viol = [k for k in ID_VIOL if k.lower() in pos_l]
        if is_cg:
            # 动画/CG 风格：额外禁止写实相机/真人词（写实风格不查，避免误伤）
            real_ban = [k for k in ID_REALISM_BAN if k in pos_l]
            if real_ban:
                print(f"❌ [{name}] 主图含写实词（CG风格禁用）: {real_ban}"); problems += 1
            # ★ v3.2.0 主图 CG 介质锚（走可接受集合，覆盖族A/C，不再写死 guoman）
            if not any(a in pos_l for a in CG_ANCHOR_ANY):
                print(f"❌ [{name}] 主图缺 CG 介质锚（须含 CG_ANCHOR_ANY 任一，见 render-medium-library 族定义）"); problems += 1
        else:
            # ★ v3.4.0-风格库 写实族主图禁磨皮网红词（正向段；事故：porcelain skin→磨皮AI脸，与族B真人皮肤锚配套）
            skin_ban = [k for k in SKIN_BAN_REAL if k in pos_l]
            if skin_ban:
                print(f"❌ [{name}] 主图含磨皮网红词（写实族禁用，改用 real photographed / visible pores）: {skin_ban}"); problems += 1
        if miss:
            print(f"❌ [{name}] 主图缺证件照要素: {miss}"); problems += 1
        if viol:
            print(f"❌ [{name}] 主图正向段含违规词: {viol}"); problems += 1
        # ③ 身份图 = 两图制（★ 2026-08-21 用户拍板：①定妆照 prompt + ②四视图角色卡 sheet_prompt）
        for idn in c.get("identities", []):
            idname = idn.get('identity_name') or idn.get('name') or ''
            # ① 身份定妆照（prompt）：证件照式正面基准图，查英文纯净 + 正面要素
            ip = str(idn.get("prompt") or "")
            cn2 = CN_RE.findall(strip_idn_anchor(pos_part(ip)))
            if cn2:
                print(f"❌ [{name}] 身份图[{idname}] 定妆照正向段含中文: {cn2[:3]}"); problems += 1
            ipos_l = pos_part(ip).lower()
            if ip and not any(k in ipos_l for k in FRONT_KEYS):
                print(f"❌ [{name}] 身份图[{idname}] 定妆照缺正面要素（{FRONT_KEYS}）"); problems += 1
            if ip and not any(k in ipos_l for k in IDN_FULL_KEYS):
                print(f"❌ [{name}] 身份图[{idname}] 定妆照缺全身要素（{IDN_FULL_KEYS}，身份定妆照=正面全身基准）"); problems += 1
            # ② 四视图角色卡（sheet_prompt）：固定中文模板（豁免英文纯净）或英文兜底模板
            sp2 = str(idn.get("sheet_prompt") or "")
            if not sp2:
                print(f"❌ [{name}] 身份图[{idname}] 缺四视图卡提示词（sheet_prompt）"); problems += 1
                continue
            if SHEET_FIXED_MARK in sp2:
                # 用户钦定中文固定模板：豁免英文纯净，查结构特征
                miss_f = [k for k in SHEET_FIXED_KEYS if k not in sp2]
                if miss_f:
                    print(f"❌ [{name}] 身份图[{idname}] 四视图卡固定模板缺结构特征: {miss_f}"); problems += 1
            else:
                cn3 = CN_RE.findall(strip_idn_anchor(pos_part(sp2)))
                if cn3:
                    print(f"❌ [{name}] 身份图[{idname}] 四视图卡正向段含中文: {cn3[:3]}"); problems += 1
                spos_l = pos_part(sp2).lower()
                miss2 = [k for k in SHEET_KEYS if k.lower() not in spos_l]
                if miss2:
                    print(f"❌ [{name}] 身份图[{idname}] 四视图卡缺要素: {miss2}"); problems += 1
                wrong2 = [k for k in SHEET_WRONG if k.lower() in spos_l]
                if wrong2:
                    print(f"❌ [{name}] 身份图[{idname}] 四视图卡误用证件照词: {wrong2}"); problems += 1

    # ④ 场景空镜（★ 只查正向段：负面段 negative:/FORBIDDEN 中的 people 等词是排除指令，不算违规；
    #   ★ 2026-09-06c：正向段 "no people / no crowd / no characters" 是否定空镜句式，亦不算人物词——
    #   只统计「非否定前缀」出现次数，防把 "Empty location with no people..." 误报为人）
    for s in d.get("scenes", []):
        sp = str(s.get("prompt") or "")
        spos = pos_part(sp)
        hits = []
        for w in PERSON_WORDS:
            cnt_all = len(re.findall(r"\b" + w + r"\b", spos, re.I))
            cnt_neg = len(re.findall(r"\bno\s+" + w + r"\b|\bwithout\s+" + w + r"\b", spos, re.I))
            if cnt_all > cnt_neg:
                hits.append(w)
        if hits:
            print(f"❌ [场景 {s.get('name')}] 正向段含人物词: {hits[:5]}"); problems += 1

    # ⑤ 道具五宫格（★ 2026-08-21：产品特写写法含中文段，豁免英文纯净，只查布局+五视图）
    #   ★ 2026-09-06c：概念参考图类道具（prompt 含 concept image/plate 等，非手持实体）豁免五宫格
    CONCEPT_PROP_MARK = re.compile(r"\bconcept\b", re.I)
    for p in d.get("props", []):
        pp = str(p.get("prompt") or "")
        if not pp:
            continue
        if CONCEPT_PROP_MARK.search(pos_part(pp)):
            continue   # 概念参考图（如地理奇观/能量特效），不是实体产品，无五视图概念
        ppos_l = pos_part(pp).lower()
        if not any(k in ppos_l for k in PROP_LAYOUT_KEYS):
            print(f"❌ [道具 {p.get('name')}] 缺五宫格布局描述（五宫格/上2下3/5-panel 等）"); problems += 1
        for vname, keys in PROP_VIEW_KEYS.items():
            if not any(k in ppos_l for k in keys):
                print(f"❌ [道具 {p.get('name')}] 五宫格缺视图: {vname}"); problems += 1

    # ⑥ 三要素内联完整性 + 视觉参考标记（★ 2026-09-02 方案 A/C：
    #   弱风格词事故固化——只查关键词存在性挡不住弱内联，必须校验 preset 指纹句整句内联）
    style_preset = None
    try:
        _ps2 = os.path.join(root, "pipeline-state.json")
        _ho2 = None
        if os.path.exists(_ps2):
            _st2 = json.load(open(_ps2, encoding="utf-8"))
            _ho2 = _st2.get("modules", {}).get("xiage-styles", {}).get("handoff")
        # ★ 2026-09-06c 同步 detect_style 修复：handoff 为 .md → 解析「风格类型」行定位真实 preset
        if _ho2 and str(_ho2).endswith(".md"):
            _fp_md = _ho2 if os.path.isabs(_ho2) else os.path.join(root, _ho2)
            if os.path.exists(_fp_md):
                _md2 = open(_fp_md, encoding="utf-8").read()
                _m2 = re.search(r"风格类型\*{0,2}[：:]\s*`?([\w\-]+)`?", _md2)
                if _m2:
                    _cand = os.path.join(root, "outputs", "styles", _m2.group(1) + ".json")
                    if os.path.exists(_cand):
                        _ho2 = os.path.join("outputs", "styles", _m2.group(1) + ".json")
        if not _ho2 or not str(_ho2).endswith(".json"):
            _sd2 = os.path.join(root, "outputs", "styles")
            if os.path.isdir(_sd2):
                _js2 = sorted(f for f in os.listdir(_sd2) if f.endswith(".json"))
                _ho2 = os.path.join("outputs", "styles", _js2[0]) if _js2 else None
        if _ho2:
            _fp2 = _ho2 if os.path.isabs(_ho2) else os.path.join(root, _ho2)
            if os.path.exists(_fp2):
                style_preset = json.load(open(_fp2, encoding="utf-8"))
    except Exception:
        style_preset = None

    style_fp = ""
    avoid_keys = []
    style_first_sent = ""
    if style_preset:
        _si = str(style_preset.get("style_instructions") or "").strip()
        _first = re.split(r"(?<=[.!?])\s+", _si)[0] if _si else ""
        style_fp = " ".join(_first.split()[:8]).lower()   # 前 8 词核心短语（抗逗号/插入语变体，仍锁 preset 原文核心）
        style_first_sent = _first.lower()   # ★ v3.2.0 供 CG body 强标记校验剥离 STYLE_HEAD 首句
        _av = re.sub(r"^FORBIDDEN:\s*", "", str(style_preset.get("avoid_instructions") or ""), flags=re.I)
        avoid_keys = [x.strip().lower() for x in _av.split(",") if x.strip()][:2]

    ref_required = False
    try:
        _cdp = os.path.join(root, "outputs", "creation-direction.json")
        if os.path.exists(_cdp):
            _cd = json.load(open(_cdp, encoding="utf-8"))
            ref_required = any(str(r.get("infusion") or "").strip() for r in (_cd.get("visual_references") or []))
    except Exception:
        pass

    _REF_MARK = "visual reference infusion"
    _OUTFIT_REF_MARK = "strictly replicate"   # 服装参考版固定模板特征（豁免，靠垫图锁风格）

    def check_inline(pp, label):
        """方案 A/C：指纹句 + 负面禁令 + 视觉参考标记。钦定固定模板（四视图卡/服装参考版）豁免。
        ★ 2026-09-06c avoid 语义等价：'NOT anime' ≡ 'FORBIDDEN: ... anime'——禁令对象词在
        负面段出现即视为已内联（旧提示词按 FORBIDDEN 句式生成，与 NOT 句式语义等价）。"""
        nonlocal problems
        pp = str(pp or "")
        if not pp:
            return
        pl = pp.lower()
        if SHEET_FIXED_MARK in pp or _OUTFIT_REF_MARK in pl:
            return
        pos_l = pos_part(pp).lower()
        if style_fp and style_fp not in pos_l:
            print(f"❌ [{label}] 缺风格三要素内联（正向段缺指纹句「{style_fp}…」——须从 preset 原文整句内联，禁自造弱化风格词）"); problems += 1
        if is_cg:
            _body = pos_l.replace(style_first_sent, "") if style_first_sent else pos_l
            if not any(m in _body for m in CG_STRONG_STYLE):
                print(f"❌ [{label}] CG 风正向 body 缺主动风格化锚（剥 STYLE_HEAD 首句后无 cel-influenced/not photographic/flat cel 等——写实人像词会淹没介质句致风格漂，见 render-medium-library 对应族 body 强标记）"); problems += 1
        for _ak in avoid_keys:
            # 语义等价兜底：NOT X ≡ FORBIDDEN 段含 X
            _obj = re.sub(r"^(not|no)\s+", "", _ak).strip()
            _equiv = _obj and _obj in pl and ("forbidden" in pl or "negative" in pl)
            if not _equiv:
                print(f"❌ [{label}] 负面段缺关键禁令「{_ak}」（avoid_instructions 原文内联）"); problems += 1
        if ref_required and _REF_MARK not in pl:
            print(f"❌ [{label}] 缺视觉参考注入标记「Visual reference infusion」"); problems += 1

    for c in d.get("characters", []):
        _nm = c.get("name", "?")
        check_inline(c.get("portrait_prompt") or c.get("prompt"), f"{_nm} 主图")
        for _idn in c.get("identities", []):
            _inm = _idn.get("identity_name") or _idn.get("name") or ""
            check_inline(_idn.get("prompt"), f"{_nm} 身份图[{_inm}] 定妆照")
            # 四视图卡整体豁免（生成时以定妆照垫图锁风格，不靠提示词承载风格三要素）

    for s in d.get("scenes", []):
        check_inline(s.get("prompt"), f"场景 {s.get('name')}")
    for p in d.get("props", []):
        check_inline(p.get("prompt"), f"道具 {p.get('name')}")

    # ⑧ 依赖门禁 + 道具锚点（★ 2026-09-03 集成，前半程方法论蒸馏）
    _char_list = d.get("characters", [])
    _char_names = {c.get("name") for c in _char_list}
    for c in _char_list:
        dep = c.get("dependencies")
        if not isinstance(dep, dict):
            dep = {}
        ups_raw = dep.get("upstream") or []
        ups = ups_raw if isinstance(ups_raw, list) else [ups_raw]
        if not ups:
            continue
        _cdep_name = c.get("name", "?")
        _bad = [u for u in ups if u not in _char_names]
        if _bad:
            print(f"❌ [角色 {_cdep_name}] dependencies.upstream 指向不存在的资产名: {_bad}"); problems += 1
        _pp8 = str(c.get("portrait_prompt") or c.get("prompt") or "")
        if _pp8:
            for _u in ups:
                _uobj = next((x for x in _char_list if x.get("name") == _u), None)
                if _uobj is None:
                    continue
                _u_prompt = bool(str(_uobj.get("portrait_prompt") or _uobj.get("prompt") or "").strip())
                _u_ready = bool(_uobj.get("image_ready") or _uobj.get("portrait_ready"))
                if not (_u_prompt or _u_ready):
                    print(f"❌ [角色 {_cdep_name}] 下游提示词已产出，但上游 [{_u}] 主图/提示词未定稿（违反依赖门禁，先完成上游再写下游）"); problems += 1
    for p in d.get("props", []):
        _anchors_raw = p.get("continuity_anchors")
        if isinstance(_anchors_raw, str):
            _anchors_list = [_anchors_raw]
        elif isinstance(_anchors_raw, list):
            _anchors_list = _anchors_raw
        else:
            _anchors_list = []
        _anchors = [str(a).strip() for a in _anchors_list if str(a).strip()]
        if not _anchors:
            continue
        _pp9 = str(p.get("prompt") or "")
        if not _pp9:
            continue
        _miss_a = [a for a in _anchors if a not in _pp9]
        if _miss_a:
            print(f"❌ [道具 {p.get('name')}] 登记的识别锚点未逐条写入提示词: {_miss_a[:3]}（跨镜连续性锚点必须进词）"); problems += 1

    # ⑩ 双语成对（★ 2026-09-06 双语双产契约：prompt=EN 生图主字段，prompt_cn=CN 理解层，成对产出）
    #   四视图卡固定中文模板（sheet_prompt 含「请基于参考人物」）本身是中文，豁免
    def check_pair(en, cn, label):
        nonlocal problems
        en = str(en or "").strip(); cn = str(cn or "").strip()
        if not en and not cn:
            return
        if en and not cn:
            print(f"❌ [{label}] EN 提示词缺配对 prompt_cn（双语双产契约，需结构化对译回补）"); problems += 1
        elif cn and not en:
            print(f"❌ [{label}] 有 prompt_cn 但缺 EN 主字段（EN 是生图执行稿，缺即不可生成）"); problems += 1

    for c in d.get("characters", []):
        _nm = c.get("name", "?")
        check_pair(c.get("portrait_prompt") or c.get("prompt"), c.get("portrait_prompt_cn") or c.get("prompt_cn"), f"{_nm} 主图")
        for _idn in c.get("identities", []):
            _inm = _idn.get("identity_name") or _idn.get("name") or ""
            check_pair(_idn.get("prompt"), _idn.get("prompt_cn"), f"{_nm} 身份图[{_inm}] 定妆照")
            _sp = str(_idn.get("sheet_prompt") or "")
            if _sp and SHEET_FIXED_MARK not in _sp:   # 英文兜底模板需配对；固定中文模板豁免
                check_pair(_sp, _idn.get("sheet_prompt_cn"), f"{_nm} 身份图[{_inm}] 四视图卡")
    for s in d.get("scenes", []):
        check_pair(s.get("prompt"), s.get("prompt_cn"), f"场景 {s.get('name')}")
    for p in d.get("props", []):
        check_pair(p.get("prompt"), p.get("prompt_cn"), f"道具 {p.get('name')}")

    # ================= ★ 2026-09-10 3.5.12 新增三项 =================
    # 共性根因（渔村 ep001 自检）：旧门禁只校验「已有字段对不对」，对「该产出的整层没产出 /
    # 指针指向旧文件」完全无感 → 门禁全绿而交付残缺。

    # ⑨ 陈旧图片指针：同目录存在 <stem>-<纯数字时间戳>.<ext> 且 mtime 更新 → registry 仍指旧图
    import glob as _glob
    import time as _time
    _proj = os.path.join(root, "project")

    def _iter_img_refs():
        for c in d.get("characters", []):
            yield (u"角色 %s" % c.get("name"), u"主图", c.get("image"))
            for _idn in c.get("identities", []):
                _inm = _idn.get("identity_name") or _idn.get("name") or ""
                yield (u"角色 %s/%s" % (c.get("name"), _inm), u"定妆照", _idn.get("image"))
                yield (u"角色 %s/%s" % (c.get("name"), _inm), u"四视图", _idn.get("sheet_image"))
        for _key in ("scenes", "props", "key_scenes"):
            for it in d.get(_key, []):
                yield (u"%s %s" % (_key, it.get("name")), u"图", it.get("image"))

    for _label, _slot, _ref in _iter_img_refs():
        if not _ref:
            continue
        _cur = os.path.join(_proj, str(_ref).replace("/", os.sep))
        if not os.path.exists(_cur):
            continue                      # 路径不存在由 build-data-js / repair-asset-paths 负责
        _dd, _fn = os.path.split(_cur)
        _stem, _ext = os.path.splitext(_fn)
        _cands = []
        for _q in _glob.glob(os.path.join(_dd, _stem + "-[0-9]*" + _ext)):
            _tail = os.path.splitext(os.path.basename(_q))[0]
            if _tail.startswith(_stem + "-") and _tail[len(_stem) + 1:].isdigit():
                _cands.append(_q)
        if _cands:
            _newest = max(_cands, key=os.path.getmtime)
            if os.path.getmtime(_newest) > os.path.getmtime(_cur) + 1:
                print(u"❌ [%s %s] 陈旧指针：现指 %s（%s），同目录存在更新版 %s（%s）——"
                      u"疑似换风格/重出图后未接回；主图与身份图不同介质会导致锁脸失效"
                      % (_label, _slot, os.path.basename(_cur),
                         _time.strftime("%m-%d %H:%M", _time.localtime(os.path.getmtime(_cur))),
                         os.path.basename(_newest),
                         _time.strftime("%m-%d %H:%M", _time.localtime(os.path.getmtime(_newest)))))
                problems += 1

    # ⑩ 声线字段存在性计数（声线是虾塘四域之一，整层缺失必须报）
    # 契约正本 = xiatang-characters SKILL.md「声线域契约」：唯一键名 voice_desc（+ voice_ready）
    _chars = [c for c in d.get("characters", []) if not c.get("group")]
    _has_desc = [c for c in _chars if str(c.get("voice_desc") or "").strip()]
    if _chars and not _has_desc:
        print(u"❌ [声线] 声线域未落库：%d 个角色无一条 voice_desc——"
              u"声线是虾塘四域之一、与脸/服装同级的连续性锚点，走到配音合成必卡门控。"
              u"补法：按 xiatang SKILL.md「声线域契约」逐角色写 voice_desc（音色/年龄感/语速/气息/情绪底色），"
              u"再跑 build-data-js.py 放行入快照" % len(_chars))
        problems += 1
    else:
        _no_voice = [c.get("name") for c in _chars if not str(c.get("voice_desc") or "").strip()]
        if _no_voice:
            print(u"❌ [声线] %d/%d 个角色缺 voice_desc：%s"
                  % (len(_no_voice), len(_chars), u"、".join([str(x) for x in _no_voice[:8]])))
            problems += 1

    # ⑪ 场景图门通向兜底（条款正本 = xiatang scene-assets.md A2·5，此处只机械校验）
    _DOOR_MARK = "Doorway relation:"
    _DOOR_WORDS = ("door", "doorway", "gate", "entrance", "threshold",
                   "门", "门口", "门槛", "入口", "堂屋")
    for s in d.get("scenes", []):
        _img = str(s.get("image") or "").strip()
        if not _img or not os.path.exists(os.path.join(_proj, _img.replace("/", os.sep))):
            continue                      # ★ 图真在盘上才算「会被垫图」（registry 有路径但文件缺失另由同步检查管）
        # ★ 3.5.13 解除条件改用盘上事实：显式 layout_ready=true，或约定路径下真有 layout 图
        _lay = str(s.get("layout_image") or "").strip()
        if s.get("layout_ready") is True or (
                _lay and os.path.exists(os.path.join(_proj, _lay.replace("/", os.sep)))):
            continue                      # layout 已就位 → 兜底自动解除，分工回到 A2
        _pos = pos_part(str(s.get("prompt") or ""))
        _low = _pos.lower()
        if not any(w in _low for w in _DOOR_WORDS):
            continue                      # 开放场景（村道/田野/海面）无门可交代，不强制
        if _DOOR_MARK not in _pos:
            print(u"❌ [场景 %s] 已被垫图但 A2 layout 未 ready（layout_ready!=true），提示词缺「%s」声明——"
                  u"布局权威缺位时门通向无人交代，生图会自行补全（实测：开门见海）"
                  % (s.get("name"), _DOOR_MARK))
            problems += 1


    if problems == 0:
        print("✅ 全部通过：资产提示词合规（英文纯净/证件照/身份图两图/场景空镜/道具五宫格/三要素内联/CG介质锚/CG强风格化锚/视觉参考注入/依赖门禁/道具锚点/双语成对/陈旧指针/声线存在/门通向兜底）")
        sys.exit(0)
    else:
        print(f"\n⚠️ 共 {problems} 处问题，请修复后重跑")
        sys.exit(1)


def selftest():
    """投毒对照：临时造最小项目目录，证明 ⑨⑩⑪ 真会报、干净时不误报（探针式断言，不受其他项噪声影响）。"""
    import shutil
    import tempfile
    print(u"=== check-assets --selftest：投毒对照 ===")
    tmp = tempfile.mkdtemp(prefix="ca_selftest_")
    proj = os.path.join(tmp, "project", "assets", "characters")
    os.makedirs(proj)
    out_dir = os.path.join(tmp, "outputs", "xiatang")
    os.makedirs(out_dir)

    def build(stale, door, voice):
        a = os.path.join(proj, "A.png")
        b = os.path.join(proj, "A-1700000000000.png")
        io.open(a, "w").write("x")
        io.open(b, "w").write("yy")
        os.utime(a, (1600000000, 1600000000))
        os.utime(b, (1700000000, 1700000000))
        img = "assets/characters/A.png" if stale else "assets/characters/A-1700000000000.png"
        ch = {"name": u"角色A", "image": img, "prompt": "x", "prompt_cn": u"x"}
        if voice:
            ch["voice_desc"] = u"女·低沉·略哑"
        base = u"a small room with a single wooden door and one window. "   # 恒含 door → ⑪ 判据成立
        dtxt = base + (("Doorway relation: the door opens onto the yard; only the yard is visible through it; "
                        "no sea and no horizon are visible. ") if door else "")
        reg = {"characters": [ch],
               "scenes": [{"name": u"场甲", "image": img, "layout_ready": False,
                           "prompt": dtxt + chr(10) + "Negative prompt: people",
                           "prompt_cn": u"一间屋"}],
               "props": [], "key_scenes": []}
        io.open(os.path.join(out_dir, "assets-registry.json"), "w", encoding="utf-8").write(
            json.dumps(reg, ensure_ascii=False))

    NEEDLES = [u"陈旧指针", u"[声线]", u"Doorway relation"]  # 探针串均取自新文案，改文案须同步
    sys.argv = ["check-assets.py", tmp]
    failed = 0
    for label, args, expect in [(u"投毒·旧指针+无声线+无门通向", (True, False, False), True),
                                (u"干净·已接回+已补齐", (False, True, True), False)]:
        build(*args)
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
        for nd in NEEDLES:
            hit = nd in rep
            ok = (hit == expect)
            if not ok:
                failed += 1
            print(u"  [%s] %-26s 探针「%s」期望=%s 实际=%s"
                  % (u"OK" if ok else u"❌ 空转/误报", label, nd, expect, hit))
    shutil.rmtree(tmp, ignore_errors=True)
    return 1 if failed else 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.argv = [a for a in sys.argv if a != "--selftest"]
        sys.exit(selftest())
    main()
