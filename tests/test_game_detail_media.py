import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QLabel,
    QLineEdit,
    QPushButton,
    QTabWidget,
    QTextEdit,
    QToolButton,
)

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

            self.assertEqual(['封面', 'Logo', '视频'], [
                tabs.tabText(index) for index in range(tabs.count())
            ])
            self.assertEqual('Logo', tabs.tabText(tabs.currentIndex()))
            dialog.close()

    def test_description_editor_has_no_background_color(self):
        dialog = GameDetailDialog({
            'title': 'Game',
            'description': '游戏简介',
        })

        description = dialog.findChild(QTextEdit, 'descriptionInput')

        self.assertIsNotNone(description)
        self.assertIn('background: transparent', description.styleSheet())
        dialog.close()

    def test_detail_exposes_editable_fields_and_readonly_rom_path(self):
        saved = []
        dialog = GameDetailDialog(
            {
                'title': 'Game',
                'path': '/roms/Game.nds',
                'description': '游戏简介',
            },
            save_targets={
                'pegasus': True,
                'gamelist': False,
                'imgs': True,
            },
            save_callback=saved.append,
        )

        self.assertFalse(
            dialog.findChild(QLineEdit, 'titleInput').isReadOnly())
        self.assertFalse(
            dialog.findChild(QTextEdit, 'descriptionInput').isReadOnly())
        self.assertTrue(
            dialog.findChild(QLineEdit, 'romPathInput').isReadOnly())
        targets = dialog.findChild(QLabel, 'saveTargetsLabel').text()
        self.assertIn('Pegasus', targets)
        self.assertIn('Imgs', targets)
        self.assertNotIn('gamelist.xml', targets)
        dialog.close()

    def test_remove_video_and_save_calls_callback(self):
        saved = []
        dialog = GameDetailDialog(
            {'title': 'Game', 'video': '/media/Game/video.mp4'},
            save_targets={'pegasus': True, 'gamelist': False, 'imgs': False},
            save_callback=saved.append,
        )

        remove_video = dialog.findChild(QToolButton, 'removeVideoButton')
        self.assertTrue(remove_video.isEnabled())
        remove_video.click()
        dialog.findChild(QPushButton, 'saveGameButton').click()

        self.assertTrue(saved[0]['video_removed'])
        self.assertEqual(QDialog.Accepted, dialog.result())

    def test_all_media_tabs_have_overlay_icon_actions(self):
        dialog = GameDetailDialog({'title': 'Game'})
        tabs = dialog.findChild(QTabWidget, 'mediaTabs')

        self.assertEqual(['封面', 'Logo', '视频'], [
            tabs.tabText(index) for index in range(tabs.count())
        ])
        for kind in ('Boxfront', 'Logo', 'Video'):
            edit = dialog.findChild(QToolButton, f'edit{kind}Button')
            remove = dialog.findChild(QToolButton, f'remove{kind}Button')
            self.assertIsNotNone(edit)
            self.assertIsNotNone(remove)
            self.assertFalse(edit.icon().isNull())
            self.assertFalse(remove.icon().isNull())
            self.assertFalse(remove.isEnabled())
        self.assertIsNone(
            dialog.findChild(QPushButton, 'chooseBoxfrontButton'))
        dialog.close()

    def test_media_actions_use_standard_svg_resources(self):
        upload = Path('assets/icons/upload.svg')
        trash = Path('assets/icons/trash.svg')

        self.assertTrue(upload.exists())
        self.assertTrue(trash.exists())
        self.assertIn('<svg', upload.read_text(encoding='utf-8'))
        self.assertIn('<svg', trash.read_text(encoding='utf-8'))

        dialog = GameDetailDialog({'title': 'Game'})
        edit = dialog.findChild(QToolButton, 'editBoxfrontButton')
        remove = dialog.findChild(QToolButton, 'removeBoxfrontButton')
        self.assertEqual('选择或替换', edit.toolTip())
        self.assertEqual('移除', remove.toolTip())
        self.assertFalse(edit.icon().isNull())
        self.assertFalse(remove.icon().isNull())
        dialog.close()

    def test_switching_to_video_tab_without_video_does_not_crash(self):
        dialog = GameDetailDialog({'title': 'Game'})
        tabs = dialog.findChild(QTabWidget, 'mediaTabs')

        tabs.setCurrentIndex(2)

        self.assertEqual('视频', tabs.tabText(tabs.currentIndex()))
        self.assertIsNone(dialog._media_player)
        dialog.close()

    def test_removing_video_then_switching_to_video_tab_does_not_crash(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            video = Path(temp_dir) / 'video.mp4'
            video.write_bytes(b'data')
            dialog = GameDetailDialog({
                'title': 'Game',
                'video': str(video),
            })
            dialog.findChild(QToolButton, 'removeVideoButton').click()
            self.assertIsNone(dialog._video_widget)
            tabs = dialog.findChild(QTabWidget, 'mediaTabs')
            tabs.setCurrentIndex(2)

            self.assertEqual('视频', tabs.tabText(tabs.currentIndex()))
            self.assertIsNone(dialog._media_player)
            dialog.close()


if __name__ == '__main__':
    unittest.main()
