# 媒体框悬浮操作实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将详情弹窗媒体操作改为每个媒体页右下角的编辑与删除图标。

**Architecture:** `GameDetailDialog` 始终创建封面、Logo、视频三个标签页，每页由预览层和右下角操作层组成。Qt 运行时绘制两个图标，操作层复用现有媒体选择和移除方法，不改变保存服务。

**Tech Stack:** Python 3、PySide6、QPainter、unittest

## Global Constraints

- 三个媒体标签始终显示。
- 每页右下角显示 28 像素编辑和删除图标按钮。
- 无媒体时删除按钮禁用。
- 不新增图片资源或第三方依赖。
- 上传、移除和保存数据结构保持不变。

---

### Task 1: 媒体页悬浮图标操作

**Files:**
- Modify: `main.py:620`
- Modify: `tests/test_game_detail_media.py`

**Interfaces:**
- Consumes: `_choose_media(kind)`、`_remove_media(kind)`、`_current_media(kind)`。
- Produces: `_media_page(kind, content) -> QWidget`、`create_media_action_icon(action, color) -> QIcon`。

- [ ] **Step 1: 写失败测试**

```python
def test_all_media_tabs_have_overlay_icon_actions(self):
    dialog = GameDetailDialog({'title': 'Game'})
    tabs = dialog.findChild(QTabWidget, 'mediaTabs')
    self.assertEqual(['封面', 'Logo', '视频'], [
        tabs.tabText(index) for index in range(tabs.count())
    ])
    for kind in ('Boxfront', 'Logo', 'Video'):
        edit = dialog.findChild(QToolButton, f'edit{kind}Button')
        remove = dialog.findChild(QToolButton, f'remove{kind}Button')
        self.assertFalse(edit.icon().isNull())
        self.assertTrue(remove.isEnabled() is False)
```

再增加有视频时 `removeVideoButton` 启用并可产生 `video_removed=True` 的断言，同时断言旧 `chooseBoxfrontButton` 不存在。

- [ ] **Step 2: 运行测试确认失败**

Run: `QT_QPA_PLATFORM=offscreen .conda-env/bin/python -m unittest tests.test_game_detail_media -v`

Expected: FAIL，当前只有存在媒体的标签，且操作按钮位于媒体框下方。

- [ ] **Step 3: 实现 Qt 绘制图标**

```python
def create_media_action_icon(action, color='#c9d1d9'):
    pixmap = QPixmap(20, 20)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setPen(QPen(QColor(color), 1.8, Qt.SolidLine,
                        Qt.RoundCap, Qt.RoundJoin))
    if action == 'edit':
        painter.drawLine(5, 15, 14, 6)
        painter.drawLine(12, 4, 16, 8)
        painter.drawLine(4, 16, 7, 15)
    else:
        painter.drawLine(6, 7, 7, 16)
        painter.drawLine(14, 7, 13, 16)
        painter.drawLine(5, 5, 15, 5)
    painter.end()
    return QIcon(pixmap)
```

- [ ] **Step 4: 实现常驻标签和悬浮操作层**

`_populate_media_tabs()` 固定遍历 `('封面', 'boxfront')`、`('Logo', 'logo')`、`('视频', 'video')`。每个预览控件传入 `_media_page()`，后者使用容器和底部右对齐布局放置两个 `QToolButton`，设置 28×28、图标、工具提示、对象名和透明悬停样式；删除按钮的 enabled 状态取决于 `_current_media(kind)` 是否有值。

- [ ] **Step 5: 移除旧文字按钮行**

删除 `_build_ui()` 中创建 `选择封面/Logo/视频` 与 `移除封面/Logo/视频` 的循环，仅保留媒体标签控件。

- [ ] **Step 6: 运行针对性与完整测试**

Run: `QT_QPA_PLATFORM=offscreen .conda-env/bin/python -m unittest tests.test_game_detail_media -v`

Expected: PASS。

Run: `QT_QPA_PLATFORM=offscreen .conda-env/bin/python -m unittest discover -s tests -v`

Expected: 全部 PASS。

- [ ] **Step 7: 检查并提交**

```bash
git diff --check
git add main.py tests/test_game_detail_media.py docs/superpowers/plans/2026-07-29-media-overlay-actions.md
git commit -m "ui: 精简媒体编辑操作"
```
