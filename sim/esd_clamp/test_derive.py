"""Replay the archived ESD clamp reports with python3 -I sim/esd_clamp/test_derive.py."""

import copy
import gzip
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ARCHIVE = HERE / "records" / "20261023T172346Z"


class DeriveTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.work = Path(temp.name)
        with gzip.open(ARCHIVE / "report_cap.json.gz", "rt") as stream:
            self.cap = json.load(stream)
        self.corners = self.cap["corners"]
        self.zero = next(
            c for c in self.corners if c["corner_id"] == "typical/0.000V/-40C"
        )
        self.unlabeled = copy.deepcopy(self.zero)
        del self.unlabeled["supply_v"]
        self.unlabeled.update(corner_id="typical/novdd/-40C", status="error")
        for measurement in self.unlabeled["measurements"]:
            measurement["value"] = -0.0001

    def derive(self, case, corners=None):
        cap = ARCHIVE / "report_cap.json.gz"
        if corners is not None:
            cap = self.work / "cap.json"
            cap.write_text(json.dumps({**self.cap, "corners": corners}))
        return subprocess.run(
            [
                sys.executable,
                "-I",
                HERE / "esd_clamp.py",
                "derive",
                "--fwd",
                ARCHIVE / "report_fwd.json.gz",
                "--leak",
                ARCHIVE / "report_leak.json.gz",
                "--cap",
                cap,
                "--grid",
                ARCHIVE / "grid.json",
                "--out",
                self.work / case,
            ],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_row_order(self):
        baseline = self.derive("original")
        self.assertEqual(baseline.returncode, 0, baseline.stderr)
        expected = json.loads((ARCHIVE / "summary.json").read_text())
        self.assertEqual(
            json.loads((self.work / "original/summary.json").read_text()), expected
        )
        record = (self.work / "original/record.md").read_bytes()
        for case, corners in [
            ("first", [self.unlabeled] + self.corners),
            ("last", self.corners + [self.unlabeled]),
        ]:
            with self.subTest(case=case):
                result = self.derive(case, corners)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(
                    json.loads((self.work / case / "summary.json").read_text()),
                    expected,
                )
                self.assertEqual((self.work / case / "record.md").read_bytes(), record)

    def test_required_bias(self):
        self.corners.remove(self.zero)
        self.corners.append(self.unlabeled)
        missing = self.derive("missing", self.corners)
        self.assertEqual(missing.returncode, 1)
        self.assertIn("cap: missing corner ('typical', -40, 0.0)", missing.stderr)

        # A small bias offset still matches the required zero-bias corner.
        self.zero["supply_v"]["vr"] = 5e-10
        self.corners.append(self.zero)
        near_zero = self.derive("near_zero", self.corners)
        self.assertEqual(near_zero.returncode, 0, near_zero.stderr)
        self.assertEqual(
            (self.work / "near_zero/summary.json").read_bytes(),
            (ARCHIVE / "summary.json").read_bytes(),
        )

        self.zero["status"] = "error"
        failed = self.derive("failed", self.corners)
        self.assertEqual(failed.returncode, 1)
        self.assertIn("cap: corner ('typical', -40, 0.0) status 'error'", failed.stderr)


if __name__ == "__main__":
    unittest.main()
