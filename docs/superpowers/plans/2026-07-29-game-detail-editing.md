# 游戏详情编辑与多目标保存实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让用户在游戏详情弹窗中编辑元数据和媒体，并按现有 Pegasus、gamelist、Imgs 配置安全保存。

**Architecture:** 新增 `game_editor.py`，以单个 `save_game_edits()` 接口封装媒体暂存、索引更新、Imgs 同步和旧媒体清理。`GameDetailDialog` 仅收集编辑状态并调用保存回调，`BasePlatformTab` 负责注入当前目录与配置并在成功后刷新展柜。

**Tech Stack:** Python 3、PySide6、`pathlib`、`shutil`、`tempfile`、`xml.etree.ElementTree`、`unittest`

## Global Constraints

- ROM 路径只读。
- 封面、Logo、视频允许上传、替换和移除。
- 上传源文件永远不删除。
- 仅删除游戏目录内、已失去全部索引引用的旧媒体。
- 未启用的 Pegasus、gamelist 或 Imgs 保持原样。
- Imgs 只保存封面，不保存 Logo 或视频。
- 所有保存目标均关闭时拒绝保存。

---

### Task 1: 单游戏索引保存

**Files:**
- Create: `game_editor.py`
- Test: `tests/test_game_editor.py`

**Interfaces:**
- Consumes: `scrape.parse_pegasus_meta()`、`scrape._write_pegasus_document()`、标准库 XML API。
- Produces: `update_pegasus_game(root: Path, game: dict) -> None`、`update_gamelist_game(root: Path, game: dict) -> None`。

- [ ] **Step 1: 写 Pegasus 单游戏更新失败测试**

```python
def test_update_pegasus_replaces_one_game_and_removes_empty_fields(self):
    root = self.make_root_with_two_games()
    update_pegasus_game(root, {
        'filename': 'Alpha.gba', 'title': '新标题',
        'developer': '', 'publisher': '新发行商', 'genres': '动作',
        'boxfront_rel_path': '', 'logo_rel_path': '', 'video_rel_path': '',
    })
    text = (root / 'metadata.pegasus.txt').read_text(encoding='utf-8')
    self.assertIn('game: 新标题', text)
    self.assertNotIn('developer: 旧开发商', text)
    self.assertIn('game: Beta', text)
```

- [ ] **Step 2: 运行测试确认失败**

Run: `.conda-env/bin/python -m unittest tests.test_game_editor.GameIndexTests.test_update_pegasus_replaces_one_game_and_removes_empty_fields -v`

Expected: FAIL，提示无法导入 `game_editor` 或函数不存在。

- [ ] **Step 3: 实现 Pegasus 单游戏更新**

```python
def update_pegasus_game(root, game):
    meta_path = Path(root) / 'metadata.pegasus.txt'
    collection_lines, existing_games = parse_pegasus_meta(meta_path)
    entry = build_edited_pegasus_entry(game)
    for record in existing_games:
        if record.get('file') == game['filename']:
            record['lines'] = entry
            break
    else:
        existing_games.append({'file': game['filename'], 'lines': entry})
    backup_file(meta_path)
    _write_pegasus_document(meta_path, collection_lines, existing_games)
```

`build_edited_pegasus_entry()` 显式映射标题、文件、游戏 ID、开发商、发行商、类型、玩家数、发售日、评分、简介和三类媒体；空值不生成字段。

- [ ] **Step 4: 写 gamelist 单游戏更新失败测试**

```python
def test_update_gamelist_replaces_one_game_and_removes_media_tags(self):
    root = self.make_root_with_two_games()
    update_gamelist_game(root, {
        'filename': 'Alpha.gba', 'title': '新标题',
        'boxfront_rel_path': '', 'logo_rel_path': '', 'video_rel_path': '',
    })
    alpha = ET.parse(root / 'gamelist.xml').find("./game[path='./Alpha.gba']")
    self.assertEqual('新标题', alpha.findtext('name'))
    self.assertIsNone(alpha.find('image'))
    self.assertIsNotNone(ET.parse(root / 'gamelist.xml').find("./game[path='./Beta.gba']"))
```

- [ ] **Step 5: 实现 gamelist 精确更新并运行测试**

实现 `_set_or_remove(element, tag, value)`，有值时创建或更新，无值时删除旧标签；日期和评分沿用现有 `write_gamelist_xml()` 转换规则。写入前调用 `backup_file()`，再以 UTF-8 和 XML 声明写回。

Run: `.conda-env/bin/python -m unittest tests.test_game_editor.GameIndexTests -v`

Expected: PASS。

- [ ] **Step 6: 提交索引保存功能**

```bash
git add game_editor.py tests/test_game_editor.py
git commit -m "feat: 添加单游戏索引保存"
```

### Task 2: 媒体事务与安全清理

**Files:**
- Modify: `game_editor.py`
- Modify: `tests/test_game_editor.py`

