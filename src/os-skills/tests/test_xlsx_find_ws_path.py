#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Tests for find_ws_path's relationship Target resolution.

The minimal_xlsx template — and any workbook whose rels use the relative
Target form — used to crash find_ws_path with FileNotFoundError: relative
targets were joined to the unpacked root instead of the source part's
directory (xl/), so the documented "cp -r templates/minimal_xlsx" flow
could never run. Both xlsx_insert_row.py and xlsx_add_column.py carry a
copy of the function; both must resolve the same way.
"""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

sys.dont_write_bytecode = True

SCRIPTS = Path(__file__).resolve().parents[1] / "others" / "xlsx" / "scripts"
TEMPLATE = SCRIPTS.parent / "templates" / "minimal_xlsx"
sys.path.insert(0, str(SCRIPTS))
import xlsx_add_column  # noqa: E402
import xlsx_insert_row  # noqa: E402

NS_PKG_REL = "http://schemas.openxmlformats.org/package/2006/relationships"


class FindWsPathTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.work = os.path.join(self.tmp.name, "work")
        shutil.copytree(TEMPLATE, self.work)

    def tearDown(self):
        self.tmp.cleanup()

    def rels_path(self):
        return os.path.join(self.work, "xl", "_rels", "workbook.xml.rels")

    def test_relative_target_resolves_under_xl(self):
        """The template's Target="worksheets/sheet1.xml" is relative to
        xl/ (the directory of the source part), not to the unpacked root.
        """
        for module in (xlsx_insert_row, xlsx_add_column):
            with self.subTest(module=module.__name__):
                resolved = module.find_ws_path(self.work, None)
                expected = os.path.join(self.work, "xl", "worksheets", "sheet1.xml")
                self.assertEqual(os.path.normpath(resolved), os.path.normpath(expected))
                self.assertTrue(os.path.isfile(resolved), resolved)

    def test_absolute_target_still_resolves(self):
        """openpyxl-style absolute Targets keep working unchanged."""
        rels_tree = ET.parse(self.rels_path())
        for rel in rels_tree.getroot():
            if rel.get("Target") == "worksheets/sheet1.xml":
                rel.set("Target", "/xl/worksheets/sheet1.xml")
        rels_tree.write(self.rels_path(), encoding="unicode", xml_declaration=False)
        resolved = xlsx_insert_row.find_ws_path(self.work, None)
        expected = os.path.join(self.work, "xl", "worksheets", "sheet1.xml")
        self.assertEqual(os.path.normpath(resolved), os.path.normpath(expected))
        self.assertTrue(os.path.isfile(resolved), resolved)

    def test_named_sheet_resolution(self):
        resolved = xlsx_insert_row.find_ws_path(self.work, "Sheet1")
        expected = os.path.join(self.work, "xl", "worksheets", "sheet1.xml")
        self.assertEqual(os.path.normpath(resolved), os.path.normpath(expected))

    def test_documented_template_flow_insert_row(self):
        """references/create.md's flow: copy the template, insert a row.

        Before the fix this crashed with FileNotFoundError before doing
        any work.
        """
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "xlsx_insert_row.py"),
                self.work,
                "--at",
                "2",
                "--text",
                "A=hello",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        with open(
            os.path.join(self.work, "xl", "sharedStrings.xml"), encoding="utf-8"
        ) as handle:
            self.assertIn("hello", handle.read())

    def test_documented_template_flow_add_column(self):
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "xlsx_add_column.py"),
                self.work,
                "--col",
                "C",
                "--header",
                "Total",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        # the template sheet is empty, so the header lands in the shared
        # strings table (0 cells added); the point is the script runs to
        # completion instead of FileNotFoundError on the worksheet path
        with open(
            os.path.join(self.work, "xl", "sharedStrings.xml"), encoding="utf-8"
        ) as handle:
            self.assertIn("Total", handle.read())


if __name__ == "__main__":
    unittest.main()
