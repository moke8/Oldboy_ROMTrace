# PSP Game ID Database Design

## Goal

Add a bundled PSP `DISC_ID` to English title mapping and standardize all
generated database module names as `game_<platform>_db.py`.

The final database modules are:

- `game_gba_db.py`
- `game_nds_db.py`
- `game_ps1_db.py`
- `game_psp_db.py`

The builder scripts keep their existing `build_<platform>_db.py` names.

## Data Source Decision

Use the Redump PSP disc listing at
`http://redump.org/discs/system/psp/` as the PSP mapping source.

No-Intro DAT-o-MATIC is not suitable for this mapping. Its catalog does not
provide an official PSP UMD game set; the available PSP sets cover PSN,
Minis, unofficial, or non-Redump data. Its export process also uses
asynchronous download tickets, which is unsuitable for a predictable builder.

The downloadable Redump PSP DAT contains titles and hashes but no serial
fields. The Redump HTML listing contains both titles and serials across 35
paginated pages. A current source inspection found 3,500 rows and about 3,395
unique high-confidence PSP IDs when selecting the first valid PSP serial from
each row.

## PSP Builder

Add `build_psp_db.py` using only the Python standard library. It will:

1. Download the first Redump PSP listing page.
2. Discover the last page number from the pagination links.
3. Download every listing page in page order.
4. Parse each game title and its full serial cell.
5. Select the first serial matching `U[CL][A-Z]{2}[ -]?\d{5}`.
6. Normalize the key to uppercase alphanumeric `DISC_ID` form, such as
   `ULJM05101`.
7. Normalize the title with `clean_db_title()` so trailing parenthesized
   metadata and trailing whitespace are removed.
8. Preserve the first title encountered for duplicate IDs and write the
   sorted `PSP_GAME_DB` dictionary to `game_psp_db.py`.

Only the first matching serial is used because Redump serial cells can also
contain package, reissue, or promotional catalog numbers. Importing every
listed serial creates known cross-title conflicts. Fetching every disc detail
page would expose Redump's `Internal Serial`, but would require roughly 3,500
additional requests and is not appropriate for this builder.

The parser will reject malformed IDs and escape generated Python string
literals. HTTP and parsing failures stop generation with a clear error instead
of producing a partial database.

## Runtime Lookup

Update `platform_psp.py` to import `PSP_GAME_DB` from `game_psp_db.py`.

Normalize a `PARAM.SFO` `DISC_ID` by removing punctuation and whitespace and
uppercasing it. If the normalized ID exists in the database, use the mapped
value for `title_en`. Otherwise, retain the existing behavior and use the SFO
`TITLE`. Keep the original display `title` unchanged and return the normalized
ID in `disc_id`.

This keeps ROM inspection offline at runtime. Network access is needed only
when explicitly regenerating the database.

## Database Module Rename

Rename the existing GBA, NDS, and PS1 database files without regenerating
their contents. Update platform imports and builder default output paths to
the new names. Update active tests and README references. Historical design
and implementation documents retain their original filenames because they
describe the repository state at the time they were written.

## Testing

Add focused tests for:

- Redump pagination discovery and row parsing.
- PSP ID validation and normalization.
- First-valid-serial selection when a cell contains multiple serials.
- Duplicate ID handling and title normalization in generated output.
- PSP database lookup from ISO/PBP metadata.
- Unknown-ID fallback to `PARAM.SFO.TITLE`.
- The renamed GBA, NDS, and PS1 modules and builder output defaults.

Run the complete unit test suite after generating `game_psp_db.py`. Also
compile the builders, database modules, and affected platform modules to catch
syntax and import errors.
