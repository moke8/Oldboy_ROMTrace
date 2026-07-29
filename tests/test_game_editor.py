import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from game_editor import update_gamelist_game, update_pegasus_game


class GameIndexTests(unittest.TestCase):
    def _make_root_with_two_games(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        (root / 'metadata.pegasus.txt').write_text(
            'collection: GBA\n'
            'shortname: gba\n\n'
            'game: Alpha\n'
            'file: Alpha.gba\n'
            'developer: 旧开发商\n'
            'assets.boxFront: media/Alpha/boxfront.png\n\n'
            'game: Beta\n'
            'file: Beta.gba\n'
            'developer: 保留开发商\n',
            encoding='utf-8',
        )
        (root / 'gamelist.xml').write_text(
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<gameList>'
            '<game><path>./Alpha.gba</path><name>Alpha</name>'
            '<developer>旧开发商</developer>'
            '<image>./media/Alpha/boxfront.png</image></game>'
            '<game><path>./Beta.gba</path><name>Beta</name>'
            '<developer>保留开发商</developer></game>'
            '</gameList>',
            encoding='utf-8',
        )
        return root

    def test_update_pegasus_replaces_one_game_and_removes_empty_fields(self):
        root = self._make_root_with_two_games()

        update_pegasus_game(root, {
            'filename': 'Alpha.gba',
            'title': '新标题',
            'game_id': '42',
            'developer': '',
            'publisher': '新发行商',
            'genres': '动作',
            'players': '2',
            'release': '2026-07-29',
            'rating': '90%',
            'description': '新简介',
            'boxfront_rel_path': '',
            'logo_rel_path': '',
            'video_rel_path': '',
        })

        text = (root / 'metadata.pegasus.txt').read_text(encoding='utf-8')
        self.assertIn('game: 新标题', text)
        self.assertIn('x-id: 42', text)
        self.assertIn('publisher: 新发行商', text)
        self.assertIn('genre: 动作', text)
        self.assertNotIn('developer: 旧开发商', text)
        self.assertNotIn('assets.boxFront:', text)
        self.assertIn('game: Beta', text)
        self.assertIn('developer: 保留开发商', text)

    def test_update_gamelist_replaces_one_game_and_removes_media_tags(self):
        root = self._make_root_with_two_games()

        update_gamelist_game(root, {
            'filename': 'Alpha.gba',
            'title': '新标题',
            'developer': '',
            'publisher': '新发行商',
            'genres': '动作',
            'boxfront_rel_path': '',
            'logo_rel_path': '',
            'video_rel_path': '',
        })

        tree = ET.parse(root / 'gamelist.xml')
        alpha = tree.find("./game[path='./Alpha.gba']")
        beta = tree.find("./game[path='./Beta.gba']")
        self.assertEqual('新标题', alpha.findtext('name'))
        self.assertIsNone(alpha.find('developer'))
        self.assertEqual('新发行商', alpha.findtext('publisher'))
        self.assertEqual('动作', alpha.findtext('genre'))
        self.assertIsNone(alpha.find('image'))
        self.assertIsNotNone(beta)
        self.assertEqual('保留开发商', beta.findtext('developer'))


if __name__ == '__main__':
    unittest.main()
