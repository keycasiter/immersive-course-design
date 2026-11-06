#!/usr/bin/env python3
"""Run isolated review-packet contract regressions; all reviewer/learner data are synthetic."""
import argparse
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile

from validate_immersion_review import CATALOG, RUBRIC, digest, read_json, validate


def fixture(base, atom="M13-A01", stage="design"):
    (base / "observation.txt").write_text("SYNTHETIC fixture: entry observation\nSYNTHETIC fixture: later observation\n")
    (base / "trace.json").write_text(json.dumps({"events": ["SYNTHETIC start", "SYNTHETIC end"],
                                              "a/b": {"~key": True}}))
    catalog_hash, rubric_hash = digest(CATALOG), digest(RUBRIC)
    unit = {"identifier": "entry_observation", "atom_identifier": atom, "evaluation_stage": stage,
            "experience_intent": "Locate the current object", "construct": "orientation",
            "element_identifiers": [], "design_decisions": ["Keep the object visible before the first action"],
            "scene_identifiers": ["observation_scene"], "beat_identifiers": ["observation_beat"],
            "shot_identifiers": [], "asset_identifiers": [],
            "observable_success": "Current object and situation can be located",
            "observable_failure": "Only the world name can be located",
            "required_routes": ["normal", "reentry"], "comparison_plan": "Remove the entry object cue; keep speech constant"}
    plan = {"schema_version": "2.0", "course_identifier": "synthetic_fixture", "course_version": "fixture_only",
            "scope": "local_revision", "scope_description": "Isolated schema fixture; no actual course/reviewer/learner",
            "catalog_sha256": catalog_hash, "rubric_sha256": rubric_hash, "units": [unit],
            "coverage": [{"atom_identifier": task["identifier"],
                          "applicability": "applicable" if task["identifier"] == atom else "not_applicable_with_reason",
                          "applicability_reason": "Within this isolated entry fixture" if task["identifier"] == atom else "Outside local fixture scope",
                          "unit_identifiers": ["entry_observation"] if task["identifier"] == atom else []}
                         for task in read_json(CATALOG)["tasks"]]}
    plan_path = base / "plan.json"
    plan_path.write_text(json.dumps(plan))
    locator = {"kind": "line_range", "start_line": 1, "end_line": 1}
    packet = {"schema_version": "2.0", "course_identifier": plan["course_identifier"],
              "course_version": plan["course_version"], "purpose": "diagnostic",
              "catalog_sha256": catalog_hash, "rubric_sha256": rubric_hash,
              "plan": {"path": "plan.json", "sha256": digest(plan_path)},
              "artifacts": [{"identifier": "observed_doc", "path": "observation.txt",
                             "sha256": digest(base / "observation.txt"), "kind": "document"},
                            {"identifier": "observed_trace", "path": "trace.json",
                             "sha256": digest(base / "trace.json"), "kind": "runtime_log"}],
              "calibrations": [], "records": [{
                  "identifier": "synthetic_review", "unit_identifier": unit["identifier"],
                  "atom_identifier": atom, "catalog_sha256": catalog_hash, "rubric_sha256": rubric_hash,
                  "evaluation_stage": stage, "applicability": "applicable",
                  "applicability_reason": "Entry in declared local scope", "score": 2,
                  "reviewer_role": "author_self_review", "reviewer_identifier": "synthetic_fixture_author",
                  "artifact_sha256": digest(base / "observation.txt"), "time_range_or_locator": locator,
                  "observed_behavior": "SYNTHETIC observation says object remains visible",
                  "criterion_rationale": "SYNTHETIC entry cue meets the declared sample criterion",
                  "limitation_or_counterexample": "SYNTHETIC only; no authenticated review or learner trial",
                  "status": "observed", "finding": "established",
                  "evidence_references": [{"artifact_identifier": "observed_doc", "locator": locator}],
                  "observed_routes": ["normal", "reentry"], "calibration_identifier": None}]}
    return plan, packet


def rebind_plan(base, plan, packet):
    (base / "plan.json").write_text(json.dumps(plan))
    packet["plan"]["sha256"] = digest(base / "plan.json")