**Interfaces:**
- Consumes: Task 1 的两个索引更新函数。
- Produces: `save_game_edits(root: Path, original: dict, edited: dict, targets: dict) -> dict`。

- [ ] **Step 1: 写媒体替换与多目标失败测试**

```python
def test_save_replaces_media_updates_enabled_targets_and_imgs(self):
    root, original = self.make_game_with_media()
    upload = root.parent / 'upload.webp'
    upload.write_bytes(b'new-cover')
    result = save_game_edits(root, original, {
        **original, 'title': '新标题', 'boxfront_upload': str(upload),
    }, {'pegasus': True, 'gamelist': False, 'imgs': True})
    self.assertEqual(b'new-cover', Path(result['boxfront']).read_bytes())
    self.assertEqual(b'new-cover', (root / 'Imgs/Alpha.webp').read_bytes())
    self.assertTrue(upload.exists())
    self.assertEqual(self.original_gamelist, (root / 'gamelist.xml').read_text(encoding='utf-8'))
```

- [ ] **Step 2: 写移除、共享引用和外部文件保护失败测试**

```python
def test_remove_media_does_not_delete_external_or_shared_files(self):
    root, original = self.make_game_with_shared_and_external_media()
    save_game_edits(root, original, {
        **original, 'boxfront_removed': True, 'logo_removed': True,
    }, {'pegasus': True, 'gamelist': True, 'imgs': True})
    self.assertTrue(self.shared_cover.exists())
    self.assertTrue(self.external_logo.exists())
    self.assertFalse((root / 'Imgs/Alpha.png').exists())
```

- [ ] **Step 3: 运行测试确认失败**

Run: `.conda-env/bin/python -m unittest tests.test_game_editor.GameSaveTests -v`

Expected: FAIL，提示 `save_game_edits` 不存在。

- [ ] **Step 4: 实现媒体准备和目标路径**

```python
MEDIA_NAMES = {'boxfront': 'boxfront', 'logo': 'logo', 'video': 'video'}

def _prepare_media(root, filename, kind, upload_path, temp_dir):
    source = Path(upload_path)
    if not source.is_file():
        raise ValueError(f'媒体文件不存在: {source}')
    relative = Path(standard_media_path(filename, kind, source.suffix.lower()))
    staged = Path(temp_dir) / relative.name
    shutil.copy2(source, staged)
    return staged, relative
```

扩展 `standard_media_path()` 统一产生三个媒体路径；上传为空且未移除时沿用旧路径，移除时生成空相对路径。

- [ ] **Step 5: 实现保存编排与回滚边界**

`save_game_edits()` 校验至少一个目标启用，使用 `TemporaryDirectory(dir=root)` 暂存媒体，先为启用索引生成备份和新内容，再原子替换正式媒体。异常时恢复索引备份并清理本次创建的正式媒体；成功后才进入旧媒体清理。

- [ ] **Step 6: 实现引用扫描和安全删除**

```python
def _safe_old_media_candidates(root, original, final_paths):
    references = collect_all_index_media_references(root)
    for key in ('boxfront', 'logo', 'video'):
        old = _resolved_local_path(original.get(key), root)
        if old and _is_within(old, root) and old not in final_paths and old not in references:
            yield old
```

引用扫描同时读取 Pegasus 的三个 `assets.*` 字段及 gamelist 的 `image`、`marquee`、`video`。删除仅使用解析后的绝对路径，并通过 `Path.relative_to(root.resolve())` 校验边界。

- [ ] **Step 7: 实现 Imgs 语义并运行测试**

启用 `imgs` 且有封面时，以 ROM stem 和封面扩展名覆盖副本，并清理该 ROM 的其他图片扩展名副本；启用且移除封面时删除该 ROM 对应副本；未启用时完全不碰 `Imgs`。

Run: `.conda-env/bin/python -m unittest tests.test_game_editor -v`

Expected: PASS。

- [ ] **Step 8: 提交媒体保存功能**

```bash
git add game_editor.py tests/test_game_editor.py
git commit -m "feat: 安全保存游戏媒体"
```

### Task 3: 可编辑详情弹窗

**Files:**
- Modify: `main.py:600`
- Modify: `tests/test_game_detail_media.py`

**Interfaces:**
- Consumes: `GameDetailDialog(game_data, save_targets, save_callback, parent=None)`。
- Produces: `GameDetailDialog.edited_game() -> dict`，保存成功时 `accept()`。

- [ ] **Step 1: 写编辑字段和只读路径失败测试**

```python
def test_detail_exposes_editable_fields_and_readonly_rom_path(self):
    dialog = GameDetailDialog(self.game, self.targets, self.saved.append)
    self.assertFalse(dialog.findChild(QLineEdit, 'titleInput').isReadOnly())
    self.assertFalse(dialog.findChild(QTextEdit, 'descriptionInput').isReadOnly())
    self.assertTrue(dialog.findChild(QLineEdit, 'romPathInput').isReadOnly())
    self.assertIn('Pegasus', dialog.findChild(QLabel, 'saveTargetsLabel').text())
```

