import re
import tempfile
import unittest
from pathlib import Path

import build_psp_db
from build_psp_db import (
    discover_page_count,
    extract_serial_map,
    write_database,
)


PAGE_ONE = '''
<form><div class="pages"><a href="?page=2">2</a></div></form>
<table class="games">
<tr>
  <td>Japan</td>
  <td><a href="/disc/1/">Valkyrie Profile: Lenneth (Japan)<br />
      <span>localized title</span></a></td>
  <td>PSP</td><td>1.00</td><td></td><td></td>
  <td title="ULJM 05101, ULJM 06000">ULJM 05101, ...</td><td></td>
</tr>
<tr>
  <td>Unknown</td><td><a href="/disc/2/">Invalid</a></td>
  <td>PSP</td><td>1.00</td><td></td><td></td>
  <td title="ULUS12345A">ULUS12345A</td><td></td>
</tr>
</table>
'''

PAGE_TWO = '''
<table class="games">
<tr>
  <td>Japan</td><td><a href="/disc/3/">Later Duplicate</a></td>
  <td>PSP</td><td>1.01</td><td></td><td></td>
  <td title="ULJM-05101">ULJM-05101</td><td></td>
</tr>
<tr>
  <td>USA</td><td><a href="/disc/4/">Director's Game (USA) (Demo)</a></td>
  <td>PSP</td><td>1.00</td><td></td><td></td>
  <td title="ULUS-10001">ULUS-10001</td><td></td>
</tr>
</table>
'''


class PSPDatabaseBuilderTests(unittest.TestCase):
    def test_discovers_last_page(self):
        self.assertEqual(2, discover_page_count(PAGE_ONE))

    def test_extracts_first_valid_serial_and_keeps_first_duplicate(self):
        self.assertEqual({
            'ULJM05101': 'Valkyrie Profile: Lenneth',
            'ULUS10001': "Director's Game",
        }, extract_serial_map([PAGE_ONE, PAGE_TWO]))

    def test_writes_sorted_importable_database(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'game_psp_db.py'
            write_database(
                {'ULUS10001': "Director's Game", 'ULJM05101': 'Valkyrie'},
                output,
                'fixture',
            )
            generated = output.read_text(encoding='utf-8')

        self.assertLess(generated.index("'ULJM05101'"),
                        generated.index("'ULUS10001'"))
        self.assertIn("Director\\'s Game", generated)

    def test_rejects_a_page_without_game_rows(self):
        with self.assertRaisesRegex(ValueError, 'no game rows'):
            extract_serial_map(['<html><body>unexpected response</body></html>'])

    def test_rejects_database_below_safe_entry_count(self):
        with self.assertRaisesRegex(ValueError, 'at least 3300'):
            build_psp_db.validate_serial_map({'ULJM05101': 'Valkyrie'})


class PSPGeneratedDatabaseTests(unittest.TestCase):
    def test_generated_database_has_expected_psp_ids(self):
        from game_psp_db import PSP_GAME_DB

        self.assertGreaterEqual(len(PSP_GAME_DB), 3300)
        self.assertIn('ULJM05101', PSP_GAME_DB)
        self.assertTrue(all(
            re.fullmatch(r'U[CL][A-Z]{2}\d{5}', disc_id)
            for disc_id in PSP_GAME_DB
        ))


if __name__ == '__main__':
    unittest.main()
