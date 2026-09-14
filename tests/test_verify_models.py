"""Checkpoint validation must examine file bytes without loading a model."""
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


class VerifyModelsTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location('verify_models', ROOT / 'scripts/verify-models.py')
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.directory = Path(self.tmp.name)
        self.hashes = {'fixture.pth': 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad'}

    def test_accepts_exact_bytes(self):
        (self.directory / 'fixture.pth').write_bytes(b'abc')
        with patch.dict(self.module.HASHES, self.hashes, clear=True):
            self.module.verify(self.directory)

    def test_rejects_corrupt_bytes(self):
        (self.directory / 'fixture.pth').write_bytes(b'abd')
        with patch.dict(self.module.HASHES, self.hashes, clear=True):
            with self.assertRaisesRegex(ValueError, 'fixture.pth'):
                self.module.verify(self.directory)

    def test_rejects_missing_checkpoint(self):
        with patch.dict(self.module.HASHES, self.hashes, clear=True):
            with self.assertRaises(FileNotFoundError):
                self.module.verify(self.directory)


if __name__ == '__main__':
    unittest.main()
