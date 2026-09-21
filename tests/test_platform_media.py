import os
import tempfile
import unittest
from pathlib import Path
from types import MethodType
from unittest.mock import Mock, patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtWidgets import QApplication, QPushButton, QWidget

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


class SelectedScrapeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _menu_with_selection(self):
        calls = []
        widget = QWidget()
        card_a = Mock(game={'file': 'a.nds', 'title': 'Alpha'})
        card_b = Mock(game={'file': 'b.nds', 'title': 'Beta'})
        widget._worker = None
        widget._selected_cards = {card_a, card_b}
        widget._scrape_games = (
            lambda filenames, scrape_mode: calls.append((filenames, scrape_mode)))
        widget._build_game_context_menu = MethodType(
            BasePlatformTab._build_game_context_menu, widget)
        return widget._build_game_context_menu(card_a), calls

    def test_scrape_selected_action_passes_filenames_not_checked_flag(self):
        menu, calls = self._menu_with_selection()
        action = next(
            item for item in menu.actions()
            if '补全选中游戏' in item.text())
        action.trigger()

        self.assertEqual(1, len(calls))
        filenames, scrape_mode = calls[0]
        self.assertEqual('complement', scrape_mode)
        self.assertCountEqual(['a.nds', 'b.nds'], filenames)

    def test_refresh_selected_action_passes_filenames_not_checked_flag(self):
        menu, calls = self._menu_with_selection()
        action = next(
            item for item in menu.actions()
            if '刷新选中游戏' in item.text())
        action.trigger()

        self.assertEqual(1, len(calls))
        filenames, scrape_mode = calls[0]
        self.assertEqual('refresh', scrape_mode)
        self.assertCountEqual(['a.nds', 'b.nds'], filenames)


class DirectoryPersistTests(unittest.TestCase):
    def test_pick_dir_saves_platform_directory(self):
        tab = Mock()
        tab.dir_input = Mock()
        tab._persist_config = MethodType(
            BasePlatformTab._persist_config, tab)
        with patch(
            'platform_base.QFileDialog.getExistingDirectory',
            return_value=r'E:\roms\3ds',
        ):
            BasePlatformTab._pick_dir(tab)

        tab.dir_input.setText.assert_called_once_with(r'E:\roms\3ds')
        tab._on_dir_changed.assert_called_once_with(r'E:\roms\3ds')
        tab.window.return_value.save_config.assert_called_once()

    def test_cancelled_pick_dir_does_not_save(self):
        tab = Mock()
        tab.dir_input = Mock()
        with patch(
            'platform_base.QFileDialog.getExistingDirectory',
            return_value='',
        ):
            BasePlatformTab._pick_dir(tab)

        tab.dir_input.setText.assert_not_called()
        tab.window.return_value.save_config.assert_not_called()


class ManualSearchDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _dialog(self, title='Mario Kart', settings=None):
        widget = QWidget()
        logs = []
        widget._log = logs.append
        widget.window = lambda: Mock(get_global_settings=lambda: settings or {
            'translate_provider': 'google',
            'google_lang': 'zh-CN',
            'translate_configs': {},
        })
        widget._translate_search_keyword = MethodType(
            BasePlatformTab._translate_search_keyword, widget)
        widget._build_manual_search_dialog = MethodType(
            BasePlatformTab._build_manual_search_dialog, widget)
        dialog, line_edit = widget._build_manual_search_dialog(
            title, 'mario.nds')
        return widget, dialog, line_edit, logs

    def test_manual_search_uses_literal_extract_and_translate_buttons(self):
        _widget, dialog, line_edit, _logs = self._dialog()
        self.addCleanup(dialog.close)

        extract = dialog.findChild(QPushButton, 'extractRomTitleButton')
        translate_btn = dialog.findChild(QPushButton, 'translateSearchButton')
        self.assertIsNotNone(extract)
        self.assertIsNotNone(translate_btn)
        self.assertEqual('提取', extract.text())
        self.assertEqual('翻译', translate_btn.text())
        self.assertEqual('Mario Kart', line_edit.text())

    def test_translate_button_replaces_keyword_using_scrape_settings(self):
        _widget, dialog, line_edit, logs = self._dialog()
        self.addCleanup(dialog.close)
        translate_btn = dialog.findChild(QPushButton, 'translateSearchButton')

        with patch(
            'translate_base.translate', return_value='马里奥卡丁车',
        ) as mock_translate:
            translate_btn.click()

        mock_translate.assert_called_once_with(
            'Mario Kart', 'zh-CN', 'google', {}, log=_widget._log)
        self.assertEqual('马里奥卡丁车', line_edit.text())
        self.assertTrue(any('马里奥卡丁车' in msg for msg in logs))

    def test_translate_button_keeps_text_when_translation_is_disabled(self):
        _widget, dialog, line_edit, logs = self._dialog(settings={
            'translate_provider': 'off',
            'google_lang': 'zh-CN',
            'translate_configs': {},
        })
        self.addCleanup(dialog.close)
        translate_btn = dialog.findChild(QPushButton, 'translateSearchButton')

        with patch('translate_base.translate') as mock_translate:
            translate_btn.click()

        mock_translate.assert_not_called()
        self.assertEqual('Mario Kart', line_edit.text())
        self.assertTrue(any('未启用翻译' in msg for msg in logs))


if __name__ == '__main__':
    unittest.main()
