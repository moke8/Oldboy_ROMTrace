import tempfile
import unittest
from pathlib import Path

from build_nds_db import extract_serial_map, write_database


class NDSDatabaseBuilderTests(unittest.TestCase):
    def test_extracts_valid_serials_and_keeps_first_duplicate(self):
        xml = '''<?xml version="1.0"?>
<datafile>
  <game name="Ys DS (Japan)"><rom serial="AYDJ"/></game>
  <game name="Ys DS (Revision)"><rom serial="AYDJ"/></game>
  <game name="Ys II DS (Japan)"><rom serial="AYEJ"/></game>
  <game name="Invalid"><rom serial="!n/a"/></game>
  <game name="Too Long"><rom serial="ABCDE"/></game>
</datafile>'''
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'nds.dat'
            source.write_text(xml, encoding='utf-8')
            result = extract_serial_map(source)

        self.assertEqual({
            'AYDJ': 'Ys DS (Japan)',
            'AYEJ': 'Ys II DS (Japan)',
        }, result)

    def test_writes_sorted_importable_python_database(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'nds_game_db.py'
            write_database(
                {'AYEJ': 'Ys II DS (Japan)', 'AYDJ': "Ys DS Director's Cut"},
                output,
                'fixture.dat',
            )
            generated = output.read_text(encoding='utf-8')

        self.assertIn("# 来源: fixture.dat", generated)
        self.assertIn("# 条目数: 2", generated)
        self.assertLess(generated.index("'AYDJ'"), generated.index("'AYEJ'"))
        self.assertIn("Director\\'s Cut", generated)


if __name__ == '__main__':
    unittest.main()
