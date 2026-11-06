#!/usr/bin/env python3
"""Synthetic regressions for decision, utterance and job registries."""

import copy

from validate_registries import canonical_digest, digest_text, validate


def main():
    decision = {
        "decision_identifier": "route", "decision_version": "0.1", "status": "confirmed",
        "question": "Which delivery route?", "source_basis": ["user"],
        "selected_direction": "interactive_web", "rationale": "Requires direct manipulation",
        "affected_identifiers": ["whole_course"],
    }
    decision["body_sha256"] = canonical_digest(decision)
    utterance = {
        "utterance_identifier": "line", "utterance_version": "0.1",
        "authority": "course-design.md", "speaker_identifier": "guide",
        "purpose": "Open the task", "text": "请比较这两次变化。",
        "usage_references": ["speech_line"],
    }
    utterance["text_sha256"] = digest_text(utterance["text"])
    job = {
        "schema_version": "1.0", "job_identifier": "job", "asset_identifier": "asset",
        "asset_version": "0.1", "provider": "synthetic", "phase": "accepted",
        "terminal_phase": "accepted",
        "attempts": [{"attempt_identifier": "attempt_1"}],
        "output_paths": ["output.mp4"],
        "output_attempt_identifiers": {"output.mp4": "attempt_1"},
    }
    assert not validate({"decisions": [decision]}, {"utterances": [utterance]}, [job])
    changed = copy.deepcopy(decision)
    changed["selected_direction"] = "linear_media"
    assert any("decision body changed" in error for error in
               validate({"decisions": [changed]}, {"utterances": [utterance]}, [job]))
    changed_job = copy.deepcopy(job)
    changed_job["output_attempt_identifiers"]["output.mp4"] = "unknown"
    assert any("unknown attempt" in error for error in
               validate({"decisions": [decision]}, {"utterances": [utterance]}, [changed_job]))
    print("PASS: registry and generic job contract regressions")


if __name__ == "__main__":
    main()
