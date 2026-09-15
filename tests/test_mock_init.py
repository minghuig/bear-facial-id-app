import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class MockInitTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location('mock_init', ROOT / 'scripts/mock_init.py')
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / '.env.mock.example').write_text(
            'WORKER_TOKEN=replace-with-at-least-24-random-characters\n')

    def test_creates_private_mock_environment_once(self):
        path, created = self.module.prepare(self.root)
        self.assertTrue(created)
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        token = path.read_text().split('=', 1)[1].strip()
        self.assertGreaterEqual(len(token), 24)

        repeated, created = self.module.prepare(self.root)
        self.assertFalse(created)
        self.assertEqual(repeated.read_text(), path.read_text())


if __name__ == '__main__':
    unittest.main()
