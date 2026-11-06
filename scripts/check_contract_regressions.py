#!/usr/bin/env python3
"""Isolated acceptance probes. Synthetic approvals are never course approval evidence."""

import copy
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from unittest.mock import patch
from types import SimpleNamespace
import wave

import generate_course_voice as voice
from production_contract import check_previous, event_digest, STAGES, validate_joint
from validate_course import validate as course_check
from validate_production import validate, approval_fingerprint, file_digest
from demo_contract import GATE_BY_KIND
from demo_regression_fixtures import sync_workflow, install_runtime, install_content_quality

ROOT = Path(__file__).resolve().parents[1]
RESULTS = []


def fill(value):
    if isinstance(value, str):
        return re.sub(r"\{\{.*?\}\}", "Synthetic fixture", value)
    if isinstance(value, list):
        return [fill(item) for item in value]
    if isinstance(value, dict):
        return {key: fill(item) for key, item in value.items()}
    return value


def check(name, errors, expected=None):
    if expected is None:
        assert not errors, (name, errors)
    else:
        assert any(expected in error for error in errors), (name, errors)
    RESULTS.append({"case": name, "status": "passed"})


def event(data, event_type, status, scopes=(), confirmations=(), evidence=("verification",),
          affected_assets=(), invalidated_from_status=None):
    history = data["status_history"]
    row = {
        "event_identifier": f"event_{len(history)}", "event_type": event_type,
        "status": status, "recorded_at": "2026-11-03T00:00:00Z",
        "recorded_by": "Synthetic recorder", "reason": "Isolated acceptance probe",
        "course_version": data["course_version"], "scope_identifiers": list(scopes),
        "confirmation_identifiers": list(confirmations), "evidence_references": list(evidence),
        "affected_asset_identifiers": list(affected_assets),
        "invalidated_from_status": invalidated_from_status,
        "evidence_fingerprints": {
            reference: next(row.get("content_sha256") for row in data["evidence_files"]
                            if row["reference_identifier"] == reference)
            for reference in evidence
        },
        "previous_event_sha256": history[-1]["event_sha256"] if history else None,
        "asset_snapshots": {
            asset["asset_identifier"]: {
                "asset_version": asset["asset_version"],
                "file_snapshots": copy.deepcopy(asset["acceptance"]["file_snapshots"])}
            for asset in data["assets"]
            if asset.get("delivery_class") == "formal" and asset.get("status") == "accepted"
        } if status in STAGES[3:] else {},
    }
    row["event_sha256"] = event_digest(row)
    history.append(row)
    data["current_status"] = status
    sync_workflow(data)


