#!/usr/bin/env python3
"""Validate the explicit visual gate for video-led course pages."""

import argparse
import json
from pathlib import Path
from validate_production import file_digest


REQUIRED_STATES = {"playback", "paused", "feedback", "return"}
STATE_SURFACES = {
    "playback": {"scene-media"}, "paused": {"scene-media", "task-surface"},
    "feedback": {"task-surface"}, "return": {"scene-media"},
}
STATE_ACTIONS = {"playback": {0, 1}, "paused": {1}, "feedback": {1}, "return": {0, 1}}
REQUIRED_DECORATION_FIELDS = {
    "decoration_identifier",
    "state_scope",
    "visual_role",
    "teaching_purpose",
    "removal_loss",
    "asset_or_css_reference",
    "acceptance_evidence",
}


def text(value):
    return isinstance(value, str) and bool(value.strip())


def validate(data, base=None, runtime_fingerprints=None):
    errors = []
    if not isinstance(data, dict):
        return ["visual gate must be an object"]
    if data.get("contract_version") != "1.1":
        errors.append("contract_version must be 1.1; legacy evidence is not current visual acceptance")
    if data.get("profile_identifier") != "video_led_web":
        errors.append("profile_identifier must be video_led_web")
    states = data.get("states")
    if not isinstance(states, list):
        return ["states must be a list"]
    seen = set()
    for index, state in enumerate(states):
        label = f"states[{index}]"
        if not isinstance(state, dict):
            errors.append(f"{label} must be an object")
            continue
        identifier = state.get("state_identifier")
        if not isinstance(identifier, str):
            errors.append(f"{label}.state_identifier must be text")
            continue
        if identifier in seen:
            errors.append(f"duplicate state_identifier: {identifier}")
        seen.add(identifier)
        if not text(identifier):
            errors.append(f"{label}.state_identifier is required")
        for key in ("primary_surface", "allowed_layers", "forbidden_persistent_layers",
                    "evidence_status", "evidence_references"):
            value = state.get(key)
            if key.endswith("_layers") or key.endswith("_references"):
                if not isinstance(value, list):
                    errors.append(f"{label}.{key} must be a list")
            elif not text(value):
                errors.append(f"{label}.{key} is required")
        if not isinstance(state.get("primary_surface"), str) or \
                state["primary_surface"] not in STATE_SURFACES.get(identifier, set()):
            errors.append(f"{label}.primary_surface contradicts the state contract")
        if type(state.get("primary_action_count")) is not int or \
                state["primary_action_count"] not in STATE_ACTIONS.get(identifier, set()):
            errors.append(f"{label}.primary_action_count must be a single applicable action")
    if seen != REQUIRED_STATES:
        errors.append(f"states must cover exactly {sorted(REQUIRED_STATES)}")

    decorations = data.get("decorations")
    if not isinstance(decorations, list):
        errors.append("decorations must be a list")
    else:
        identifiers = set()
        for index, decoration in enumerate(decorations):
            label = f"decorations[{index}]"
            if not isinstance(decoration, dict):
                errors.append(f"{label} must be an object")
                continue
            identifier = decoration.get("decoration_identifier")
            if not isinstance(identifier, str):
                errors.append(f"{label}.decoration_identifier must be text")
                continue
            if identifier in identifiers:
                errors.append(f"duplicate decoration_identifier: {identifier}")
            identifiers.add(identifier)
            for key in REQUIRED_DECORATION_FIELDS:
                if key == "teaching_purpose" and decoration.get("visual_role") == "atmosphere":
                    continue
                if not text(decoration.get(key)):
                    errors.append(f"{label}.{key} is required")
            if isinstance(decoration.get("visual_role"), str) and \
                    decoration["visual_role"] in {"decoration", "ornament"}:
                errors.append(f"{label}.visual_role must name a learning-supporting role")
            if decoration.get("visual_role") == "atmosphere":
                if not text(decoration.get("experience_purpose")):
                    errors.append(f"{label}.experience_purpose is required")
                for key in ("required_for_learning", "covers_protected_content", "receives_input",
                            "background_has_audio"):
                    if decoration.get(key) is not False:
                        errors.append(f"{label}.{key} must be false")
                if not text(decoration.get("attention_constraint")):
                    errors.append(f"{label}.attention_constraint is required")

    if not isinstance(data.get("status"), str) or data["status"] not in {"planned", "failed", "passed"}:
        errors.append("status must be planned, failed or passed")
    evidence = data.get("evidence")
    evidence = evidence if isinstance(evidence, list) else []
    evidence_by_id = {}
    if not isinstance(evidence, list) or not evidence:
        errors.append("evidence must be a non-empty list")
    else:
        for index, row in enumerate(evidence):
            label = f"evidence[{index}]"
            if not isinstance(row, dict):
                errors.append(f"{label} must be an object")
                continue
            for key in ("evidence_identifier", "state_identifier", "status", "viewport",
                        "browser", "entry_action", "result"):
                if not text(row.get(key)):
                    errors.append(f"{label}.{key} is required")
            identifier = row.get("evidence_identifier")
            if isinstance(identifier, str):
                if identifier in evidence_by_id:
                    errors.append(f"duplicate evidence_identifier: {identifier}")
                evidence_by_id[identifier] = row
            if not isinstance(row.get("state_identifier"), str) or row["state_identifier"] not in REQUIRED_STATES:
                errors.append(f"{label}: unknown evidence state")
    if data.get("status") == "passed":
        if not text(data.get("course_version")):
            errors.append("passed visual gate requires course_version")
        if not isinstance(data.get("runtime_fingerprints"), dict) or not data["runtime_fingerprints"]:
            errors.append("passed visual gate requires runtime fingerprints")
        if runtime_fingerprints is not None and data.get("runtime_fingerprints") != runtime_fingerprints:
            errors.append("visual gate runtime fingerprints are stale")
        binding = data.get("runtime_fingerprints", {})
        snapshots = data.get("runtime_file_snapshots")
        if not isinstance(snapshots, list) or not snapshots:
            errors.append("passed visual gate requires actual runtime_file_snapshots")
        else:
            bound_evidence = binding.get("evidence", {}) if isinstance(binding, dict) else {}
            seen_references = set()
            for row in snapshots:
                if not isinstance(row, dict) or not isinstance(row.get("reference_identifier"), str):
                    errors.append("visual runtime snapshot must identify evidence")
                    continue
                reference = row["reference_identifier"]
                seen_references.add(reference)
                if row.get("content_sha256") != bound_evidence.get(reference):
                    errors.append("visual runtime snapshot differs from fingerprints")
                try:
                    path = Path(row["path"])
                    path = path if path.is_absolute() else Path(base or ".") / path
                    if file_digest(path) != row.get("content_sha256"):
                        errors.append("visual runtime file changed")
                except (OSError, KeyError, ValueError, TypeError):
                    errors.append("visual runtime file cannot be read")
            if seen_references != set(bound_evidence):
                errors.append("visual runtime snapshots must cover every bound evidence file")
        if any(state.get("evidence_status") != "passed" for state in states if isinstance(state, dict)):
            errors.append("status=passed requires passed evidence for every state")
        if any(row.get("status") != "passed" for row in evidence if isinstance(row, dict)):
            errors.append("status=passed requires passed evidence rows")
        for state in states:
            if not isinstance(state, dict):
                continue
            references = state.get("evidence_references")
            if not isinstance(references, list) or not references:
                errors.append("passed evidence requires non-empty state references")
                continue
            covered = set()
            for reference in references:
                row = evidence_by_id.get(reference, {}) if isinstance(reference, str) else {}
                if not row:
                    errors.append(f"unknown visual evidence reference: {reference}")
                    continue
                if row.get("state_identifier") != state.get("state_identifier"):
                    errors.append(f"{reference}: evidence belongs to another state")
                if row.get("course_version") != data.get("course_version"):
                    errors.append(f"{reference}: outdated visual evidence version")
                if row.get("runtime_fingerprints") != data.get("runtime_fingerprints"):
                    errors.append(f"{reference}: visual evidence runtime fingerprint differs")
                viewport = row.get("viewport_class")
                if isinstance(viewport, str):
                    covered.add(viewport)
                import re
                dimensions = re.fullmatch(r"([1-9][0-9]*)x([1-9][0-9]*)", str(row.get("viewport")))
                if not isinstance(viewport, str) or viewport not in {"desktop", "narrow"} or not dimensions or \
                        ((int(dimensions[1]) <= 600) != (viewport == "narrow")):
                    errors.append(f"{reference}: invalid viewport dimensions/class")
                artifact = row.get("artifact")
                if not isinstance(artifact, dict) or not text(artifact.get("path")):
                    errors.append(f"{reference}: actual screenshot/operation artifact required")
                else:
                    try:
                        path = Path(artifact["path"])
                        path = path if path.is_absolute() else Path(base or ".") / path
                        if file_digest(path) != artifact.get("content_sha256"):
                            errors.append(f"{reference}: visual evidence artifact changed")
                    except (OSError, ValueError):
                        errors.append(f"{reference}: visual evidence artifact cannot be read")
                if not text(row.get("captured_at")):
                    errors.append(f"{reference}: captured_at is required")
            if covered != {"desktop", "narrow"}:
                errors.append(f"{state.get('state_identifier')}: passed evidence must cover desktop and narrow")
        for decoration in decorations if isinstance(decorations, list) else []:
            if isinstance(decoration, dict):
                reference = decoration.get("acceptance_evidence")
                row = evidence_by_id.get(reference, {}) if isinstance(reference, str) else {}
                if not row or row.get("state_identifier") != decoration.get("state_scope"):
                    errors.append("decoration acceptance evidence must bind its state")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("gate", type=Path)
    args = parser.parse_args()
    try:
        data = json.loads(args.gate.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"cannot read visual gate: {exc}")
    errors = validate(data, args.gate.resolve().parent)
    if errors:
        raise SystemExit("\n".join(errors))
    print(f"visual gate structure passed: {len(data['states'])} states, {len(data['decorations'])} decorations")
    print(f"Visual acceptance status: {data['status']}; structure alone is not visual review.")


if __name__ == "__main__":
    main()
