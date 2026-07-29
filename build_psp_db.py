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