def main():
    with tempfile.TemporaryDirectory(prefix="course-contract-check-") as directory:
        base = Path(directory)
        blueprint = fill(json.loads((ROOT / "assets/course-blueprint.template.json").read_text()))
        for source in blueprint["sources"]:
            source["verification_status"] = "verified"
        draft = fill(json.loads((ROOT / "assets/production-manifest.template.json").read_text()))
        draft["approval_subjects"].sort(key=lambda row: {
            "design": 0, "media_contract": 1, "media_sample": 2, "clarification": 3, "demo": 4
        }[row["kind"]])
        draft["work_scope"]["endpoint"] = "effect_evaluated"
        for entry in draft["evidence_files"]:
            path = base / entry["path"]
            path.write_text(json.dumps(blueprint) if entry["kind"] == "course_blueprint"
                            else "Synthetic content, never approval evidence.\n")
            entry.update(course_version="0.1", content_sha256=file_digest(path),
                         bound_identifiers=["objective_core"])
        install_content_quality(draft, base, blueprint)
        for reference, kind in (
                ("clarification_intake", "clarification_intake"),
                ("experience_blueprint", "experience_blueprint"),
                ("storyboard", "storyboard"),
                ("interaction_visual_spec", "interaction_visual_spec")):
            if any(row["reference_identifier"] == reference for row in draft["evidence_files"]):
                continue
            path = base / (reference + ".txt")
            path.write_text("Synthetic experience evidence: " + reference)
            draft["evidence_files"].append({
                "reference_identifier": reference, "kind": kind, "path": path.name,
                "course_version": "0.1", "content_sha256": file_digest(path),
                "bound_identifiers": ["objective_core"],
            })
        for identifier, kind in (
                ("human_record", "human_confirmation"), ("voice_reference", "voice_reference"),
                ("sample_entry", "runtime"), ("audio_probe", "audio_probe"),
                ("functional", "functional_acceptance"), ("trial", "learner_trial"),
                ("effect", "effect_evaluation")):
            path = base / (identifier + ".txt")
            path.write_text("Synthetic probe only: " + identifier)
            draft["evidence_files"].append({
                "reference_identifier": identifier, "kind": kind, "path": path.name,
                "course_version": "0.1", "content_sha256": file_digest(path),
                "bound_identifiers": ["objective_core"],
            })
        draft["status_history"] = []
        event(draft, "advance", "design_draft")
        check("v12_draft", validate(draft, base))
        check("joint_draft", validate_joint(draft, base))
        accepted_prototype = copy.deepcopy(draft)
        accepted_prototype["work_scope"]["scope_type"] = "course_implementation"
        accepted_prototype["work_scope"]["endpoint"] = "functional_accepted"
        accepted_prototype["delivery_endpoint"] = "interaction_complete_prototype"
        accepted_prototype["acceptance_status"] = "accepted"
        accepted_prototype["accepted_scope"] = "interaction"
        accepted_prototype["acceptance_evidence"] = {
            "evidence_references": ["verification"],
            "review_owner": "Synthetic human",
            "accepted_at": "2026-11-03T00:00:00Z",
            "reviewed_version": accepted_prototype["course_version"],
        }
        check("unconfirmed_interaction_prototype_rejected", validate(accepted_prototype, base),
              "delivery_endpoint requires a later formal current_status")
        bad = copy.deepcopy(accepted_prototype)
        bad["accepted_scope"] = None
        check("accepted_requires_scope", validate(bad, base), "accepted_scope does not match")
        bad = copy.deepcopy(draft)
        bad["delivery_endpoint"] = "functional_course"
        check("endpoint_requires_formal_status", validate(bad, base),
              "delivery_endpoint requires a later formal current_status")
        bad = copy.deepcopy(accepted_prototype)
        bad["acceptance_evidence"]["evidence_references"] = ["missing_evidence"]
        check("acceptance_requires_known_evidence", validate(bad, base),
              "acceptance_evidence unknown evidence reference")
        blueprint_path = base / "course-blueprint.json"

        def approve(data, subject):
            gate = GATE_BY_KIND[subject["kind"]]
            record = {
                "confirmation_identifier": f"confirmation_{len(data['status_history'])}_{subject['kind']}",
                "scope_identifier": subject["scope_identifier"], "confirmed_by": "Synthetic human",
                "confirmed_at": "2026-11-03T00:00:00Z",
                "confirmed_version": subject["subject_version"],
                "content_sha256": approval_fingerprint(data, subject, base),
                "dependency_fingerprints": {
                    identifier: approval_fingerprint(
                        data, next(row for row in data["approval_subjects"]
                                   if row["scope_identifier"] == identifier), base)
                    for identifier in subject["depends_on_scope_identifiers"]
                },
                "evidence_references": ["human_record"],
            }
            data["approval_gates"][gate]["confirmations"].append(record)
            event(data, "reconfirm", data["current_status"], [subject["scope_identifier"]],
                  [record["confirmation_identifier"]])

        design = copy.deepcopy(draft)
        approve(design, design["approval_subjects"][3])
        approve(design, design["approval_subjects"][0])
        event(design, "advance", "design_confirmed")
        design["approval_gates"]["design_confirmation"]["status"] = "confirmed"
        check("active_design_approval", validate(design, base))
        metadata_only = copy.deepcopy(design)
        metadata_only["experience_profile"]["coverage_status"] = "reviewed"
        check("experience_review_status_not_in_fingerprint", validate(metadata_only, base))
        for pointer in ("/experience_profile", "/experience_profile/coverage_status"):
            bad_pointer = copy.deepcopy(draft)
            bad_pointer["approval_subjects"][0]["materials"][-1]["json_pointers"].append(pointer)
            check(f"reject_experience_metadata_pointer_{pointer}", validate(bad_pointer, base),
                  "manifest pointers")
        changed_route = copy.deepcopy(design)
        changed_route["experience_profile"]["beat_identifiers"].reverse()
        assert validate(changed_route, base), "Changed beat order must invalidate its design approval"
        RESULTS.append({"case": "changed_beat_order_invalidates_approval", "status": "passed"})
        participation_file = base / "scene-interaction-plan.json"
        original_participation = participation_file.read_bytes()
        participation_file.write_bytes(original_participation + b"\nChanged interaction content")
        assert validate(design, base), "Changed participation plan must invalidate its design approval"
        RESULTS.append({"case": "changed_participation_invalidates_approval", "status": "passed"})
        participation_file.write_bytes(original_participation)
        probe_path = base / "manifest-probe.json"
        probe_path.write_text(json.dumps(design), encoding="utf-8")
        subprocess.run([sys.executable, str(ROOT / "scripts/validate_production.py"),
                        str(probe_path)], check=True)
        bp_reviewed = copy.deepcopy(blueprint)
        bp_reviewed["evaluation_plan"]["design_review"].update(status="completed",
                                                              evidence_references=["verification"])
        blueprint_path.write_text(json.dumps(bp_reviewed))
        next(row for row in design["evidence_files"] if row["kind"] == "course_blueprint")[
            "content_sha256"] = file_digest(blueprint_path)
        check("joint_design_confirmed", validate_joint(design, base))
        check("phase_metadata_not_in_design_fingerprint", validate(design, base))
        total_version = copy.deepcopy(design)
        total_version["course_version"] = "0.2"
        for entry in total_version["evidence_files"]:
            entry["bound_versions"] = {"design_whole_course": "0.1"}
        check("package_version_preserves_unchanged_scope_approval", validate(total_version, base))

        bad = copy.deepcopy(design)
        bad["course_identifier"] = "wrong_course"
        check("wrong_course", validate_joint(bad, base), "course_identifier differs")
        bad = copy.deepcopy(design)
        bad["evidence_registry"][0]["source_references"] = ["unknown_source"]
        check("unknown_source", validate_joint(bad, base), "unknown source reference")
        bad = copy.deepcopy(design)
        bad["assets"] = []
        check("missing_required_resources", validate_joint(bad, base), "required resource lacks asset")
        bad = copy.deepcopy(design)
        bad["learning_records"]["minimum_fields"].remove("evaluation_status")
        check("record_fields_mismatch", validate_joint(bad, base), "record fields differ")
        bad_bp = copy.deepcopy(bp_reviewed)
        bad_bp["evaluation_plan"]["learner_trial"].update(status="completed", evidence_references=["missing"])
        blueprint_path.write_text(json.dumps(bad_bp))
        check("completed_trial_on_draft", validate_joint(draft, base), "completion differs")
        check("missing_phase_evidence", validate_joint(draft, base), "evidence not registered")
        blueprint_path.write_text(json.dumps(bp_reviewed))

        bad_bp = copy.deepcopy(blueprint)
        bad_bp["scenes"][2]["task"]["outcomes"]["success"] = "scene_practice"
        check("correct_self_loop", course_check(bad_bp, base), "success must advance")
        bad_bp["scenes"][2]["task"]["outcomes"]["success"] = "scene_instruction"
        check("multi_scene_correct_cycle", course_check(bad_bp, base), "correct outcomes cannot reach")
        bad_bp = copy.deepcopy(blueprint)
        bad_bp["scenes"][3]["task"]["outcome_conditions"]["continue_after_review"] = ["feedback_viewed"]
        check("continue_without_attempt", course_check(bad_bp, base), "requires attempt_saved")
        bad_bp = copy.deepcopy(blueprint)
        bad_bp["learning_core"] = "TBD"
        check("bare_tbd", course_check(bad_bp, base, complete_design=True), "TBD marker")
        bad_bp["learning_core"] = "Final statement"
        bad_bp["sources"][0]["original_quote"] = "The source literally says TBD."
        check("literal_quote_allowed", course_check(bad_bp, base, complete_design=True))
        shared = copy.deepcopy(blueprint)
        second_goal = copy.deepcopy(shared["learning_objectives"][0])
        second_goal["objective_identifier"] = "objective_second"
        shared["learning_objectives"].append(second_goal)
        shared["knowledge_organization"]["units"][0]["objective_identifiers"].append("objective_second")
        second_instruction = copy.deepcopy(shared["scenes"][1])
        second_instruction.update(scene_identifier="scene_instruction_second",
                                  beat_identifiers=["beat_instruction_second"],
                                  objective_identifiers=["objective_second"])
        shared["scenes"][1]["next_scene_identifier"] = "scene_instruction_second"
        shared["scenes"].insert(2, second_instruction)
        shared["knowledge_organization"]["units"][0]["teaching_scene_identifiers"].append("scene_instruction_second")
        shared["scope_coverage"]["required_content_inventory"][0][
            "objective_identifiers"
        ].append("objective_second")
        shared["scope_coverage"]["coverage_map"][0]["scene_identifiers"].append(
            "scene_instruction_second"
        )
        shared["scope_coverage"]["coverage_map"][0]["beat_identifiers"].append(
            "beat_instruction_second"
        )
        second_plan = copy.deepcopy(shared["instructional_design"]["objective_plans"][0])
        second_plan.update(objective_identifier="objective_second",
                           teaching_scene_identifiers=["scene_instruction_second"])
        second_plan["demonstration"]["scene_identifiers"] = ["scene_instruction_second"]
        shared["instructional_design"]["objective_plans"].append(second_plan)
        for scene in shared["scenes"]:
            if scene["kind"] in ("practice", "transfer"):
                scene["objective_identifiers"].append("objective_second")
        second_evaluation = copy.deepcopy(shared["evaluation_plan"]["objective_evaluations"][0])
        second_evaluation["objective_identifier"] = "objective_second"
        shared["evaluation_plan"]["objective_evaluations"].append(second_evaluation)
        check("shared_knowledge_across_objective_subsets", course_check(shared, base, learning_design=True))

        # Actual encoded probe files test audio metadata, never media quality.
        silent = base / "silent.mp4"
        sounded = base / "sound.mp4"
        common = ["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi",
                  "-i", "color=c=black:s=32x32:r=5"]
        subprocess.run(common + ["-t", "0.4", "-c:v", "libx264", str(silent)], check=True)
        subprocess.run(common + ["-f", "lavfi", "-i", "sine=frequency=440:sample_rate=24000",
                                "-t", "0.4", "-c:v", "libx264", "-c:a", "aac", str(sounded)],
                       check=True)
        diagram = base / "diagram.svg"
        diagram.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32"/>')
        sample = copy.deepcopy(design)
        sample["media_production_contract"]["voice_reference_identifiers"] = ["voice_reference"]
        for asset, path in zip(sample["assets"], [sounded, diagram]):
            asset.update(status="accepted", files=[{"path": path.name}])
            asset["governance"]["privacy_review_status"] = "reviewed"
            asset["accessibility"]["status"] = "accepted"
            asset["acceptance"] = {
                "asset_version": asset["asset_version"],
                "file_snapshots": [{"path": path.name, "content_sha256": file_digest(path)}],
                "checks": ["decodable", "content_correct", "continuity", "equivalent_path",
                           "voice_content", "lip_synchronization", "timbre_continuity", "mix"],
                "evidence_references": ["verification"],
            }
            if asset["kind"] == "linear_video":
                asset["delivery"].update(
                    formal_linear_video=False, embedded_voice=True, environment_and_action_audio=True,
                    separate_web_audio_stems=True, separate_branch_audio="not_applicable",
                    branch_audio_not_applicable_reason="No branches in encoded probe",
                    audio_probe_evidence_references=["audio_probe"])
        complete_demo = copy.deepcopy(design)
        complete_demo["delivery_endpoint"] = "interaction_complete_prototype"
        complete_demo["acceptance_status"] = "browser_verified"
        complete_demo["assets"][1] = copy.deepcopy(sample["assets"][1])
        install_runtime(complete_demo, base)
        check("full_course_demo_differs_only_by_video", validate(complete_demo, base))
        incomplete_demo = copy.deepcopy(complete_demo)
        incomplete_demo["assets"][1]["status"] = "ready"
        check("full_course_demo_rejects_incomplete_non_video_asset",
              validate(incomplete_demo, base), "requires accepted non-video asset")
        representative = sample["representative_sample"]
        representative["covered_asset_identifiers"] = ["video_introduction", "diagram_core"]
        representative["candidate_asset_versions"] = {"video_introduction": "0.1", "diagram_core": "0.1"}
        representative["acceptance_evidence_references"] = ["verification"]
        for risk in representative["risk_coverage"]:
            risk.update(status="passed", evidence_references=["verification"])
        sample["approval_subjects"][2]["materials"] = [
            {"source": "evidence_file", "reference_identifier": "sample_entry", "fingerprint_mode": "bytes"}]
        for subject in sample["approval_subjects"][1:3]:
            approve(sample, subject)
        event(sample, "advance", "media_sample_confirmed")
        sample["approval_gates"]["media_sample_confirmation"]["status"] = "confirmed"
        check("accepted_sample_with_actual_audio", validate(sample, base))
        facilitated = copy.deepcopy(sample)
        facilitated["work_scope"]["learner_delivery_type"] = "facilitated_instruction"
        facilitated["representative_sample"].update(
            media_modes=[], covered_asset_identifiers=[], candidate_asset_versions={}
        )
        facilitated["representative_sample"]["risk_coverage"] = [
            {
                "risk_identifier": identifier, "critical": True,
                "selection_reason": "Synthetic facilitated delivery risk",
                "status": "passed", "evidence_references": ["verification"],
            }
            for identifier in (
                "content", "facilitator_handoff", "representative_delivery", "equivalent_path"
            )
        ]
        facilitated_sample_subject = next(
            row for row in facilitated["approval_subjects"] if row["kind"] == "media_sample"
        )
        facilitated_sample_confirmation = next(
            row for row in facilitated["approval_gates"]["media_sample_confirmation"]["confirmations"]
            if row["scope_identifier"] == facilitated_sample_subject["scope_identifier"]
        )
        facilitated_sample_confirmation["content_sha256"] = approval_fingerprint(
            facilitated, facilitated_sample_subject, base
        )
        check("facilitated_delivery_uses_walkthrough_not_media_or_mobile", validate(facilitated, base))
        no_video_blueprint = copy.deepcopy(bp_reviewed)
        no_video_blueprint["media_resources"] = [no_video_blueprint["media_resources"][1]]
        no_video_blueprint["scenes"][0]["media_resource_identifiers"] = ["diagram_core"]
        for unit in no_video_blueprint["opening"].get("information_units", []):
            unit["media_resource_identifiers"] = ["diagram_core"]
        original_blueprint_bytes = blueprint_path.read_bytes()
        blueprint_path.write_text(json.dumps(no_video_blueprint))
        no_video = copy.deepcopy(draft)
        no_video["assets"] = [copy.deepcopy(sample["assets"][1])]
        no_video["work_scope"]["covered_asset_identifiers"] = ["diagram_core"]
        no_video["media_production_contract"].update(voice_present=False, voice_reference_identifiers=[])
        no_video["approval_subjects"][1]["covered_identifiers"] = ["diagram_core"]
        no_video["approval_subjects"][2]["materials"] = copy.deepcopy(sample["approval_subjects"][2]["materials"])
        no_video["representative_sample"] = copy.deepcopy(sample["representative_sample"])
        no_video["representative_sample"].update(
            media_modes=["diagram"], covered_asset_identifiers=["diagram_core"],
            candidate_asset_versions={"diagram_core": "0.1"})
        no_video["representative_sample"]["risk_coverage"][2].update(
            critical=False, status="not_applicable", not_applicable_reason="No voices or video")
        approve(no_video, no_video["approval_subjects"][3])
        approve(no_video, no_video["approval_subjects"][0])
        event(no_video, "advance", "design_confirmed")
        no_video["approval_gates"]["design_confirmation"]["status"] = "confirmed"
        for subject in no_video["approval_subjects"][1:3]:
            approve(no_video, subject)
        event(no_video, "advance", "media_sample_confirmed")
        no_video["approval_gates"]["media_sample_confirmation"]["status"] = "confirmed"
        check("diagram_only_sample_needs_no_video_or_voice", validate(no_video, base))
        check("joint_diagram_only_course", validate_joint(no_video, base))
        blueprint_path.write_bytes(original_blueprint_bytes)
        bad = copy.deepcopy(sample)
        bad["assets"][0]["status"] = "planned"
        check("planned_sample_blocked", validate(bad, base), "candidate not accepted")
        bad = copy.deepcopy(sample)
        bad["representative_sample"]["risk_coverage"][2]["status"] = "planned"
        check("uncovered_critical_risk", validate(bad, base), "critical sample risk not covered")
        bad = copy.deepcopy(sample)
        bad["assets"][0]["delivery"]["embedded_voice"] = False
        check("formal_flag_cannot_bypass_audio", validate(bad, base), "formal video requires embedded_voice")
        bad = copy.deepcopy(sample)
        bad["assets"][0]["files"] = [{"path": silent.name}]
        bad["assets"][0]["acceptance"]["file_snapshots"] = [
            {"path": silent.name, "content_sha256": file_digest(silent)}]
        check("silent_mp4_blocked", validate(bad, base), "no real audio stream")
        bad = copy.deepcopy(sample)
        bad["assets"][0]["delivery_class"] = "intermediate"
        check("required_intermediate_blocked", validate(bad, base), "cannot be intermediate")

        previous = copy.deepcopy(sample)
        revised = copy.deepcopy(sample)
        event(revised, "invalidate", "design_confirmed", ["media_sample_hardest_loop"])
        revised["approval_gates"]["media_sample_confirmation"]["status"] = "pending"
        revised["representative_sample"]["selection_reason"] = "Revised actual sample"
        check("rollback_preserves_history", validate(revised, base))
        check("append_history_prefix", check_previous(previous, revised))
        changed_dependencies = copy.deepcopy(revised)
        changed_dependencies["approval_subjects"][2]["depends_on_scope_identifiers"] = [
            "design_whole_course"
        ]
        check("approval_dependencies_are_immutable",
              check_previous(previous, changed_dependencies), "dependencies are immutable")
        bad = copy.deepcopy(revised)
        bad["status_history"] = bad["status_history"][-1:]
        check("deleted_history_detected", check_previous(previous, bad), "exact prefix")
        bad = copy.deepcopy(revised)
        bad["status_history"][0]["reason"] = "Changed old history"
        check("rewritten_event_detected", validate(bad, base), "event content changed")
        check("rewritten_prefix_detected", check_previous(previous, bad), "exact prefix")
        approve(revised, revised["approval_subjects"][2])
        event(revised, "advance", "media_sample_confirmed")
        revised["approval_gates"]["media_sample_confirmation"]["status"] = "confirmed"
        check("reconfirm_with_archive", validate(revised, base))
        editorial = copy.deepcopy(revised)
        design_file = base / "course-design.md"
        original_design = design_file.read_bytes()
        design_file.write_bytes(original_design + b"\n")
        subject = editorial["approval_subjects"][0]
        original_approval = editorial["approval_gates"]["design_confirmation"]["confirmations"][0]
        subject["editorial_changes"] = [{
            "classification": "non_semantic_editorial", "approved_sha256": original_approval["content_sha256"],
            "current_sha256": approval_fingerprint(editorial, subject, base),
            "recorded_by": "Synthetic reviewer", "recorded_at": "2026-11-03T00:00:00Z",
            "reason": "Whitespace only", "evidence_references": ["verification"],
        }]
        check("editorial_change_preserves_dependency_approval", validate(editorial, base))
        design_file.write_bytes(original_design)
        bad = copy.deepcopy(revised)
        event(bad, "invalidate", "design_draft", ["design_whole_course"])
        bad["approval_gates"]["design_confirmation"]["status"] = "pending"
        bad["approval_gates"]["media_sample_confirmation"]["status"] = "pending"
        check("design_invalidates_dependent_sample", validate(bad, base))
        bad["current_status"] = "media_sample_confirmed"
        check("stale_downstream_status", validate(bad, base), "replay-derived design_draft")
        bad = copy.deepcopy(revised)
        event(bad, "advance", "functional_accepted")
        check("stage_skip_rejected", validate(bad, base), "cannot skip")

        production = copy.deepcopy(revised)
        production["demo_completion"] = copy.deepcopy(complete_demo["demo_completion"])
        install_runtime(production, base)
        approve(production, production["approval_subjects"][4])
        install_runtime(production, base, formal=True)
        event(production, "advance", "production_complete")
        check("production_complete", validate(production, base))
        bp_ready = copy.deepcopy(bp_reviewed)
        for resource, path in zip(bp_ready["media_resources"], [sounded, diagram]):
            resource.update(production_status="ready", file_path=path.name)
        unverified_blueprint = copy.deepcopy(bp_ready)
        for source in unverified_blueprint["sources"]:
            source["verification_status"] = "provided"
        blueprint_path.write_text(json.dumps(unverified_blueprint))
        check("production_requires_verified_sources", validate_joint(production, base), "source not verified")
        for source in bp_ready["sources"]:
            source["verification_status"] = "verified"
        blueprint_path.write_text(json.dumps(bp_ready))
        check("joint_production_files", validate_joint(production, base))
        bad = copy.deepcopy(production)
        bad["assets"][1]["asset_version"] = "0.2"
        bad["assets"][1]["acceptance"]["asset_version"] = "0.2"
        check("changed_asset_cannot_reuse_stage_acceptance", validate(bad, base), "delivered assets changed")
        functionally_tested = copy.deepcopy(production)
        event(functionally_tested, "advance", "functional_accepted", evidence=["functional"])
        event(functionally_tested, "invalidate", "production_complete",
              affected_assets=["diagram_core"], invalidated_from_status="functional_accepted")
        check("downstream_invalidation_preserves_both_approval_gates", validate(functionally_tested, base))
        bad = copy.deepcopy(production)
        next(row for row in bad["evidence_files"] if row["reference_identifier"] == "verification")[
            "content_sha256"] = "0" * 64
        check("outdated_evidence_hash", validate(bad, base), "file content changed")
        bad = copy.deepcopy(production)
        verification_file = base / "verification.md"
        original_verification = verification_file.read_bytes()
        verification_file.write_bytes(original_verification + b"New unrelated evidence")
        next(row for row in bad["evidence_files"] if row["reference_identifier"] == "verification")[
            "content_sha256"] = file_digest(verification_file)
        check("replaced_stage_evidence_cannot_reuse_advance", validate(bad, base), "changed since the advance")
        verification_file.write_bytes(original_verification)
        complete = copy.deepcopy(production)
        for status, ref in (("functional_accepted", "functional"), ("learner_trial_complete", "trial"),
                            ("effect_evaluated", "effect")):
            event(complete, "advance", status, evidence=[ref])
        complete["effect_result"] = {
            "conclusion": "not_supported", "objective_identifiers": ["objective_core"],
            "conditions": "Synthetic conditions", "uncertainty": "Synthetic uncertainty",
            "retention_and_transfer_scope": "Not studied", "evidence_references": ["effect"],
        }
        check("negative_effect_can_complete_process", validate(complete, base))
        complete["effect_result"]["conclusion"] = "inconclusive"
        check("inconclusive_effect_can_complete_process", validate(complete, base))
        complete["effect_result"]["conclusion"] = "proven"
        check("invalid_effect_conclusion", validate(complete, base), "conclusion invalid")

        bad = copy.deepcopy(draft)
        bad["evaluation_capabilities"]["open_response_review"]["mode"] = "verified_ai"
        check("ai_mode_disabled_conflict", validate(bad, base), "must agree")
        ai = bad["evaluation_capabilities"]["ai_evaluation"]
        ai.update(enabled=True, evaluator_identifier="evaluator", evaluator_version="1",
                  prompt_version="1", rubric_version="1", objective_identifiers=["objective_core"],
                  configuration_evidence_references=["evaluation_plan"],
                  validation_evidence_references=["verification"])
        ai["validation_binding"] = {key: ai[key] for key in (
            "evaluator_identifier", "evaluator_version", "prompt_version", "rubric_version", "objective_identifiers")}
        ai["validation_binding"]["configuration_fingerprints"] = {
            "evaluation_plan": file_digest(base / "evaluation-plan.md")}
        check("ai_bound_configuration", validate(bad, base))
        ai["prompt_version"] = "2"
        check("ai_changed_prompt_invalidates", validate(bad, base), "binding differs: prompt_version")

        local = fill(json.loads((ROOT / "assets/asset-manifest.template.json").read_text()))
        (base / "asset-process.md").write_text("Synthetic asset process")
        check("asset_scope_without_course_profile", validate(local, base))
        parent_path = base / "parent-manifest.json"
        parent_path.write_text(json.dumps(design), encoding="utf-8")
        parent_confirmation = design["approval_gates"]["design_confirmation"]["confirmations"][0]
        inherited = copy.deepcopy(local)
        inherited["work_scope"]["parent_manifest_reference"] = parent_path.name
        inherited["work_scope"]["inherited_confirmations"] = [{
            "confirmation_identifier": parent_confirmation["confirmation_identifier"],
            "scope_identifier": parent_confirmation["scope_identifier"],
            "subject_version": design["approval_subjects"][0]["subject_version"],
            "content_sha256": parent_confirmation["content_sha256"],
            "parent_manifest_sha256": file_digest(parent_path),
        }]
        check("resolved_parent_confirmation", validate(inherited, base))
        inherited["work_scope"]["inherited_confirmations"][0]["parent_manifest_sha256"] = "0" * 64
        check("changed_parent_manifest_rejected", validate(inherited, base), "parent manifest file changed")
        local["current_status"] = "production_complete"
        check("asset_scope_cannot_promote_parent", validate(local, base), "parent's course lifecycle")
        invalid_local = copy.deepcopy(draft)
        invalid_local["work_scope"]["scope_type"] = "local_design"
        check("local_design_endpoint_cannot_claim_full_effect", validate(invalid_local, base), "endpoint exceeds")

        # Error inputs must yield diagnostics, not unhandled Python exceptions.
        for invalid in ([], {}, None):
            for key in ("kind", "response_type", "pedagogical_role"):
                malformed = copy.deepcopy(blueprint)
                target = malformed["scenes"][2] if key == "kind" else malformed["scenes"][2]["task"]
                target[key] = invalid
                assert course_check(malformed, base)
            for key, target_path in (
                    ("type", "evidence_registry"), ("kind", "assets")):
                malformed = copy.deepcopy(draft)
                malformed[target_path][0][key] = invalid
                assert validate(malformed, base)
        RESULTS.append({"case": "malformed_nested_types_return_diagnostics", "status": "passed"})

        page = base / "index.html"
        css = base / "course-page.css"
        css.write_bytes((ROOT / "assets/course-page.css").read_bytes())
        markup = fill((ROOT / "assets/course-page.template.html").read_text())
        markup = markup.replace("</body>", "<script>function f(){if(true){return 1;}}</script></body>")
        page.write_text(markup)
        page_script = ROOT / "scripts/validate_page_structure.py"
        result = subprocess.run([sys.executable, str(page_script), str(page)], capture_output=True, text=True)
        check("legal_javascript_braces", [] if result.returncode == 0 else [result.stderr])
        page.write_text(markup.replace("Synthetic fixture", "{{COURSE_TITLE}}", 1))
        result = subprocess.run([sys.executable, str(page_script), str(page)], capture_output=True, text=True)
        check("real_page_placeholder_rejected", [result.stderr], "模板")
        page.write_text(markup)
        receipt = base / "dom-receipt.json"
        receipt.write_text(json.dumps({"url": "http://localhost/probe", "captured_at": "synthetic",
                                     "browser": "synthetic", "application_version": "0.1",
                                     "viewport": {"width": 390}, "dom_sha256": file_digest(page)}))
        result = subprocess.run([sys.executable, str(page_script), str(page), "--mode", "runtime_dom",
                                 "--runtime-evidence", str(receipt)], capture_output=True, text=True)
        check("runtime_dom_receipt", [] if result.returncode == 0 else [result.stderr])
        page.write_text("<div id='root'></div>")
        result = subprocess.run([sys.executable, str(page_script), str(page), "--mode", "runtime_dom",
                                 "--runtime-evidence", str(receipt)], capture_output=True, text=True)
        check("runtime_shell_is_not_a_dom_pass", [result.stderr], "哈希")
        (base / "video-led-course-page.css").write_bytes((ROOT / "assets/video-led-course-page.css").read_bytes())
        video_markup = fill((ROOT / "assets/video-led-course-page.template.html").read_text())
        page.write_text(video_markup)
        result = subprocess.run([sys.executable, str(page_script), str(page)], capture_output=True, text=True)
        check("video_profile_bounded_region", [] if result.returncode == 0 else [result.stderr])
        without_card = re.sub(r'<div id="task-layer" hidden>.*?</section>\s*</div>',
                              '<div id="task-layer" hidden></div>', video_markup, flags=re.S)
        assert without_card != video_markup
        page.write_text(without_card)
        result = subprocess.run([sys.executable, str(page_script), str(page)], capture_output=True, text=True)
        check("video_profile_needs_no_card", [] if result.returncode == 0 else [result.stderr])
        page.write_text(without_card.replace('data-experience-profile="video_led_web"', ""))
        result = subprocess.run([sys.executable, str(page_script), str(page)], capture_output=True, text=True)
        check("generic_profile_still_requires_work_surface", [result.stderr], "task-surface")
        page.write_text(video_markup.replace('aria-labelledby="task-title"', ""))
        result = subprocess.run([sys.executable, str(page_script), str(page)], capture_output=True, text=True)
        check("scene_region_requires_accessible_name", [result.stderr], "可访问名称")

        model_dir = base / "model"
        model_dir.mkdir()
        (model_dir / "config.json").write_text('{"tts_model_type":"base"}')
        (model_dir / "model.safetensors.index.json").write_text(
            '{"weight_map":{"layer":"model-00001-of-00001.safetensors"}}')
        (model_dir / "model-00001-of-00001.safetensors").write_bytes(b"synthetic weight")
        assert len(voice.model_identity(model_dir)) == 3
        RESULTS.append({"case": "sharded_model_preflight", "status": "passed"})
        (model_dir / "model-00001-of-00001.safetensors").unlink()
        try:
            voice.model_identity(model_dir)
            raise AssertionError("missing shard was allowed")
        except ValueError:
            RESULTS.append({"case": "missing_shard_before_inference", "status": "passed"})
        (model_dir / "model.safetensors.index.json").unlink()
        (model_dir / "model.safetensors").write_bytes(b"synthetic single weight")
        assert len(voice.model_identity(model_dir)) == 2
        RESULTS.append({"case": "single_file_model_preflight", "status": "passed"})
        preflight_output = base / "preflight.wav"
        preflight = subprocess.run([
            sys.executable, str(ROOT / "scripts/generate_course_voice.py"),
            "--voice-id", "VM01", "--text", "仅做结构预检。", "--model-dir", str(model_dir),
            "--output", str(preflight_output), "--preflight",
        ], capture_output=True, text=True)
        assert preflight.returncode == 0 and not preflight_output.exists(), preflight.stderr
        RESULTS.append({"case": "voice_cli_preflight_without_gpu_or_output", "status": "passed"})
        catalog = base / "catalog.json"
        catalog.write_text("{}")
        reference = base / "reference.wav"
        with wave.open(str(reference), "wb") as stream:
            stream.setparams((1, 2, 24000, 0, "NONE", "not compressed"))
            stream.writeframes(b"\x01\x00" * 100)
        voices = {"VM01": {"reference_audio": reference.name}}
        for name, path in (("direct", reference), ("catalog", catalog),
                           ("symbolic", base / "alias.wav"), ("hardlink", base / "hard.wav")):
            if name == "symbolic":
                path.symlink_to(reference)
            if name == "hardlink":
                os.link(reference, path)
            try:
                voice.protect_outputs([path], catalog, voices)
                raise AssertionError(name)
            except ValueError:
                RESULTS.append({"case": "protected_output_" + name, "status": "passed"})

        class FakeSoundfile:
            @staticmethod
            def write(path, audio, sample_rate, subtype):
                with wave.open(path, "wb") as stream:
                    stream.setparams((1, 2, sample_rate, 0, "NONE", "not compressed"))
                    stream.writeframes(b"\x01\x00" * len(audio))

        output = base / "generated.wav"
        voice.publish_pair(output, [1] * 20, 24000, {"voice_id": "probe"}, FakeSoundfile)
        metadata = json.loads(output.with_suffix(".json").read_text())
        assert metadata["publication_status"] == "complete" and metadata["output_sha256"] == file_digest(output)
        RESULTS.append({"case": "voice_pair_complete_receipt", "status": "passed"})
        original_wav, original_json = output.read_bytes(), output.with_suffix(".json").read_bytes()
        real_replace = os.replace

        def fail_metadata(source, destination):
            if Path(source).name == "metadata.json":
                raise OSError("Synthetic publication failure")
            return real_replace(source, destination)

        with patch.object(voice.os, "replace", side_effect=fail_metadata):
            try:
                voice.publish_pair(output, [1] * 50, 24000, {}, FakeSoundfile, overwrite=True)
                raise AssertionError("failed metadata publication was accepted")
            except OSError:
                pass
        assert output.read_bytes() == original_wav and output.with_suffix(".json").read_bytes() == original_json
        assert json.loads(output.with_suffix(".generation-status.json").read_text())["status"] == "failed"
        RESULTS.append({"case": "voice_publication_failure_rolls_back_pair", "status": "passed"})
        empty_output = base / "first-failed.wav"
        with patch.object(voice.os, "replace", side_effect=fail_metadata):
            try:
                voice.publish_pair(empty_output, [1] * 50, 24000, {}, FakeSoundfile)
                raise AssertionError("first failed publication was accepted")
            except OSError:
                pass
        assert not empty_output.exists() and not empty_output.with_suffix(".json").exists()
        RESULTS.append({"case": "first_publication_failure_leaves_no_partial_pair", "status": "passed"})
        with voice.output_reservation(output):
            try:
                with voice.output_reservation(output):
                    raise AssertionError("duplicate output lock was accepted")
            except ValueError:
                RESULTS.append({"case": "concurrent_output_lock_rejected", "status": "passed"})
        fake_torch = SimpleNamespace(
            cuda=SimpleNamespace(is_available=lambda: True, reset_peak_memory_stats=lambda: None),
            set_num_threads=lambda _: None, float16="synthetic_float16",
        )
        loaded_models = []
        generated_jobs = []

        def load_model(*args, **kwargs):
            loaded_models.append(object())
            return loaded_models[-1]

        def fake_generate(job, args, catalog, weight_identity, model, *unused):
            generated_jobs.append((job["output"], model))

        fake_qwen = SimpleNamespace(Qwen3TTSModel=SimpleNamespace(from_pretrained=load_model))
        with patch.dict(sys.modules, {"numpy": SimpleNamespace(), "soundfile": FakeSoundfile,
                                      "torch": fake_torch, "qwen_tts": fake_qwen}), \
                patch.object(voice, "version", return_value="synthetic"), \
                patch.object(voice, "generate_job", side_effect=fake_generate):
            voice.run_jobs([{"output": base / "batch-one.wav"}, {"output": base / "batch-two.wav"}],
                           SimpleNamespace(model_dir=model_dir), {}, {})
        assert len(loaded_models) == 1 and len(generated_jobs) == 2
        assert all(model is loaded_models[0] for output, model in generated_jobs)
        RESULTS.append({"case": "batch_jobs_reuse_one_model_load", "status": "passed"})

    print(json.dumps({"passed": len(RESULTS), "cases": RESULTS,
                      "limits": "Synthetic metadata and encoded probes; no GPU inference, human quality review or learner study."},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
