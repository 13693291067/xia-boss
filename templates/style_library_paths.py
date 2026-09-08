# -*- coding: utf-8 -*-
"""风格挂载库路径解析（★ v3.4.0-风格库 单一来源）。
build-data-js.py 与 server.py 共用，避免"库目录清单"两处各写一份而漂移。
放置：与调用方同目录——skill 的 scripts/、templates/，以及项目 project/（随模板拷入）。
旧项目缺本文件时，调用方会回退到 skill 的 scripts/templates 位置 import，不会崩。"""
import os


def library_dirs():
    """返回 (skill 种子库目录列表, 用户级库目录)。"""
    dirs = []
    env = os.environ.get("XIA_BOSS_SKILL_DIR", "")
    if env:
        dirs.append(os.path.join(env, "modules", "xiage-styles", "styles-library"))
    dirs.append(os.path.expanduser("~/.qwenworkcn/skills/xia-boss/modules/xiage-styles/styles-library"))
    dirs.append(os.path.expanduser("~/.workbuddy/skills/xia-boss/modules/xiage-styles/styles-library"))
    user_dir = os.path.expanduser("~/.qwenworkcn/xiage-style-library")
    return dirs, user_dir


def resolve():
    """供调用方 import 失败时的兜底：直接返回与 library_dirs 等价的默认值（不含外部逻辑，仅路径）。
    正常情况下调用方 import 本模块成功，不会走到这里。"""
    return library_dirs()
