import unittest
from unittest.mock import patch

from datasource_screenscraper import _parse_game_data
from datasource_thegamesdb import fetch_game_images


class ScreenScraperMediaTests(unittest.TestCase):
    def test_maps_boxfront_logo_and_direct_video_by_type(self):
        jeu = {
            'id': '42',
            'medias': [
                {'type': 'wheel-hd', 'region': 'wor', 'url': 'logo.png'},
                {'type': 'box-2D', 'region': 'wor', 'url': 'box.png'},
                {'type': 'video-normalized', 'region': 'wor', 'url': 'video.mp4'},
            ],
        }

        result = _parse_game_data(jeu, include_boxart=True)

        self.assertEqual('box.png', result['boxfront_url'])
        self.assertEqual('logo.png', result['logo_url'])
        self.assertEqual('video.mp4', result['video_url'])


class TheGamesDBMediaTests(unittest.TestCase):
    def test_maps_front_boxart_and_clearlogo_separately(self):
        response = {
            'data': {
                'base_url': {'original': 'https://cdn.test/'},
                'images': {'42': [
                    {'type': 'boxart', 'side': 'back', 'filename': 'back.jpg'},
                    {'type': 'clearlogo', 'filename': 'logo.png'},
                    {'type': 'boxart', 'side': 'front', 'filename': 'front.jpg'},
                ]},
            },
        }
        with patch('datasource_thegamesdb._tgdb_request', return_value=response):
            result = fetch_game_images('key', 42, log=lambda _message: None)

        self.assertEqual('https://cdn.test/front.jpg', result['boxfront_url'])
        self.assertEqual('https://cdn.test/logo.png', result['logo_url'])


if __name__ == '__main__':
    unittest.main()
