import struct
import tempfile
import unittest
from pathlib import Path

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
    def test_chinese_title_is_not_replaced_with_disc_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            game = Path(tmp) / 'game.pbp'
            _write_pbp(game, '北欧女神 蕾娜斯', 'ULJM05101')

            result = extract_psp_info(game, log=lambda _: None)

        self.assertEqual('北欧女神 蕾娜斯', result['title_en'])
        self.assertEqual('ULJM05101', result['disc_id'])
        self.assertNotEqual(result['disc_id'], result['title_en'])


if __name__ == '__main__':
    unittest.main()
