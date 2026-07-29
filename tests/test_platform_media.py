import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from platform_base import BasePlatformTab, load_showcase_games


class ShowcaseMediaTests(unittest.TestCase):
    def test_pegasus_preserves_all_media_and_prefers_boxfront(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / 'Game.nds').write_bytes(b'rom')
            media = root / 'media' / 'Game'
            media.mkdir(parents=True)
            (media / 'boxfront.png').write_bytes(b'box')
            (media / 'logo.png').write_bytes(b'logo')
            (media / 'video.mp4').write_bytes(b'video')
            (root / 'metadata.pegasus.txt').write_text(
                'game: Game\n'
                'file: Game.nds\n'
                'assets.boxFront: media/Game/boxfront.png\n'
                'assets.logo: media/Game/logo.png\n'
                'assets.video: media/Game/video.mp4\n',
                encoding='utf-8',
            )

            games, _, _ = load_showcase_games(root, 'nds')

        game = games[0]
        self.assertTrue(game['boxfront'].endswith('boxfront.png'))
        self.assertTrue(game['logo'].endswith('logo.png'))
        self.assertTrue(game['video'].endswith('video.mp4'))
        self.assertEqual(game['boxfront'], game['cover'])

    def test_local_logo_is_default_when_boxfront_is_missing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / 'Game.nds').write_bytes(b'rom')
            media = root / 'media' / 'Game'
            media.mkdir(parents=True)
            (media / 'logo.png').write_bytes(b'logo')

            games, _, _ = load_showcase_games(root, 'nds')

        self.assertEqual(games[0]['logo'], games[0]['cover'])
        self.assertNotIn('boxfront', games[0])

    def test_gamelist_maps_image_marquee_and_video(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / 'Game.nds').write_bytes(b'rom')
            for name in ('boxfront.png', 'logo.png', 'video.mp4'):
                (root / name).write_bytes(b'data')
            (root / 'gamelist.xml').write_text(
                '<gameList><game><path>./Game.nds</path><name>Game</name>'
                '<image>./boxfront.png</image><marquee>./logo.png</marquee>'
                '<video>./video.mp4</video></game></gameList>',
                encoding='utf-8',
            )

            games, _, _ = load_showcase_games(root, 'nds')

        self.assertTrue(games[0]['boxfront'].endswith('boxfront.png'))
        self.assertTrue(games[0]['logo'].endswith('logo.png'))
        self.assertTrue(games[0]['video'].endswith('video.mp4'))


class DetailSaveIntegrationTests(unittest.TestCase):
    def test_detail_save_uses_current_targets_and_reloads_showcase(self):
        game = {'file': 'Game.nds', 'title': 'Game'}
        saved_edit = {'file': 'Game.nds', 'title': '新标题'}
        captured = {}

        class FakeDialog:
            def __init__(self, *args, **kwargs):
                captured.update(kwargs)

            def exec(self):
                captured['save_callback'](saved_edit)

        tab = Mock()
        tab.meta_check.isChecked.return_value = True
        tab.gamelist_check.isChecked.return_value = False
        tab.dir_input.text.return_value = '/roms'
        tab.window.return_value.get_global_settings.return_value = {
            'anbernic_compatible': True,
        }

        with patch('main.GameDetailDialog', FakeDialog), \
                patch('game_editor.save_game_edits') as save:
            BasePlatformTab._show_detail(tab, game)

        self.assertEqual(
            {'pegasus': True, 'gamelist': False, 'imgs': True},
            captured['save_targets'],
        )
        save.assert_called_once_with(
            Path('/roms'), game, saved_edit,
            {'pegasus': True, 'gamelist': False, 'imgs': True},
        )
        tab._load_showcase.assert_called_once_with('/roms')


if __name__ == '__main__':
    unittest.main()
