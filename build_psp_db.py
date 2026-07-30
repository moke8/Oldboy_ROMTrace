#!/usr/bin/env python3
"""Generate a PSP DISC_ID to English title mapping from Redump."""

import argparse
import csv
from html.parser import HTMLParser
import io
from pathlib import Path
import re
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from build_db_utils import clean_db_title


SOURCE_URL = 'http://redump.org/discs/system/psp/'
NPS_SOURCE_URL = 'https://nopaystation.com/tsv/PSP_GAMES.tsv'
NOINTRO_SOURCE_URL = (
    'https://raw.githubusercontent.com/libretro/libretro-database/master/'
    'metadat/no-intro/Sony%20-%20PlayStation%20Portable%20(PSN).dat'
)
LIBRETRO_SERIAL_URL = (
    'https://raw.githubusercontent.com/libretro/libretro-database/master/'
    'metadat/serial/Sony%20-%20PlayStation%20Portable.dat'
)
DEFAULT_OUTPUT = Path('game_psp_db.py')
MIN_EXPECTED_ENTRIES = 3300
MIN_EXPECTED_PSN_ENTRIES = 2000
DISC_ID_PATTERN = re.compile(
    r'(?<![A-Z0-9])(U[CL][A-Z]{2})[ -]?(\d{5})(?!\d)',
    re.IGNORECASE,
)
PAGE_PATTERN = re.compile(r'[?&]page=(\d+)')
PSP_ID_PATTERN = re.compile(r'(?:U[CL]|NP)[A-Z]{2}\d{5}')
QUOTED_FIELD_PATTERN = re.compile(r'^(name|comment)\s+"((?:\\.|[^"])*)"')
METADATA_SERIAL_PATTERN = re.compile(
    r'\bserial\s+"([A-Z]{4})[- _]?(\d{5})"', re.IGNORECASE
)
KNOWN_PSN_TITLES = {
    'NPJH50226': 'Ys - Felghana No Chikai',
    'NPJH50473': 'Eiyuu Densetsu - Ao no Kiseki',
}


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


def normalize_psp_id(value):
    compact = re.sub(r'[^A-Z0-9]', '', (value or '').upper())
    return compact if PSP_ID_PATTERN.fullmatch(compact) else ''


def extract_nps_serial_map(content):
    serial_map = {}
    rows = csv.reader(io.StringIO(content), delimiter='\t')
    next(rows, None)
    for row in rows:
        if len(row) < 3:
            continue
        disc_id = normalize_psp_id(row[0])
        title = row[2].strip()
        if disc_id.startswith('NP') and title:
            serial_map.setdefault(disc_id, clean_db_title(title))
    return serial_map


def _unescape_metadata_title(value):
    return value.replace(r'\"', '"').replace(r'\\', '\\')


def _extract_metadata_serial_map(content, title_field):
    serial_map = {}
    current_title = None
    current_serial = None
    in_game = False

    for raw_line in content.splitlines():
        line = raw_line.strip()
        if line == 'game (':
            in_game = True
            current_title = None
            current_serial = None
            continue
        if not in_game:
            continue

        title_match = QUOTED_FIELD_PATTERN.match(line)
        if (title_match and title_match.group(1) == title_field
                and current_title is None):
            current_title = _unescape_metadata_title(title_match.group(2))

        serial_match = METADATA_SERIAL_PATTERN.search(line)
        if serial_match and current_serial is None:
            current_serial = normalize_psp_id(''.join(serial_match.groups()))

        if line == ')':
            if (current_title and current_serial
                    and current_serial.startswith('NP')):
                serial_map.setdefault(
                    current_serial, clean_db_title(current_title)
                )
            in_game = False

    return serial_map


def extract_no_intro_serial_map(content):
    return _extract_metadata_serial_map(content, 'name')


def extract_libretro_serial_map(content):
    return _extract_metadata_serial_map(content, 'comment')


def merge_serial_maps(umd_map, psn_map, *title_maps):
    merged = dict(umd_map)
    merged.update(psn_map)
    for title_map in title_maps:
        for disc_id, title in title_map.items():
            normalized = normalize_psp_id(disc_id)
            if normalized.startswith('NP') and title:
                merged[normalized] = clean_db_title(title)
    return merged


def validate_serial_map(serial_map):
    if len(serial_map) < MIN_EXPECTED_ENTRIES:
        raise ValueError(
            f'Redump PSP database requires at least {MIN_EXPECTED_ENTRIES} '
            f'entries; found {len(serial_map)}'
        )


def validate_combined_map(serial_map):
    umd_count = sum(
        disc_id.startswith(('UC', 'UL')) for disc_id in serial_map
    )
    psn_count = sum(disc_id.startswith('NP') for disc_id in serial_map)
    if umd_count < MIN_EXPECTED_ENTRIES:
        raise ValueError(
            f'PSP database requires at least {MIN_EXPECTED_ENTRIES} UMD '
            f'entries; found {umd_count}'
        )
    if psn_count < MIN_EXPECTED_PSN_ENTRIES:
        raise ValueError(
            f'PSP database requires at least {MIN_EXPECTED_PSN_ENTRIES} PSN '
            f'entries; found {psn_count}'
        )


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
    umd_map = extract_serial_map(pages)
    validate_serial_map(umd_map)

    nps_map = extract_nps_serial_map(download_page(NPS_SOURCE_URL))
    no_intro_map = extract_no_intro_serial_map(
        download_page(NOINTRO_SOURCE_URL)
    )
    libretro_map = extract_libretro_serial_map(
        download_page(LIBRETRO_SERIAL_URL)
    )
    serial_map = merge_serial_maps(
        umd_map,
        nps_map,
        no_intro_map,
        libretro_map,
        KNOWN_PSN_TITLES,
    )
    validate_combined_map(serial_map)
    sources = ', '.join((
        SOURCE_URL,
        NPS_SOURCE_URL,
        NOINTRO_SOURCE_URL,
        LIBRETRO_SERIAL_URL,
    ))
    write_database(serial_map, args.output, sources)
    print(
        f'Extracted {len(umd_map)} UMD and '
        f'{sum(key.startswith("NP") for key in serial_map)} PSN mappings'
    )
    print(f'Wrote {args.output}')


if __name__ == '__main__':
    main()
