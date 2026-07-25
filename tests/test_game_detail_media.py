import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtWidgets import QApplication, QLabel, QScrollArea, QTabWidget

from main import GameDetailDialog


class GameDetailMediaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_shows_all_media_tabs_and_defaults_to_boxfront(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for name in ('boxfront.png', 'logo.png', 'video.mp4'):
                (root / name).write_bytes(b'data')
            dialog = GameDetailDialog({
                'title': 'Game',
                'boxfront': str(root / 'boxfront.png'),
                'logo': str(root / 'logo.png'),
                'video': str(root / 'video.mp4'),
            })

            tabs = dialog.findChild(QTabWidget, 'mediaTabs')

            self.assertIsNotNone(tabs)
            self.assertEqual(['封面', 'Logo', '视频'], [
                tabs.tabText(index) for index in range(tabs.count())
            ])
            self.assertEqual('封面', tabs.tabText(tabs.currentIndex()))
            dialog.close()

    def test_logo_is_default_when_boxfront_is_missing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            logo = Path(temp_dir) / 'logo.png'
            logo.write_bytes(b'data')
            dialog = GameDetailDialog({
                'title': 'Game',
                'logo': str(logo),
            })

            tabs = dialog.findChild(QTabWidget, 'mediaTabs')

            self.assertEqual(['Logo'], [
                tabs.tabText(index) for index in range(tabs.count())
            ])
            self.assertEqual('Logo', tabs.tabText(tabs.currentIndex()))
            dialog.close()

    def test_description_has_no_background_color(self):
        dialog = GameDetailDialog({
            'title': 'Game',
            'description': '游戏简介',
        })

        description = dialog.findChild(QLabel, 'descriptionLabel')
        scroll = dialog.findChild(QScrollArea, 'descriptionScroll')

        self.assertIsNotNone(description)
        self.assertIsNotNone(scroll)
        self.assertIn('background: transparent', description.styleSheet())
        self.assertIn('background: transparent', scroll.styleSheet())
        dialog.close()


if __name__ == '__main__':
    unittest.main()
