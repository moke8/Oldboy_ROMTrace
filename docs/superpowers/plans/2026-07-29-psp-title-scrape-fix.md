# PSP 英文标题刮削修复实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 确保 PSP 刮削关键词来自 `PARAM.SFO.TITLE`，游戏 ID 永远不会被当作英文标题。

**Architecture:** 保持现有 PSP ISO/CSO/PBP 解析流程不变，只修正解析结果中 `title_en` 的赋值规则。`DISC_ID` 继续独立保存在 `disc_id`，供唯一标识使用。

**Tech Stack:** Python 3、`unittest`、PSP `PARAM.SFO`

## Global Constraints

- `PARAM.SFO.TITLE` 直接作为 PSP 的 `title` 与 `title_en`。
- `DISC_ID` 只能写入 `disc_id`，不得进入 `title_en`。
- 不引入 PSP 游戏名称对照表或网络依赖。

---

### Task 1: PSP 标题与 ID 分离

**Files:**
- Create: `tests/test_platform_psp.py`
- Modify: `platform_psp.py:255`

**Interfaces:**
- Consumes: `extract_psp_info(psp_path, lang_code='en', log=print)`
- Produces: `info['title_en']` 始终为 `PARAM.SFO.TITLE`，`info['disc_id']` 独立保存编号

- [ ] **Step 1: 写入失败回归测试**

构造包含中文 `TITLE` 与 `DISC_ID` 的最小 PSP ISO，断言 `title_en` 保留标题且不等于游戏 ID。

- [ ] **Step 2: 运行测试确认失败**

Run: `.conda-env/bin/python -m unittest tests.test_platform_psp -v`

Expected: 中文标题用例失败，实际 `title_en` 为 `ULJM05101`。

- [ ] **Step 3: 实现最小修复**

删除 `_has_cjk(title)` 时将 `title_en` 替换成 `disc_id` 的分支，始终执行 `title_en = title`。

- [ ] **Step 4: 验证测试与真实 ISO**

Run: `.conda-env/bin/python -m unittest tests.test_platform_psp -v`

Expected: 所有 PSP 平台测试通过。

Run: `.conda-env/bin/python -c "from platform_psp import extract_psp_info; print(extract_psp_info('/media/Mokevip/Mokevip SD/Roms/PSP/北欧女神 蕾娜斯 汉化版.iso')['title_en'])"`

Expected: 输出 `VALKYRIE PROFILE -LENNETH-`。

- [ ] **Step 5: 运行完整测试集**

Run: `.conda-env/bin/python -m unittest discover -s tests -v`

Expected: 测试集无新增失败。
