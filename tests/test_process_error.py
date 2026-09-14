import sys
import subprocess
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'workers'))


class ProcessErrorTests(unittest.TestCase):
    def test_keeps_underlying_error(self):
        from process_error import describe
        error = subprocess.CalledProcessError(1, ['python'], stderr='Traceback...\nImportError: library unavailable\n')
        self.assertIn('ImportError: library unavailable', describe(error))

    def test_removes_signed_url_query(self):
        from process_error import describe
        error = subprocess.CalledProcessError(1, ['python'], stderr='HTTP error https://bucket/image?secret=hidden')
        self.assertNotIn('secret=hidden', describe(error))

    def test_signal_without_stderr_still_has_exit_code(self):
        from process_error import describe
        self.assertIn('-9', describe(subprocess.CalledProcessError(-9, ['python'])))


if __name__ == '__main__': unittest.main()
