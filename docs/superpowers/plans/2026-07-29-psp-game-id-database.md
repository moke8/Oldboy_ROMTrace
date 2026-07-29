# PSP Game ID Database Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an offline PSP `DISC_ID` title lookup generated from Redump and rename every generated database module to `game_<platform>_db.py`.

**Architecture:** A standard-library builder downloads and parses Redump's paginated PSP listing, accepts only the first valid PSP serial in each row, normalizes titles, and emits a static Python dictionary. `platform_psp.py` performs a normalized dictionary lookup and falls back to the SFO title; existing GBA, NDS, and PS1 data files are renamed in place without regeneration.

**Tech Stack:** Python 3.8+, `html.parser`, `urllib.request`, `unittest`, existing `build_db_utils.clean_db_title`

---

### Task 1: Rename Existing Database Modules

**Files:**
- Rename: `gba_game_db.py` to `game_gba_db.py`
- Rename: `nds_game_db.py` to `game_nds_db.py`
- Rename: `ps1_game_db.py` to `game_ps1_db.py`
- Modify: `build_gba_db.py:9`
- Modify: `build_nds_db.py:13`
- Modify: `build_ps1_db.py:25`
- Modify: `platform_gba.py:7`
- Modify: `platform_nds.py:8`
- Modify: `platform_ps1.py:8`
- Modify: `tests/test_build_gba_db.py:27`
- Modify: `tests/test_build_nds_db.py:5-45`
- Modify: `tests/test_build_ps1_db.py:5-44`

- [ ] **Step 1: Update tests to require the new output names**

In `tests/test_build_gba_db.py`, change the generated path to:

```python
generated = (tmp_path / 'game_gba_db.py').read_text(encoding='utf-8')
```

In `tests/test_build_nds_db.py`, import `DEFAULT_OUTPUT`, use
`game_nds_db.py` for temporary outputs, and add:

```python
def test_default_output_uses_standard_database_name(self):
    self.assertEqual(Path('game_nds_db.py'), DEFAULT_OUTPUT)
```

In `tests/test_build_ps1_db.py`, import `DEFAULT_OUTPUT`, use
`game_ps1_db.py` for temporary outputs, and add:

```python
def test_default_output_uses_standard_database_name(self):
    self.assertEqual(Path('game_ps1_db.py'), DEFAULT_OUTPUT)
```

- [ ] **Step 2: Run the focused tests and confirm the old names fail**

Run:

```powershell
python -m unittest tests.test_build_gba_db tests.test_build_nds_db tests.test_build_ps1_db -v
```

Expected: the new default-name assertions fail, and the GBA subprocess test
cannot find `game_gba_db.py`.

- [ ] **Step 3: Rename the data files and update producers and consumers**

Rename the three existing database files without running their builders:

```powershell
Move-Item -LiteralPath gba_game_db.py -Destination game_gba_db.py
Move-Item -LiteralPath nds_game_db.py -Destination game_nds_db.py
Move-Item -LiteralPath ps1_game_db.py -Destination game_ps1_db.py
```

Apply these exact code changes:

```python
# build_gba_db.py
OUTPUT = "game_gba_db.py"

# build_nds_db.py
DEFAULT_OUTPUT = Path('game_nds_db.py')

# build_ps1_db.py
DEFAULT_OUTPUT = Path('game_ps1_db.py')

# platform_gba.py
from game_gba_db import GBA_GAME_DB

# platform_nds.py
from game_nds_db import NDS_GAME_DB

# platform_ps1.py
from game_ps1_db import PS1_GAME_DB
```

- [ ] **Step 4: Run the renamed-module tests**

Run:

```powershell
python -m unittest tests.test_build_gba_db tests.test_build_nds_db tests.test_build_ps1_db tests.test_platform_gba tests.test_platform_nds tests.test_platform_ps1 -v
```

Expected: all tests pass and imports resolve from the renamed modules.

- [ ] **Step 5: Commit the rename**

