import tempfile
import unittest
from pathlib import Path

from build_wii_db import DEFAULT_OUTPUT, extract_id_map, write_database


class WiiDatabaseBuilderTests(unittest.TestCase):
    def test_default_output_uses_standard_database_name(self):
        self.assertEqual(Path('game_wii_db.py'), DEFAULT_OUTPUT)

    def test_extracts_six_character_ids_and_keeps_first_duplicate(self):
        source = '''TITLES = https://www.gametdb.com (type: Wii language: EN)
SMNP01 = New Super Mario Bros. Wii
SMNP01 = Newer Duplicate Should Be Ignored
RMGE01 = Super Mario Galaxy (USA)
SHORT = Too Short
TOOLONG1 = Too Long
# comment
'''
        result = extract_id_map(source)

        self.assertEqual({
            'SMNP01': 'New Super Mario Bros. Wii',
            'RMGE01': 'Super Mario Galaxy (USA)',
        }, result)

    def test_writes_sorted_importable_database_with_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'game_wii_db.py'
            write_database(
                {'RMGE01': 'Super Mario Galaxy', 'SMNP01': "Mario's Game"},
                output,
                'wiitdb-en.txt',
            )
            generated = output.read_text(encoding='utf-8')

        self.assertIn('wiitdb-en.txt', generated)
        self.assertIn('https://www.gametdb.com', generated)
        self.assertLess(generated.index("'RMGE01'"),
                        generated.index("'SMNP01'"))
        self.assertIn("Mario\\'s Game", generated)

    def test_normalizes_names_written_to_database(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'game_wii_db.py'
            write_database(
                {'SMNP01': 'New Super Mario Bros. Wii (USA) (Rev 1)'},
                output,
                'fixture.txt',
            )
            generated = output.read_text(encoding='utf-8')

        self.assertIn("'SMNP01': 'New Super Mario Bros. Wii'", generated)


class WiiGeneratedDatabaseTests(unittest.TestCase):
    def test_generated_database_has_expected_wii_ids(self):
        from game_wii_db import WII_GAME_DB

        self.assertGreaterEqual(len(WII_GAME_DB), 5000)
        self.assertEqual(
            'New Super Mario Bros. Wii',
            WII_GAME_DB['SMNP01'],
        )
        self.assertNotIn('TITLES', WII_GAME_DB)
        self.assertTrue(all(len(game_id) == 6 for game_id in WII_GAME_DB))


if __name__ == '__main__':
    unittest.main()
