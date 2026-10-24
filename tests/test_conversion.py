"""Unit tests for the non-GUI logic in src/main.py.

These exercise pure functions / QThread helper methods directly, without
starting a QApplication - the test runner (see .github/workflows/ci.yml)
sets QT_QPA_PLATFORM=offscreen as a belt-and-braces measure, but none of
these tests should need a display at all.
"""

import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import main  # noqa: E402


class OutputPathTests(unittest.TestCase):
    def test_defaults_next_to_source_file(self):
        worker = main.ConversionWorker(files=[], output_dir="")
        result = worker._output_path("/home/user/captures/office.pcapng")
        self.assertEqual(result, "/home/user/captures/office.22000")

    def test_uses_custom_output_dir_when_set(self):
        worker = main.ConversionWorker(files=[], output_dir="/data/out")
        result = worker._output_path("/home/user/captures/office.pcapng")
        self.assertEqual(result, str(Path("/data/out/office.22000")))

    def test_preserves_stem_for_various_extensions(self):
        worker = main.ConversionWorker(files=[])
        for src, expected in [
            ("capture.cap", "capture.22000"),
            ("capture.pcap", "capture.22000"),
            ("capture.pcapng", "capture.22000"),
        ]:
            with self.subTest(src=src):
                self.assertTrue(worker._output_path(src).endswith(expected))


class ToolVersionDetectionTests(unittest.TestCase):
    @patch("main.shutil.which", return_value=None)
    def test_not_found_when_not_on_path(self, _which):
        found, version = main.detect_tool_version("hcxpcapngtool")
        self.assertFalse(found)
        self.assertEqual(version, "Not found")

    @patch("main.subprocess.run")
    @patch("main.shutil.which", return_value="/usr/bin/hashcat")
    def test_parses_version_from_output(self, _which, mock_run):
        mock_run.return_value = MagicMock(
            stdout="hashcat (v6.2.6) starting\n", stderr=""
        )
        found, version = main.detect_tool_version("hashcat")
        self.assertTrue(found)
        self.assertEqual(version, "6.2.6")

    @patch("main.subprocess.run")
    @patch("main.shutil.which", return_value="/usr/bin/hashcat")
    def test_found_but_unparseable_version_falls_back(self, _which, mock_run):
        mock_run.return_value = MagicMock(stdout="no version here\n", stderr="")
        found, version = main.detect_tool_version("hashcat")
        self.assertTrue(found)
        self.assertEqual(version, "installed")

    @patch("main.subprocess.run", side_effect=subprocess.TimeoutExpired("x", 5))
    @patch("main.shutil.which", return_value="/usr/bin/hashcat")
    def test_found_but_command_hangs_does_not_raise(self, _which, _run):
        found, version = main.detect_tool_version("hashcat")
        self.assertTrue(found)
        self.assertEqual(version, "installed")


class CheckHcxtoolsTests(unittest.TestCase):
    def _make_app_stub(self, hcx_path):
        app = main.HashCatcher.__new__(main.HashCatcher)
        app.hcx_path = hcx_path
        return app

    @patch("main.shutil.which", return_value="/usr/bin/hcxpcapngtool")
    def test_bare_command_resolved_via_path(self, _which):
        app = self._make_app_stub("hcxpcapngtool")
        self.assertTrue(app.check_hcxtools())

    @patch("main.shutil.which", return_value=None)
    def test_bare_command_not_on_path(self, _which):
        app = self._make_app_stub("hcxpcapngtool")
        self.assertFalse(app.check_hcxtools())

    def test_absolute_path_checked_directly(self):
        app = self._make_app_stub(__file__)  # this test file exists
        self.assertTrue(app.check_hcxtools())

    def test_absolute_path_missing(self):
        app = self._make_app_stub("/no/such/binary/here")
        self.assertFalse(app.check_hcxtools())


if __name__ == "__main__":
    unittest.main()