```powershell
git add --all -- gba_game_db.py nds_game_db.py ps1_game_db.py game_gba_db.py game_nds_db.py game_ps1_db.py build_gba_db.py build_nds_db.py build_ps1_db.py platform_gba.py platform_nds.py platform_ps1.py tests/test_build_gba_db.py tests/test_build_nds_db.py tests/test_build_ps1_db.py
git commit -m "refactor: 统一游戏数据库模块命名"
```

### Task 2: Build the Redump PSP Parser

**Files:**
- Create: `build_psp_db.py`
- Create: `tests/test_build_psp_db.py`
- Reuse: `build_db_utils.py`

- [ ] **Step 1: Write failing parser and writer tests**

Create `tests/test_build_psp_db.py` with a compact Redump fixture containing
pagination, a title with a localized `<span>`, multiple serials, an invalid
serial, a duplicate ID, and trailing title metadata:

```python
import tempfile
import unittest
from pathlib import Path

from build_psp_db import (
    discover_page_count,
    extract_serial_map,
    write_database,
)


PAGE_ONE = '''
<form><div class="pages"><a href="?page=2">2</a></div></form>
<table class="games">
<tr>
  <td>Japan</td>
  <td><a href="/disc/1/">Valkyrie Profile: Lenneth (Japan)<br />
      <span>localized title</span></a></td>
  <td>PSP</td><td>1.00</td><td></td><td></td>
  <td title="ULJM 05101, ULJM 06000">ULJM 05101, ...</td><td></td>
</tr>
<tr>
  <td>Unknown</td><td><a href="/disc/2/">Invalid</a></td>
  <td>PSP</td><td>1.00</td><td></td><td></td>
  <td title="ROSE 00001">ROSE 00001</td><td></td>
</tr>
</table>
'''

PAGE_TWO = '''
<table class="games">
<tr>
  <td>Japan</td><td><a href="/disc/3/">Later Duplicate</a></td>
  <td>PSP</td><td>1.01</td><td></td><td></td>
  <td title="ULJM-05101">ULJM-05101</td><td></td>
</tr>
<tr>
  <td>USA</td><td><a href="/disc/4/">Director's Game (USA) (Demo)</a></td>
  <td>PSP</td><td>1.00</td><td></td><td></td>
  <td title="ULUS-10001">ULUS-10001</td><td></td>
</tr>
</table>
'''


class PSPDatabaseBuilderTests(unittest.TestCase):
    def test_discovers_last_page(self):
        self.assertEqual(2, discover_page_count(PAGE_ONE))

    def test_extracts_first_valid_serial_and_keeps_first_duplicate(self):
        self.assertEqual({
            'ULJM05101': 'Valkyrie Profile: Lenneth',
            'ULUS10001': "Director's Game",
        }, extract_serial_map([PAGE_ONE, PAGE_TWO]))

    def test_writes_sorted_importable_database(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'game_psp_db.py'
            write_database(
                {'ULUS10001': "Director's Game", 'ULJM05101': 'Valkyrie'},
                output,
                'fixture',
            )
            generated = output.read_text(encoding='utf-8')
        self.assertLess(generated.index("'ULJM05101'"),
                        generated.index("'ULUS10001'"))
        self.assertIn("Director\\'s Game", generated)

    def test_rejects_a_page_without_game_rows(self):
        with self.assertRaisesRegex(ValueError, 'no game rows'):
            extract_serial_map(['<html><body>unexpected response</body></html>'])


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run the test and verify the builder is missing**

Run:

```powershell
python -m unittest tests.test_build_psp_db -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'build_psp_db'`.

- [ ] **Step 3: Implement the standard-library listing parser**

Create `build_psp_db.py` with these public boundaries:

```python
#!/usr/bin/env python3
"""Generate a PSP DISC_ID to English title mapping from Redump."""

import argparse
from html.parser import HTMLParser
from pathlib import Path
import re
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from build_db_utils import clean_db_title


