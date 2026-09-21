import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import platform_wii
from platform_wii import extract_wii_info


def _write_wbfs(path, game_id, title, title_bytes=None):
    data = bytearray(0x260)
    data[0:4] = b'WBFS'
    data[0x200:0x200 + len(game_id)] = game_id.encode('ascii')
    data[0x218:0x21C] = b'\x5d\x1c\x9e\xa3'
    encoded = title_bytes if title_bytes is not None else title.encode('utf-8')
    data[0x220:0x220 + len(encoded)] = encoded
    path.write_bytes(data)


class WiiPlatformTests(unittest.TestCase):
    def test_known_game_id_uses_database_title(self):
        with tempfile.TemporaryDirectory() as tmp:
            rom = Path(tmp) / 'nsmb.wbfs'
            _write_wbfs(rom, 'SMNP01', 'Newer SMBW')
            with patch.dict(
                platform_wii.WII_GAME_DB,
                {'SMNP01': 'New Super Mario Bros. Wii'},
                clear=True,
            ):
                result = extract_wii_info(rom, log=lambda _: None)

        self.assertEqual('Newer SMBW', result['title'])
        self.assertEqual('New Super Mario Bros. Wii', result['title_en'])
        self.assertEqual('SMNP01', result['game_id'])

    def test_unknown_game_id_keeps_disc_title(self):
        with tempfile.TemporaryDirectory() as tmp:
            rom = Path(tmp) / 'newer.wbfs'
            _write_wbfs(rom, 'SMNW03', 'Newer SMBW')
            with patch.dict(platform_wii.WII_GAME_DB, {}, clear=True):
                result = extract_wii_info(rom, log=lambda _: None)

        self.assertEqual('Newer SMBW', result['title'])
        self.assertEqual('Newer SMBW', result['title_en'])
        self.assertEqual('SMNW03', result['game_id'])

    def test_truncated_utf8_disc_title_falls_back_to_filename(self):
        with tempfile.TemporaryDirectory() as tmp:
            rom = Path(tmp) / '超级马里奥银河 [RMGJ01].wbfs'
            _write_wbfs(
                rom, 'RMGJ01', '',
                title_bytes=bytes.fromhex('e8b685e7baa7e9'),
            )
            with patch.dict(
                platform_wii.WII_GAME_DB,
                {'RMGJ01': 'Super Mario Galaxy'},
                clear=True,
            ):
                result = extract_wii_info(rom, log=lambda _: None)

        self.assertEqual('超级马里奥银河', result['title'])
        self.assertEqual('Super Mario Galaxy', result['title_en'])
        self.assertEqual('RMGJ01', result['game_id'])


if __name__ == '__main__':
    unittest.main()
