# DB Title Normalization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove all trailing parenthesized groups and trailing whitespace from future and existing game database titles.

**Architecture:** Put the normalization rule in a small shared builder utility. Apply it at each builder's output boundary, then mechanically apply the identical rule in place to the three tracked database modules without invoking their generators.

**Tech Stack:** Python 3 standard library, `unittest`, PowerShell for the one-time in-place data rewrite.

---

### Task 1: Shared Title Normalizer and NDS Integration

**Files:**
- Create: `build_db_utils.py`
- Modify: `build_nds_db.py`
- Modify: `tests/test_build_nds_db.py`

- [ ] **Step 1: Write failing normalization tests through the NDS writer**

```python
    def test_normalizes_names_written_to_database(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'nds_game_db.py'
            write_database({
                'A001': ('Pac-Pix (Europe) (En,Fr,De,Es,It) '
                         '(Demo) (Kiosk)'),
                'A002': 'Game Title (USA)   ',
                'A003': 'Game (Subtitle) - Edition',
                'A004': 'Plain Game   ',
                'A005': 'Collection (aka Game (Best))',
                'A006': 'Memories (aka Edition))',
            }, output, 'fixture.dat')
            generated = output.read_text(encoding='utf-8')

        self.assertIn("'A001': 'Pac-Pix'", generated)
        self.assertIn("'A002': 'Game Title'", generated)
        self.assertIn("'A003': 'Game (Subtitle) - Edition'", generated)
        self.assertIn("'A004': 'Plain Game'", generated)
        self.assertIn("'A005': 'Collection'", generated)
        self.assertIn("'A006': 'Memories'", generated)
```

- [ ] **Step 2: Run the tests and verify RED**

Run: `python -m unittest tests.test_build_nds_db.NDSDatabaseBuilderTests.test_normalizes_names_written_to_database -v`

Expected: FAIL because generated output still contains trailing groups.

- [ ] **Step 3: Implement the minimal normalizer**

```python
def _matching_open_parenthesis(title):
    depth = 0
    for index in range(len(title) - 1, -1, -1):
        char = title[index]
        if char == ')':
            depth += 1
        elif char == '(':
            depth -= 1
            if depth == 0:
                return index
    return None


def clean_db_title(title):
    cleaned = title.rstrip()
    while cleaned.endswith(')'):
        group_start = _matching_open_parenthesis(cleaned)
        if group_start is None:
            cleaned = cleaned[:-1].rstrip()
            continue
        cleaned = cleaned[:group_start].rstrip()
    return cleaned
```

Import the function in `build_nds_db.py` and replace the escaping line with:

```python
escaped = clean_db_title(name).replace('\\', '\\\\').replace("'", "\\'")
```

- [ ] **Step 4: Run the tests and verify GREEN**

Run: `python -m unittest tests.test_build_nds_db -v`

Expected: all NDS builder tests PASS.

### Task 2: Apply Normalization in the GBA and PS1 Builders

**Files:**
- Modify: `build_gba_db.py`
- Modify: `build_ps1_db.py`
- Modify: `tests/test_build_ps1_db.py`
- Create: `tests/test_build_gba_db.py`

- [ ] **Step 1: Add failing output tests**

Create the GBA integration test without importing its top-level script:

```python
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class GBADatabaseBuilderTests(unittest.TestCase):
    def test_generated_database_normalizes_title(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source = tmp_path / 'Nintendo - Game Boy Advance.xml'
            source.write_text(
                '<game name="Digimon - Battle Spirit (Europe) '
                '(En,Fr,De,Es,It)"><file serial="ABCD"/></game>',
                encoding='utf-8',
            )
            subprocess.run(
                [sys.executable, str(ROOT / 'build_gba_db.py')],
                cwd=tmp_path,
                check=True,
                capture_output=True,
                text=True,
            )
            generated = (tmp_path / 'gba_game_db.py').read_text(
                encoding='utf-8'
            )

        self.assertIn("'ABCD': 'Digimon - Battle Spirit'", generated)
```

Add this PS1 writer test to `PS1DatabaseBuilderTests`:

```python
    def test_normalizes_names_written_to_database(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'ps1_game_db.py'
            write_database(
                {'SLUS-00001': 'Air Combat (USA) (Rev 1)'},
                output,
                'fixture.yaml',
            )
            generated = output.read_text(encoding='utf-8')

        self.assertIn("'SLUS-00001': 'Air Combat'", generated)
```

- [ ] **Step 2: Run the builder tests and verify RED**

