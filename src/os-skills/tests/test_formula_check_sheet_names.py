#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Tests for formula_check.py quoted sheet-name parsing.

Regression tests for sheet names containing apostrophes: Excel escapes
an apostrophe in a sheet name by doubling it inside the quotes, so a
formula referencing the sheet It's is written 'It''s'!A1. The quoted-
name pattern used to stop at the first apostrophe and capture "s",
producing a false broken_sheet_ref against a sheet that does exist.
"""

import os
from pathlib import Path
import sys
import time
import unittest

sys.dont_write_bytecode = True

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "others" / "xlsx" / "scripts"),
)
import formula_check as fc  # noqa: E402


class TestExtractSheetRefs(unittest.TestCase):
    def test_quoted_name_with_escaped_apostrophe(self):
        """'It''s'!A1 references the sheet named It's — not a sheet named s.

        Before the fix the pattern '([^']+)'! captured "s", so the
        validator reported a missing sheet "s" for a perfectly valid
        formula.
        """
        self.assertEqual(fc.extract_sheet_refs("SUM('It''s'!A1:B2)"), ["It's"])

    def test_escaped_apostrophe_mixed_with_plain_quoted(self):
        self.assertEqual(
            fc.extract_sheet_refs("='Q1 Data'!A1+'It''s'!B2"),
            ["Q1 Data", "It's"],
        )

    def test_name_that_is_only_an_escaped_apostrophe(self):
        # A sheet literally named ' — quoted as '''' (quote, doubled, quote).
        self.assertEqual(fc.extract_sheet_refs("=''''!A1"), ["'"])

    def test_plain_quoted_name_unchanged(self):
        self.assertEqual(fc.extract_sheet_refs("='Budget FY25'!A1"), ["Budget FY25"])

    def test_unquoted_name_unchanged(self):
        self.assertEqual(fc.extract_sheet_refs("=Sheet1!A1"), ["Sheet1"])

    def test_31_char_name_with_escapes_still_extracted(self):
        """The {0,31} bound counts escapes as single iterations, so a
        maximal legal sheet name with apostrophes still extracts."""
        name = "It'" + "s" * 28  # 31 chars, one escaped apostrophe
        quoted = "'" + name.replace("'", "''") + "'"
        self.assertEqual(fc.extract_sheet_refs(f"={quoted}!A1"), [name])

    def test_unclosed_apostrophe_run_stays_fast(self):
        """An unclosed apostrophe run must not trigger quadratic
        backtracking.

        The unbounded escape-aware quantifier took ~0.9s on an
        8192-character payload (Excel's formula length cap) and ~3.5s at
        16384, doubling with every 2x length; check() calls this
        function on every formula before the name scan, so the
        workbook-level hang survives the name scan's own bound without
        this one.
        """
        payload = "=SUM('" + "'" * 8192 + "x"
        start = time.perf_counter()
        fc.extract_sheet_refs(payload)
        self.assertLess(time.perf_counter() - start, 0.5)


if __name__ == "__main__":
    unittest.main()
