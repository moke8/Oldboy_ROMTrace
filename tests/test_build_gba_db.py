import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class GBADatabaseBuilderTests(unittest.TestCase):
    def test_generated_database_normalizes_title(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source = tmp_path / 'Nintendo - Game Boy Advance.xml'
            source.write_text(
                '<game name="Digimon - Battle Spirit (Europe) '
                '(En,Fr,De,Es,It)"><file serial="ABCD"/></game>',
                encoding='utf-8',
            )
            subprocess.run(
                [sys.executable, str(ROOT / 'build_gba_db.py')],
                cwd=tmp_path,
                check=True,
                capture_output=True,
            )
            generated = (tmp_path / 'game_gba_db.py').read_text(
                encoding='utf-8'
            )

        self.assertIn("'ABCD': 'Digimon - Battle Spirit'", generated)


if __name__ == '__main__':
    unittest.main()
