#!/usr/bin/env python3
"""Record-integrity regressions; fixtures contain no learner-study evidence."""

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from validate_storyboard_review import CONTRACT, validate


ROOT = Path(__file__).resolve().parent.parent


class StoryboardReviewContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="storyboard-record-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "storyboard.md"
        self.source.write_text("First object.\nSecond action.\n", encoding="utf-8")
        evidence = {"unit_identifier": "shot_a", "start_line": 1,
                    "end_line": 1, "quote": "First object."}
        self.record = {
            "contract_version": "1.0", "review_kind": "author_self_review",
            "reviewer": "Fixture author; self-review",
            "source": {"path": "storyboard.md", "sha256": hashlib.sha256(self.source.read_bytes()).hexdigest()},
            "scope": {"kind": "whole_storyboard", "units": [
                {"identifier": "shot_a", "start_line": 1, "end_line": 2}]},
            "reviewed_unit_identifiers": ["shot_a"],
            "dimensions": [{"identifier": identifier, "status": "present_in_text",
                            "unit_identifiers": ["shot_a"], "evidence": [copy.deepcopy(evidence)],
                            "observation": "Synthetic text observation."}
                           for identifier in CONTRACT["dimension_identifiers"]],
            "participation_checks": [],
            "participation_check_not_applicable_reason": "Explicit observation; no response promise.",
            "limitations": ["Fixture text only; no media or learners."],
            **CONTRACT["fixed_fields"]
        }

    def check(self, error=None):
        errors = validate(self.record, self.root)
        if error is None:
            self.assertEqual(errors, [])
        else:
            self.assertTrue(any(error in item for item in errors), errors)

    def test_valid_observation_route(self):
        self.record["dimensions"][3]["status"] = "not_applicable"
        self.check()

    def test_external_courseware_reference_route_is_reachable(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        review = (ROOT / "references/storyboard-review.md").read_text(encoding="utf-8")
        library = ROOT / "references/external-courseware-reference-library.md"
        pointer = "external-courseware-reference-library.md"
        self.assertIn(pointer, skill)
        self.assertIn(pointer, review)
        content = library.read_text(encoding="utf-8")
        self.assertIn("https://www.feixianglaoshi.com/#/home?tab=app-plaza", content)
        self.assertIn("catalog_only", content)
        self.assertIn("小满食堂-指挥机器人送餐", content)

    def test_issue_record_is_valid_without_acceptance(self):
        self.record["dimensions"][0]["status"] = "issue"
        self.check()

    def test_independent_review_enum_is_supported(self):
        self.record["review_kind"] = "independent_text_review"
        self.check()

    def test_old_version_is_not_new_pass(self):
        self.record["contract_version"] = "0.9"
        self.check("unsupported contract_version")

    def test_missing_required_field(self):
        del self.record["limitations"]
        self.check("missing=")

    def test_unknown_acceptance_field(self):
        self.record["story_passed"] = True
        self.check("unknown=")

    def test_no_aggregate_semantic_acceptance(self):
        self.record["semantic_acceptance"] = "accepted"
        self.check("requires not_computed")

    def test_no_media_or_learner_claims(self):
        for key in ("media_evaluation", "learner_evaluation"):
            with self.subTest(key=key):
                value = self.record[key]
                self.record[key] = "passed"
                self.check("requires not_run")
                self.record[key] = value

    def test_stale_source_is_rejected(self):
        self.source.write_text("Different object.\nSecond action.\n", encoding="utf-8")
        self.check("stale binding")

    def test_empty_hash(self):
        self.record["source"]["sha256"] = ""
        self.check("invalid hash")

    def test_missing_source(self):
        self.record["source"]["path"] = "missing.md"
        self.check("cannot read")

    def test_path_escape(self):
        self.record["source"]["path"] = "../outside.md"
        self.check("inside review root")

    def test_symlink_escape(self):
        with tempfile.TemporaryDirectory(prefix="storyboard-outside-") as outside:
            other = Path(outside) / "outside.md"
            other.write_text("Outside.", encoding="utf-8")
            (self.root / "link.md").symlink_to(other)
            self.record["source"]["path"] = "link.md"
            self.check("inside review root")

    def test_empty_scope(self):
        self.record["scope"]["units"] = []
        self.check("must be non-empty")

    def test_whole_scope_cannot_omit_text(self):
        self.record["scope"]["units"][0]["end_line"] = 1
        self.check("omits non-empty")

    def test_selected_scope_can_be_partial(self):
        self.record["scope"]["kind"] = "selected_units"
        self.record["scope"]["units"][0]["end_line"] = 1
        self.check()

    def test_overlapping_unit_ranges(self):
        self.record["scope"]["units"].append(
            {"identifier": "shot_b", "start_line": 2, "end_line": 2})
        self.check("overlapping")

    def test_bool_is_not_line_number(self):
        self.record["scope"]["units"][0]["start_line"] = True
        self.check("invalid line range")

    def test_unreviewed_unit(self):
        self.record["reviewed_unit_identifiers"] = []
        self.check("must equal selected")

    def test_dimension_missing_or_duplicated(self):
        self.record["dimensions"][1] = copy.deepcopy(self.record["dimensions"][0])
        self.check("each contract dimension exactly once")

    def test_unknown_dimension_status(self):
        self.record["dimensions"][0]["status"] = "immersive"
        self.check("unsupported status")

    def test_quote_required_for_judgment(self):
        self.record["dimensions"][0]["evidence"] = []
        self.check("requires unit and quote")

    def test_fabricated_quote(self):
        self.record["dimensions"][0]["evidence"][0]["quote"] = "Invented action."
        self.check("quote absent")

    def test_quote_from_wrong_line(self):
        self.record["dimensions"][0]["evidence"][0]["quote"] = "Second action."
        self.check("quote absent")

    def test_unknown_unit_reference(self):
        self.record["dimensions"][0]["unit_identifiers"] = ["missing"]
        self.check("unknown unit reference")

    def test_placeholder_is_rejected(self):
        self.record["reviewer"] = "{{reviewer}}"
        self.check("unresolved placeholder")

    def add_walk(self):
        self.record["participation_check_not_applicable_reason"] = None
        self.record["participation_checks"] = [{
            "unit_identifier": "shot_a", "promise": "Choose a marker.",
            "inputs": [
                {"input": "A", "visible_result": "Marker A", "next_unit_identifier": "shot_a", "return_state": "A kept"},
                {"input": "B", "visible_result": "Marker B", "next_unit_identifier": "shot_a", "return_state": "B kept"}],
            "observation": "Fixture walk, not browser evidence."
        }]

    def test_two_input_walk(self):
        self.add_walk()
        self.check()

    def test_identical_results_can_document_a_semantic_failure(self):
        self.add_walk()
        self.record["participation_checks"][0]["inputs"][1]["visible_result"] = "Marker A"
        self.record["participation_checks"][0]["observation"] = "Same result contradicts response promise."
        self.check()

    def test_same_input_is_not_two_walks(self):
        self.add_walk()
        self.record["participation_checks"][0]["inputs"][1]["input"] = "A"
        self.check("different inputs")

    def test_missing_second_walk(self):
        self.add_walk()
        self.record["participation_checks"][0]["inputs"].pop()
        self.check("exactly two")

    def test_walk_unknown_next_unit(self):
        self.add_walk()
        self.record["participation_checks"][0]["inputs"][0]["next_unit_identifier"] = "missing"
        self.check("unknown next unit")

    def test_no_walk_requires_reason(self):
        self.record["participation_check_not_applicable_reason"] = None
        self.check("non-empty text")

    def test_malformed_collections_report_errors(self):
        for field in ("dimensions", "participation_checks", "limitations"):
            with self.subTest(field=field):
                original = self.record[field]
                self.record[field] = {}
                self.check("must be a list")
                self.record[field] = original

    def test_cli_preserves_failure_exit_status(self):
        self.record["semantic_acceptance"] = "accepted"
        path = self.root / "review.json"
        path.write_text(json.dumps(self.record), encoding="utf-8")
        command = [sys.executable, str(Path(__file__).with_name("validate_storyboard_review.py")),
                   "--review", str(path), "--root", str(self.root)]
        result = subprocess.run(command, text=True, capture_output=True)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(json.loads(result.stdout)["record_valid"])


if __name__ == "__main__":
    unittest.main()
