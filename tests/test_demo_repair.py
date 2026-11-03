"""Run with FACEIT_TEST_DEMO and FACEIT_TEST_ZST pointing to a known affected pair."""
import hashlib
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from game_install import install_demo
from demo_repair import repair_demo


def sha(path):
    with open(path, 'rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


class RepairTests(unittest.TestCase):
    def test_invalid_input_preserved(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'broken.dem'
            p.write_bytes(b'PBDEMS2\0' + bytes(8) + b'\x07\x01\xff')
            before = sha(p)
            with self.assertRaises(RuntimeError):
                repair_demo(p)
            self.assertEqual(sha(p), before)
            self.assertFalse(p.with_name(p.name + '.repair').exists())

    @unittest.skipUnless(os.environ.get('FACEIT_TEST_DEMO'), 'requires affected demo fixture')
    def test_real_demo_install(self):
        source = Path(os.environ['FACEIT_TEST_DEMO'])
        before = sha(source)
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            game = base / 'игра с пробелами' / 'game' / 'csgo'
            game.mkdir(parents=True)
            exe = game.parent / 'bin' / 'win64' / 'cs2.exe'
            exe.parent.mkdir(parents=True); exe.touch()
            fixed = install_demo(source, game, 'Тест')
            self.assertTrue(fixed['repaired'])
            repaired = Path(fixed['file'])
            fixed_hash = sha(repaired)
            self.assertEqual(sha(source), before)
            self.assertFalse(repair_demo(repaired)['changed'])
            self.assertEqual(sha(repaired), fixed_hash)
            same = install_demo(repaired, game, 'Тест')
            self.assertFalse(same['repaired'])
            copied = install_demo(repaired, game, 'copy')
            self.assertFalse(copied['repaired'])
            self.assertEqual(sha(copied['file']), fixed_hash)
            with self.assertRaises(FileExistsError):
                install_demo(source, game, 'Тест')
            in_game = game / 'original.dem'
            shutil.copyfile(source, in_game)
            same = install_demo(in_game, game, 'original')
            self.assertEqual(Path(same['file']).name, 'original_fixed.dem')
            self.assertEqual(sha(in_game), before)
            self.assertEqual(sha(same['file']), fixed_hash)
            zst = os.environ.get('FACEIT_TEST_ZST')
            if zst:
                zst_hash = sha(zst)
                compressed = install_demo(zst, game, 'unpacked')
                self.assertTrue(compressed['repaired'])
                self.assertEqual(sha(compressed['file']), fixed_hash)
                self.assertEqual(sha(zst), zst_hash)
            broken = base / 'broken.dem'
            broken.write_bytes(b'PBDEMS2\0' + bytes(8) + b'\x07\x01\xff')
            with self.assertRaises(RuntimeError):
                install_demo(broken, game, 'broken')
            self.assertFalse((game / 'broken.dem').exists())
            self.assertFalse(list(game.glob('.faceit-import-*')))


if __name__ == '__main__':
    unittest.main()