- [ ] **Step 2: 写媒体选择、移除和保存回调失败测试**

```python
def test_remove_video_and_save_calls_callback(self):
    dialog = GameDetailDialog(self.game, self.targets, self.saved.append)
    dialog.findChild(QPushButton, 'removeVideoButton').click()
    dialog.findChild(QPushButton, 'saveGameButton').click()
    self.assertTrue(self.saved[0]['video_removed'])
    self.assertEqual(QDialog.Accepted, dialog.result())
```

- [ ] **Step 3: 运行测试确认失败**

Run: `QT_QPA_PLATFORM=offscreen .conda-env/bin/python -m unittest tests.test_game_detail_media -v`

Expected: FAIL，现有构造函数和只读标签不满足断言。

- [ ] **Step 4: 将详情字段改为输入控件**

为每个字段设置稳定 `objectName`；简介使用 `QTextEdit`，ROM 路径使用只读 `QLineEdit`。保留现有媒体标签页与播放逻辑。

- [ ] **Step 5: 增加媒体编辑状态和控件**

为 `boxfront`、`logo`、`video` 保存 `{upload: '', removed: False}` 状态；“选择文件”使用适配类型的 `QFileDialog.getOpenFileName()`，选择后清除 removed 并刷新对应预览；“移除”清空 upload、设置 removed 并显示占位页。

- [ ] **Step 6: 增加保存目标与回调错误处理**

保存按钮构造 `edited_game()`，调用 `save_callback(edited)`；成功后 `accept()`，异常时通过 `QMessageBox.critical()` 显示错误并保持弹窗打开。目标标签只读显示已启用项。

- [ ] **Step 7: 运行详情测试**

Run: `QT_QPA_PLATFORM=offscreen .conda-env/bin/python -m unittest tests.test_game_detail_media -v`

Expected: PASS。

- [ ] **Step 8: 提交详情编辑界面**

```bash
git add main.py tests/test_game_detail_media.py
git commit -m "feat: 支持编辑游戏详情"
```

### Task 4: 平台接线与完整回归

**Files:**
- Modify: `platform_base.py:426`
- Modify: `tests/test_platform_media.py`
- Modify: `README.md:50`

**Interfaces:**
- Consumes: `game_editor.save_game_edits()` 和 Task 3 的新弹窗构造函数。
- Produces: 从游戏卡片打开编辑弹窗、保存后刷新当前展柜的完整用户流程。

- [ ] **Step 1: 写平台配置传递失败测试**

```python
@patch('main.GameDetailDialog')
@patch('platform_base.save_game_edits')
def test_detail_save_uses_current_targets_and_reloads_showcase(self, save, dialog):
    tab = self.make_platform_tab()
    tab.meta_check.setChecked(True)
    tab.gamelist_check.setChecked(False)
    tab._global_settings = {'anbernic_compatible': True}
    tab._show_detail(self.game)
    _, kwargs = dialog.call_args
    self.assertEqual({'pegasus': True, 'gamelist': False, 'imgs': True}, kwargs['save_targets'])
```

- [ ] **Step 2: 运行测试确认失败**

Run: `QT_QPA_PLATFORM=offscreen .conda-env/bin/python -m unittest tests.test_platform_media -v`

Expected: FAIL，当前 `_show_detail()` 未传保存配置和回调。

- [ ] **Step 3: 接入当前配置与保存服务**

`_show_detail()` 从 `self.meta_check`、`self.gamelist_check` 和 `self.window().get_global_settings()` 构造目标；回调调用 `save_game_edits(Path(self.dir_input.text()), game, edited, targets)`，成功后 `_load_showcase()`。

- [ ] **Step 4: 更新 README**

在“游戏详情媒体”附近增加：详情支持编辑元数据、上传/移除封面 Logo 视频，并按现有 Pegasus、gamelist 和 Anbernic 配置保存。

- [ ] **Step 5: 运行针对性测试**

Run: `QT_QPA_PLATFORM=offscreen .conda-env/bin/python -m unittest tests.test_game_editor tests.test_game_detail_media tests.test_platform_media -v`

Expected: PASS。

- [ ] **Step 6: 运行完整测试套件**

Run: `QT_QPA_PLATFORM=offscreen .conda-env/bin/python -m unittest discover -s tests -v`

Expected: 全部 PASS。

- [ ] **Step 7: 检查格式和工作区差异**

Run: `git diff --check && git status --short`

Expected: `git diff --check` 无输出；状态只包含本功能文件以及用户原有未跟踪内容。

- [ ] **Step 8: 提交完整功能**

```bash
git add platform_base.py tests/test_platform_media.py README.md
git commit -m "feat: 按配置保存游戏详情"
```
