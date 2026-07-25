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
