#!/usr/bin/env python3
"""Isolated positive/negative content-gate and joint-binding regressions."""
import argparse
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile

from check_workflow_and_demo import fixture
from production_contract import validate_joint
from validate_production import validate as production_check, approval_fingerprint
from validate_content_quality import validate, content_fingerprint, file_fingerprint
from check_video_led_visual_gate import validate as visual_check

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    results = []
    def check(name, errors, expected=None):
        assert not errors if expected is None else any(expected in error for error in errors), (name, errors)
        results.append({"case": name, "status": "passed", "diagnostic": expected})
    with tempfile.TemporaryDirectory(prefix="content-quality-regression-") as directory:
        base = Path(directory)
        data = fixture(base)
        path = base / "content-design-quality.json"
        content = json.loads(path.read_text())
        check("approved_quality", validate(content, True, base))
        check("joint_approved", validate_joint(data, base))
        for name, edit, diagnostic in (
            ("self_signature", lambda c: c["content_review"].update(review_owner="Agent"), "human review_owner"),
            ("empty_review", lambda c: c["content_review"].update(evidence_references=[], evidence_files=[]), "non-empty strings"),
            ("stale_version", lambda c: c["content_review"].update(reviewed_version="old"), "reviewed_version is stale"),
            ("stale_hash", lambda c: c["content_review"].update(reviewed_content_sha256="0"*64), "sha256 is stale"),
            ("single_type", lambda c: [row.update(problem_type="explanation") for row in c["content_candidates"]], "three problem types"),
            ("uncovered_second", lambda c: c["core_objective_identifiers"].append("second"), "five content_candidates"),
            ("unknown_problem", lambda c: c["content_candidates"][0].update(problem_type="unknown"), "problem_type is invalid"),
            ("null_element", lambda c: c.update(immersion_elements=[None]), "must be an object"),
            ("boolean_score", lambda c: c["content_candidates"][0]["quality_scores"].update(disciplinary_authenticity=True), "integers"),
            ("missing_source", lambda c: c.update(source_identifiers=[]), "non-empty strings"),
            ("legacy_schema", lambda c: c.update(schema_version="1.0"), "must be 1.1"),
        ):
            bad = copy.deepcopy(content)
            edit(bad)
            check(name, validate(bad, True, base), diagnostic)
        for key in ("subject", "grade_band", "key_constraints", "learner_actions",
                    "likely_misconceptions", "source_boundary"):
            bad = copy.deepcopy(content)
            bad["content_candidates"][0].pop(key)
            check("missing_" + key, validate(bad, True, base), key)
        bad = copy.deepcopy(content)
        bad["immersion_elements"] = [{
            "element_identifier": "atmosphere", "value_kind": "experience",
            "why_keep": "Maintain the same room across a pause", "removal_loss": "Abrupt room discontinuity",
            "engineering_constraint": "Silent low motion behind protected content", "replaceable_by": "Static same-room image",
            "experience_effect": "Spatial continuity", "required_for_learning": False}]
        bad["content_review"]["reviewed_content_sha256"] = content_fingerprint(bad)
        check("experience_without_new_learning_evidence", validate(bad, True, base))
        bad["immersion_elements"][0]["required_for_learning"] = True
        check("experience_cannot_carry_unique_knowledge", validate(bad, True, base), "unique required knowledge")
        pending = copy.deepcopy(content)
        pending["content_review"]["status"] = "pending"
        check("draft_can_remain_pending", validate(pending, False, base))
        original = path.read_bytes()
        path.write_text(json.dumps(pending))
        check("joint_blocks_pending", validate_joint(data, base), "must be approved")
        path.write_bytes(original)
        missing = copy.deepcopy(data)
        missing.pop("content_design")
        check("joint_requires_explicit_quality", validate_joint(missing, base), "requires content_design")
        subject = next(row for row in data["approval_subjects"] if row["kind"] == "design")
        before = approval_fingerprint(data, subject, base)
        changed = copy.deepcopy(content)
        changed["content_candidates"][0]["learner_problem"] += " changed"
        path.write_text(json.dumps(changed))
        assert approval_fingerprint(data, subject, base) != before
        check("changed_candidate_invalidates_design", production_check(data, base), "confirmation")
        path.write_bytes(original)
        review = base / "quality-teacher-review.txt"
        review_original = review.read_bytes()
        review.write_text("Changed synthetic reviewer bytes")
        assert approval_fingerprint(data, subject, base) != before
        check("changed_teacher_file", validate(content, True, base), "evidence changed")
        review.write_bytes(review_original)
        check("joint_unknown_blueprint_source", validate(content, True, base, sources=set()), "unknown blueprint source")
        gate = json.loads((ROOT / "assets/video-led-visual-gate.template.json").read_text())
        gate["decorations"][0].update(visual_role="atmosphere", teaching_purpose="",
            experience_purpose="Continue the same room", attention_constraint="Low motion behind video",
            required_for_learning=False, covers_protected_content=False, receives_input=False, background_has_audio=False)
        check("visual_allows_optional_atmosphere", visual_check(gate))
        for key in ("required_for_learning", "covers_protected_content", "receives_input", "background_has_audio"):
            bad_gate = copy.deepcopy(gate)
            bad_gate["decorations"][0][key] = True
            check("visual_blocks_atmosphere_" + key, visual_check(bad_gate), key + " must be false")
        for key in ("experience_purpose", "attention_constraint"):
            bad_gate = copy.deepcopy(gate)
            bad_gate["decorations"][0][key] = ""
            check("visual_requires_atmosphere_" + key, visual_check(bad_gate), key)
        gate_path = base / "visual-gate.json"
        gate_path.write_text(json.dumps(gate))
        result = subprocess.run([sys.executable, str(ROOT / "scripts/check_video_led_visual_gate.py"),
                                 str(gate_path)], capture_output=True, text=True)
        assert result.returncode == 0, result.stdout + result.stderr
        results.append({"case": "atmosphere_visual_CLI", "status": "passed"})
        # Actual strict CLI, not just the imported function.
        result = subprocess.run([sys.executable, str(ROOT / "scripts/validate_content_quality.py"),
                                 str(path), "--require-approved"], capture_output=True, text=True)
        assert result.returncode == 0, result.stdout + result.stderr
        results.append({"case": "strict_CLI", "status": "passed"})
    report = {"passed": len(results), "cases": results,
              "limits": "Synthetic reviewer records; no real teacher identity, semantic scoring or learning results."}
    if args.output:
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
