#!/usr/bin/env python3
"""Regression probes for the instructional-cycle blueprint extension."""

import copy
import json
import re
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


class InstructionalCycleContractTests(unittest.TestCase):
    def setUp(self):
        self.data = filled_fixture(json.loads(
            (ROOT / "assets/course-blueprint.template.json").read_text(encoding="utf-8")))

    def check(self, expected=None, **options):
        errors = validate(self.data, ROOT, **options)
        if expected is None:
            self.assertEqual(errors, [])
        else:
            self.assertTrue(any(expected in error for error in errors), errors)

    def plan(self):
        return self.data["instructional_design"]["objective_plans"][0]

    def test_complete_extension(self):
        self.check(instructional_cycle=True)

    def test_missing_whole_task_output(self):
        self.data["instructional_design"]["whole_task"]["learner_output"] = ""
        self.check("whole_task missing learner_output")

    def test_invalid_sequencing_strategy(self):
        self.data["instructional_design"]["whole_task"]["sequencing_strategy"] = "always_discover"
        self.check("invalid sequencing_strategy")

    def test_non_string_decisions_return_validation_errors(self):
        self.plan()["demonstration"]["decision"] = []
        self.plan()["articulation_and_reflection"]["decision"] = {}
        self.check("demonstration invalid decision")
        self.check("articulation_and_reflection invalid decision")

    def test_whole_task_presentation_must_be_required(self):
        self.data["scenes"][0]["required"] = False
        self.check("presentation scene must be required")

    def test_demonstration_requires_content(self):
        self.plan()["demonstration"]["content"] = ""
        self.check("demonstration missing content")

    def test_demonstration_not_required_needs_no_scene(self):
        demonstration = self.plan()["demonstration"]
        demonstration["decision"] = "not_required"
        self.check("not_required must not list scenes")

    def test_demonstration_not_required_is_allowed_with_rationale(self):
        demonstration = self.plan()["demonstration"]
        demonstration["decision"] = "not_required"
        demonstration["scene_identifiers"] = []
        demonstration["content"] = ""
        self.check(instructional_cycle=True)

    def test_demonstration_must_use_teaching_scene(self):
        self.plan()["demonstration"]["scene_identifiers"] = ["scene_practice"]
        self.check("requires a linked teaching scene")

    def test_guided_practice_must_be_practice(self):
        self.plan()["guided_practice_task_identifiers"] = ["task_transfer"]
        self.check("guided practice requires a linked practice task")

    def test_independent_application_must_be_transfer(self):
        self.plan()["independent_task_identifiers"] = ["task_practice"]
        self.check("independent application requires a linked transfer task")

    def test_reflection_prompt_is_required_when_embedded(self):
        self.plan()["articulation_and_reflection"]["prompt"] = ""
        self.check("articulation_and_reflection missing prompt")

    def test_reflection_not_required_is_allowed_with_rationale(self):
        reflection = self.plan()["articulation_and_reflection"]
        reflection["decision"] = "not_required"
        reflection["task_identifiers"] = []
        reflection["prompt"] = ""
        self.check(instructional_cycle=True)

    def test_reflection_task_must_cover_objective(self):
        second = copy.deepcopy(self.data["learning_objectives"][0])
        second["objective_identifier"] = "objective_second"
        self.data["learning_objectives"].append(second)
        self.plan()["articulation_and_reflection"]["task_identifiers"] = ["task_transfer"]
        self.plan()["objective_identifier"] = "objective_second"
        self.check("articulation task does not cover objective")

    def test_task_cannot_bypass_whole_task_presentation(self):
        whole_task = self.data["instructional_design"]["whole_task"]
        whole_task["presentation_scene_identifier"] = "scene_instruction"
        self.data["scenes"][0]["next_scene_identifier"] = "scene_practice"
        self.check("task can be reached before whole-task presentation")

    def test_legacy_instruction_remains_compatible(self):
        instruction = self.data["instructional_design"]
        del instruction["contract_version"]
        del instruction["whole_task"]
        for plan in instruction["objective_plans"]:
            for key in (
                    "demonstration", "guided_practice_task_identifiers",
                    "independent_task_identifiers", "application_conditions",
                    "articulation_and_reflection"):
                del plan[key]
        self.check(learning_design=True)
        self.check("contract_version must be 1.0", instructional_cycle=True)


if __name__ == "__main__":
    unittest.main()
