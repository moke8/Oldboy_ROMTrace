import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import platform_psp
from platform_psp import extract_psp_info


def _build_sfo(values):
    keys = bytearray()
    data = bytearray()
    entries = bytearray()
    key_offsets = {}

    for key in values:
        key_offsets[key] = len(keys)
        keys.extend(key.encode('utf-8') + b'\x00')

    key_table_offset = 0x14 + len(values) * 0x10
    data_table_offset = (key_table_offset + len(keys) + 3) & ~3
    for key, value in values.items():
        encoded = value.encode('utf-8') + b'\x00'
        data_offset = len(data)
        data.extend(encoded)
        entries.extend(struct.pack(
            '<HHIII', key_offsets[key], 0x0204, len(encoded),
            len(encoded), data_offset,
        ))

    header = b'\x00PSF' + struct.pack(
        '<IIII', 0x00000101, key_table_offset,
        data_table_offset, len(values),
    )
    padding = b'\x00' * (data_table_offset - key_table_offset - len(keys))
    return header + entries + keys + padding + data


def _write_pbp(path, title, disc_id):
    sfo = _build_sfo({'TITLE': title, 'DISC_ID': disc_id})
    sfo_offset = 0x28
    end_offset = sfo_offset + len(sfo)
    header = b'\x00PBP' + struct.pack('<I', 0x00010000)
    header += struct.pack('<8I', sfo_offset, *([end_offset] * 7))
    path.write_bytes(header + sfo)


class PSPPlatformTests(unittest.TestCase):
    def test_known_disc_id_uses_database_title(self):
        with tempfile.TemporaryDirectory() as tmp:
            game = Path(tmp) / 'game.pbp'
            _write_pbp(game, 'Chinese Localized Title', 'uljm-05101')
            with patch.dict(
                platform_psp.PSP_GAME_DB,
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
            with patch.dict(platform_psp.PSP_GAME_DB, {}, clear=True):
                result = extract_psp_info(game, log=lambda _: None)

        self.assertEqual('Unknown Localized Title', result['title_en'])
        self.assertEqual('ULJM99999', result['disc_id'])


if __name__ == '__main__':
    unittest.main()
