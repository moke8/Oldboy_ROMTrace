# PSP PSN Database and PS1 Fallback Design

## Goal

Extend the bundled PSP title database beyond physical UMD serials so PSP PSN
images with `NPxx` IDs resolve to stable search titles. When a file handled by
the PSP scanner is actually a PS1 image, reuse the existing PS1 parser instead
of falling back immediately to the embedded or filename title.

## Scope

- Preserve all existing Redump-derived PSP UMD mappings.
- Add PSP PSN games, Minis, PSP Go, NeoGeo, PC Engine, and demo IDs.
- Keep runtime lookup offline through the committed `game_psp_db.py` module.
- Fall back to PS1 parsing for shared `.pbp` and `.iso` formats under the
  conditions defined below.
- Exclude DLC, updates, homebrew-only IDs, UMD Video, and UMD Music.
- Do not change any non-PSP database or platform behavior.

## Data Sources and Precedence

The builder combines sources in this order:

1. Redump PSP listings provide the existing physical UMD ID and title map.
2. NoPayStation `PSP_GAMES.tsv` supplies broad PSN `NPxx` ID coverage.
3. No-Intro PSP PSN metadata and the matching Libretro PSP serial/title
   metadata supply normalized English or romanized titles where available.

Later title-enrichment sources may replace a NoPayStation native-region title
for the same normalized ID, but they must not remove IDs. If no normalized
English or romanized title exists, retain the NoPayStation title. Existing UMD
entries remain available and deterministic.

All stored titles pass through the existing trailing-parenthesis normalizer.
All PSP IDs are stored uppercase without separators, including both physical
`UCxx`/`ULxx` families and digital `NPxx` families.

## Builder Behavior

`build_psp_db.py` gains independently testable parsers for the PSN sources and
a deterministic merge function. Its normal generation path downloads all
required sources, validates that both the existing UMD population and a
substantial PSN population are present, then writes one sorted
`PSP_GAME_DB` dictionary.

Generation fails before replacing the output when a required source is
unavailable, malformed, or below its expected minimum count. Duplicate IDs
within one source keep the first stable mapping; higher-priority title sources
may explicitly replace the title during the merge.

The committed database must include at least these regressions:

- `NPJH50226` -> `Ys - Felghana No Chikai`
- `NPJH50473` -> `Eiyuu Densetsu - Ao no Kiseki`

## Runtime Lookup and PS1 Fallback

`platform_psp.py` normalizes all supported PSP serial families, including
`NPxx`, before lookup.

For a valid PSP image, a `PSP_GAME_DB` hit remains authoritative. On a PSP
database miss:

- For `.pbp`, call the PS1 parser. Use its result only when it resolves a PS1
  serial through the existing `PS1_GAME_DB`; otherwise keep the PSP SFO title
  and icon metadata.
- For `.iso`, call the PS1 parser only when PSP ISO parsing cannot find valid
  PSP metadata.
- Never send `.cso` to the PS1 parser.

This prevents an unknown PSP homebrew PBP from being mislabeled as PS1 while
allowing PS1 Classics and misplaced PS1 ISO files to resolve through the
existing PS1 database.

## Testing

Tests cover:

- Parsing and normalizing `NPxx` IDs from each PSN source.
- Merge precedence and preservation of existing Redump UMD mappings.
- Generated database integrity, minimum counts, and the two known `NPJH`
  regressions.
- PSP lookup for normalized digital IDs.
- `.pbp` PS1 fallback on a confirmed PS1 database hit.
- Retaining PSP metadata for an unknown PSP PBP.
- `.iso` fallback after PSP parsing failure and no `.cso` fallback.
- The existing PSP, PS1, and builder test suites.
