# PSP PSN Database and PS1 Fallback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add PSP PSN `NPxx` title mappings to the bundled database and route unresolved PSP PBP/ISO files through the existing PS1 parser.

**Architecture:** Extend the existing PSP builder with isolated parsers for NoPayStation TSV and Libretro-hosted No-Intro/serial metadata, then merge those mappings with the Redump UMD map before one atomic database write. Runtime PSP lookup remains offline; known PS1 PBP serials and failed PSP ISO parses delegate to `platform_ps1`.

**Tech Stack:** Python 3 standard library (`csv`, `io`, `re`, `urllib`), `unittest`, existing Redump/NoPayStation/Libretro data sources.

---

### Task 1: Parse and Merge PSP PSN Sources

**Files:**
- Modify: `tests/test_build_psp_db.py`
- Modify: `build_psp_db.py`

- [x] **Step 1: Write failing source parser and merge tests**

Add fixtures containing a NoPayStation header and rows, No-Intro `game` blocks,
and Libretro `comment`/`serial` pairs. Assert these behaviors:

```python
def test_extracts_nopaystation_psn_ids_and_native_titles(self):
    content = (
        'Title ID\tRegion\tName\tPKG direct link\n'
        'NPJH50226\tJP\tイース -フェルガナの誓い- スーパープライス\thttps://example\n'
    )
    self.assertEqual(
        {'NPJH50226': 'イース -フェルガナの誓い- スーパープライス'},
        extract_nps_serial_map(content),
    )

def test_title_metadata_overrides_nps_but_preserves_umd(self):
    merged = merge_serial_maps(
        {'ULJM05101': 'Valkyrie Profile: Lenneth'},
        {'NPJH50226': 'イース'},
        {'NPJH50226': 'Ys - Felghana No Chikai'},
    )
    self.assertEqual('Valkyrie Profile: Lenneth', merged['ULJM05101'])
    self.assertEqual('Ys - Felghana No Chikai', merged['NPJH50226'])
```

- [x] **Step 2: Run the focused tests and verify failure**

Run: `python -m unittest tests.test_build_psp_db.PSPDatabaseBuilderTests -v`

Expected: FAIL because `extract_nps_serial_map` and `merge_serial_maps` are not defined.

- [x] **Step 3: Implement source parsing, normalization, and merge**

Add these public boundaries to `build_psp_db.py`:

```python
NPS_SOURCE_URL = 'https://nopaystation.com/tsv/PSP_GAMES.tsv'
NOINTRO_SOURCE_URL = (
    'https://raw.githubusercontent.com/libretro/libretro-database/master/'
    'metadat/no-intro/Sony%20-%20PlayStation%20Portable%20(PSN).dat'
)
LIBRETRO_SERIAL_URL = (
    'https://raw.githubusercontent.com/libretro/libretro-database/master/'
    'metadat/serial/Sony%20-%20PlayStation%20Portable.dat'
)

def normalize_psp_id(value):
    compact = re.sub(r'[^A-Z0-9]', '', (value or '').upper())
    return compact if re.fullmatch(r'(?:U[CL]|NP)[A-Z]{2}\d{5}', compact) else ''

def extract_nps_serial_map(content):
    rows = csv.reader(io.StringIO(content), delimiter='\t')
    next(rows, None)
    result = {}
    for row in rows:
        if len(row) >= 3:
            disc_id = normalize_psp_id(row[0])
            if disc_id and disc_id.startswith('NP') and row[2].strip():
                result.setdefault(disc_id, clean_db_title(row[2].strip()))
    return result

def merge_serial_maps(umd_map, psn_map, *title_maps):
    merged = dict(umd_map)
    merged.update(psn_map)
    for title_map in title_maps:
        for disc_id, title in title_map.items():
            normalized = normalize_psp_id(disc_id)
            if normalized.startswith('NP') and title:
                merged[normalized] = clean_db_title(title)
    return merged
```

Implement block parsers for No-Intro `name`/`serial` entries and Libretro
`comment`/`rom ( serial ...)` entries using line-oriented state, plus fixed
romanized titles for the two confirmed Libretro mappings:

```python
KNOWN_PSN_TITLES = {
    'NPJH50226': 'Ys - Felghana No Chikai',
    'NPJH50473': 'Eiyuu Densetsu - Ao no Kiseki',
}
```

- [x] **Step 4: Run the builder tests and verify pass**

Run: `python -m unittest tests.test_build_psp_db.PSPDatabaseBuilderTests -v`

Expected: all builder unit tests PASS.

- [x] **Step 5: Commit parser and merge support**

```bash
git add tests/test_build_psp_db.py build_psp_db.py
git commit -m "feat: 合并 PSP PSN 编号数据源"
```

### Task 2: Generate and Validate the Combined Database

**Files:**
- Modify: `tests/test_build_psp_db.py`
- Modify: `build_psp_db.py`
- Modify: `game_psp_db.py`

- [x] **Step 1: Expand generated database integrity tests**

Replace the UMD-only ID assertion with accepted UMD and PSN families, require
at least 5,300 total entries, and assert:

