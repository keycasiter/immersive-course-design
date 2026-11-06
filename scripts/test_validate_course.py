#!/usr/bin/env python3
"""Regression fixtures for blueprint contracts; these are not learner-study data."""

import copy
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

from validate_course import validate


ROOT = Path(__file__).resolve().parent.parent


def filled_fixture(value):
    if isinstance(value, str):
        return re.sub(r"\{\{.*?\}\}", "Regression fixture text", value)
    if isinstance(value, list):
        return [filled_fixture(item) for item in value]
    if isinstance(value, dict):
        return {key: filled_fixture(item) for key, item in value.items()}
    return value


class LearningDesignContractTests(unittest.TestCase):
    def setUp(self):
        self.data = filled_fixture(json.loads(
            (ROOT / "assets/course-blueprint.template.json").read_text(encoding="utf-8")))

    def check(self, expected=None, **options):
        errors = validate(self.data, ROOT, **options)
        if expected is None:
            self.assertEqual(errors, [])
        else:
            self.assertTrue(any(expected in error for error in errors), errors)

    def add_unit(self):
        unit = copy.deepcopy(self.data["knowledge_organization"]["units"][0])
        unit["knowledge_identifier"] = "knowledge_second"
        self.data["knowledge_organization"]["units"].append(unit)
        self.data["scope_coverage"]["coverage_map"][0]["knowledge_identifiers"].append(
            "knowledge_second"
        )

    def add_relation(self, source, target, kind="prerequisite"):
        self.data["knowledge_organization"]["relations"].append({
            "from_knowledge_identifier": source,
            "to_knowledge_identifier": target,
            "relation_type": kind,
            "rationale": "Regression relationship"
        })

    def test_complete_learning_design(self):
        self.check(complete_design=True, learning_design=True)

    def test_complete_full_course_coverage(self):
        self.check(full_course=True)

    def test_full_course_requires_scope_coverage(self):
        del self.data["scope_coverage"]
        self.check("Full course requires scope_coverage", full_course=True)

    def test_full_course_rejects_deferred_content(self):
        self.data["scope_coverage"]["deferred_content"] = [{
            "content_identifier": "content_later",
            "reason": "Synthetic deferred content",
        }]
        self.check("cannot defer required content", full_course=True)

    def test_full_course_requires_every_required_beat(self):
        mapping = self.data["scope_coverage"]["coverage_map"][0]
        mapping["beat_identifiers"].remove("beat_summary")
        self.check("omits one or more required Beats", full_course=True)

    def test_full_course_inventory_must_cover_required_objectives(self):
        inventory = self.data["scope_coverage"]["required_content_inventory"][0]
        inventory["objective_identifiers"] = []
        self.check("objective_identifiers must be a non-empty list", full_course=True)

    def test_prior_knowledge_can_have_no_teaching_scene(self):
        self.add_unit()
        unit = self.data["knowledge_organization"]["units"][1]
        unit["assumed_known"] = True
        unit["teaching_scene_identifiers"] = []
        self.check(learning_design=True)

    def test_prerequisite_cycle_is_rejected(self):
        self.add_unit()
        self.add_relation("knowledge_core", "knowledge_second")
        self.add_relation("knowledge_second", "knowledge_core")
        self.check("Prerequisite cycle")

    def test_causal_feedback_cycle_is_allowed(self):
        self.add_unit()
        self.add_relation("knowledge_core", "knowledge_second", "causal")
        self.add_relation("knowledge_second", "knowledge_core", "causal")
        self.check(learning_design=True)

    def test_unknown_knowledge_reference(self):
        self.add_relation("knowledge_core", "unknown_unit")
        self.check("unknown reference: unknown_unit")

    def test_missing_instructional_plan(self):
        self.data["instructional_design"]["objective_plans"] = []
        self.check("Required objective missing instructional plan")

    def test_instruction_cannot_use_opening_as_teaching(self):
        plan = self.data["instructional_design"]["objective_plans"][0]
        plan["teaching_scene_identifiers"] = ["scene_introduction"]
        self.check("requires a required teaching scene")

    def test_duplicate_knowledge_unit(self):
        units = self.data["knowledge_organization"]["units"]
        units.append(copy.deepcopy(units[0]))
        self.check("Duplicate knowledge_identifier")

    def test_missing_formative_checkpoint(self):
        self.data["evaluation_plan"]["formative_assessment"] = []
        self.check("Practice task missing formative checkpoint")

    def test_missing_instructional_action(self):
        rule = self.data["evaluation_plan"]["formative_assessment"][0]["evidence_interpretations"][0]
        rule["instructional_action"] = ""
        self.check("missing instructional_action")

    def test_recheck_must_cover_diagnosed_objective(self):
        transfer = self.data["scenes"][3]
        transfer["objective_identifiers"] = []
        self.check("recheck does not cover objective")

    def test_recheck_cannot_be_orientation(self):
        self.data["scenes"][3]["task"]["pedagogical_role"] = "orientation"
        self.check("recheck requires a learning task")

    def test_rubric_and_conditions_are_required(self):
        del self.data["evaluation_plan"]["objective_evaluations"][0]["rubric_reference"]
        self.check("missing rubric_reference")

    def test_malformed_extension_returns_errors(self):
        self.data["knowledge_organization"]["units"] = [None, []]
        self.data["instructional_design"] = None
        self.data["evaluation_plan"]["formative_assessment"] = [None]
        self.check("must be an object")

    def test_malformed_task_role_returns_errors(self):
        self.data["scenes"][2]["task"]["pedagogical_role"] = []
        self.check("invalid pedagogical_role")

    def test_missing_knowledge_objective_coverage(self):
        self.data["knowledge_organization"]["units"] = []
        self.check("Required objective missing knowledge unit")

    def test_integration_must_cover_required_objectives(self):
        self.data["knowledge_organization"]["integration_task_identifiers"] = []
        self.check("Required objective missing integration task")

    def test_version_one_one_remains_compatible(self):
        self.data["schema_version"] = "1.1"
        del self.data["knowledge_organization"]
        del self.data["instructional_design"]
        del self.data["evaluation_plan"]["formative_assessment"]
        del self.data["evaluation_plan"]["objective_evaluations"][0]["rubric_reference"]
        del self.data["evaluation_plan"]["objective_evaluations"][0]["assessment_conditions"]
        self.check(complete_design=True)
        self.check("require schema 1.2", learning_design=True)

    def test_version_one_zero_remains_basic_only(self):
        self.data["schema_version"] = "1.0"
        self.check()
        self.check("Complete design requires schema", complete_design=True)

    def test_template_is_structural_only(self):
        self.data = json.loads((ROOT / "assets/course-blueprint.template.json").read_text(encoding="utf-8"))
        self.check()
        self.check("unfilled template", learning_design=True)

    def test_cli_stdin_learning_design(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/validate_course.py"), "-", "--learning-design"],
            input=json.dumps(self.data), text=True, capture_output=True, check=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PASS:", result.stdout)

    def test_cli_stdin_full_course(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/validate_course.py"), "-", "--full-course"],
            input=json.dumps(self.data), text=True, capture_output=True, check=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PASS:", result.stdout)


if __name__ == "__main__":
    unittest.main()
