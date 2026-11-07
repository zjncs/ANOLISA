#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Tests for shared_strings_builder.py XML 1.0 character validation.

html.escape() does not touch control characters, so a string carrying
one (a vertical tab pasted from elsewhere, a NUL from a broken export)
used to produce a sharedStrings.xml that is not well-formed — xlsx_pack
only reported a cryptic parse error later and Excel rejected the
workbook outright.
"""

import io
import sys
import unittest
import xml.etree.ElementTree as ET
from contextlib import redirect_stderr
from pathlib import Path

sys.dont_write_bytecode = True

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "others" / "xlsx" / "scripts"),
)
import shared_strings_builder as b  # noqa: E402


class ValidateStringsTests(unittest.TestCase):
    def test_illegal_control_char_rejected_with_clean_error(self):
        for bad in ("bad\x0bstring", "a\x00b", "x\x1fy", "c\x0cd"):
            with self.subTest(bad=repr(bad)):
                with self.assertRaises(SystemExit) as ctx:
                    with redirect_stderr(io.StringIO()) as err:
                        b.validate_strings(["ok", bad])
                self.assertEqual(ctx.exception.code, 1)
                self.assertIn("not a legal XML 1.0 character", err.getvalue())
                self.assertIn("index 1", err.getvalue())

    def test_legal_whitespace_and_text_accepted(self):
        # tab/newline/CR are the C0 controls XML 1.0 allows; CJK and
        # astral text must pass untouched
        b.validate_strings(
            ["with\ttab", "with\nnewline", "with\rCR", "预算表", "emoji: \U0001F600", ""]
        )

    def test_xml_output_is_well_formed_for_legal_strings(self):
        xml = b.build_xml(["plain", "with\ttab", "预算 <100>", " spaced "])
        root = ET.fromstring(xml)
        self.assertEqual(root.tag, f"{{{b.SST_NS}}}sst")


class CliTests(unittest.TestCase):
    SCRIPT = str(Path(__file__).resolve().parents[1] / "others" / "xlsx" / "scripts" / "shared_strings_builder.py")

    def test_cli_rejects_control_char_input(self):
        import subprocess

        proc = subprocess.run(
            [sys.executable, self.SCRIPT, "ok", "bad\x0bstring"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 1)
        self.assertIn("not a legal XML 1.0 character", proc.stderr)
        self.assertNotIn("<sst", proc.stdout)

    def test_cli_output_parses_for_normal_input(self):
        import subprocess

        proc = subprocess.run(
            [sys.executable, self.SCRIPT, "Revenue", "预算表"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0)
        ET.fromstring(proc.stdout)


if __name__ == "__main__":
    unittest.main()
