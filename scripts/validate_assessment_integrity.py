#!/usr/bin/env python3
"""Check assessment declarations and file bindings; not semantics or runtime locks."""

import argparse
import hashlib
import json
from pathlib import Path
import re

RELEASE = "all_group_first_responses_persisted_or_assisted"
ROUTES = {
    "feedback", "rubric", "knowledge_help", "prior_answer_content", "summary",
    "refresh", "close_reopen", "deep_link", "history", "clear_continue",
}
DIMENSIONS = {"condition", "data", "evidence", "constraint", "representation", "object_property"}


def validate(data, base, require_reviewed=False):
    errors = []
    if not isinstance(data, dict):
        return ["assessment integrity must be an object"]

    def text(value):
        return isinstance(value, str) and bool(value.strip())

    def strings(value, label, nonempty=True):
        if not isinstance(value, list) or (nonempty and not value) or any(
                not text(item) for item in value):
            errors.append(f"{label}: requires a list of non-empty strings")
            return []
        if len(set(value)) != len(value):
            errors.append(f"{label}: duplicate identifiers")
        return value

    def rows(value, label):
        if not isinstance(value, list) or not value:
            errors.append(f"{label}: requires a non-empty list")
            return []
        result = []
        for row in value:
            if not isinstance(row, dict):
                errors.append(f"{label}: row must be an object")
            else:
                result.append(row)
        return result

    def reference(value, label):
        if not text(value) or value not in evidence:
            errors.append(f"{label}: unknown evidence reference")
            return False
        return True

    def flags(row, names, label, expected=True):
        row = row if isinstance(row, dict) else {}
        for name in names:
            if row.get(name) is not expected:
                errors.append(f"{label}.{name}: must be {str(expected).lower()}")

    if data.get("schema_version") != "1.0":
        errors.append("schema_version must be 1.0")
    version = data.get("course_version")
    if not text(version):
        errors.append("course_version is required")
    evidence = {}
    for row in rows(data.get("evidence_files"), "evidence_files"):
        identifier = row.get("reference_identifier")
        if not text(identifier):
            errors.append("evidence_files: reference_identifier is required")
            continue
        if identifier in evidence:
            errors.append("evidence_files: duplicate reference_identifier")
        evidence[identifier] = row
        if row.get("course_version") != version:
            errors.append(f"{identifier}: stale evidence course_version")
        if not text(row.get("anchor")):
            errors.append(f"{identifier}: material anchor is required")
        try:
            if not text(row.get("path")):
                raise ValueError("path is required")
            path = Path(row["path"])
            path = path if path.is_absolute() else Path(base) / path
            content = path.read_bytes()
            fingerprint = hashlib.sha256(content).hexdigest()
            if row.get("content_sha256") != fingerprint:
                errors.append(f"{identifier}: stale evidence fingerprint")
            if text(row.get("anchor")) and row["anchor"] not in content.decode("utf-8"):
                errors.append(f"{identifier}: material anchor not found")
        except (OSError, ValueError, UnicodeError) as exc:
            errors.append(f"{identifier}: unreadable evidence ({exc})")

    tasks = {}
    response_identifiers = set()
    for row in rows(data.get("tasks"), "tasks"):
        identifier = row.get("task_identifier")
        if not text(identifier):
            errors.append("tasks: task_identifier is required")
            continue
        if identifier in tasks:
            errors.append("tasks: duplicate task_identifier")
        tasks[identifier] = row
        if row.get("kind") not in ("independent_assessment", "post_feedback_recheck"):
            errors.append(f"{identifier}: invalid task kind")
        reference(row.get("material_reference"), identifier + ".material_reference")
        reference(row.get("rubric_reference"), identifier + ".rubric_reference")
        responses = strings(row.get("first_response_items"), identifier + ".first_response_items")
        if response_identifiers.intersection(responses):
            errors.append(f"{identifier}: first response items overlap another task")
        response_identifiers.update(responses)
        strings(row.get("answer_related_task_identifiers"),
                identifier + ".answer_related_task_identifiers", False)
        evaluator = row.get("evaluator")
        if evaluator not in ("human", "self_assessment", "deterministic", "validated_ai"):
            errors.append(f"{identifier}: invalid evaluator")
        if row.get("input_kind") not in ("open", "deterministic"):
            errors.append(f"{identifier}: invalid input_kind")
        if evaluator == "deterministic" and row.get("input_kind") != "deterministic":
            errors.append(f"{identifier}: deterministic evaluator cannot judge open input")
        if evaluator == "validated_ai":
            reference(row.get("calibration_reference"), identifier + ".calibration_reference")
        if row.get("initial_evaluation_state") not in (
                "review_pending", "unscored", "self_assessment_pending"):
            errors.append(f"{identifier}: invalid initial_evaluation_state")
        if row.get("input_kind") == "open" and evaluator != "validated_ai" and \
                row.get("initial_evaluation_state") != "review_pending":
            errors.append(f"{identifier}: unvalidated open input must remain review_pending")
        if type(row.get("transfer_required")) is not bool:
            errors.append(f"{identifier}: transfer_required must be boolean")
        if row.get("transfer_required") is False:
            if not text(row.get("transfer_not_required_reason")):
                errors.append(f"{identifier}: transfer_not_required_reason is required")
            continue
        contrast = row.get("transfer_contrast")
        contrast = contrast if isinstance(contrast, dict) else {}
        for key in ("baseline_reference", "current_reference"):
            reference(contrast.get(key), identifier + ".transfer_contrast." + key)
        if contrast.get("baseline_reference") == contrast.get("current_reference"):
            errors.append(f"{identifier}: transfer must reference distinct materials")
        baseline = evidence.get(contrast.get("baseline_reference"), {}) if text(
            contrast.get("baseline_reference")) else {}
        current = evidence.get(contrast.get("current_reference"), {}) if text(
            contrast.get("current_reference")) else {}
        if baseline and current and (baseline.get("path"), baseline.get("anchor")) == (
                current.get("path"), current.get("anchor")):
            errors.append(f"{identifier}: transfer material references are aliases")
        if contrast.get("current_reference") != row.get("material_reference"):
            errors.append(f"{identifier}: transfer current material differs from task material")
        for key in ("invariant_target", "required_reasoning_adjustment"):
            if not text(contrast.get(key)):
                errors.append(f"{identifier}: transfer requires {key}")
        for change in rows(contrast.get("changed_dimensions"), identifier + ".changed_dimensions"):
            if not isinstance(change.get("kind"), str) or change["kind"] not in DIMENSIONS:
                errors.append(f"{identifier}: transfer requires a substantive dimension")
            before, after = change.get("before"), change.get("after")
            if not text(before) or not text(after) or \
                    " ".join(before.split()).casefold() == " ".join(after.split()).casefold():
                errors.append(f"{identifier}: changed dimension must have distinct before/after")
        review = row.get("transfer_review")
        review = review if isinstance(review, dict) else {}
        if review.get("status") not in ("pending", "reviewed"):
            errors.append(f"{identifier}: invalid transfer review status")
        if require_reviewed and review.get("status") != "reviewed":
            errors.append(f"{identifier}: transfer review is pending")
        if review.get("status") == "reviewed":
            if not text(review.get("reviewer")):
                errors.append(f"{identifier}: transfer reviewer is required")
            if review.get("course_version") != version:
                errors.append(f"{identifier}: stale transfer review version")
            reference(review.get("evidence_reference"), identifier + ".transfer_review")

    groups = {}
    membership = {}
    for row in rows(data.get("assessment_groups"), "assessment_groups"):
        identifier = row.get("group_identifier")
        if not text(identifier):
            errors.append("assessment_groups: group_identifier is required")
            continue
        if identifier in groups:
            errors.append("assessment_groups: duplicate group_identifier")
        groups[identifier] = row
        for task in strings(row.get("task_identifiers"), identifier + ".task_identifiers"):
            if task not in tasks or tasks[task].get("kind") != "independent_assessment":
                errors.append(f"{identifier}: group member must be an independent task")
            if task in membership:
                errors.append(f"{task}: independent task occurs in multiple groups")
            membership[task] = identifier
        if row.get("feedback_release") != RELEASE:
            errors.append(f"{identifier}: feedback must wait for all group first responses")
        flags(row.get("persistence_policy"), (
            "requires_durable_write", "first_responses_immutable", "write_failure_keeps_locked",
            "explicit_missing_record_required"), identifier + ".persistence_policy")
        resources = row.get("resource_policy")
        resources = resources if isinstance(resources, dict) else {}
        allowed = strings(resources.get("allowed_before_release"), identifier + ".allowed_resources")
        if set(allowed) != {"original_material", "accessible_equivalent", "operation_help"}:
            errors.append(f"{identifier}: undeclared or answer-revealing pre-release resource")
        normal = resources.get("declared_normal_resources", [])
        if not isinstance(normal, list):
            errors.append(f"{identifier}: declared_normal_resources must be a list")
            normal = []
        resource_ids = set()
        for entry in normal:
            if not isinstance(entry, dict):
                errors.append(f"{identifier}: normal resource must be an object")
                continue
            resource_id = entry.get("resource_identifier")
            if not text(resource_id) or resource_id in resource_ids:
                errors.append(f"{identifier}: normal resource identifier must be unique text")
            if text(resource_id):
                resource_ids.add(resource_id)
            reference(entry.get("evidence_reference"), identifier + ".normal_resource")
            if not text(entry.get("allowed_use")):
                errors.append(f"{identifier}: normal resource allowed_use is required")
        flags(resources, ("knowledge_help_marks_entire_group_assisted",
                          "persist_assistance_before_reveal"), identifier + ".resource_policy")
        recovery = row.get("recovery_policy")
        recovery = recovery if isinstance(recovery, dict) else {}
        routes = strings(recovery.get("guarded_routes"), identifier + ".guarded_routes")
        if not ROUTES.issubset(routes):
            errors.append(f"{identifier}: guarded recovery/feedback routes are incomplete")
        flags(recovery, ("restore_from_durable_state", "retain_answer_exposure_on_clear_continue"),
              identifier + ".recovery_policy")
        if recovery.get("missing_corrupt_or_stale_state") != "locked":
            errors.append(f"{identifier}: invalid recovery must remain locked")
    for identifier, row in tasks.items():
        if row.get("kind") == "independent_assessment" and identifier not in membership:
            errors.append(f"{identifier}: independent task missing assessment group")
        for related in strings(row.get("answer_related_task_identifiers"),
                               identifier + ".answer_related_task_identifiers", False):
            if related not in tasks or related == identifier:
                errors.append(f"{identifier}: unknown or self-related task")
            elif membership.get(related) != membership.get(identifier) or \
                    identifier not in membership:
                errors.append(f"{identifier}: answer-related tasks must share a feedback group")
    flags(data.get("result_policy"), (
        "missing_is_valid_independent_evidence", "self_assessment_can_promote_mastery",
        "open_response_keyword_scoring", "revision_overwrites_first_response",
        "recheck_can_relabel_original_independent"), "result_policy", False)
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("document", type=Path)
    parser.add_argument("--require-reviewed", action="store_true")
    args = parser.parse_args()
    try:
        data = json.loads(args.document.read_text(encoding="utf-8"))
        errors = validate(data, args.document.resolve().parent, args.require_reviewed)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    if errors:
        print("\n".join("ERROR: " + error for error in errors))
        raise SystemExit(1)
    print("assessment integrity contract passed; semantics and runtime locks not verified")


if __name__ == "__main__":
    main()
