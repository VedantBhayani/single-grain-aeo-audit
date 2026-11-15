"""The box script's lock: a second run must refuse while one holds it. Needs bash and flock (Linux CI)."""
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

try:
    import fcntl
except ImportError:  # Windows
    fcntl = None

SCRIPT = Path(__file__).resolve().parent.parent / "aeo_watch" / "box_run.sh"


@unittest.skipUnless(fcntl and shutil.which("bash") and shutil.which("flock"), "needs bash + flock (Linux)")
class LockTests(unittest.TestCase):
    def test_second_run_refuses_while_the_lock_is_held(self):
        with tempfile.TemporaryDirectory() as h:
            with open(Path(h) / "aeo.lock", "w") as held:
                fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
                r = subprocess.run(["bash", str(SCRIPT), "--mode", "new"], capture_output=True, text=True,
                                   env={**os.environ, "AEO_HOME": h}, timeout=60)
            self.assertEqual(r.returncode, 75, r.stdout + r.stderr)
            self.assertIn("still going", r.stdout)
            self.assertFalse((Path(h) / "aeo-state").exists())  # it never started


if __name__ == "__main__":
    unittest.main()
