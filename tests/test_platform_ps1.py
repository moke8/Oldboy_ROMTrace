import unittest

from platform_ps1 import _resolve_title_en


class PS1PlatformTests(unittest.TestCase):
    def test_known_serial_uses_database_title(self):
        self.assertEqual(
            'Namco Anthology 1',
            _resolve_title_en('SLPS_012.20', '三国志2 霸王的大陆'),
        )

    def test_unknown_serial_keeps_title_instead_of_game_id(self):
        self.assertEqual(
            '未知游戏',
            _resolve_title_en('SLPS-99999', '未知游戏'),
        )


if __name__ == '__main__':
    unittest.main()
