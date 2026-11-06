#!/usr/bin/env python3
"""Synthetic opening contract regressions; never runtime or learner-study evidence."""

import copy
import json
from pathlib import Path
import re
import subprocess
import sys
import unittest

from opening_contract import OPENING_EXTENSION_FIELDS
from validate_course import validate


ROOT = Path(__file__).resolve().parents[1]


def fill(value):
    if isinstance(value, str):
        return re.sub(r"\{\{.*?\}\}", "Synthetic opening text", value)
    if isinstance(value, list):
        return [fill(item) for item in value]
    if isinstance(value, dict):
        return {key: fill(item) for key, item in value.items()}
    return value


class OpeningContractChecks(unittest.TestCase):
    def setUp(self):
        self.data = fill(json.loads((ROOT / "assets/course-blueprint.template.json").read_text()))
        self.opening = self.data["opening"]

    def check(self, expected=None, **options):
        errors = validate(self.data, ROOT, **options)
        if expected is None:
            self.assertEqual(errors, [])
        else:
            self.assertTrue(any(expected in error for error in errors), errors)

    def unit(self):
        return self.opening["information_units"][1]

    def legacy(self):
        for key in OPENING_EXTENSION_FIELDS:
            self.opening.pop(key, None)

    def inherit(self, mode="embedded"):
        self.opening["entry_mode"] = mode
        self.unit().update(
            delivery="inherited", presentation_event="verified_prior_context",
            content_reference="inherited_context.content",
            inherited_context={
                "course_identifier": "parent_course", "course_version": "previous_version",
                "presentation_reference": "parent introduction event",
                "content": "Actual previously presented background text",
                "replay_reference": "local background replay",
            })

    def test_new_contract_and_learning_design(self):
        self.check(opening_design=True, learning_design=True)

    def test_old_one_two_remains_compatible(self):
        self.legacy()
        self.check(learning_design=True)
        self.check("contract_version must be 1.0, 1.1 or 1.2", opening_design=True)

    def test_old_one_one_remains_compatible(self):
        self.legacy()
        self.data["schema_version"] = "1.1"
        self.check(complete_design=True)

    def test_basic_one_zero_does_not_claim_new_opening(self):
        self.data["schema_version"] = "1.0"
        self.check()
        self.check("Opening design checks require schema", opening_design=True)

    def test_extension_cannot_hide_by_removing_version(self):
        del self.opening["contract_version"]
        self.check("contract_version must be 1.0, 1.1 or 1.2")

    def test_unknown_contract_version(self):
        self.opening["contract_version"] = "future"
        self.check("contract_version must be 1.0, 1.1 or 1.2")

    def test_contract_one_zero_remains_compatible(self):
        self.opening["contract_version"] = "1.0"
        del self.opening["experience_entry"]
        del self.opening["orientation_bootstrap"]
        self.check(opening_design=True)

    def test_contract_one_one_requires_experience_entry(self):
        self.opening["contract_version"] = "1.1"
        del self.opening["experience_entry"]
        self.check("experience_entry must be an object")

    def test_contract_one_one_requires_entry_fields(self):
        self.opening["contract_version"] = "1.1"
        self.opening["experience_entry"]["first_consequential_action"] = ""
        self.check("experience_entry missing first_consequential_action")

    def test_contract_one_one_rejects_unknown_intensity(self):
        self.opening["contract_version"] = "1.1"
        self.opening["experience_entry"]["intensity"] = "cinematic"
        self.check("experience_entry.intensity must be compact, standard or extended")

    def test_contract_one_one_remains_compatible_without_orientation_bootstrap(self):
        self.opening["contract_version"] = "1.1"
        del self.opening["orientation_bootstrap"]
        self.check(opening_design=True)

    def test_contract_one_two_requires_orientation_bootstrap(self):
        del self.opening["orientation_bootstrap"]
        self.check("orientation_bootstrap must be an object")

    def test_contract_one_two_requires_orientation_fields(self):
        self.opening["orientation_bootstrap"]["minimal_world_model"] = ""
        self.check("orientation_bootstrap missing minimal_world_model")

    def test_contract_one_two_requires_orientation_purposes(self):
        for unit in self.opening["information_units"]:
            if "world_model" in unit["purposes"]:
                unit["purposes"].remove("world_model")
        self.check("information_units missing purpose: world_model")

    def test_course_title_does_not_replace_introduction(self):
        self.opening["course_introduction"] = ""
        self.check("missing course_introduction")

    def test_scene_summary_cannot_replace_introduction(self):
        self.opening["course_introduction"] = "Course-specific learner-facing text"
        self.opening["information_units"][0]["content_reference"] = "scene.narration"
        self.check("must present the declared course_introduction")

    def test_empty_information_units(self):
        self.opening["information_units"] = []
        self.check("information_units cannot be empty")

    def test_missing_background_purpose(self):
        self.unit()["purposes"].remove("background")
        self.check("missing purpose: background")

    def test_one_segment_can_cover_multiple_purposes(self):
        self.opening["information_units"] = [self.opening["information_units"][0]]
        self.opening["information_units"][0]["purposes"] = [
            "course_introduction", "host_welcome", "background", "world_model",
            "journey_preview", "problem", "learner_role", "first_action"]
        self.check(opening_design=True)

    def test_unknown_scene(self):
        self.unit()["scene_identifier"] = "unknown_scene"
        self.check("unknown scene_identifier")

    def test_background_after_first_task_is_rejected(self):
        self.unit().update(scene_identifier="scene_transfer", media_resource_identifiers=[])
        self.check("lacks information purpose before first task")

    def test_same_scene_before_task_is_allowed(self):
        self.unit().update(scene_identifier="scene_practice", media_resource_identifiers=[],
                           presentation_event="before_task_open")
        self.check(opening_design=True)

    def test_content_after_task_open_is_rejected(self):
        self.unit()["presentation_event"] = "after_task_open"
        self.check("inline content must precede task opening")

    def test_later_task_cannot_be_declared_first(self):
        self.opening["first_task_identifiers"] = ["task_transfer"]
        self.check("is not a first disciplinary task")

    def test_duplicate_first_task_is_rejected(self):
        self.opening["first_task_identifiers"] *= 2
        self.check("duplicate reference")

    def branch(self):
        alternative = copy.deepcopy(self.data["scenes"][2])
        alternative.update(
            scene_identifier="scene_branch",
            beat_identifiers=["beat_branch"],
            required=False,
        )
        alternative["task"]["task_identifier"] = "task_branch"
        alternative["task"]["outcomes"] = {
            "success": "scene_practice", "needs_help": "scene_branch"}
        self.data["scenes"].append(alternative)
        instruction = self.data["scenes"][1]
        instruction["task"] = copy.deepcopy(self.data["scenes"][2]["task"])
        instruction["task"].update(task_identifier="task_direction", pedagogical_role="orientation")
        instruction["task"]["outcomes"] = {
            "success": "scene_practice", "needs_help": "scene_branch"}
        instruction["next_scene_identifier"] = None

    def test_every_entry_branch_requires_its_first_task(self):
        self.branch()
        self.check("missing entry branch task: task_branch")

    def test_multiple_first_tasks_are_allowed(self):
        self.branch()
        self.opening["first_task_identifiers"].append("task_branch")
        self.check(opening_design=True, learning_design=True)

    def test_mutually_exclusive_branches_may_each_supply_complete_context(self):
        self.branch()
        self.opening["first_task_identifiers"].append("task_branch")
        purposes = [
            "course_introduction", "host_welcome", "background", "world_model",
            "journey_preview", "problem", "learner_role", "first_action",
        ]
        prototype = copy.deepcopy(self.opening["information_units"][0])
        prototype.update(
            purposes=purposes,
            delivery="inline",
            content_reference="opening.course_introduction",
            presentation_event="before_task_open",
            media_resource_identifiers=[],
        )
        first = copy.deepcopy(prototype)
        first.update(information_identifier="branch_a_context", scene_identifier="scene_practice")
        second = copy.deepcopy(prototype)
        second.update(information_identifier="branch_b_context", scene_identifier="scene_branch")
        self.opening["information_units"] = [first, second]
        self.check(opening_design=True, learning_design=True)

    def test_first_task_in_entry_scene_is_detected(self):
        introduction = self.data["scenes"][0]
        introduction["task"] = copy.deepcopy(self.data["scenes"][2]["task"])
        introduction["task"]["task_identifier"] = "task_entry"
        introduction["task"]["outcomes"] = {
            "success": "scene_instruction", "needs_help": "scene_introduction"}
        introduction["next_scene_identifier"] = None
        self.check("missing entry branch task: task_entry")
        self.opening["first_task_identifiers"] = ["task_entry"]
        self.check(opening_design=True)

    def test_unknown_media_reference(self):
        self.unit()["media_resource_identifiers"] = ["unknown_media"]
        self.check("unknown reference: unknown_media")

    def test_media_must_be_linked_to_presentation_scene(self):
        self.unit()["media_resource_identifiers"] = ["diagram_core"]
        self.check("media is not linked to its scene")

    def test_pure_text_opening_needs_no_new_media(self):
        for unit in self.opening["information_units"]:
            unit["media_resource_identifiers"] = []
        self.check(opening_design=True)

    def test_inherited_embedded_background(self):
        self.inherit()
        self.check(opening_design=True)

    def test_inherited_resumed_background(self):
        self.inherit("resumed")
        self.check(opening_design=True)

    def test_standalone_cannot_borrow_unverified_background(self):
        self.inherit("standalone")
        self.check("standalone entry cannot inherit background")

    def test_inherited_background_requires_version_and_replay(self):
        self.inherit()
        del self.unit()["inherited_context"]["course_version"]
        self.check("inherited_context missing course_version")
        del self.unit()["inherited_context"]["replay_reference"]
        self.check("inherited_context missing replay_reference")

    def test_inherited_background_still_requires_local_fallback(self):
        self.inherit()
        self.unit()["equivalent_content"] = ""
        self.check("missing equivalent_content")

    def test_inline_cannot_claim_inherited_context(self):
        self.unit()["inherited_context"] = {"content": "Previously seen"}
        self.check("inline delivery cannot claim inherited_context")

    def test_term_introduction_reference_and_meaning(self):
        self.opening["essential_terms"] = [{
            "term": "P", "meaning": "The protein being tracked in this example",
            "information_identifier": "opening_scenario_context"}]
        self.check(opening_design=True)
        self.opening["essential_terms"][0]["information_identifier"] = "unknown_information"
        self.check("unknown information_identifier")
        self.opening["essential_terms"][0]["meaning"] = ""
        self.check("missing meaning")

    def test_unknown_body_reference(self):
        self.unit()["content_reference"] = "unrelated.design.notes"
        self.check("invalid inline content_reference")

    def test_missing_presentation_binding(self):
        self.unit()["presentation_reference"] = ""
        self.check("missing presentation_reference")

    def test_missing_reentry_policy(self):
        self.opening["reentry_policy"] = ""
        self.check("missing reentry_policy")

    def test_malformed_values_return_errors(self):
        self.opening["entry_mode"] = []
        self.opening["first_task_identifiers"] = [{}]
        self.opening["information_units"] = [None, {
            "information_identifier": [], "purposes": [{}], "delivery": [],
            "scene_identifier": [], "content_reference": {}, "presentation_event": [],
            "media_resource_identifiers": [{}]}]
        self.opening["essential_terms"] = [None, {"term": [], "meaning": {},
                                                 "information_identifier": []}]
        self.check("must be an object")

    def test_template_is_not_a_complete_opening(self):
        self.data = json.loads((ROOT / "assets/course-blueprint.template.json").read_text())
        self.check()
        self.check("unfilled template", opening_design=True)

    def test_cli_strict_and_legacy_paths(self):
        command = [sys.executable, str(ROOT / "scripts/validate_course.py"), "-"]
        result = subprocess.run(command + ["--learning-design", "--opening-design"],
                                input=json.dumps(self.data), capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.legacy()
        result = subprocess.run(command, input=json.dumps(self.data), capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("LEGACY OPENING", result.stdout)
        result = subprocess.run(command + ["--opening-design"], input=json.dumps(self.data),
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn("contract_version must be 1.0, 1.1 or 1.2", result.stdout)


if __name__ == "__main__":
    unittest.main()
