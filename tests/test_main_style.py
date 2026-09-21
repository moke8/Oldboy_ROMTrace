import unittest

from PySide6.QtWidgets import QApplication, QAbstractSpinBox

from main import MainWindow, STYLESHEET


class MainStyleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_thread_spin_box_uses_readable_dark_theme(self):
        self.assertIn('QSpinBox {', STYLESHEET)
        self.assertIn('background: #0d1117', STYLESHEET)
        self.assertIn('color: #e6edf3', STYLESHEET)
        self.assertIn('QSpinBox::up-button, QSpinBox::down-button', STYLESHEET)

    def test_thread_spin_box_has_visible_controls_and_enough_width(self):
        window = MainWindow()

        self.assertEqual(
            QAbstractSpinBox.ButtonSymbols.UpDownArrows,
            window.thread_spin.buttonSymbols(),
        )
        self.assertEqual(64, window.thread_spin.width())
        self.assertIn('QSpinBox::up-arrow {', STYLESHEET)
        self.assertIn('image: url(assets/icons/chevron-up.svg)', STYLESHEET)
        self.assertIn('QSpinBox::down-arrow {', STYLESHEET)
        self.assertIn('image: url(assets/icons/chevron-down.svg)', STYLESHEET)
        window.close()

    def test_window_uses_product_title_and_generated_icon(self):
        window = MainWindow()

        self.assertEqual('Oldboy ROMTrace', window.windowTitle())
        self.assertFalse(window.windowIcon().isNull())
        self.assertFalse(window.windowIcon().pixmap(64, 64).isNull())
        window.close()

    def test_window_saves_config_on_close(self):
        from unittest.mock import patch

        window = MainWindow()
        self.addCleanup(window.close)
        with patch.object(window, 'save_config') as save:
            window.close()
            save.assert_called_once()


if __name__ == '__main__':
    unittest.main()
