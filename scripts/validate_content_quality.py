#!/usr/bin/env python3
"""Validate the content quality contract."""

import argparse
import hashlib
import json
from pathlib import Path
import re

MODE = {"imagineering_only", "project_extension", "pbl_bounded", "pbl_full"}
SCORES = (
    "disciplinary_authenticity", "problem_tension", "learner_agency",
    "evidence_visibility", "progression", "memory_value",
    "contextual_fit", "production_feasibility",
)
WEIGHTS = (.20, .15, .15, .15, .15, .10, .05, .05)
PROBLEM_TYPES = {"observation", "explanation", "decision", "repair", "creation", "transfer"}
SHA256 = re.compile(r"[0-9a-f]{64}")


def content_fingerprint(data):
    """Review binds the design payload, excluding its own review record."""
    payload = {key: value for key, value in data.items() if key != "content_review"}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False,
                                    separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def file_fingerprint(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate(data, approved=False, base=None, objectives=None, sources=None):
    errors = []
    if not isinstance(data, dict):
        return ["content quality must be an object"]
    def text(value):
        return isinstance(value, str) and bool(value.strip())
    def strings(value, label, nonempty=True):
        if not isinstance(value, list) or (nonempty and not value) or \
                any(not text(item) for item in value):
            errors.append(f"{label} requires a list of non-empty strings")
            return []
        if len(set(value)) != len(value):
            errors.append(f"{label} contains duplicates")
        return value
    if data.get("schema_version") != "1.1":
        errors.append("schema_version must be 1.1; legacy content needs explicit review migration")
    if not text(data.get("course_version")):
        errors.append("course_version is required")
    core = strings(data.get("core_objective_identifiers"), "core_objective_identifiers")
    declared_sources = strings(data.get("source_identifiers"), "source_identifiers")
    if objectives is not None and set(core) != set(objectives):
        errors.append("core objectives must cover the scoped blueprint objectives exactly")
    if sources is not None and not set(declared_sources).issubset(sources):
        errors.append("source_identifiers contains an unknown blueprint source")
    if data.get("experience_design_mode") not in MODE:
        errors.append("invalid experience_design_mode")
    candidates = data.get("content_candidates", [])
    if not isinstance(candidates, list):
        return errors + ["content_candidates must be a list"]
    ids = set()
    approved_ids = set()
    by_objective = {key: [] for key in core}
    for i, item in enumerate(candidates):
        name = f"content_candidates[{i}]"
        if not isinstance(item, dict):
            errors.append(f"{name} must be an object")
            continue
        identifier = item.get("candidate_id")
        if not text(identifier):
            errors.append(f"{name}.candidate_id is required")
            continue
        if identifier in ids:
            errors.append(f"{name}.candidate_id is duplicated")
        ids.add(identifier)
        objective = item.get("objective_identifier")
        if isinstance(objective, str) and objective in by_objective:
            by_objective[objective].append(item)
        else:
            errors.append(f"{name}.objective_identifier is not a core objective")
        for key in ("subject", "grade_band", "objective_identifier", "learner_problem",
                    "subject_move", "student_product", "transfer_condition", "experience_world",
                    "immersion_increment"):
            if not text(item.get(key)):
                errors.append(f"{name}.{key} is required")
        if not isinstance(item.get("problem_type"), str) or item["problem_type"] not in PROBLEM_TYPES:
            errors.append(f"{name}.problem_type is invalid")
        for key in ("key_constraints", "learner_actions", "likely_misconceptions", "source_boundary"):
            values = strings(item.get(key), f"{name}.{key}")
            if key == "source_boundary" and not set(values).issubset(declared_sources):
                errors.append(f"{name}.source_boundary contains an undeclared source")
        scores = item.get("quality_scores", {})
        scores = scores if isinstance(scores, dict) else {}
        values = [scores.get(key) for key in SCORES]
        if any(type(value) is not int or value < 0 or value > 4 for value in values):
            errors.append(f"{name}.quality_scores must contain integers from 0 to 4")
            continue
        if item.get("quality_decision") not in {
                "candidate", "content_review_pending", "content_approved", "content_revise"}:
            errors.append(f"{name}.quality_decision is invalid")
        if item.get("quality_decision") == "content_approved":
            score = sum(value * weight for value, weight in zip(values, WEIGHTS)) / 4 * 100
            if score < 85 or values[0] < 3 or values[2] < 2 or values[3] < 3 or values[6] < 3:
                errors.append(f"{name} fails content_approved quality gates")
            else:
                approved_ids.add(item.get("candidate_id"))
    for objective, rows in by_objective.items():
        if len(rows) < 5:
            errors.append(f"{objective}: at least five content_candidates are required")
        if len({row.get("problem_type") for row in rows if isinstance(row.get("problem_type"), str)}) < 3:
            errors.append(f"{objective}: at least three problem types are required")
    selected = strings(data.get("selected_candidate_ids"), "selected_candidate_ids", approved)
    if any(item not in ids for item in selected):
        errors.append("selected_candidate_ids contains an unknown candidate")
    if approved and {row.get("objective_identifier") for row in candidates
                     if isinstance(row, dict) and row.get("candidate_id") in selected} != set(core):
        errors.append("selected candidates must cover every core objective")
    elements = data.get("immersion_elements")
    if not isinstance(elements, list):
        errors.append("immersion_elements must be a list")
        elements = []
    element_ids = set()
    for i, row in enumerate(elements):
        name = f"immersion_elements[{i}]"
        if not isinstance(row, dict):
            errors.append(f"{name} must be an object")
            continue
        identifier = row.get("element_identifier")
        if not text(identifier) or identifier in element_ids:
            errors.append(f"{name}.element_identifier must be unique text")
        if isinstance(identifier, str):
            element_ids.add(identifier)
        role = row.get("value_kind")
        if role not in ("learning", "experience", "both"):
            errors.append(f"{name}.value_kind is invalid")
        for key in ("why_keep", "removal_loss", "engineering_constraint", "replaceable_by"):
            if not text(row.get(key)):
                errors.append(f"{name}.{key} is required")
        if role in ("learning", "both"):
            linked = strings(row.get("learning_objective_identifiers"), f"{name}.objectives")
            if not set(linked).issubset(core):
                errors.append(f"{name}: unknown learning objective")
            for key in ("learner_action_enabled", "evidence_changed"):
                if not text(row.get(key)):
                    errors.append(f"{name}.{key} is required")
        if role in ("experience", "both") and not text(row.get("experience_effect")):
            errors.append(f"{name}.experience_effect is required")
        if role == "experience" and row.get("required_for_learning") is not False:
            errors.append(f"{name}: experience-only media cannot carry unique required knowledge")
    review = data.get("content_review", {})
    review = review if isinstance(review, dict) else {}
    if approved and (not selected or any(item not in approved_ids for item in selected)):
        errors.append("selected candidates must be content_approved")
    if approved and review.get("status") != "approved":
        errors.append("content_review.status must be approved")
    if approved:
        owner = review.get("review_owner")
        if not text(owner) or re.search(r"\bagent\b|\bscript\b|\bgenerator\b|\bai\b|机器人|脚本|生成器",
                                       str(owner), re.I):
            errors.append("content_review requires a human review_owner")
        if review.get("reviewed_version") != data.get("course_version"):
            errors.append("content_review.reviewed_version is stale")
        if review.get("reviewed_content_sha256") != content_fingerprint(data):
            errors.append("content_review.reviewed_content_sha256 is stale")
        if not text(review.get("reviewed_at")):
            errors.append("content_review.reviewed_at is required")
        references = strings(review.get("evidence_references"), "content_review.evidence_references")
        snapshots = review.get("evidence_files")
        if not isinstance(snapshots, list):
            errors.append("content_review.evidence_files must be a list")
            snapshots = []
        seen = set()
        for row in snapshots:
            if not isinstance(row, dict) or not text(row.get("reference_identifier")):
                errors.append("content review evidence snapshot must be an object with an identifier")
                continue
            reference = row["reference_identifier"]
            if reference in seen:
                errors.append("duplicate content review evidence snapshot")
            seen.add(reference)
            sha = row.get("content_sha256")
            try:
                path = Path(row["path"])
                if not isinstance(sha, str) or not SHA256.fullmatch(sha) or \
                        file_fingerprint(path if path.is_absolute() else Path(base or ".") / path) != sha:
                    errors.append(f"{reference}: content review evidence changed")
            except (OSError, ValueError, KeyError, TypeError):
                errors.append(f"{reference}: content review evidence cannot be read")
        if seen != set(references):
            errors.append("content review evidence snapshots must cover references exactly")
    return errors


def manifest_content_fingerprint(data, base):
    """Include real quality/review bytes in every design approval's invalidation identity."""
    declaration = data["content_design"]
    entries = {row["reference_identifier"]: row for row in data["evidence_files"]}
    reference = declaration["reference_identifier"]
    path = Path(entries[reference]["path"])
    path = path if path.is_absolute() else Path(base) / path
    content = json.loads(path.read_text())
    return {"declaration": declaration, "quality_sha256": file_fingerprint(path),
            "review_files": {row["reference_identifier"]: file_fingerprint(
                Path(row["path"]) if Path(row["path"]).is_absolute() else path.parent / row["path"])
                for row in content.get("content_review", {}).get("evidence_files", [])}}


def validate_manifest_content(data, base, approved=False, objectives=None, sources=None):
    declaration = data.get("content_design")
    if not isinstance(declaration, dict):
        return ["manifest requires content_design"]
    entries = {row.get("reference_identifier"): row for row in data.get("evidence_files", [])
               if isinstance(row, dict) and isinstance(row.get("reference_identifier"), str)}
    reference = declaration.get("reference_identifier")
    entry = entries.get(reference, {}) if isinstance(reference, str) else {}
    if entry.get("kind") != "content_design_quality":
        return ["content_design must reference registered content_design_quality evidence"]
    try:
        path = Path(entry["path"])
        path = path if path.is_absolute() else Path(base) / path
        content = json.loads(path.read_text())
    except (OSError, KeyError, TypeError, ValueError) as exc:
        return [f"cannot read content_design: {exc}"]
    errors = validate(content, approved, path.parent, objectives, sources)
    if not isinstance(content, dict):
        return errors
    def version_matches(row):
        if row.get("course_version") == data.get("course_version"):
            return True
        subjects = {item.get("scope_identifier"): item for item in data.get("approval_subjects", [])
                    if isinstance(item, dict) and isinstance(item.get("scope_identifier"), str)}
        bound = row.get("bound_versions")
        if not isinstance(bound, dict) or not bound:
            return False
        covered = set()
        for key, version in bound.items():
            subject = subjects.get(key, {})
            if subject.get("kind") != "design" or subject.get("subject_version") != version:
                return False
            covered.update(item for item in subject.get("covered_identifiers", []) if isinstance(item, str))
        return set(content.get("core_objective_identifiers", [])).issubset(covered)
    if file_fingerprint(path) != entry.get("content_sha256") or not version_matches(entry) or \
            content.get("course_version") != entry.get("course_version"):
        errors.append("content_design file binding/version is stale")
    for key in ("experience_design_mode", "selected_candidate_ids"):
        if declaration.get(key) != content.get(key):
            errors.append(f"content_design.{key} differs from quality file")
    review = content.get("content_review", {})
    if isinstance(review, dict):
        if declaration.get("quality_review_evidence_references") != review.get("evidence_references"):
            errors.append("manifest content review references differ")
        for row in review.get("evidence_files", []) if isinstance(review.get("evidence_files"), list) else []:
            if not isinstance(row, dict):
                continue
            bound = entries.get(row.get("reference_identifier"), {}) if isinstance(row.get("reference_identifier"), str) else {}
            if bound.get("kind") != "content_review" or not version_matches(bound) or \
                    bound.get("course_version") != content.get("course_version") or \
                    bound.get("content_sha256") != row.get("content_sha256"):
                errors.append("content review evidence is not registered with the current version/hash")
            try:
                registered = Path(bound["path"])
                registered = registered if registered.is_absolute() else Path(base) / registered
                snapshot = Path(row["path"])
                snapshot = snapshot if snapshot.is_absolute() else path.parent / snapshot
                if registered.resolve() != snapshot.resolve():
                    errors.append("content review snapshot points to a different file")
            except (KeyError, TypeError):
                errors.append("invalid content review registered path")
    if approved and declaration.get("status") != "content_approved":
        errors.append("manifest content_design.status must be content_approved")
    return errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("document", type=Path)
    parser.add_argument("--require-approved", action="store_true")
    parser.add_argument("--show-content-fingerprint", action="store_true")
    args = parser.parse_args()
    data = json.loads(args.document.read_text(encoding="utf-8"))
    if args.show_content_fingerprint:
        print(content_fingerprint(data))
        return
    errors = validate(data, args.require_approved, args.document.resolve().parent)
    if errors:
        print("\n".join(f"ERROR: {error}" for error in errors))
        raise SystemExit(1)
    print("content quality contract passed")


if __name__ == "__main__":
    main()
