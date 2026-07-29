import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch

from game_editor import (
    save_game_edits,
    update_gamelist_game,
    update_pegasus_game,
)


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


class GameSaveTests(unittest.TestCase):
    def _make_game_with_media(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name) / 'roms'
        root.mkdir()
        (root / 'Alpha.gba').write_bytes(b'rom')
        media_dir = root / 'media' / 'Alpha'
        media_dir.mkdir(parents=True)
        old_cover = media_dir / 'boxfront.png'
        old_logo = media_dir / 'logo.png'
        old_video = media_dir / 'video.mp4'
        old_cover.write_bytes(b'old-cover')
        old_logo.write_bytes(b'old-logo')
        old_video.write_bytes(b'old-video')
        (root / 'metadata.pegasus.txt').write_text(
            'game: Alpha\nfile: Alpha.gba\n'
            'assets.boxFront: media/Alpha/boxfront.png\n'
            'assets.logo: media/Alpha/logo.png\n'
            'assets.video: media/Alpha/video.mp4\n',
            encoding='utf-8',
        )
        gamelist = (
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<gameList><game><path>./Alpha.gba</path><name>Alpha</name>'
            '<image>./media/Alpha/boxfront.png</image>'
            '<marquee>./media/Alpha/logo.png</marquee>'
            '<video>./media/Alpha/video.mp4</video>'
            '</game></gameList>'
        )
        (root / 'gamelist.xml').write_text(gamelist, encoding='utf-8')
        (root / 'Imgs').mkdir()
        (root / 'Imgs' / 'Alpha.png').write_bytes(b'old-cover')
        original = {
            'filename': 'Alpha.gba',
            'file': 'Alpha.gba',
            'title': 'Alpha',
            'path': str(root / 'Alpha.gba'),
            'boxfront': str(old_cover),
            'logo': str(old_logo),
            'video': str(old_video),
        }
        return root, original, gamelist

    def test_save_replaces_media_updates_enabled_targets_and_imgs(self):
        root, original, original_gamelist = self._make_game_with_media()
        upload = root.parent / 'upload.webp'
        upload.write_bytes(b'new-cover')

        result = save_game_edits(
            root,
            original,
            {**original, 'title': '新标题',
             'boxfront_upload': str(upload)},
            {'pegasus': True, 'gamelist': False, 'imgs': True},
        )

        self.assertEqual(b'new-cover', Path(result['boxfront']).read_bytes())
        self.assertEqual(b'new-cover', (root / 'Imgs/Alpha.webp').read_bytes())
        self.assertFalse((root / 'Imgs/Alpha.png').exists())
        self.assertTrue(upload.exists())
        self.assertIn(
            'assets.boxFront: media/Alpha/boxfront.webp',
            (root / 'metadata.pegasus.txt').read_text(encoding='utf-8'),
        )
        self.assertEqual(
            original_gamelist,
            (root / 'gamelist.xml').read_text(encoding='utf-8'),
        )
        self.assertTrue(root.joinpath('media/Alpha/boxfront.png').exists())

    def test_replaced_media_is_deleted_after_all_references_are_updated(self):
        root, original, _ = self._make_game_with_media()
        upload = root.parent / 'upload.webp'
        upload.write_bytes(b'new-cover')

        save_game_edits(
            root,
            original,
            {**original, 'boxfront_upload': str(upload)},
            {'pegasus': True, 'gamelist': True, 'imgs': False},
        )

        self.assertFalse(root.joinpath('media/Alpha/boxfront.png').exists())

    def test_remove_media_does_not_delete_external_or_shared_files(self):
        root, original, _ = self._make_game_with_media()
        external_logo = root.parent / 'external-logo.png'
        external_logo.write_bytes(b'external')
        original['logo'] = str(external_logo)
        shared_cover = root / 'media' / 'Alpha' / 'boxfront.png'
        with (root / 'metadata.pegasus.txt').open('a', encoding='utf-8') as file:
            file.write(
                '\ngame: Beta\nfile: Beta.gba\n'
                'assets.boxFront: media/Alpha/boxfront.png\n'
            )

        save_game_edits(
            root,
            original,
            {**original, 'boxfront_removed': True, 'logo_removed': True},
            {'pegasus': True, 'gamelist': True, 'imgs': True},
        )

        self.assertTrue(shared_cover.exists())
        self.assertTrue(external_logo.exists())
        self.assertFalse((root / 'Imgs' / 'Alpha.png').exists())
        alpha = ET.parse(root / 'gamelist.xml').find(
            "./game[path='./Alpha.gba']")
        self.assertIsNone(alpha.find('image'))
        self.assertIsNone(alpha.find('marquee'))

    def test_rejects_save_when_all_targets_are_disabled(self):
        root, original, _ = self._make_game_with_media()

        with self.assertRaisesRegex(ValueError, '至少启用一个保存目标'):
            save_game_edits(
                root,
                original,
                original,
                {'pegasus': False, 'gamelist': False, 'imgs': False},
            )

    def test_imgs_failure_restores_indexes_media_and_old_copy(self):
        root, original, _ = self._make_game_with_media()
        original_meta = (root / 'metadata.pegasus.txt').read_bytes()
        upload = root.parent / 'upload.webp'
        upload.write_bytes(b'new-cover')

        def fail_after_removing_old_copy(*args):
            (root / 'Imgs' / 'Alpha.png').unlink()
            raise OSError('模拟 Imgs 写入失败')

        with patch('game_editor._sync_anbernic_cover',
                   side_effect=fail_after_removing_old_copy):
            with self.assertRaisesRegex(OSError, '模拟 Imgs 写入失败'):
                save_game_edits(
                    root,
                    original,
                    {**original, 'boxfront_upload': str(upload)},
                    {'pegasus': True, 'gamelist': False, 'imgs': True},
                )

        self.assertEqual(
            original_meta,
            (root / 'metadata.pegasus.txt').read_bytes(),
        )
        self.assertEqual(
            b'old-cover',
            (root / 'media' / 'Alpha' / 'boxfront.png').read_bytes(),
        )
        self.assertFalse(
            (root / 'media' / 'Alpha' / 'boxfront.webp').exists())
        self.assertEqual(
            b'old-cover',
            (root / 'Imgs' / 'Alpha.png').read_bytes(),
        )


if __name__ == '__main__':
    unittest.main()