SOURCE_URL = 'http://redump.org/discs/system/psp/'
DEFAULT_OUTPUT = Path('game_psp_db.py')
DISC_ID_PATTERN = re.compile(
    r'(?<![A-Z0-9])(U[CL][A-Z]{2})[ -]?(\d{5})(?!\d)', re.IGNORECASE
)
PAGE_PATTERN = re.compile(r'[?&]page=(\d+)')


class _RedumpListingParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows = []
        self._in_games = False
        self._row = None
        self._cell = None
        self._in_title_link = False
        self._title_finished = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'table' and 'games' in attrs.get('class', '').split():
            self._in_games = True
            return
        if not self._in_games:
            return
        if tag == 'tr':
            self._row = []
        elif tag == 'td' and self._row is not None:
            self._cell = {
                'text': [], 'primary': [], 'title': attrs.get('title', '')
            }
            self._row.append(self._cell)
        elif tag == 'a' and self._row is not None and len(self._row) == 2:
            self._in_title_link = True
            self._title_finished = False
        elif tag == 'br' and self._in_title_link:
            self._title_finished = True

    def handle_endtag(self, tag):
        if not self._in_games:
            return
        if tag == 'a':
            self._in_title_link = False
        elif tag == 'td':
            self._cell = None
        elif tag == 'tr':
            if self._row is not None and len(self._row) >= 7:
                title = ' '.join(''.join(self._row[1]['primary']).split())
                serial = (self._row[6]['title'] or
                          ' '.join(''.join(self._row[6]['text']).split()))
                if title:
                    self.rows.append((title, serial))
            self._row = None
        elif tag == 'table':
            self._in_games = False

    def handle_data(self, data):
        if self._cell is None:
            return
        self._cell['text'].append(data)
        if self._in_title_link and not self._title_finished:
            self._cell['primary'].append(data)


def discover_page_count(content):
    return max([1] + [int(value) for value in PAGE_PATTERN.findall(content)])


def _extract_rows(content):
    parser = _RedumpListingParser()
    parser.feed(content)
    return parser.rows


def _extract_disc_id(serial_text):
    match = DISC_ID_PATTERN.search(serial_text.upper())
    return ''.join(match.groups()).upper() if match else None


def extract_serial_map(page_contents):
    serial_map = {}
    for page_number, content in enumerate(page_contents, start=1):
        rows = _extract_rows(content)
        if not rows:
            raise ValueError(
                f'Redump PSP page {page_number} contained no game rows'
            )
        for title, serial_text in rows:
            disc_id = _extract_disc_id(serial_text)
            if disc_id:
                serial_map.setdefault(disc_id, clean_db_title(title))
    return serial_map


def download_page(url):
    request = Request(url, headers={'User-Agent': 'game-scanf PSP DB builder'})
    with urlopen(request, timeout=30) as response:
        encoding = response.headers.get_content_charset() or 'utf-8'
        return response.read().decode(encoding)


def download_listing_pages(source_url=SOURCE_URL):
    first_page = download_page(source_url)
    pages = [first_page]
    for page in range(2, discover_page_count(first_page) + 1):
        pages.append(download_page(urljoin(source_url, f'?page={page}')))
    return pages


def write_database(serial_map, output_path, source_name):
    lines = [
        '#!/usr/bin/env python3',
        '"""PSP DISC_ID to English game title mapping (generated)."""',
        '',
        f'# Source: {source_name}',
        f'# Entries: {len(serial_map)}',
        '',
        'PSP_GAME_DB = {',
    ]
    for disc_id, name in sorted(serial_map.items()):
        escaped = clean_db_title(name).replace('\\', '\\\\').replace(
            "'", "\\'"
        )
        lines.append(f"    '{disc_id}': '{escaped}',")
    lines.extend(['}', ''])
    Path(output_path).write_text('\n'.join(lines), encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description='Generate PSP Game ID map')
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    pages = download_listing_pages()
    serial_map = extract_serial_map(pages)
    if not serial_map:
        raise RuntimeError('Redump PSP listing contained no valid DISC_ID rows')
    write_database(serial_map, args.output, SOURCE_URL)
    print(f'Extracted {len(serial_map)} PSP DISC_ID mappings')
    print(f'Wrote {args.output}')


