# 标准媒体操作图标实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 使用标准上传与垃圾桶 SVG 替换媒体操作的手绘图标。

**Architecture:** 图标由 `assets/icons` 中的项目资源提供，`GameDetailDialog` 直接通过文件路径构造 `QIcon`。删除不再需要的 `create_media_action_icon()`，其余按钮布局和行为不变。

**Tech Stack:** Python 3、PySide6、SVG、unittest

## Global Constraints

- 上传图标采用托盘与向上箭头。
- 删除图标采用完整垃圾桶轮廓。
- 不增加第三方依赖。
- 按钮尺寸、位置和行为不变。

---

### Task 1: 替换媒体操作图标

**Files:**
- Create: `assets/icons/upload.svg`
- Create: `assets/icons/trash.svg`
- Modify: `main.py:90`
- Modify: `tests/test_game_detail_media.py`

**Interfaces:**
- Consumes: Qt `QIcon(path)`。
- Produces: `MEDIA_UPLOAD_ICON`、`MEDIA_TRASH_ICON` 图标路径常量。

- [ ] **Step 1: 写失败测试**

```python
def test_media_actions_use_standard_svg_resources(self):
    upload = Path('assets/icons/upload.svg')
    trash = Path('assets/icons/trash.svg')
    self.assertTrue(upload.exists())
    self.assertTrue(trash.exists())
    self.assertIn('<svg', upload.read_text(encoding='utf-8'))
    self.assertIn('<svg', trash.read_text(encoding='utf-8'))
```

同时断言编辑按钮工具提示为“选择或替换”，删除按钮工具提示为“移除”，且图标非空。

- [ ] **Step 2: 运行测试确认失败**

Run: `QT_QPA_PLATFORM=offscreen .conda-env/bin/python -m unittest tests.test_game_detail_media -v`

Expected: FAIL，两个 SVG 文件尚不存在。

- [ ] **Step 3: 新增标准 SVG**

`upload.svg` 使用 `viewBox="0 0 24 24"`，包含向上箭头、竖线和底部托盘；`trash.svg` 使用相同 viewBox，包含桶盖、桶身与两条内部竖线。两者使用 `fill="none"`、`stroke="#c9d1d9"`、`stroke-linecap="round"`、`stroke-linejoin="round"`。

- [ ] **Step 4: 接入资源并移除手绘函数**

```python
MEDIA_UPLOAD_ICON = str(Path(__file__).parent / 'assets/icons/upload.svg')
MEDIA_TRASH_ICON = str(Path(__file__).parent / 'assets/icons/trash.svg')

edit.setIcon(QIcon(MEDIA_UPLOAD_ICON))
remove.setIcon(QIcon(MEDIA_TRASH_ICON))
```

删除 `create_media_action_icon()`，不修改按钮尺寸、位置、样式或信号连接。

- [ ] **Step 5: 运行完整验证**

Run: `QT_QPA_PLATFORM=offscreen .conda-env/bin/python -m unittest discover -s tests -v`

Expected: 全部 PASS。

Run: `git diff --check`

Expected: 无输出。

- [ ] **Step 6: 提交**

```bash
git add assets/icons/upload.svg assets/icons/trash.svg main.py tests/test_game_detail_media.py docs/superpowers/plans/2026-07-29-standard-media-icons.md
git commit -m "ui: 使用标准媒体操作图标"
```
