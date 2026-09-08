# 已有旧项目手动同步 SOP（templates/ → 旧项目 project/）

> 适用：模板升级（新增模块/修复）后，让**已创建的旧项目**获得新能力（如听风电影模块）。
> 最高原则：**只覆盖代码层，绝不动数据层**；同步五步缺一不可——备份 → 盘点差异 → 覆盖 → 替换占位符/回迁定制 → 重启验证。

## 0. 同步范围（★ 先背下来）

| 层 | 文件 | 同步？ |
|---|---|---|
| 代码层 | `index.html` `css/` `js/`（10 文件）`server.py` `api_slot.py` `build-data-js.py` | ✅ 覆盖（第 3 步） |
| 启动器 | `启动项目台.bat` `启动项目台.ps1` | ⚠️ 一般不动；动了必须重做占位符替换（bat 纯 ASCII + `{{TITLE}}`） |
| 配置层 | `img_config.json` `ann_tags_config.json` | ❌ **禁止覆盖**（渠道/key/默认尺寸/标注词是项目私有） |
| 数据层 | `xiaji.db` `assets/` `outputs/` `chapters/` `docs/` `pipeline-state.json` | ❌ **永远不碰** |

## 1. 备份（必做，防覆盖后悔）

```bash
PJ="<项目根>/project"
BK="$PJ/_backup-<YYYYMMDD>"
mkdir -p "$BK" && cp -r "$PJ/index.html" "$PJ/css" "$PJ/js" \
  "$PJ/server.py" "$PJ/api_slot.py" "$PJ/build-data-js.py" "$BK/"
```
（项目里没有的文件会 cp 报错，忽略即可；备份放项目内，回滚透明）

## 2. 盘点差异（★ 防覆盖项目私有定制）

```bash
T=~/.workbuddy/skills/xia-boss/templates
for f in index.html css/main.css js/gen.js js/core.js js/xiajing.js js/xiatang.js \
         js/xialiao.js js/xiage.js js/agent.js js/ann.js js/init.js \
         server.py api_slot.py build-data-js.py; do
  n=$(diff <(tr -d '\r' < "$PJ/$f") <(tr -d '\r' < "$T/$f") 2>/dev/null | grep -c '^[<>]')
  echo "$n  $f"
done
```
- **diff = 0** → 该文件直接覆盖，零风险。
- **diff 小且模板侧是新功能、项目侧是本地定制**（如场景图按钮尺寸/图标微调）→ 正常覆盖，但把项目侧差异**记下来**，第 4 步回迁。
- **diff 巨大**（项目 JS 有大改）→ ⚠️ 不要盲覆盖该文件，改用**按块移植**：只把模板新增的功能块搬进去（参考 platform-fixes.md 对应条目的改动清单），搬完 node --check。

## 3. 覆盖代码

```bash
cp "$T/index.html" "$PJ/index.html"
cp -r "$T/css/." "$PJ/css/"
cp -r "$T/js/." "$PJ/js/"
cp "$T/server.py" "$PJ/server.py"
cp "$T/api_slot.py" "$PJ/api_slot.py" 2>/dev/null || true
cp "$T/build-data-js.py" "$PJ/build-data-js.py"
```

## 4. 替换占位符 + 回迁定制（★ 双向复制纪律的「模板→项目」方向）

1. `grep -rn "{{项目名}}" "$PJ"` → 全部替换为**本剧剧名**（正常分布：index.html 3 处 / server.py 3 处 / js/gen.js 兜底 1 处；bat 用 `{{TITLE}}`）。
2. 把第 2 步记下的**项目私有定制**从备份 diff 里回迁（改完 node --check / py_compile）。
3. 复扫：`grep -rn "{{项目名}}\|{{TITLE}}" "$PJ"` 应为 0；剧名只出现在允许位置。
4. 清理复制带进来的运行残留：`rm -rf "$PJ/__pycache__"`。

## 5. 重启 + 验证

1. **杀旧进程重启**（server.py 变了必须重启；bat 自带清端口）。
2. 浏览器 **Ctrl+Shift+R 硬刷新**（新 index.html 的 `?v=` 版本号会自动破 JS/CSS 缓存）。
3. 验证清单：
   - [ ] 侧栏出现新增入口（如「🎬 听风电影」）；
   - [ ] ⚙ 设置出现新增项（如「🧭 分镜主力线」）；
   - [ ] Console 无 `xxx is not defined`（有 = 某个新 JS 没加载/没复制全）；
   - [ ] 跑 `build-data-js.py <项目根>` → 页面数据正常、无新增报错（新模块快照为空属正常，首次使用时生成）；
   - [ ] 真实生一张图：任务完成 → 资产位**不刷新页面**即时更新（验证 mark_ready 落库对 + rerenderCurrent 分支成对）。

## 6. 常见坑

- **img_config.json 被覆盖** = 渠道/key 全丢（只能从备份恢复）。
- 旧项目没有新模块的数据目录（如 `outputs/tingfeng/`）→ 正常，首次使用该功能时自动生成。
- 「模板→项目」复制后忘替换占位符 → 页面标题/侧栏显示 `{{项目名}}` 字面量（#39）。
- 项目 JS 与模板 diff 巨大时强行覆盖 = 项目定制全毁（#38）——走按块移植。
- 同步完成后把项目私有定制的**长期改动**回写进模板（双向纪律），下次同步才不会再丢。
