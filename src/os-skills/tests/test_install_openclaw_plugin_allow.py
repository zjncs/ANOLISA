#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Tests for install_openclaw.py merge_plugin_allow shape tolerance.

Both configs come from user-editable JSON. Before the fix:
- "plugins": null on either side crashed apply_config with a bare
  AttributeError (None.get);
- a non-list "allow" (the string "all") silently spread into
  per-character entries, corrupting the written config.
"""

import sys
import unittest
from pathlib import Path

sys.dont_write_bytecode = True

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "ai" / "install-openclaw" / "scripts"),
)
import install_openclaw as m  # noqa: E402


class MergePluginAllowTests(unittest.TestCase):
    def test_canonical_merge_dedupes_and_orders(self):
        merged = m.merge_plugin_allow(
            {"plugins": {"allow": ["a", "b"]}},
            {"plugins": {"allow": ["b", "c"]}},
        )
        self.assertEqual(merged["plugins"]["allow"], ["a", "b", "c"])

    def test_null_existing_plugins_no_crash(self):
        merged = m.merge_plugin_allow(
            {"plugins": None}, {"plugins": {"allow": ["a"]}}
        )
        self.assertEqual(merged["plugins"]["allow"], ["a"])

    def test_null_merged_plugins_no_crash(self):
        merged = m.merge_plugin_allow(
            {"plugins": {"allow": ["a"]}}, {"plugins": None, "other": 1}
        )
        self.assertIsNone(merged["plugins"])
        self.assertEqual(merged["other"], 1)

    def test_string_allow_not_char_spread(self):
        merged = m.merge_plugin_allow(
            {"plugins": {"allow": ["a"]}}, {"plugins": {"allow": "bc"}}
        )
        # a non-list allow has nothing to concatenate: it is left exactly
        # as the deep merge produced it, never spread into characters
        self.assertEqual(merged["plugins"]["allow"], "bc")

    def test_missing_plugins_sides(self):
        merged = m.merge_plugin_allow({}, {"plugins": {"allow": ["x"]}})
        self.assertEqual(merged["plugins"]["allow"], ["x"])
        merged = m.merge_plugin_allow({"plugins": {"allow": ["y"]}}, {})
        self.assertEqual(merged, {})

    def test_falsy_allow_entries_dropped(self):
        # ordered_unique skips falsy entries; the contract is preserved
        merged = m.merge_plugin_allow(
            {"plugins": {"allow": ["", None]}},
            {"plugins": {"allow": ["z"]}},
        )
        self.assertEqual(merged["plugins"]["allow"], ["z"])


if __name__ == "__main__":
    unittest.main()
