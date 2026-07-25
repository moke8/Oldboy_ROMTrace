# NDS DAT 英文标题映射实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 通过内置 No-Intro Game Code 映射，为 NDS ROM 提供可靠的规范英文标题，同时保留横幅中的本地化显示标题。

**Architecture:** 构建阶段由独立生成器读取 No-Intro DAT 并生成静态 `NDS_GAME_DB` 字典；运行时解析器只按 ROM Header 的四位 Game Code 查字典，不读取或散列完整 ROM。数据库命中时清理 No-Intro 区域/语言后缀作为 `title_en`，未命中时沿用横幅英语槽回退。

**Tech Stack:** Python 3.8+、标准库 `xml.etree.ElementTree`、`unittest`、PySide6、No-Intro Nintendo DS DAT。

## Global Constraints

- 保留 ROM 横幅标题作为本地化显示标题 `title`。
- 优先通过 NDS Game Code 查表得到规范英文搜索标题 `title_en`。
- 应用运行时不得解析原始 DAT，也不得计算 ROM 哈希。
- 同一有效四位序列号有多个名称时保留 DAT 中首次出现的名称。
- 未知 Game Code 必须保持现有英语横幅槽及 `title` 回退行为。
- 不改变 NDS 图标、发行商及多语言横幅解析逻辑，也不修改其他平台。
- 新增及修改的代码注释使用中文。

---

### Task 1: DAT 轻量字典生成器

**Files:**
- Create: `build_nds_db.py`
- Create: `tests/test_build_nds_db.py`
- Generate: `nds_game_db.py`
- Source input: `Nintendo - Nintendo DS (Decrypted) (20260724-122857).dat`

**Interfaces:**
- Consumes: No-Intro XML DAT，其中游戏为 `<game name="...">`，文件为 `<rom serial="...">`。
- Produces: `extract_serial_map(input_path: str | pathlib.Path) -> dict[str, str]`、`write_database(serial_map: dict[str, str], output_path: str | pathlib.Path, source_name: str) -> None`，以及可导入的 `NDS_GAME_DB: dict[str, str]`。

- [ ] **Step 1: 编写失败的生成器测试**

创建 `tests/test_build_nds_db.py`：

```python
import tempfile
import unittest
from pathlib import Path

from build_nds_db import extract_serial_map, write_database


class NDSDatabaseBuilderTests(unittest.TestCase):
    def test_extracts_valid_serials_and_keeps_first_duplicate(self):
        xml = '''<?xml version="1.0"?>
<datafile>
  <game name="Ys DS (Japan)"><rom serial="AYDJ"/></game>
  <game name="Ys DS (Revision)"><rom serial="AYDJ"/></game>
  <game name="Ys II DS (Japan)"><rom serial="AYEJ"/></game>
  <game name="Invalid"><rom serial="!n/a"/></game>
  <game name="Too Long"><rom serial="ABCDE"/></game>
</datafile>'''
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'nds.dat'
            source.write_text(xml, encoding='utf-8')
            result = extract_serial_map(source)

        self.assertEqual({
            'AYDJ': 'Ys DS (Japan)',
            'AYEJ': 'Ys II DS (Japan)',
        }, result)

    def test_writes_sorted_importable_python_database(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'nds_game_db.py'
            write_database(
                {'AYEJ': 'Ys II DS (Japan)', 'AYDJ': "Ys DS Director's Cut"},
                output,
                'fixture.dat',
            )
            generated = output.read_text(encoding='utf-8')

        self.assertIn("# 来源: fixture.dat", generated)
        self.assertIn("# 条目数: 2", generated)
        self.assertLess(generated.index("'AYDJ'"), generated.index("'AYEJ'"))
        self.assertIn("Director\\'s Cut", generated)


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: 运行测试并确认按预期失败**

Run: `python3 -m unittest tests.test_build_nds_db -v`

Expected: FAIL，错误为 `ModuleNotFoundError: No module named 'build_nds_db'`。

- [ ] **Step 3: 编写最小生成器实现**

创建 `build_nds_db.py`：

```python
#!/usr/bin/env python3
"""从 No-Intro NDS DAT 提取 Game Code → 游戏名映射。"""

