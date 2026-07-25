import tempfile
import unittest
from pathlib import Path

from platform_base import load_showcase_games


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


if __name__ == '__main__':
    unittest.main()
