"""Offline tests using synthetic snippets, never a real printer configuration."""

import contextlib
import io
import os
from pathlib import Path
import tempfile
import unittest

from prepare_ppd import COMMENT, UnsupportedPPD, main, prepare


PDF_RULE = b'*cupsFilter2: "application/vnd.cups-pdf application/pdf 10 -"\n'
URF_RULE = b'*cupsFilter2: "image/urf image/urf 100 -"\n'
# Minimal parser fixture, deliberately not an installable printer driver.
FIXTURE = (
    b'*PPD-Adobe: "4.3"\n'
    b'*NickName: "Synthetic example"\n'
    b'*cupsFilter2: "image/jpeg image/jpeg 0 -"\n'
    + PDF_RULE + URF_RULE
    + b'*DefaultDuplex: DuplexNoTumble\n'
    b'*cupsBackSide: Rotated\n'
    b'*DefaultResolution: 300dpi\n'
    b'*DefaultcupsPrintQuality: Normal\n'
    b'*cupsPrintQuality High: "<</HWResolution[600 600]>>setpagedevice"\n'
    + '*de_DE.Translation Duplex/Doppelseitiger Druck: ""\n'.encode()
)


class PreparationTests(unittest.TestCase):
    def test_only_pdf_rule_changes(self):
        result, count = prepare(FIXTURE)
        self.assertEqual(count, 1)
        self.assertEqual(result, FIXTURE.replace(PDF_RULE, COMMENT + b"\n"))

    def test_duplex_back_side_and_high_quality_are_preserved(self):
        result, _ = prepare(FIXTURE)
        for line in FIXTURE.splitlines():
            if any(key in line for key in (b"Duplex", b"cupsBackSide", b"Resolution", b"PrintQuality")):
                self.assertIn(line, result)

    def test_crlf_and_non_ascii_bytes_are_preserved(self):
        source = FIXTURE.replace(b"\n", b"\r\n") + b'*% opaque byte: \xff\r\n'
        result, _ = prepare(source)
        self.assertEqual(result, source.replace(PDF_RULE.replace(b"\n", b"\r\n"), COMMENT + b"\r\n"))

    def test_different_pdf_source_and_cost(self):
        source = FIXTURE.replace(PDF_RULE, b'*cupsFilter2: "application/pdf application/pdf 500 -"\n')
        self.assertEqual(prepare(source)[1], 1)

    def test_multiple_pdf_pass_through_rules(self):
        source = FIXTURE + b'*cupsFilter2: "application/pdf application/pdf 20 -"\n'
        result, count = prepare(source)
        self.assertEqual(count, 2)
        self.assertNotIn(b"application/pdf", result)

    def test_missing_urf_is_rejected(self):
        with self.assertRaises(UnsupportedPPD):
            prepare(FIXTURE.replace(URF_RULE, b""))

    def test_already_modified_input_is_rejected(self):
        with self.assertRaises(UnsupportedPPD):
            prepare(prepare(FIXTURE)[0])

    def test_alternative_postscript_output_is_rejected(self):
        with self.assertRaises(UnsupportedPPD):
            prepare(FIXTURE + b'*cupsFilter2: "application/vnd.cups-postscript application/postscript 0 -"\n')

    def test_custom_pdf_filter_is_rejected(self):
        with self.assertRaises(UnsupportedPPD):
            prepare(FIXTURE + b'*cupsFilter2: "application/pdf application/pdf 5 custom-filter"\n')

    def test_malformed_filter_rule_is_rejected(self):
        with self.assertRaises(UnsupportedPPD):
            prepare(FIXTURE + b'*cupsFilter2: "not a supported rule"\n')

    def test_missing_header_is_rejected(self):
        with self.assertRaises(UnsupportedPPD):
            prepare(b"not a PPD")


class FileTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.source = self.root / "input.ppd"
        self.source.write_bytes(FIXTURE)
        self.output = self.root / "output.ppd"

    def run_main(self, *args):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return main([str(arg) for arg in args])

    def test_new_private_file_and_source_unchanged(self):
        self.assertEqual(self.run_main(self.source, self.output), 0)
        self.assertEqual(self.source.read_bytes(), FIXTURE)
        self.assertEqual(self.output.read_bytes(), prepare(FIXTURE)[0])
        if os.name == "posix":
            self.assertEqual(self.output.stat().st_mode & 0o777, 0o600)

    def test_existing_output_is_never_overwritten(self):
        self.output.write_bytes(b"keep this")
        self.assertEqual(self.run_main(self.source, self.output), 1)
        self.assertEqual(self.output.read_bytes(), b"keep this")

    def test_in_place_edit_is_rejected(self):
        self.assertEqual(self.run_main(self.source, self.source), 1)
        self.assertEqual(self.source.read_bytes(), FIXTURE)

    @unittest.skipUnless(os.name == "posix", "POSIX symlink test")
    def test_symlink_to_source_is_rejected(self):
        self.output.symlink_to(self.source)
        self.assertEqual(self.run_main(self.source, self.output), 1)
        self.assertEqual(self.source.read_bytes(), FIXTURE)

    def test_check_does_not_create_output(self):
        self.assertEqual(self.run_main(self.source, "--check"), 0)
        self.assertEqual(list(self.root.iterdir()), [self.source])

    def test_unsupported_input_does_not_create_output(self):
        self.source.write_bytes(FIXTURE.replace(URF_RULE, b""))
        self.assertEqual(self.run_main(self.source, self.output), 1)
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