```python
self.assertEqual('Ys - Felghana No Chikai', PSP_GAME_DB['NPJH50226'])
self.assertEqual(
    'Eiyuu Densetsu - Ao no Kiseki',
    PSP_GAME_DB['NPJH50473'],
)
self.assertTrue(all(
    re.fullmatch(r'(?:U[CL]|NP)[A-Z]{2}\d{5}', disc_id)
    for disc_id in PSP_GAME_DB
))
```

- [x] **Step 2: Run integrity test and verify failure**

Run: `python -m unittest tests.test_build_psp_db.PSPGeneratedDatabaseTests -v`

Expected: FAIL because the committed database lacks `NPxx` entries.

- [x] **Step 3: Add downloads and population validation**

Make `main()` download Redump pages plus the three PSN metadata files, parse
them independently, merge them, validate at least 3,300 UMD and 2,000 PSN IDs,
then write once. Extend the `# Source:` line to list all source URLs.

- [x] **Step 4: Generate `game_psp_db.py` through the local proxy**

Run in PowerShell:

```powershell
$env:http_proxy='http://127.0.0.1:17891'
$env:https_proxy='http://127.0.0.1:17891'
python build_psp_db.py
```

Expected: output reports at least 5,300 combined mappings and writes
`game_psp_db.py` only after validation passes.

- [x] **Step 5: Run builder and database tests**

Run: `python -m unittest tests.test_build_psp_db -v`

Expected: all tests PASS, including both known `NPJH` mappings.

- [x] **Step 6: Commit generated database**

```bash
git add build_psp_db.py tests/test_build_psp_db.py game_psp_db.py
git commit -m "data: 补充 PSP PSN Game ID 对照表"
```

### Task 3: Normalize Digital IDs and Fall Back to PS1

**Files:**
- Modify: `tests/test_platform_psp.py`
- Modify: `platform_psp.py`

- [x] **Step 1: Write failing runtime tests**

Add tests that assert a hyphenated lowercase `NPJH` ID resolves through
`PSP_GAME_DB`, a known PS1 PBP delegates to `platform_ps1`, an unknown PSP PBP
keeps its PSP title/icon behavior, a failed PSP ISO delegates to PS1, and CSO
never delegates.

```python
def test_known_psn_id_uses_psp_database(self):
    with tempfile.TemporaryDirectory() as tmp:
        game = Path(tmp) / 'game.pbp'
        _write_pbp(game, 'Japanese Title', 'npjh-50226')
        with patch.dict(platform_psp.PSP_GAME_DB,
                        {'NPJH50226': 'Ys - Felghana No Chikai'}, clear=True):
            result = extract_psp_info(game, log=lambda _: None)
    self.assertEqual('Ys - Felghana No Chikai', result['title_en'])
    self.assertEqual('NPJH50226', result['disc_id'])
```

- [x] **Step 2: Run PSP platform tests and verify failure**

Run: `python -m unittest tests.test_platform_psp -v`

Expected: digital normalization and PS1 delegation tests FAIL.

- [x] **Step 3: Implement guarded PS1 delegation**

Update `_normalize_disc_id()` to accept `(?:U[CL]|NP)[A-Z]{2}\d{5}`. Import
`extract_ps1_info` and the existing `PS1_GAME_DB`, then add:

```python
def _extract_known_ps1_info(path, lang_code, log):
    info = extract_ps1_info(path, lang_code, log)
    if info and info.get('disc_id') in PS1_GAME_DB:
        return info
    return None
```

For `.pbp`, return the known PS1 result only after PSP lookup misses. For a
PSP `.iso` whose SFO cannot be read, return `extract_ps1_info(...)`. Preserve
the current PSP result for unknown PBP files and never delegate `.cso`.

- [x] **Step 4: Run PSP and PS1 tests**

Run: `python -m unittest tests.test_platform_psp tests.test_platform_ps1 -v`

Expected: all PSP and PS1 tests PASS.

- [x] **Step 5: Commit runtime fallback**

```bash
git add platform_psp.py tests/test_platform_psp.py
git commit -m "fix: PSP 未命中时回退 PS1 解析"
```

### Task 4: Documentation and Final Verification

**Files:**
- Modify: `README.md`

- [x] **Step 1: Document combined PSP sources and fallback**

Update the PSP platform row and project file descriptions to state that PSP
uses Redump UMD plus NoPayStation/No-Intro PSN IDs and that PS1-compatible PBP
files fall back to the PS1 database.

- [x] **Step 2: Run targeted and full tests**

Run:

```powershell
python -m unittest tests.test_build_psp_db tests.test_platform_psp tests.test_platform_ps1 -v
python -m unittest discover -s tests -v
python -m compileall -q build_psp_db.py game_psp_db.py platform_psp.py
git diff --check
```

Expected: all tests PASS, compilation exits 0, and `git diff --check` reports
no whitespace errors.

- [x] **Step 3: Commit documentation and plan**

```bash
git add README.md docs/superpowers/plans/2026-07-30-psp-psn-and-ps1-fallback.md
git commit -m "docs: 更新 PSP PSN 数据库说明"
```

- [x] **Step 4: Inspect final repository state**

Run: `git status --short --branch` and `git log -6 --oneline`

Expected: `master` contains the design, parser, database, runtime, and docs
commits; only the user's pre-existing `.claude/` and `CLAUDE.md` remain
untracked.
