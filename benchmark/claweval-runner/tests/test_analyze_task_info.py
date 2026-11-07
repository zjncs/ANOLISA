# Copyright 2026 Alibaba Cloud
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""load_task_info must tolerate null and scalar shapes in task.yaml.

A bare YAML key (``prompt:``) parses as null and a plain scalar
(``prompt: do the thing``) parses as a string; both are valid YAML for a
field the report treats as a mapping. Before the fix each shape crashed
the whole analyze run with a bare AttributeError/TypeError instead of
producing the report.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "analyze.py"


@pytest.fixture(scope="module")
def script_mod():
    spec = importlib.util.spec_from_file_location("test_analyze_task_info", SCRIPT_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["test_analyze_task_info"] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _write_task(tasks_dir: Path, task_id: str, yaml_text: str) -> None:
    task_dir = tasks_dir / task_id
    task_dir.mkdir(parents=True)
    (task_dir / "task.yaml").write_text(yaml_text, encoding="utf-8")


def test_null_prompt_and_reference_do_not_crash(script_mod, tmp_path):
    _write_task(
        tmp_path,
        "t1",
        "task_id: t1\ntask_name: T\nprompt:\nreference_solution:\n",
    )
    info = script_mod.load_task_info("t1", str(tmp_path))
    assert info["prompt"] == ""
    assert info["reference_solution"] == ""
    assert info["task_name"] == "T"


def test_scalar_prompt_is_used_as_text(script_mod, tmp_path):
    _write_task(tmp_path, "t2", "task_id: t2\nprompt: do the thing\n")
    info = script_mod.load_task_info("t2", str(tmp_path))
    assert info["prompt"] == "do the thing"


def test_canonical_prompt_mapping_unchanged(script_mod, tmp_path):
    _write_task(
        tmp_path,
        "t3",
        "task_id: t3\n"
        "prompt:\n"
        "  text: solve the task now\n"
        "scoring_components:\n"
        "  - correctness\n"
        "judge_rubric: rubric text\n"
        "primary_dimensions:\n"
        "  - depth\n",
    )
    info = script_mod.load_task_info("t3", str(tmp_path))
    assert info["prompt"] == "solve the task now"
    assert info["scoring_components"] == ["correctness"]
    assert info["judge_rubric"] == "rubric text"
    assert info["primary_dimensions"] == ["depth"]


def test_null_list_and_text_fields_coerced(script_mod, tmp_path):
    _write_task(
        tmp_path,
        "t4",
        "task_id: t4\ntask_name:\nscoring_components:\njudge_rubric:\n",
    )
    info = script_mod.load_task_info("t4", str(tmp_path))
    assert info["task_name"] == ""
    assert info["scoring_components"] == []
    assert info["judge_rubric"] == ""
    # missing task.yaml keeps the existing not-found contract
    missing = script_mod.load_task_info("absent", str(tmp_path))
    assert missing == {"task_id": "absent", "error": "task.yaml not found"}


def test_long_prompt_and_reference_truncated(script_mod, tmp_path):
    _write_task(
        tmp_path,
        "t5",
        "task_id: t5\n"
        "prompt:\n  text: " + "p" * 500 + "\n"
        "reference_solution: " + "r" * 500 + "\n",
    )
    info = script_mod.load_task_info("t5", str(tmp_path))
    assert len(info["prompt"]) == 300
    assert len(info["reference_solution"]) == 300
