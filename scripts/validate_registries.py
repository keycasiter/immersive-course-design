#!/usr/bin/env python3
"""Validate decision, utterance and generic media-job registries."""

import argparse
import hashlib
import json
from pathlib import Path
from submission_contract import validate_job_readbacks


TERMINAL_PHASES = {"accepted", "failed", "cancelled", "timed_out"}


def digest_text(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def canonical_digest(value):
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return digest_text(payload)


def load(path, errors):
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"{path}: {exc}")
        return {}
    if not isinstance(value, dict):
        errors.append(f"{path}: root must be an object")
        return {}
    return value


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def validate(decisions, utterances, jobs, job_bases=None):
    errors = []
    seen = set()
    for index, row in enumerate(decisions.get("decisions", [])):
        path = f"decisions[{index}]"
        if not isinstance(row, dict):
            errors.append(f"{path}: must be an object")
            continue
        identifier = row.get("decision_identifier")
        if not nonempty(identifier) or identifier in seen:
            errors.append(f"{path}.decision_identifier: must be non-empty and unique")
        seen.add(identifier)
        for key in (
                "decision_version", "status", "question", "selected_direction",
                "rationale", "body_sha256"):
            if not nonempty(row.get(key)):
                errors.append(f"{path}.{key}: requires text")
        if not isinstance(row.get("source_basis"), list) or not row["source_basis"]:
            errors.append(f"{path}.source_basis: requires entries")
        if not isinstance(row.get("affected_identifiers"), list) or not row["affected_identifiers"]:
            errors.append(f"{path}.affected_identifiers: requires entries")
        expected = canonical_digest({key: value for key, value in row.items() if key != "body_sha256"})
        if row.get("body_sha256") != expected:
            errors.append(f"{path}.body_sha256: decision body changed")

    seen = set()
    for index, row in enumerate(utterances.get("utterances", [])):
        path = f"utterances[{index}]"
        if not isinstance(row, dict):
            errors.append(f"{path}: must be an object")
            continue
        identifier = row.get("utterance_identifier")
        if not nonempty(identifier) or identifier in seen:
            errors.append(f"{path}.utterance_identifier: must be non-empty and unique")
        seen.add(identifier)
        for key in (
                "utterance_version", "authority", "speaker_identifier", "purpose", "text",
                "text_sha256"):
            if not nonempty(row.get(key)):
                errors.append(f"{path}.{key}: requires text")
        if row.get("text_sha256") != digest_text(row.get("text", "")):
            errors.append(f"{path}.text_sha256: utterance text changed")
        if not isinstance(row.get("usage_references"), list) or not row["usage_references"]:
            errors.append(f"{path}.usage_references: requires entries")

    for job_index, job in enumerate(jobs):
        path = f"jobs[{job_index}]"
        if job.get("schema_version") not in ("1.0", "1.1"):
            errors.append(f"{path}.schema_version: must be 1.0 or 1.1")
        for key in ("job_identifier", "asset_identifier", "asset_version", "provider", "phase"):
            if not nonempty(job.get(key)):
                errors.append(f"{path}.{key}: requires text")
        attempts = job.get("attempts")
        if not isinstance(attempts, list):
            errors.append(f"{path}.attempts: must be an array")
            attempts = []
        attempt_ids = []
        for attempt_index, attempt in enumerate(attempts):
            attempt_path = f"{path}.attempts[{attempt_index}]"
            if not isinstance(attempt, dict):
                errors.append(f"{attempt_path}: must be an object")
                continue
            attempt_id = attempt.get("attempt_identifier")
            if not nonempty(attempt_id):
                errors.append(f"{attempt_path}.attempt_identifier: requires text")
            attempt_ids.append(attempt_id)
        if len(attempt_ids) != len(set(attempt_ids)):
            errors.append(f"{path}.attempts: attempt identifiers must be unique")
        terminal = job.get("terminal_phase")
        if terminal is not None and terminal not in TERMINAL_PHASES:
            errors.append(f"{path}.terminal_phase: invalid terminal phase")
        outputs = job.get("output_paths")
        bindings = job.get("output_attempt_identifiers")
        if not isinstance(outputs, list) or not isinstance(bindings, dict):
            errors.append(f"{path}: output paths and attempt bindings have invalid types")
        elif terminal == "accepted":
            if not outputs:
                errors.append(f"{path}: accepted job requires outputs")
            if set(outputs) != set(bindings):
                errors.append(f"{path}: accepted outputs must all bind to attempts")
            if any(attempt_id not in attempt_ids for attempt_id in bindings.values()):
                errors.append(f"{path}: output binds an unknown attempt")
        base = job_bases[job_index] if job_bases is not None else Path.cwd()
        validate_job_readbacks(job, base, errors, path)
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("decision_registry", type=Path)
    parser.add_argument("utterance_registry", type=Path)
    parser.add_argument("jobs", nargs="*", type=Path)
    args = parser.parse_args()
    parse_errors = []
    decisions = load(args.decision_registry, parse_errors)
    utterances = load(args.utterance_registry, parse_errors)
    jobs = [load(path, parse_errors) for path in args.jobs]
    errors = parse_errors + validate(decisions, utterances, jobs,
                                     [path.resolve().parent for path in args.jobs])
    if errors:
        print("INVALID:\n" + "\n".join(f"- {error}" for error in errors))
        return 1
    print(f"VALID: {len(decisions.get('decisions', []))} decisions, "
          f"{len(utterances.get('utterances', []))} utterances, {len(jobs)} jobs")
    if any(job.get("schema_version") == "1.0" for job in jobs):
        print("LEGACY 1.0: final request readback is not validated when absent.")
    print("Job checks prove request consistency, not correspondence to a video plan or provider receipt.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