Run: `python -m unittest tests.test_build_gba_db tests.test_build_nds_db tests.test_build_ps1_db -v`

Expected: FAIL because generated output still contains trailing groups.

- [ ] **Step 3: Integrate `clean_db_title`**

Import `clean_db_title` in both builders and apply it immediately before escaping and writing each mapping value:

```python
escaped = clean_db_title(name).replace('\\', '\\\\').replace("'", "\\'")
```

- [ ] **Step 4: Run the builder tests and verify GREEN**

Run: `python -m unittest tests.test_build_gba_db tests.test_build_nds_db tests.test_build_ps1_db -v`

Expected: all builder tests PASS.

### Task 3: Update Existing Databases In Place

**Files:**
- Modify: `gba_game_db.py`
- Modify: `nds_game_db.py`
- Modify: `ps1_game_db.py`

- [ ] **Step 1: Record current key sets and entry counts from Git HEAD**

Use `git show HEAD:<file>` and Python AST parsing to establish the original mapping keys and counts without running a builder. The final verification script in Step 3 performs this comparison.

- [ ] **Step 2: Mechanically rewrite only mapping values**

Run a PowerShell in-place transformation that preserves each file's existing text except for mapping values:

```powershell
$utf8 = [System.Text.UTF8Encoding]::new($false)
$linePattern = [regex]::new(
    "(?m)^(\s*'[^'\r\n]+':\s*')((?:\\.|[^'\r\n])*)(',\r?$)"
)
$suffixPattern = [regex]::new('(?:\s*\([^()]*\))+\s*$')
foreach ($path in 'gba_game_db.py', 'nds_game_db.py', 'ps1_game_db.py') {
    $text = [System.IO.File]::ReadAllText($path, $utf8)
    $updated = $linePattern.Replace($text, {
        param($match)
        $name = $suffixPattern.Replace($match.Groups[2].Value, '').TrimEnd()
        return $match.Groups[1].Value + $name + $match.Groups[3].Value
    })
    [System.IO.File]::WriteAllText($path, $updated, $utf8)
}
```

Do not run `build_gba_db.py`, `build_nds_db.py`, or `build_ps1_db.py`.

The current PS1 source has two nested or malformed alias suffixes which the
flat mechanical pass does not match. Update these values directly:

```python
'SLPM-86628': 'Kinniku Banzuke Vol.1 - Ore Ga Saikyou No Otoko Da [Konami the Best]'
'SLPM-87217': 'Tokimeki Memorial 2 - Substories vol. 3 - Memories Ringing On [Konami The Best]'
```

- [ ] **Step 3: Verify data invariants**

Run this read-only Python verification:

```python
import ast
import importlib
import subprocess

from build_db_utils import clean_db_title

files = {
    'gba_game_db.py': ('gba_game_db', 'GBA_GAME_DB', 2796),
    'nds_game_db.py': ('nds_game_db', 'NDS_GAME_DB', 6858),
    'ps1_game_db.py': ('ps1_game_db', 'PS1_GAME_DB', 10763),
}
for path, (module_name, variable, expected_count) in files.items():
    head_text = subprocess.run(
        ['git', '-c', 'safe.directory=C:/Users/65283/Documents/Code/game-scanf',
         'show', f'HEAD:{path}'],
        check=True, capture_output=True, text=True, encoding='utf-8',
    ).stdout
    head_db = ast.literal_eval(
        next(node.value for node in ast.parse(head_text).body
             if isinstance(node, ast.Assign)
             and node.targets[0].id == variable)
    )
    current_db = getattr(importlib.import_module(module_name), variable)
    assert len(current_db) == expected_count
    assert current_db.keys() == head_db.keys()
    assert all(value == value.rstrip() for value in current_db.values())
    assert all(clean_db_title(value) == value for value in current_db.values())
```

Expected counts remain GBA 2796, NDS 6858, and PS1 10763.

### Task 4: Full Verification

**Files:**
- Verify all modified files

- [ ] **Step 1: Run focused tests**

Run: `python -m unittest tests.test_build_gba_db tests.test_build_nds_db tests.test_build_ps1_db -v`

Expected: PASS with no failures or errors.

- [ ] **Step 2: Run the full test suite**

Run: `python -m unittest discover -s tests -v`

Expected: PASS with no failures or errors.

- [ ] **Step 3: Inspect the diff**

Run: `git diff --check` and `git diff --stat`.

Expected: no whitespace errors; changes are limited to the shared utility, builder tests and scripts, design/plan documents, and mapping values in the three existing database files.
