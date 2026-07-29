import os
import unittest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtWidgets import QApplication

from main import ScrapeSettingsDialog, _migrate_translation_settings


class ScrapeSettingsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_media_options_have_expected_defaults(self):
        dialog = ScrapeSettingsDialog({})
        self.addCleanup(dialog.close)

        self.assertTrue(dialog.normalize_media_check.isChecked())
        self.assertFalse(dialog.anbernic_compatible_check.isChecked())
        settings = dialog.get_settings()
        self.assertTrue(settings['normalize_media_paths'])
        self.assertFalse(settings['anbernic_compatible'])

    def test_media_options_restore_saved_values(self):
        dialog = ScrapeSettingsDialog({
            'normalize_media_paths': False,
            'anbernic_compatible': True,
        })
        self.addCleanup(dialog.close)

        self.assertFalse(dialog.normalize_media_check.isChecked())
        self.assertTrue(dialog.anbernic_compatible_check.isChecked())

    def test_translation_provider_defaults_to_google(self):
        dialog = ScrapeSettingsDialog({})
        self.addCleanup(dialog.close)

        providers = [
            dialog.translate_provider_combo.itemData(index)
            for index in range(dialog.translate_provider_combo.count())
        ]
        self.assertEqual(providers, ['off', 'google', 'ai'])
        self.assertEqual(dialog.translate_provider_combo.currentData(), 'google')
        self.assertTrue(dialog.ai_config_widget.isHidden())

    def test_ai_config_is_saved_and_restored_when_switching_provider(self):
        dialog = ScrapeSettingsDialog({
            'translate_provider': 'ai',
            'translate_configs': {
                'google': {},
                'ai': {
                    'base_url': 'https://old.example.com/v1',
                    'model': 'old-model',
                    'api_key': 'old-key',
                },
            },
        })
        self.addCleanup(dialog.close)

        self.assertFalse(dialog.ai_config_widget.isHidden())
        self.assertEqual(dialog.ai_base_url_input.text(), 'https://old.example.com/v1')
        dialog.ai_base_url_input.setText('https://new.example.com/v1')
        dialog.ai_model_input.setText('new-model')
        dialog.ai_api_key_input.setText('new-key')

        dialog.translate_provider_combo.setCurrentIndex(
            dialog.translate_provider_combo.findData('google'))
        dialog.translate_provider_combo.setCurrentIndex(
            dialog.translate_provider_combo.findData('ai'))

        self.assertEqual(dialog.ai_base_url_input.text(), 'https://new.example.com/v1')
        self.assertEqual(dialog.ai_model_input.text(), 'new-model')
        self.assertEqual(dialog.ai_api_key_input.text(), 'new-key')
        settings = dialog.get_settings()
        self.assertEqual(settings['translate_provider'], 'ai')
        self.assertEqual(settings['translate_configs']['ai'], {
            'base_url': 'https://new.example.com/v1',
            'model': 'new-model',
            'api_key': 'new-key',
        })

    def test_old_disabled_translation_setting_migrates_to_off(self):
        dialog = ScrapeSettingsDialog({'translate': False})
        self.addCleanup(dialog.close)

        self.assertEqual(dialog.translate_provider_combo.currentData(), 'off')

    def test_migration_removes_legacy_translate_field(self):
        settings = {'translate': False, 'online_mode': True}

        _migrate_translation_settings(settings)

        self.assertEqual(settings['translate_provider'], 'off')
        self.assertNotIn('translate', settings)


if __name__ == '__main__':
    unittest.main()