if __name__ == '__main__':
    main()
```

- [ ] **Step 4: Run the builder unit tests**

Run:

```powershell
python -m unittest tests.test_build_psp_db -v
```

Expected: all three tests pass.

- [ ] **Step 5: Commit the tested builder**

```powershell
git add build_psp_db.py tests/test_build_psp_db.py
git commit -m "feat: 添加 PSP 数据库生成器"
```

### Task 3: Generate and Validate the PSP Database

**Files:**
- Create: `game_psp_db.py`
- Modify: `tests/test_build_psp_db.py`

- [ ] **Step 1: Add a failing generated-database integrity test**

Add to `tests/test_build_psp_db.py`:

```python
class PSPGeneratedDatabaseTests(unittest.TestCase):
    def test_generated_database_has_expected_psp_ids(self):
        from game_psp_db import PSP_GAME_DB

        self.assertGreaterEqual(len(PSP_GAME_DB), 3300)
        self.assertIn('ULJM05101', PSP_GAME_DB)
        self.assertTrue(all(
            re.fullmatch(r'U[CL][A-Z]{2}\d{5}', disc_id)
            for disc_id in PSP_GAME_DB
        ))
```

Also add `import re` at the top of the test module.

- [ ] **Step 2: Run the integrity test and verify the database is missing**

Run:

```powershell
python -m unittest tests.test_build_psp_db.PSPGeneratedDatabaseTests -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'game_psp_db'`.

- [ ] **Step 3: Generate the committed PSP database from Redump**

Run:

```powershell
python build_psp_db.py
```

Expected: 35 listing pages are processed, at least 3,300 mappings are written,
and `game_psp_db.py` is created. Do not accept a file below the tested minimum.

- [ ] **Step 4: Run parser and generated-data tests**

Run:

```powershell
python -m unittest tests.test_build_psp_db -v
python -m py_compile build_psp_db.py game_psp_db.py
```

Expected: all tests pass and both files compile without output.

- [ ] **Step 5: Commit the generated mapping**

```powershell
git add game_psp_db.py tests/test_build_psp_db.py
git commit -m "data: 添加 PSP Game ID 对照表"
```

### Task 4: Use PSP IDs at Runtime

**Files:**
- Modify: `platform_psp.py:3-9,254-260`
- Modify: `tests/test_platform_psp.py:1-58`

- [ ] **Step 1: Replace the existing PSP expectation with lookup and fallback tests**

Import `patch` and add these tests to `PSPPlatformTests`:

```python
from unittest.mock import patch


def test_known_disc_id_uses_database_title(self):
    with tempfile.TemporaryDirectory() as tmp:
        game = Path(tmp) / 'game.pbp'
        _write_pbp(game, 'Chinese Localized Title', 'uljm-05101')
        with patch.dict(
            'platform_psp.PSP_GAME_DB',
            {'ULJM05101': 'Valkyrie Profile: Lenneth'},
            clear=True,
        ):
            result = extract_psp_info(game, log=lambda _: None)

    self.assertEqual('Chinese Localized Title', result['title'])
    self.assertEqual('Valkyrie Profile: Lenneth', result['title_en'])
    self.assertEqual('ULJM05101', result['disc_id'])


def test_unknown_disc_id_falls_back_to_sfo_title(self):
    with tempfile.TemporaryDirectory() as tmp:
        game = Path(tmp) / 'game.pbp'
        _write_pbp(game, 'Unknown Localized Title', 'ULJM99999')
        with patch.dict('platform_psp.PSP_GAME_DB', {}, clear=True):
            result = extract_psp_info(game, log=lambda _: None)

    self.assertEqual('Unknown Localized Title', result['title_en'])
    self.assertEqual('ULJM99999', result['disc_id'])
