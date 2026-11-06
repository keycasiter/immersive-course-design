#!/usr/bin/env python3
"""Validate scoped text-review records, never story quality or acceptance."""

import argparse
import hashlib
import json
import re
from pathlib import Path


CONTRACT = json.loads(
    (Path(__file__).resolve().parent.parent / "assets/storyboard-review.contract.json")
    .read_text(encoding="utf-8")
)


def validate(record, root):
    errors = []
    root = Path(root).resolve()

    def fields(value, expected, label):
        if not isinstance(value, dict):
            errors.append(f"{label}: must be an object")
            return False
        missing = set(expected) - set(value)
        extra = set(value) - set(expected)
        if missing or extra:
            errors.append(f"{label}: missing={sorted(missing)}, unknown={sorted(extra)}")
        return not missing

    def text(value, label):
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{label}: must be non-empty text")
            return False
        if "{{" in value or "}}" in value:
            errors.append(f"{label}: unresolved placeholder")
            return False
        return True

    def unique_strings(value, label, allow_empty=False):
        if not isinstance(value, list):
            errors.append(f"{label}: must be a list")
            return []
        if not value and not allow_empty:
            errors.append(f"{label}: must be non-empty")
        for item in value:
            text(item, label)
        valid = [item for item in value if isinstance(item, str)]
        if len(valid) != len(set(valid)):
            errors.append(f"{label}: duplicate identifiers")
        return valid

    def line_range(value, label, count):
        start, end = value.get("start_line"), value.get("end_line")
        if (type(start) is not int or type(end) is not int
                or start < 1 or end < start or end > count):
            errors.append(f"{label}: invalid line range")
            return None
        return start, end

    if not fields(record, CONTRACT["required_fields"], "review"):
        return errors
    if record["contract_version"] != CONTRACT["contract_version"]:
        errors.append("review: unsupported contract_version")
    if record["review_kind"] not in CONTRACT["review_kinds"]:
        errors.append("review: unsupported review_kind")
    text(record["reviewer"], "reviewer")
    for key, expected in CONTRACT["fixed_fields"].items():
        if record[key] != expected:
            errors.append(f"{key}: text review requires {expected}")
    unique_strings(record["limitations"], "limitations")

    source = record["source"]
    if not fields(source, CONTRACT["source_fields"], "source"):
        return errors
    if not text(source["path"], "source.path"):
        return errors
    source_path = (root / source["path"]).resolve()
    if Path(source["path"]).is_absolute() or not source_path.is_relative_to(root):
        errors.append("source.path: must resolve inside review root")
        return errors
    try:
        source_bytes = source_path.read_bytes()
        lines = source_bytes.decode("utf-8").splitlines()
    except (OSError, UnicodeError) as error:
        errors.append(f"source: cannot read UTF-8 text ({type(error).__name__})")
        return errors
    if not isinstance(source["sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", source["sha256"]):
        errors.append("source.sha256: invalid hash")
    if source["sha256"] != hashlib.sha256(source_bytes).hexdigest():
        errors.append("source.sha256: stale binding")

    scope = record["scope"]
    if not fields(scope, CONTRACT["scope_fields"], "scope"):
        return errors
    if scope["kind"] not in CONTRACT["scope_kinds"]:
        errors.append("scope.kind: unsupported scope")
    if not isinstance(scope["units"], list) or not scope["units"]:
        errors.append("scope.units: must be non-empty")
        return errors
    units, covered = {}, set()
    for unit in scope["units"]:
        if not fields(unit, CONTRACT["unit_fields"], "unit"):
            continue
        identifier = unit["identifier"]
        if not text(identifier, "unit.identifier"):
            continue
        if identifier in units:
            errors.append("unit.identifier: duplicate identifier")
        span = line_range(unit, identifier, len(lines))
        if span:
            selected = set(range(span[0], span[1] + 1))
            if selected & covered:
                errors.append(f"{identifier}: overlapping unit ranges")
            covered |= selected
            units[identifier] = span
    if scope["kind"] == "whole_storyboard":
        unread = {i for i, line in enumerate(lines, 1) if line.strip()} - covered
        if unread:
            errors.append(f"scope: whole_storyboard omits non-empty lines {sorted(unread)}")
    reviewed = unique_strings(record["reviewed_unit_identifiers"], "reviewed_unit_identifiers")
    if set(reviewed) != set(units):
        errors.append("reviewed_unit_identifiers: must equal selected scope units")

    dimensions = record["dimensions"]
    if not isinstance(dimensions, list):
        errors.append("dimensions: must be a list")
        return errors
    identifiers, referenced = [], set()
    for dimension in dimensions:
        if not fields(dimension, CONTRACT["dimension_fields"], "dimension"):
            continue
        identifier, status = dimension["identifier"], dimension["status"]
        if not text(identifier, "dimension.identifier"):
            continue
        identifiers.append(identifier)
        if status not in CONTRACT["dimension_statuses"]:
            errors.append(f"{identifier}: unsupported status")
        text(dimension["observation"], f"{identifier}.observation")
        references = unique_strings(dimension["unit_identifiers"], identifier, allow_empty=True)
        if set(references) - set(units):
            errors.append(f"{identifier}: unknown unit reference")
        referenced |= set(references)
        evidence = dimension["evidence"]
        if not isinstance(evidence, list):
            errors.append(f"{identifier}: evidence must be a list")
            continue
        if status in ("issue", "present_in_text") and (not evidence or not references):
            errors.append(f"{identifier}: text judgment requires unit and quote evidence")
        for item in evidence:
            if not fields(item, CONTRACT["evidence_fields"], "evidence"):
                continue
            unit_id = item["unit_identifier"]
            if not isinstance(unit_id, str) or unit_id not in units or unit_id not in references:
                errors.append(f"{identifier}: evidence references unknown or unselected unit")
                continue
            span = line_range(item, f"{identifier}.evidence", len(lines))
            if not span:
                continue
            unit_span = units[unit_id]
            if span[0] < unit_span[0] or span[1] > unit_span[1]:
                errors.append(f"{identifier}: evidence outside cited unit")
            if text(item["quote"], "evidence.quote"):
                passage = "\n".join(lines[span[0] - 1:span[1]])
                if item["quote"] not in passage:
                    errors.append(f"{identifier}: quote absent from cited lines")
    if (len(identifiers) != len(set(identifiers))
            or set(identifiers) != set(CONTRACT["dimension_identifiers"])):
        errors.append("dimensions: requires each contract dimension exactly once")
    if set(units) - referenced:
        errors.append("dimensions: selected units lack review references")

    checks = record["participation_checks"]
    if not isinstance(checks, list):
        errors.append("participation_checks: must be a list")
        return errors
    reason = record["participation_check_not_applicable_reason"]
    if checks and reason is not None:
        errors.append("participation_checks: applicability reason must be null when checks exist")
    if not checks:
        text(reason, "participation_check_not_applicable_reason")
    for check in checks:
        if not fields(check, CONTRACT["participation_fields"], "participation"):
            continue
        if not isinstance(check["unit_identifier"], str) or check["unit_identifier"] not in units:
            errors.append("participation: unknown unit reference")
        text(check["promise"], "participation.promise")
        text(check["observation"], "participation.observation")
        inputs = check["inputs"]
        if not isinstance(inputs, list) or len(inputs) != 2:
            errors.append("participation: requires exactly two input walks")
            continue
        names = []
        for item in inputs:
            if not fields(item, CONTRACT["input_fields"], "participation.input"):
                continue
            for key in ("input", "visible_result", "return_state"):
                text(item[key], f"participation.{key}")
            if isinstance(item["input"], str):
                names.append(item["input"])
            if (not isinstance(item["next_unit_identifier"], str)
                    or item["next_unit_identifier"] not in units):
                errors.append("participation: unknown next unit")
        if len(names) == 2 and names[0] == names[1]:
            errors.append("participation: input walks must use different inputs")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    try:
        record = json.loads(args.review.read_text(encoding="utf-8"))
        errors = validate(record, args.root)
    except (OSError, ValueError) as error:
        errors = [f"review: cannot read JSON ({type(error).__name__})"]
    print(json.dumps({
        "record_valid": not errors, "errors": errors,
        "semantic_acceptance": "not_computed",
        "media_evaluation": "not_run", "learner_evaluation": "not_run"
    }, ensure_ascii=False, indent=2))
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