import argparse
import xml.etree.ElementTree as ET
from pathlib import Path

DEFAULT_INPUT = Path(
    'Nintendo - Nintendo DS (Decrypted) (20260724-122857).dat'
)
DEFAULT_OUTPUT = Path('nds_game_db.py')


def extract_serial_map(input_path):
    root = ET.parse(input_path).getroot()
    serial_map = {}
    for game in root.iter('game'):
        name = game.get('name', '')
        if not name:
            continue
        for rom in game.iter('rom'):
            serial = rom.get('serial', '')
            if (len(serial) == 4 and serial.isalnum()
                    and serial not in serial_map):
                serial_map[serial] = name
    return serial_map


def write_database(serial_map, output_path, source_name):
    lines = [
        '#!/usr/bin/env python3',
        '"""NDS game_code(serial) → 完整游戏名映射表（自动生成，勿手动编辑）。"""',
        '',
        f'# 来源: {source_name}',
        f'# 条目数: {len(serial_map)}',
        '',
        'NDS_GAME_DB = {',
    ]
    for serial, name in sorted(serial_map.items()):
        escaped = name.replace('\\', '\\\\').replace("'", "\\'")
        lines.append(f"    '{serial}': '{escaped}',")
    lines.extend(['}', ''])
    Path(output_path).write_text('\n'.join(lines), encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description='生成 NDS Game Code 映射表')
    parser.add_argument('input', nargs='?', type=Path, default=DEFAULT_INPUT)
    parser.add_argument('output', nargs='?', type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    serial_map = extract_serial_map(args.input)
    write_database(serial_map, args.output, args.input.name)
    print(f'共提取 {len(serial_map)} 个 serial → name 映射')
    print(f'已写入 {args.output}')


if __name__ == '__main__':
    main()
```

- [ ] **Step 4: 运行生成器单元测试并确认通过**

Run: `python3 -m unittest tests.test_build_nds_db -v`

Expected: 2 tests PASS。

- [ ] **Step 5: 从完整 DAT 生成静态数据库并校验关键条目**

Run: `python3 build_nds_db.py`

Expected: 输出 `共提取 6858 个 serial → name 映射` 并生成 `nds_game_db.py`。

Run: `python3 -c "from nds_game_db import NDS_GAME_DB; assert NDS_GAME_DB['AYDJ'] == 'Ys DS (Japan)'; assert NDS_GAME_DB['AYEJ'] == 'Ys II DS (Japan)'; print(len(NDS_GAME_DB))"`

Expected: 输出 `6858`。

- [ ] **Step 6: 提交生成器、测试和生成数据库**

```bash
git add build_nds_db.py nds_game_db.py tests/test_build_nds_db.py
git commit -m "feat: 添加 NDS No-Intro 标题数据库"
```

---

### Task 2: NDS 解析器接入英文标题映射

**Files:**
- Create: `tests/test_platform_nds.py`
- Modify: `platform_nds.py:1-145`
- Modify: `README.md:31-38,88-105`

**Interfaces:**
- Consumes: Task 1 生成的 `NDS_GAME_DB: dict[str, str]`。
- Produces: `_clean_title(raw_name: str) -> str`；`extract_nds_info()` 返回结构保持不变，但已知 Game Code 的 `title_en` 优先使用清理后的 No-Intro 名称。

- [ ] **Step 1: 编写已知代码、未知代码和标题清理的失败测试**

创建 `tests/test_platform_nds.py`：

```python
import struct
import tempfile
import unittest
from pathlib import Path

from platform_nds import _clean_title, extract_nds_info


def _write_nds(path, game_code, japanese_title, english_title):
    header = bytearray(0x200)
    header[0:12] = b'YS DS'.ljust(12, b'\x00')
    header[0x0C:0x10] = game_code.encode('ascii')
    struct.pack_into('<I', header, 0x68, 0x200)

    banner = bytearray(0x840)
    struct.pack_into('<H', banner, 0, 1)
    bitmap_start = 0x20
    banner[bitmap_start:bitmap_start + 512] = bytes(512)
    palette_start = 0x220
    banner[palette_start:palette_start + 32] = bytes(32)
    for offset, value in ((0x240, japanese_title), (0x340, english_title)):
        encoded = value.encode('utf-16-le')
        banner[offset:offset + len(encoded)] = encoded

    path.write_bytes(header + banner)


class NDSPlatformTests(unittest.TestCase):
    def test_known_game_code_uses_database_for_english_title(self):
        with tempfile.TemporaryDirectory() as tmp:
            rom = Path(tmp) / 'ys.nds'
            _write_nds(rom, 'AYDJ', 'イースDS', 'イースDS')
            result = extract_nds_info(rom, lang_code='ja', log=lambda _: None)

        self.assertEqual('イースDS', result['title'])
        self.assertEqual('Ys DS', result['title_en'])
        self.assertEqual('AYDJ', result['game_code'])

    def test_unknown_game_code_keeps_banner_english_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            rom = Path(tmp) / 'unknown.nds'
            _write_nds(rom, 'ZZZZ', '未知のゲーム', 'Unknown Game')
            result = extract_nds_info(rom, lang_code='ja', log=lambda _: None)

        self.assertEqual('未知のゲーム', result['title'])
        self.assertEqual('Unknown Game', result['title_en'])

    def test_clean_title_removes_no_intro_parenthesized_suffixes(self):
        self.assertEqual('Ys DS', _clean_title('Ys DS (Japan)'))
        self.assertEqual(
            'Game Title',
            _clean_title('Game Title (Europe) (En,Fr,De,Es,It)'),
        )


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: 运行 NDS 平台测试并确认按预期失败**

Run: `python3 -m unittest tests.test_platform_nds -v`

Expected: FAIL，导入 `_clean_title` 失败，且现有解析器尚未使用 `NDS_GAME_DB`。

- [ ] **Step 3: 最小接入静态映射**

在 `platform_nds.py` 的标准库导入中增加 `re`，并导入数据库：

```python
import re
import struct
from pathlib import Path

from nds_game_db import NDS_GAME_DB
```

在 NDS ROM 解析区增加：

```python
def _clean_title(raw_name):
    """移除 No-Intro 名称中的区域、语言及版本括号后缀。"""
    return re.sub(r'\s*\(.*?\)', '', raw_name).strip()
```

将 `extract_nds_info()` 中 `title_en` 的赋值替换为：

```python
        db_name = NDS_GAME_DB.get(game_code)
        title_en = _clean_title(db_name) if db_name else (titles.get('en') or title)
```

- [ ] **Step 4: 运行 NDS 平台测试并确认通过**

Run: `python3 -m unittest tests.test_platform_nds -v`

Expected: 3 tests PASS。

- [ ] **Step 5: 更新项目说明**

将 README 支持平台表中的 NDS 解析方式更新为：

```markdown
| Nintendo DS | `.nds` | ROM Header Game Code → No-Intro 英文名，多语言横幅标题与图标解码 |
```

在项目结构中补充：

```text
nds_game_db.py           # NDS Game Code → 游戏名映射表（自动生成）
build_nds_db.py          # 从 No-Intro DAT 生成 NDS 映射表
```

- [ ] **Step 6: 使用实际 ROM 验证用户报告的案例**

Run: `QT_QPA_PLATFORM=offscreen python3 -c "from platform_nds import extract_nds_info; p='/media/Mokevip/Mokevip SD/Roms/NDS/伊苏1.nds'; i=extract_nds_info(p, 'ja', log=lambda _: None); print(i['title'], i['title_en'], i['game_code'])"`

Expected: 输出 `イースDS Ys DS AYDJ`。

- [ ] **Step 7: 运行完整测试集与静态校验**

Run: `QT_QPA_PLATFORM=offscreen python3 -m unittest discover -s tests -v`

Expected: 所有测试 PASS，无异常或新增警告。

Run: `python3 -m py_compile build_nds_db.py nds_game_db.py platform_nds.py tests/test_build_nds_db.py tests/test_platform_nds.py`

Expected: 命令退出码为 0，无输出。

Run: `git diff --check`

Expected: 命令退出码为 0，无输出。

- [ ] **Step 8: 提交解析器、测试和文档**

```bash
git add platform_nds.py tests/test_platform_nds.py README.md
git commit -m "fix: 使用 NDS 游戏代码补全英文标题"
```