```

- [ ] **Step 2: Run the PSP platform tests and verify lookup failure**

Run:

```powershell
python -m unittest tests.test_platform_psp -v
```

Expected: the known-ID test fails because `title_en` still uses the SFO title.

- [ ] **Step 3: Implement normalized PSP database lookup**

At the top of `platform_psp.py`, add `re` and the database import:

```python
import re

from game_psp_db import PSP_GAME_DB
```

Add focused helpers before `extract_psp_info`:

```python
def _normalize_disc_id(disc_id):
    compact = re.sub(r'[^A-Z0-9]', '', (disc_id or '').upper())
    if re.fullmatch(r'U[CL][A-Z]{2}\d{5}', compact):
        return compact
    return disc_id or ''


def _resolve_title_en(disc_id, fallback_title):
    return PSP_GAME_DB.get(_normalize_disc_id(disc_id)) or fallback_title
```

Change the result construction in `extract_psp_info` to:

```python
normalized_disc_id = _normalize_disc_id(disc_id)
info = {
    'title': title,
    'title_en': _resolve_title_en(normalized_disc_id, title),
    'disc_id': normalized_disc_id,
    'publisher': '',
    'filename': Path(psp_path).name,
}
```

- [ ] **Step 4: Run the PSP platform and broader platform tests**

Run:

```powershell
python -m unittest tests.test_platform_psp -v
python -m unittest discover -s tests -p "test_platform_*.py" -v
```

Expected: all platform tests pass.

- [ ] **Step 5: Commit the runtime integration**

```powershell
git add platform_psp.py tests/test_platform_psp.py
git commit -m "feat: 使用 PSP Game ID 解析英文标题"
```

### Task 5: Documentation and Full Verification

**Files:**
- Modify: `README.md:106-124`

- [ ] **Step 1: Update active database documentation**

Replace the old database filenames in the README and add the PSP artifacts:

```text
game_gba_db.py          # GBA Game Code -> game title mapping
build_gba_db.py         # Build GBA mapping from No-Intro DAT
game_nds_db.py          # NDS Game Code -> game title mapping
build_nds_db.py         # Build NDS mapping from No-Intro DAT
game_ps1_db.py          # PS1 serial -> English title mapping
build_ps1_db.py         # Build PS1 mapping from DuckStation data
game_psp_db.py          # PSP DISC_ID -> English title mapping
build_psp_db.py         # Build PSP mapping from Redump listings
```

Keep historical files under `docs/superpowers/specs/` and
`docs/superpowers/plans/` unchanged.

- [ ] **Step 2: Verify no active code references old module names**

Run:

```powershell
rg -n "(gba|nds|ps1)_game_db" --glob "!docs/superpowers/**" --glob "!.claude/**"
```

Expected: no matches.

- [ ] **Step 3: Run the complete test suite**

Run:

```powershell
python -m unittest discover -s tests -v
```

Expected: all tests pass.

- [ ] **Step 4: Compile every affected Python module**

Run:

```powershell
python -m py_compile build_db_utils.py build_gba_db.py build_nds_db.py build_ps1_db.py build_psp_db.py game_gba_db.py game_nds_db.py game_ps1_db.py game_psp_db.py platform_gba.py platform_nds.py platform_ps1.py platform_psp.py
```

Expected: command exits successfully with no output.

- [ ] **Step 5: Review the final diff and worktree scope**

Run:

```powershell
git diff --check
git status --short
git diff --stat HEAD~4
```

Expected: no whitespace errors; only the requested code, generated database,
tests, README, and planning documents are tracked. `.claude/` and `CLAUDE.md`
remain untracked and untouched.

- [ ] **Step 6: Commit documentation**

```powershell
git add README.md
git commit -m "docs: 更新游戏数据库文件说明"
```

- [ ] **Step 7: Confirm the final repository state**

Run:

```powershell
git status --short --branch
```

Expected: the branch contains the requested commits; only the user-owned
`.claude/` and `CLAUDE.md` remain untracked.
