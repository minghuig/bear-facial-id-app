import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


class LocalRealTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location('local_real', ROOT / 'scripts/local_real.py')
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_failed_verification_creates_no_environment(self):
        with patch.object(self.module, 'verify', side_effect=ValueError('bad checkpoint')):
            with self.assertRaises(ValueError):
                self.module.prepare(self.root, self.root / 'models', 'real-v1-test')
        self.assertFalse((self.root / '.env.local-real').exists())

    def test_repeat_preserves_credentials_and_refreshes_pipeline(self):
        with patch.object(self.module, 'verify'):
            first = self.module.prepare(self.root, self.root / 'models', 'real-v1-first')
            second = self.module.prepare(self.root, self.root / 'models', 'real-v1-second')
        for key in ('DB_PASSWORD', 'WORKER_TOKEN', 'MINIO_ROOT_PASSWORD'):
            self.assertEqual(first[key], second[key])
            self.assertGreaterEqual(len(second[key]), 24)
        self.assertEqual(second['PIPELINE'], 'real-v1-second')
        self.assertEqual(second['S3_ENDPOINT'], 'http://minio:9000')
        self.assertEqual(second['CORS_ORIGIN'], 'http://localhost:5174')
        self.assertEqual(second['AWS_EC2_METADATA_DISABLED'], 'true')


if __name__ == '__main__':
    unittest.main()
