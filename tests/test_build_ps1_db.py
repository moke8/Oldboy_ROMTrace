import tempfile
import unittest
from pathlib import Path

from build_ps1_db import DEFAULT_OUTPUT, extract_serial_map, write_database


class PS1DatabaseBuilderTests(unittest.TestCase):
    def test_default_output_uses_standard_database_name(self):
        self.assertEqual(Path('game_ps1_db.py'), DEFAULT_OUTPUT)

    def test_extracts_serial_and_name_pairs(self):
        source = '''SLPS-01220:
  name: "Namco Anthology 1"
  localizedName: "ナムコアンソロジー１"
SLUS-00001:
  name: "Air Combat"
metadata:
  name: "Not a game entry"
'''

        result = extract_serial_map(source)

        self.assertEqual({
            'SLPS-01220': 'Namco Anthology 1',
            'SLUS-00001': 'Air Combat',
        }, result)

    def test_writes_sorted_importable_database_with_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'game_ps1_db.py'
            write_database(
                {'SLUS-00001': 'Air Combat', 'SLPS-01220': "Namco's Game"},
                output,
                'DuckStation gamedb.yaml',
            )
            generated = output.read_text(encoding='utf-8')

        self.assertIn('DuckStation gamedb.yaml', generated)
        self.assertIn('https://github.com/stenzek/duckstation', generated)
        self.assertLess(generated.index("'SLPS-01220'"),
                        generated.index("'SLUS-00001'"))
        self.assertIn("Namco\\'s Game", generated)

    def test_normalizes_names_written_to_database(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'game_ps1_db.py'
            write_database(
                {'SLUS-00001': 'Air Combat (USA) (Rev 1)'},
                output,
                'fixture.yaml',
            )
            generated = output.read_text(encoding='utf-8')

        self.assertIn("'SLUS-00001': 'Air Combat'", generated)


if __name__ == '__main__':
    unittest.main()
