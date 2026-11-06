#!/usr/bin/env python3
"""Isolated declaration regressions; synthetic material, no learner or browser evidence."""

import argparse
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

from validate_assessment_integrity import validate

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    results = []

    def check(name, data, base, expected=None, reviewed=False):
        errors = validate(data, base, reviewed)
        assert not errors if expected is None else any(expected in error for error in errors), (
            name, errors)
        results.append({"case": name, "status": "passed", "expected_error": expected})

    with tempfile.TemporaryDirectory(prefix="assessment-integrity-regression-") as folder:
        base = Path(folder)
        material = base / "materials.md"
        material.write_text("BASELINE conditions A\nNEW conditions B\nRUBRIC criteria\n"
                            "REVIEW synthetic review\nCALIBRATION synthetic record\n")
        fingerprint = hashlib.sha256(material.read_bytes()).hexdigest()
        data = json.loads((ROOT / "assets/assessment-integrity.template.json").read_text())
        data["course_version"] = "fixture-v1"
        for row, anchor in zip(data["evidence_files"], ("BASELINE", "NEW", "RUBRIC")):
            row.update(path=material.name, course_version="fixture-v1",
                       content_sha256=fingerprint, anchor=anchor)
        task = data["tasks"][0]
        contrast = task["transfer_contrast"]
        contrast.update(invariant_target="Explain the same relation",
                        required_reasoning_adjustment="Use altered evidence")
        contrast["changed_dimensions"] = [{"kind": "condition", "before": "A", "after": "B"}]
        check("single_group_draft", data, base)
        second = copy.deepcopy(task)
        second.update(task_identifier="task_second", first_response_items=["second_reason"],
                      answer_related_task_identifiers=["task_new"])
        task["answer_related_task_identifiers"] = ["task_second"]
        data["tasks"].append(second)
        data["assessment_groups"][0]["task_identifiers"].append("task_second")
        check("related_tasks_share_lock", data, base)
        recheck = copy.deepcopy(task)
        recheck.update(task_identifier="task_recheck", kind="post_feedback_recheck",
                       first_response_items=["recheck_reason"], answer_related_task_identifiers=[])
        data["tasks"].append(recheck)
        check("recheck_is_separate_result", data, base)
        check("review_is_not_implied", data, base, "transfer review is pending", True)

        def group(d):
            return d["assessment_groups"][0]

        mutations = [
            ("per_task_feedback", lambda d: group(d).update(feedback_release="task_first_response_saved"),
             "all group first responses"),
            ("split_related_group", lambda d: d["assessment_groups"].append(
                dict(copy.deepcopy(group(d)), group_identifier="other", task_identifiers=["task_second"]))
             or group(d).update(task_identifiers=["task_new"]), "share a feedback group"),
            ("recheck_as_independent", lambda d: group(d)["task_identifiers"].append("task_recheck"),
             "must be an independent task"),
            ("same_material", lambda d: d["tasks"][0]["transfer_contrast"].update(
                baseline_reference="material_new"), "distinct materials"),
            ("material_alias", lambda d: d["evidence_files"][0].update(anchor="NEW"), "aliases"),
            ("wording_only_transfer", lambda d: d["tasks"][0]["transfer_contrast"].update(
                changed_dimensions=[{"kind": "wording", "before": "A", "after": "B"}]),
             "substantive dimension"),
            ("unchanged_condition", lambda d: d["tasks"][0]["transfer_contrast"].update(
                changed_dimensions=[{"kind": "condition", "before": " A ", "after": "a"}]),
             "distinct before/after"),
            ("no_reasoning_change", lambda d: d["tasks"][0]["transfer_contrast"].update(
                required_reasoning_adjustment=""), "required_reasoning_adjustment"),
            ("unknown_baseline", lambda d: d["tasks"][0]["transfer_contrast"].update(
                baseline_reference="missing"), "unknown evidence reference"),
            ("stale_binding", lambda d: d["evidence_files"][0].update(content_sha256="0"*64),
             "stale evidence fingerprint"),
            ("stale_version", lambda d: d["evidence_files"][0].update(course_version="old"),
             "stale evidence course_version"),
            ("missing_anchor", lambda d: d["evidence_files"][0].update(anchor="NOT PRESENT"),
             "anchor not found"),
            ("keyword_mastery", lambda d: d["result_policy"].update(open_response_keyword_scoring=True),
             "open_response_keyword_scoring"),
            ("self_mastery", lambda d: d["result_policy"].update(self_assessment_can_promote_mastery=True),
             "self_assessment_can_promote_mastery"),
            ("missing_becomes_valid", lambda d: d["result_policy"].update(
                missing_is_valid_independent_evidence=True), "missing_is_valid_independent_evidence"),
            ("recheck_relabels_first", lambda d: d["result_policy"].update(
                recheck_can_relabel_original_independent=True), "recheck_can_relabel"),
            ("overwrite_first", lambda d: d["result_policy"].update(
                revision_overwrites_first_response=True), "revision_overwrites"),
            ("open_deterministic", lambda d: d["tasks"][0].update(evaluator="deterministic"),
             "cannot judge open input"),
            ("open_auto_established", lambda d: d["tasks"][0].update(initial_evaluation_state="mastered"),
             "initial_evaluation_state"),
            ("uncalibrated_ai", lambda d: d["tasks"][0].update(evaluator="validated_ai"),
             "calibration_reference"),
            ("shared_response_identifier", lambda d: d["tasks"][1].update(
                first_response_items=["response_reason"]), "overlap"),
            ("malformed_task", lambda d: d["tasks"].append(None), "row must be an object"),
            ("malformed_contrast", lambda d: d["tasks"][0].update(transfer_contrast=[]),
             "unknown evidence reference"),
            ("boolean_transfer_required", lambda d: d["tasks"][0].update(transfer_required="false"),
             "must be boolean"),
            ("no_group", lambda d: group(d).update(task_identifiers=["task_second"]),
             "missing assessment group"),
            ("answers_as_resources", lambda d: group(d)["resource_policy"]["allowed_before_release"].append(
                "prior_answer_content"), "answer-revealing pre-release resource"),
            ("empty_contract", lambda d: d.clear(), "schema_version"),
        ]
        for name, edit, expected in mutations:
            bad = copy.deepcopy(data)
            edit(bad)
            check(name, bad, base, expected)
        for key in ("requires_durable_write", "first_responses_immutable",
                    "write_failure_keeps_locked", "explicit_missing_record_required"):
            bad = copy.deepcopy(data)
            group(bad)["persistence_policy"][key] = False
            check("missing_" + key, bad, base, key)
        for key in ("knowledge_help_marks_entire_group_assisted", "persist_assistance_before_reveal"):
            bad = copy.deepcopy(data)
            group(bad)["resource_policy"][key] = False
            check("missing_" + key, bad, base, key)
        for route in ("refresh", "close_reopen", "deep_link", "prior_answer_content", "clear_continue"):
            bad = copy.deepcopy(data)
            group(bad)["recovery_policy"]["guarded_routes"].remove(route)
            check("unguarded_" + route, bad, base, "incomplete")
        bad = copy.deepcopy(data)
        group(bad)["recovery_policy"]["missing_corrupt_or_stale_state"] = "open"
        check("corrupt_state_opens_feedback", bad, base, "remain locked")
        bad = copy.deepcopy(data)
        group(bad)["recovery_policy"]["retain_answer_exposure_on_clear_continue"] = False
        check("clear_erases_exposure", bad, base, "retain_answer_exposure")
        stable = copy.deepcopy(data)
        for row in stable["tasks"]:
            row.update(transfer_required=False, transfer_not_required_reason="Stable classification goal",
                       input_kind="deterministic", evaluator="deterministic",
                       initial_evaluation_state="unscored")
            row.pop("transfer_contrast")
            row.pop("transfer_review")
        check("non_transfer_goal_allowed", stable, base, reviewed=True)
        with_tool = copy.deepcopy(data)
        group(with_tool)["resource_policy"]["declared_normal_resources"] = [{
            "resource_identifier": "normal_tool", "evidence_reference": "rubric",
            "allowed_use": "Use the course-declared tool while explaining its result independently"}]
        check("target_declared_normal_tool", with_tool, base)
        group(with_tool)["resource_policy"]["declared_normal_resources"][0]["evidence_reference"] = "missing"
        check("unbound_normal_tool", with_tool, base, "unknown evidence reference")
        for row in data["tasks"]:
            row["transfer_review"] = {"status": "reviewed", "reviewer": "Synthetic fixture reviewer",
                                     "course_version": "fixture-v1", "evidence_reference": "fixture_review"}
        data["evidence_files"].append(dict(data["evidence_files"][0],
                                          reference_identifier="fixture_review", anchor="REVIEW"))
        check("reviewed_fixture_bindings", data, base, reviewed=True)
        material.write_text(material.read_text() + "changed")
        check("reviewed_bytes_changed", data, base, "stale evidence fingerprint", True)
        material.write_text(material.read_text().removesuffix("changed"))
        document = base / "assessment.json"
        document.write_text(json.dumps(data))
        result = subprocess.run([sys.executable, str(ROOT / "scripts/validate_assessment_integrity.py"),
                                 str(document), "--require-reviewed"], capture_output=True, text=True)
        assert result.returncode == 0, result.stdout + result.stderr
        results.append({"case": "real_reviewed_cli", "status": "passed"})
        group(data)["feedback_release"] = "task_first_response_saved"
        document.write_text(json.dumps(data))
        result = subprocess.run([sys.executable, str(ROOT / "scripts/validate_assessment_integrity.py"),
                                 str(document)], capture_output=True, text=True)
        assert result.returncode == 1 and "all group first responses" in result.stdout, result
        results.append({"case": "real_negative_cli", "status": "passed"})
    report = {"passed": len(results), "cases": results,
              "limits": "Synthetic static contract checks; no semantics, teacher approval, runtime lock or learner results."}
    if args.output:
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
