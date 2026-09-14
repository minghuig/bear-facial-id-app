import contextlib
import io
import runpy
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT=Path(__file__).resolve().parents[1]/'scripts/release.py'

class ReleaseBranchTests(unittest.TestCase):
    def execute(self, requested, main):
        calls=[]
        def output(args, **kwargs):
            calls.append(args)
            if args[0]=='git':
                return main if args[-1]=='main^{commit}' else requested
            raise RuntimeError('infrastructure reached')
        with patch('sys.argv',[str(SCRIPT),'feature','--approved-spend']), patch('subprocess.check_output',side_effect=output), contextlib.redirect_stderr(io.StringIO()):
            try:
                runpy.run_path(str(SCRIPT),run_name='__main__')
            except (SystemExit,RuntimeError) as error:
                return error,calls
        self.fail('Release unexpectedly completed')

    def test_unmerged_revision_is_rejected_before_infrastructure(self):
        error,calls=self.execute('feature-sha','main-sha')
        self.assertIsInstance(error,SystemExit)
        self.assertEqual(error.code,2)
        self.assertTrue(all(call[0]=='git' for call in calls))

    def test_exact_main_revision_can_reach_infrastructure(self):
        error,_=self.execute('main-sha','main-sha')
        self.assertIsInstance(error,RuntimeError)
        self.assertEqual(str(error),'infrastructure reached')