def bind_primary(packet):
    record = packet["records"][0]
    if record["evidence_references"]:
        ref = record["evidence_references"][0]
        record["artifact_sha256"] = next(row["sha256"] for row in packet["artifacts"]
                                         if row["identifier"] == ref["artifact_identifier"])
        record["time_range_or_locator"] = ref["locator"]
    else:
        record["artifact_sha256"] = record["time_range_or_locator"] = None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    results = []
    with tempfile.TemporaryDirectory(prefix="immersion-review-regression-") as directory:
        base = Path(directory)
        plan, packet = fixture(base)
        def check(name, data, diagnostic=None, inspect=None):
            result = validate(data, base)
            if diagnostic:
                assert result["record_contract_status"] == "invalid" and any(diagnostic in e for e in result["errors"]), (name, result)
            else:
                assert result["record_contract_status"] == "valid", (name, result)
            if inspect:
                assert inspect(result), (name, result)
            results.append({"case": name, "status": "passed", "expected_diagnostic": diagnostic})
        check("diagnostic_observation_is_not_acceptance", packet, inspect=lambda r: r["review_coverage_complete"]
              and r["semantic_acceptance"] == "not_computed" and r["coverage"]["acceptance_use_pending"] == ["synthetic_review"])
        for name, edit, diagnostic in (
            ("stale_catalog", lambda p: p.update(catalog_sha256="0"*64), "stale catalog_sha256"),
            ("stale_rubric", lambda p: p["records"][0].update(rubric_sha256="0"*64), "mismatched rubric_sha256"),
            ("wrong_course", lambda p: p.update(course_version="other"), "differs from plan"),
            ("missing_evidence_file", lambda p: p["artifacts"][0].update(path="absent.txt"), "missing file"),
            ("stale_artifact", lambda p: p["artifacts"][0].update(sha256="0"*64), "stale sha256"),
            ("stale_plan", lambda p: p["plan"].update(sha256="0"*64), "stale sha256"),
            ("missing_required_score_field", lambda p: p["records"][0].pop("score"), "missing score"),
            ("empty_observed_evidence", lambda p: p["records"][0].update(evidence_references=[]), "observation needs evidence"),
            ("bad_locator", lambda p: p["records"][0]["evidence_references"][0]["locator"].update(end_line=200), "out-of-bounds"),
            ("unknown_artifact", lambda p: p["records"][0]["evidence_references"][0].update(artifact_identifier="absent"), "unknown artifact"),
            ("unknown_unit", lambda p: p["records"][0].update(unit_identifier="absent"), "unknown unit"),
            ("unknown_atom", lambda p: p["records"][0].update(atom_identifier="M13-A99"), "mismatched atom"),
            ("boolean_score", lambda p: p["records"][0].update(score=True), "integer 0..4"),
            ("missing_rationale", lambda p: p["records"][0].update(criterion_rationale=""), "missing criterion_rationale"),
            ("primary_binding_mismatch", lambda p: p["records"][0].update(artifact_sha256="0"*64), "primary evidence differs"),
            ("unrecognized_role", lambda p: p["records"][0].update(reviewer_role="automatic_pass"), "invalid reviewer"),
            ("unknown_calibration", lambda p: p["records"][0].update(calibration_identifier="absent"), "unknown calibration"),
            ("score_three_single_sample", lambda p: p["records"][0].update(score=3), "two evidence locators"),
            ("score_four_missing_route", lambda p: p["records"][0].update(score=4, observed_routes=["normal"]), "all declared routes"),
            ("duplicate_record", lambda p: p["records"].append(copy.deepcopy(p["records"][0])), "duplicate identifier"),
            ("wrong_finding", lambda p: p["records"][0].update(score=0), "score/finding mismatch"),
            ("null_artifact", lambda p: p["artifacts"].append(None), "object list"),
        ):
            bad = copy.deepcopy(packet)
            edit(bad)
            check(name, bad, diagnostic)
        pending = copy.deepcopy(packet)
        pending["records"][0].update(status="not_evaluated", finding="not_evaluated", score=None,
                                    evidence_references=[], artifact_sha256=None, time_range_or_locator=None, observed_routes=[],
                                    observed_behavior=None, criterion_rationale=None, limitation_or_counterexample=None)
        check("honest_not_evaluated", pending, inspect=lambda r: not r["review_coverage_complete"]
              and r["coverage"]["not_evaluated"] == ["synthetic_review"])
        pending["records"][0]["score"] = 0
        check("missing_observation_is_not_zero", pending, "unobserved score")
        missing = copy.deepcopy(packet)
        missing["records"] = []
        check("missing_record_reported_not_silently_passed", missing, inspect=lambda r: not r["review_coverage_complete"]
              and r["coverage"]["missing_records"] == ["entry_observation"])
        contradiction = copy.deepcopy(packet)
        contradiction["records"][0].update(score=0, finding="contradicted")
        check("actual_contradiction_not_offset", contradiction, inspect=lambda r: r["coverage"]["contradicted_or_weak"] == ["synthetic_review"]
              and r["semantic_acceptance"] == "not_computed")
        partial = copy.deepcopy(packet)
        partial["records"][0]["observed_routes"] = ["normal"]
        check("partial_route_coverage", partial, inspect=lambda r: not r["review_coverage_complete"]
              and r["coverage"]["units"][0]["missing_routes"] == ["reentry"])
        for name, edit, diagnostic in (
            ("missing_catalogue_disposition", lambda p: p["coverage"].pop(), "every catalogue"),
            ("duplicate_unit", lambda p: p["units"].append(copy.deepcopy(p["units"][0])), "duplicate identifier"),
            ("undefined_unit", lambda p: p["coverage"][0]["unit_identifiers"].append("absent"), "unknown/mismatched unit"),
            ("unknown_plan_atom", lambda p: p["units"][0].update(atom_identifier="absent"), "unknown atom"),
            ("invalid_stage", lambda p: p["units"][0].update(evaluation_stage="automatic"), "invalid evaluation_stage"),
            ("missing_voice_visual_decision", lambda p: p["units"][0].update(design_decisions=[]), "design_decisions"),
            ("exclude_full_course_journey", lambda p: p.update(scope="complete_course"), "cannot exclude full journey"),
            ("malformed_plan_unit", lambda p: p["units"][0].update(atom_identifier=[]), "unknown atom"),
        ):
            changed, candidate = copy.deepcopy(plan), copy.deepcopy(packet)
            edit(changed)
            rebind_plan(base, changed, candidate)
            check(name, candidate, diagnostic)
        rebind_plan(base, plan, packet)
        unknown = copy.deepcopy(plan)
        unknown["coverage"][-1].update(applicability="not_evaluated", applicability_reason="Journey not yet selected")
        candidate = copy.deepcopy(packet)
        rebind_plan(base, unknown, candidate)
        check("unknown_applicability_reported", candidate, inspect=lambda r: r["coverage"]["unknown_applicability"] == ["M18-C01-v2"]
              and not r["review_coverage_complete"])
        rebind_plan(base, plan, packet)
        pointer = copy.deepcopy(packet)
        pointer["records"][0]["evidence_references"] = [{"artifact_identifier": "observed_trace",
                                                      "locator": {"kind": "json_pointer", "value": "/a~1b/~0key"}}]
        bind_primary(pointer)
        check("RFC6901_escape_resolves", pointer)
        pointer["records"][0]["evidence_references"][0]["locator"]["value"] = "/events/99"
        check("JSON_pointer_out_of_bounds", pointer, "out-of-bounds")
        sustained = copy.deepcopy(packet)
        second = {"artifact_identifier": "observed_doc", "locator": {"kind": "line_range", "start_line": 2, "end_line": 2}}
        sustained["records"][0].update(score=4)
        sustained["records"][0]["evidence_references"].append(second)
        check("four_with_two_observations_and_routes", sustained)
        sustained["records"][0]["evidence_references"][1] = copy.deepcopy(sustained["records"][0]["evidence_references"][0])
        check("duplicate_locator_not_sustained_evidence", sustained, "duplicate evidence")
        calibrated = copy.deepcopy(packet)
        ref = calibrated["records"][0]["evidence_references"][0]
        calibration = {"identifier": "synthetic_calibration", "reviewer_identifier": "synthetic_human_fixture",
                       "reviewer_role": "human_review", "status": "completed", "catalog_sha256": digest(CATALOG),
                       "rubric_sha256": digest(RUBRIC), "evidence_references": [ref],
                       "paired_specimen_references": [ref, second], "independent_example_references": [
                           {"artifact_identifier": "observed_trace", "locator": {"kind": "json_pointer", "value": "/events/0"}}],
                       "disagreement_resolution": "SYNTHETIC only; tests required calibration fields",
                       "limitations": "SYNTHETIC fixture; not a human calibration"}
        calibrated.update(purpose="acceptance", calibrations=[calibration])
        calibrated["records"][0].update(reviewer_role="human_review", reviewer_identifier="synthetic_human_fixture",
                                        calibration_identifier="synthetic_calibration")
        check("calibration_structure_only", calibrated, inspect=lambda r: not r["coverage"]["acceptance_use_pending"]
              and r["semantic_acceptance"] == "not_computed")
        calibrated["calibrations"][0]["paired_specimen_references"] = []
        check("completed_calibration_without_specimens", calibrated, "observation needs evidence")
        calibrated["calibrations"][0]["paired_specimen_references"] = [ref, second]
        calibrated["calibrations"][0]["independent_example_references"] = [ref]
        check("holdout_cannot_reuse_paired_specimen", calibrated, "overlap paired specimens")
        calibrated["calibrations"][0]["independent_example_references"] = [
            {"artifact_identifier": "observed_trace", "locator": {"kind": "json_pointer", "value": "/events/0"}}]
        mismatch = copy.deepcopy(calibrated)
        mismatch["calibrations"][0]["reviewer_identifier"] = "other_fixture_reviewer"
        check("calibration_reviewer_mismatch", mismatch, "reviewer differs")
        model = copy.deepcopy(calibrated)
        model["calibrations"][0]["reviewer_role"] = "model_judge"
        model["records"][0]["reviewer_role"] = "model_judge"
        check("model_acceptance_needs_authorization_evidence", model, "authorization_reference")
        model["calibrations"][0]["authorization_reference"] = [
            {"artifact_identifier": "observed_doc", "locator": {"kind": "line_range", "start_line": 2, "end_line": 2}}]
        check("model_binding_does_not_sign_acceptance", model, inspect=lambda r: r["semantic_acceptance"] == "not_computed")
        for atom, stage, kind in (("M18-A08", "learner_trial", "learner_record"),
                                  ("M18-C01-v2", "controlled_runtime", "runtime_log")):
            _, separate = fixture(base, atom, stage)
            separate["artifacts"][1]["kind"] = kind
            record = separate["records"][0]
            record.update(score=None, finding="inconclusive",
                          reviewer_role="learner_observer" if stage == "learner_trial" else "author_self_review",
                          evidence_references=[{"artifact_identifier":"observed_trace",
                                                "locator":{"kind":"json_pointer","value":"/events"}}])
            bind_primary(separate)
            check(atom + "_separate_evidence", separate, inspect=lambda r: r["learner_effect"] == "not_computed")
            separate["records"][0]["score"] = 4
            check(atom + "_cannot_use_expert_score", separate, "null score")
        _, no_learner = fixture(base, "M18-A08", "learner_trial")
        no_learner["records"][0].update(score=None, finding="inconclusive")
        check("learner_claim_needs_learner_record", no_learner, "actual learner record")
        _, media = fixture(base, "M13-A05", "media_review")
        check("sound_review_cannot_use_document", media, "actual audio/video")
        wav = base / "tone.wav"
        subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "anullsrc=r=8000:cl=mono",
                        "-t", "2", "-y", str(wav)], check=True, timeout=30)
        media["artifacts"].append({"identifier": "synthetic_audio", "kind": "audio", "path": "tone.wav",
                                  "sha256": digest(wav), "duration_seconds": 2})
        media["records"][0]["evidence_references"] = [{"artifact_identifier": "synthetic_audio",
                                                     "locator": {"kind": "time_range", "start_seconds": 0, "end_seconds": 1}}]
        bind_primary(media)
        check("actual_media_bytes_and_duration", media)
        bad_media = copy.deepcopy(media)
        bad_media["artifacts"][-1]["duration_seconds"] = 10
        check("declared_duration_cannot_fake_media_bounds", bad_media, "media duration differs")
        media["records"][0]["evidence_references"][0]["locator"]["end_seconds"] = 3
        check("time_range_exceeds_actual_media", media, "out-of-bounds")
        _, cli_packet = fixture(base)
        path = base / "packet.json"
        path.write_text(json.dumps(cli_packet))
        process = subprocess.run([sys.executable, "-B", str(Path(__file__).with_name("validate_immersion_review.py")),
                                  str(path), "--output", str(base / "result.json")], capture_output=True, text=True)
        assert process.returncode == 0 and read_json(base / "result.json")["semantic_acceptance"] == "not_computed", process.stderr
        results.append({"case": "actual_CLI_and_output", "status": "passed", "expected_diagnostic": None})
    report = {"synthetic_only": True, "actual_learner_trials": 0, "actual_human_calibrations": 0,
              "passed": len(results), "cases": results}
    if args.output:
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
