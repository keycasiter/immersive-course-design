#!/usr/bin/env python3
"""Regression probes for the seven review findings. All approval records are synthetic."""

import argparse
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile

from check_contract_regressions import fill, event
from production_contract import event_digest
from demo_contract import GATE_BY_KIND, validate_runtime_delivery
from demo_regression_fixtures import install_runtime, sync_workflow, install_content_quality
from production_contract import validate_joint
from validate_production import validate, file_digest, approval_fingerprint
from check_video_led_visual_gate import validate as visual_check
from build_flova_review_index import build

ROOT = Path(__file__).resolve().parents[1]
RESULTS = []


def check(name, errors, expected=None):
    if expected is None:
        assert not errors, (name, errors)
    else:
        assert errors and any(expected in message for message in errors), (name, errors)
    RESULTS.append({"case": name, "status": "passed",
                    "observed": "valid" if expected is None else "rejected",
                    "diagnostic": None if expected is None else next(
                        line for message in errors for line in message.splitlines() if expected in line)})


def confirm(data, base, kind):
    subject = next(row for row in data["approval_subjects"] if row["kind"] == kind)
    record = {
        "confirmation_identifier": f"confirmation_{len(data['status_history'])}_{kind}",
        "scope_identifier": subject["scope_identifier"], "confirmed_by": "Synthetic human",
        "confirmed_at": "2026-11-05T00:00:00Z", "confirmed_version": subject["subject_version"],
        "content_sha256": approval_fingerprint(data, subject, base),
        "dependency_fingerprints": {
            identifier: approval_fingerprint(data, next(row for row in data["approval_subjects"]
                                                      if row["scope_identifier"] == identifier), base)
            for identifier in subject["depends_on_scope_identifiers"]
        },
        "evidence_references": ["human_record"],
    }
    data["approval_gates"][GATE_BY_KIND[kind]]["confirmations"].append(record)
    event(data, "reconfirm", data["current_status"], [subject["scope_identifier"]],
          [record["confirmation_identifier"]])
    return record


def fixture(base):
    data = fill(json.loads((ROOT / "assets/production-manifest.template.json").read_text()))
    data["work_scope"]["endpoint"] = "effect_evaluated"
    blueprint = fill(json.loads((ROOT / "assets/course-blueprint.template.json").read_text()))
    for source in blueprint["sources"]:
        source["verification_status"] = "verified"
    blueprint["evaluation_plan"]["design_review"].update(status="completed", evidence_references=["verification"])
    for identifier, kind in (
        ("experience_blueprint", "experience_blueprint"), ("storyboard", "storyboard"),
        ("interaction_visual_spec", "interaction_visual_spec"), ("human_record", "human_confirmation"),
        ("voice_reference", "voice_reference"), ("audio_probe", "audio_probe"), ("sample_entry", "runtime"),
    ):
        data["evidence_files"].append({"reference_identifier": identifier, "kind": kind,
                                      "path": identifier + ".txt"})
    for row in data["evidence_files"]:
        path = base / row["path"]
        path.write_text(json.dumps(blueprint) if row["kind"] == "course_blueprint"
                        else "Synthetic regression record, never course confirmation.")
        row.update(course_version=data["course_version"], content_sha256=file_digest(path),
                   bound_identifiers=["objective_core"])
    video = base / "sound.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "color=s=32x32:r=5",
                    "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=24000", "-t", "0.4",
                    "-c:v", "libx264", "-c:a", "aac", str(video)], check=True)
    diagram = base / "diagram.svg"
    diagram.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32"/>')
    for asset, path in zip(data["assets"], (video, diagram)):
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
            asset["delivery"].update(embedded_voice=True, environment_and_action_audio=True,
                                     separate_web_audio_stems=True, separate_branch_audio="not_applicable",
                                     branch_audio_not_applicable_reason="Synthetic fixture has no branch audio",
                                     audio_probe_evidence_references=["audio_probe"])
    # The Demo defers a different, still planned formal body; use the encoded probe only for the sample.
    data["assets"][0]["status"] = "planned"
    install_content_quality(data, base, blueprint)
    data["status_history"] = []
    event(data, "advance", "design_draft")
    confirm(data, base, "clarification")
    confirm(data, base, "design")
    event(data, "advance", "design_confirmed")
    data["approval_gates"]["design_confirmation"]["status"] = "confirmed"
    install_runtime(data, base)
    data["delivery_endpoint"] = "interaction_complete_prototype"
    data["acceptance_status"] = "browser_verified"
    sync_workflow(data)
    return data


def edit_json(data, base, reference_key, edit):
    reference = data["demo_runtime"][reference_key]
    row = next(row for row in data["evidence_files"] if row["reference_identifier"] == reference)
    path = base / row["path"]
    original = path.read_bytes()
    obj = json.loads(original)
    edit(obj)
    path.write_text(json.dumps(obj))
    row["content_sha256"] = file_digest(path)
    return path, original


def legacy_workflow(data, base):
    """A valid old seven-stage history, without dangling checkpoint references."""
    legacy = copy.deepcopy(data)
    removed = {row["scope_identifier"] for row in legacy["approval_subjects"]
               if row["kind"] in {"clarification", "demo"}}
    for key in ("workflow_contract_version", "workflow_state", "clarification",
                "demo_runtime", "demo_delivery", "runtime_delivery"):
        legacy.pop(key, None)
    legacy["approval_subjects"] = [row for row in legacy["approval_subjects"]
                                  if row["scope_identifier"] not in removed]
    subjects = {row["scope_identifier"]: row for row in legacy["approval_subjects"]}
    for row in subjects.values():
        row["depends_on_scope_identifiers"] = [key for key in row["depends_on_scope_identifiers"]
                                              if key not in removed]
    legacy["approval_gates"].pop("clarification_confirmation")
    legacy["approval_gates"].pop("demo_confirmation")
    records = {row["confirmation_identifier"]: row
               for gate in legacy["approval_gates"].values() for row in gate["confirmations"]}
    for record in records.values():
        subject = subjects[record["scope_identifier"]]
        record["content_sha256"] = approval_fingerprint(legacy, subject, base)
        record["dependency_fingerprints"] = {
            key: approval_fingerprint(legacy, subjects[key], base)
            for key in subject["depends_on_scope_identifiers"]
        }
    history = []
    for row in legacy["status_history"]:
        row["scope_identifiers"] = [key for key in row["scope_identifiers"] if key not in removed]
        row["confirmation_identifiers"] = [key for key in row["confirmation_identifiers"] if key in records]
        if row["event_type"] == "reconfirm" and not row["confirmation_identifiers"]:
            continue
        row["previous_event_sha256"] = history[-1]["event_sha256"] if history else None
        row["event_sha256"] = event_digest(row)
        history.append(row)
    legacy["status_history"] = history
    return legacy


def run(base):
    data = fixture(base)
    check("F2_F5_F6_full_storyboard_Demo", validate(data, base))
    check("F2_full_storyboard_Demo_joint", validate_joint(data, base))
    path = base / "demo.json"
    path.write_text(json.dumps(data))
    result = subprocess.run([sys.executable, str(ROOT / "scripts/validate_production.py"),
                             str(path), "--joint"], capture_output=True, text=True)
    check("F2_F6_actual_joint_CLI", [] if result.returncode == 0 else [result.stdout])
    runtime = data["demo_runtime"]
    evidence = {row["reference_identifier"]: row for row in data["evidence_files"]}
    result = subprocess.run([sys.executable, str(ROOT / "scripts/validate_video_led_runtime.py"),
                             str(base / evidence[runtime["event_map_reference"]]["path"]),
                             str(base / evidence[runtime["entry_reference"]]["path"]),
                             str(base / evidence[runtime["source_reference"]]["path"])],
                            capture_output=True, text=True)
    check("F6_storyboard_runtime_CLI", [] if result.returncode == 0 else [result.stdout])
    for name, mutate, diagnostic in (
        ("F1_legacy_workflow_rejected", lambda d: d.pop("workflow_contract_version"), "workflow_contract_version"),
        ("F1_missing_clarification", lambda d: d["approval_subjects"].__setitem__(
            slice(None), [r for r in d["approval_subjects"] if r["kind"] != "clarification"]), "clarification"),
        ("F1_invalid_clarification_type", lambda d: d["clarification"].update(
            confirmation_basis=[]), "confirmation_basis"),
        ("F1_partial_Demo_approval_scope", lambda d: next(
            row for row in d["approval_subjects"] if row["kind"] == "demo").update(
                covered_identifiers=["objective_other"]), "whole scoped objective set"),
        ("F5_unconfirmed_design", lambda d: d.update(current_status="design_draft"), "design_confirmed"),
        ("F2_missing_runtime", lambda d: d.update(demo_runtime=None), "runtime_delivery"),
        ("F2_Agent_self_acceptance", lambda d: d.update(
            acceptance_status="accepted", accepted_scope="interaction",
            acceptance_evidence={"review_owner": "Agent", "accepted_at": "2026-11-05T00:00:00Z",
                                 "reviewed_version": "0.1", "evidence_references": ["verification"]}),
         "self-signature"),
    ):
        bad = copy.deepcopy(data)
        mutate(bad)
        check(name, validate(bad, base), diagnostic)
    for name, key, mutate, diagnostic in (
        ("F2_empty_matrix", "knowledge_matrix_reference", lambda obj: obj.update(rows=[]), "matrix"),
        ("F2_wrong_objective", "knowledge_matrix_reference",
         lambda obj: obj["rows"][0].update(objective_identifier="objective_missing"), "exactly scoped"),
        ("F2_representative_browser_only", "browser_evidence_reference",
         lambda obj: obj.update(tests=obj["tests"][:1]), "paths/viewports"),
        ("F2_outdated_browser", "browser_evidence_reference",
         lambda obj: obj.update(course_version="old"), "version"),
        ("F2_unknown_browser_reference", "knowledge_matrix_reference",
         lambda obj: obj["rows"][0].update(browser_test_identifiers=["missing"]), "unknown browser test"),
        ("F2_missing_required_Beat", "browser_evidence_reference",
         lambda obj: [row.update(beat_identifiers=["beat_practice"]) for row in obj["tests"]], "omits required Beat"),
        ("F6_static_storyboard", "event_map_reference", lambda obj: obj.update(events=[]), "events"),
        ("F6_malformed_storyboard_event", "event_map_reference",
         lambda obj: obj["events"][0].update(event_class=[]), "event_class"),
        ("F2_malformed_browser_artifact", "browser_evidence_reference",
         lambda obj: obj["tests"][0]["artifacts"][0].update(kind=[]), "unsupported browser artifact"),
    ):
        bad = copy.deepcopy(data)
        edited, original = edit_json(bad, base, key, mutate)
        try:
            check(name, validate_joint(bad, base), diagnostic)
        finally:
            edited.write_bytes(original)
    bad = copy.deepcopy(data)
    bad["demo_runtime"]["browser_evidence_reference"] = "verification"
    check("F2_wrong_browser_evidence_kind", validate(bad, base), "wrong evidence kind")
    source_path = base / evidence[runtime["source_reference"]]["path"]
    original = source_path.read_bytes()
    source_path.write_bytes(original + b"\n// Changed version")
    check("F2_changed_runtime_cannot_reuse_browser", validate(data, base), "stale")
    source_path.write_bytes(original)
    record = confirm(data, base, "demo")
    data.update(acceptance_status="accepted", accepted_scope="interaction",
                acceptance_evidence={"review_owner": record["confirmed_by"], "accepted_at": record["confirmed_at"],
                                     "reviewed_version": data["course_version"],
                                     "confirmation_identifier": record["confirmation_identifier"],
                                     "evidence_references": ["human_record"]})
    check("F1_F2_accepted_Demo_binds_active_human_record", validate(data, base))
    parent = copy.deepcopy(data)
    parent.update(delivery_endpoint="media_sample", acceptance_status="browser_verified", accepted_scope=None,
                  acceptance_evidence={"evidence_references": [], "review_owner": None,
                                       "accepted_at": None, "reviewed_version": None})
    parent["assets"][0]["status"] = "accepted"
    parent["media_production_contract"]["voice_reference_identifiers"] = ["voice_reference"]
    sample = parent["representative_sample"]
    sample.update(covered_asset_identifiers=["video_introduction", "diagram_core"],
                  candidate_asset_versions={"video_introduction": "0.1", "diagram_core": "0.1"},
                  acceptance_evidence_references=["verification"])
    for row in sample["risk_coverage"]:
        row.update(status="passed", evidence_references=["verification"])
    next(row for row in parent["approval_subjects"] if row["kind"] == "media_sample")["materials"] = [
        {"source": "evidence_file", "reference_identifier": "sample_entry", "fingerprint_mode": "bytes"}]
    confirm(parent, base, "media_contract")
    sample_record = confirm(parent, base, "media_sample")
    event(parent, "advance", "media_sample_confirmed")
    parent["approval_gates"]["media_sample_confirmation"]["status"] = "confirmed"
    # Generation is no longer deferred; archive Demo delta without changing its accepted scope.
    production = copy.deepcopy(parent)
    production.update(delivery_endpoint="functional_course", acceptance_status="browser_verified",
                      accepted_scope=None, acceptance_evidence={"evidence_references": [], "review_owner": None,
                                                               "accepted_at": None, "reviewed_version": None})
    install_runtime(production, base, formal=True)
    event(production, "advance", "production_complete")
    check("F1_full_new_production_workflow", validate(production, base))
    # Production readiness does not change the approved design's JSON subtrees.
    blueprint_evidence = next(row for row in production["evidence_files"] if row["kind"] == "course_blueprint")
    blueprint_path = base / blueprint_evidence["path"]
    original_blueprint = blueprint_path.read_bytes()
    ready_blueprint = json.loads(original_blueprint)
    for resource in ready_blueprint["media_resources"]:
        asset = next(row for row in production["assets"]
                     if row["asset_identifier"] == resource["resource_identifier"])
        resource.update(production_status="ready", file_path=asset["files"][0]["path"])
    blueprint_path.write_text(json.dumps(ready_blueprint))
    blueprint_evidence["content_sha256"] = file_digest(blueprint_path)
    try:
        check("F1_full_new_production_workflow_joint", validate_joint(production, base))
        production_path = base / "new-production.json"
        production_path.write_text(json.dumps(production))
        result = subprocess.run([sys.executable, str(ROOT / "scripts/validate_production.py"),
                                 str(production_path), "--joint"], capture_output=True, text=True)
        check("F1_full_new_production_actual_joint_CLI", [] if result.returncode == 0 else [result.stdout])
        legacy_path = base / "legacy-production.json"
        legacy = legacy_workflow(production, base)
        # Preserve the ready snapshot so an external old-version CLI can verify the same fixture.
        (base / "ready-blueprint.json").write_bytes(blueprint_path.read_bytes())
        next(row for row in legacy["evidence_files"] if row["kind"] == "course_blueprint")["path"] = "ready-blueprint.json"
        legacy_path.write_text(json.dumps(legacy))
        result = subprocess.run([sys.executable, str(ROOT / "scripts/validate_production.py"),
                                 str(legacy_path), "--joint"], capture_output=True, text=True)
        check("F1_legacy_production_actual_joint_CLI",
              [result.stdout] if result.returncode != 0 else [], "workflow_contract_version")
    finally:
        blueprint_path.write_bytes(original_blueprint)
        blueprint_evidence["content_sha256"] = file_digest(blueprint_path)
    for name, kind in (("F1_missing_Demo_production", "demo"), ("F1_missing_clarification_production", "clarification")):
        bad = copy.deepcopy(production)
        bad["approval_gates"][GATE_BY_KIND[kind]]["confirmations"] = []
        check(name, validate(bad, base), "confirmation")
    bad = copy.deepcopy(production)
    bad["runtime_delivery"] = copy.deepcopy(bad["demo_runtime"])
    check("F6_formal_rejects_storyboard_runtime", validate(bad, base), "requires video_clock")
    bad = copy.deepcopy(data)
    event(bad, "invalidate", "design_confirmed", ["demo_whole_course"])
    check("F1_revoked_Demo_rejects_acceptance", validate(bad, base), "active demo_confirmation")
    gate_path = base / evidence[runtime["visual_gate_reference"]]["path"]
    gate = json.loads(gate_path.read_text())
    check("F3_valid_four_state_two_viewport_gate", visual_check(gate, base))
    result = subprocess.run([sys.executable, str(ROOT / "scripts/check_video_led_visual_gate.py"),
                             str(gate_path)], capture_output=True, text=True)
    check("F3_actual_visual_CLI", [] if result.returncode == 0 else [result.stdout])
    for name, mutate, diagnostic in (
        ("F3_dashboard_and_99_actions", lambda g: [row.update(primary_surface="dashboard", primary_action_count=99,
                                                            evidence_references=[]) for row in g["states"]], "primary_surface"),
        ("F3_boolean_action_count", lambda g: g["states"][1].update(primary_action_count=True), "primary_action_count"),
        ("F3_unknown_evidence", lambda g: g["states"][0].update(evidence_references=["missing"]), "unknown visual"),
        ("F3_single_state_evidence", lambda g: g["states"][1].update(
            evidence_references=g["states"][0]["evidence_references"]), "another state"),
        ("F3_missing_narrow", lambda g: g["states"][0].update(
            evidence_references=g["states"][0]["evidence_references"][:1]), "desktop and narrow"),
        ("F3_old_version", lambda g: g["evidence"][0].update(course_version="old"), "outdated"),
        ("F3_stale_runtime", lambda g: g["evidence"][0].update(runtime_fingerprints={}), "fingerprint differs"),
        ("F3_malformed_evidence_state", lambda g: g["evidence"][0].update(state_identifier=[]), "unknown evidence state"),
        ("F3_malformed_gate_status", lambda g: g.update(status=[]), "status must"),
    ):
        bad_gate = copy.deepcopy(gate)
        mutate(bad_gate)
        check(name, visual_check(bad_gate, base), diagnostic)
    parent_path = base / "parent.json"
    local = fill(json.loads((ROOT / "assets/asset-manifest.template.json").read_text()))
    (base / "asset-process.md").write_text("Synthetic process")
    def inherit(parent_manifest, selected_record):
        parent_path.write_text(json.dumps(parent_manifest))
        child = copy.deepcopy(local)
        child["work_scope"].update(parent_manifest_reference=parent_path.name, inherited_confirmations=[{
            "confirmation_identifier": selected_record["confirmation_identifier"],
            "scope_identifier": selected_record["scope_identifier"], "subject_version": "0.1",
            "content_sha256": selected_record["content_sha256"], "parent_manifest_sha256": file_digest(parent_path),
        }])
        return child
    check("F4_valid_parent_sample_inherited", validate(inherit(parent, sample_record), base))
    for name, revoked, diagnostic in (
        ("F4_direct_revocation", ["media_sample_hardest_loop"], "not active"),
        ("F4_design_dependency_revocation", ["design_whole_course"], "not active"),
        ("F4_multilevel_clarification_revocation", ["clarification_whole_course"], "not active"),
    ):
        revoked_parent = copy.deepcopy(parent)
        target = "design_confirmed" if revoked == ["media_sample_hardest_loop"] else "design_draft"
        event(revoked_parent, "invalidate", target, revoked)
        revoked_parent["approval_gates"]["media_sample_confirmation"]["status"] = "pending"
        if target == "design_draft":
            revoked_parent["approval_gates"]["design_confirmation"]["status"] = "pending"
        revoked_parent.update(delivery_endpoint="design_draft", acceptance_status="structure_checked",
                              accepted_scope=None, acceptance_evidence={"evidence_references": [], "review_owner": None,
                                                                       "accepted_at": None, "reviewed_version": None})
        if target == "design_draft":
            revoked_parent["demo_runtime"] = None
        sync_workflow(revoked_parent)
        check(name, validate(inherit(revoked_parent, sample_record), base), diagnostic)
    revised = copy.deepcopy(parent)
    event(revised, "invalidate", "design_confirmed", ["media_sample_hardest_loop"])
    revised["approval_gates"]["media_sample_confirmation"]["status"] = "pending"
    confirm(revised, base, "media_sample")
    event(revised, "advance", "media_sample_confirmed")
    revised["approval_gates"]["media_sample_confirmation"]["status"] = "confirmed"
    check("F4_replaced_old_confirmation_rejected", validate(inherit(revised, sample_record), base), "not active")
    design_path = base / next(row["path"] for row in parent["evidence_files"]
                             if row["reference_identifier"] == "course_design")
    original_design = design_path.read_bytes()
    design_path.write_bytes(original_design + b"\nChanged design content")
    try:
        check("F4_changed_parent_content_without_reconfirmation",
              validate(inherit(parent, sample_record), base), "Current confirmation no longer valid")
    finally:
        design_path.write_bytes(original_design)
    scope_record = parent["approval_gates"]["media_sample_confirmation"]["confirmations"][0]
    unaffected = copy.deepcopy(parent)
    event(unaffected, "invalidate", "media_sample_confirmed", ["demo_whole_course"])
    unaffected.update(acceptance_status="browser_verified", accepted_scope=None,
                      acceptance_evidence={"evidence_references": [], "review_owner": None,
                                           "accepted_at": None, "reviewed_version": None})
    check("F4_unrelated_media_contract_remains_inheritable", validate(inherit(unaffected, scope_record), base))
    # The universal Demo gate also has a legal non-web route, without HTML requirements.
    non_web = copy.deepcopy(parent)
    event(non_web, "invalidate", "media_sample_confirmed", ["demo_whole_course"])
    non_web["work_scope"]["learner_delivery_type"] = "facilitated_instruction"
    non_web["demo_runtime"] = None
    non_web["demo_delivery"] = {
        "learner_delivery_type": "facilitated_instruction", "content_reference": "walkthrough_materials",
        "walkthrough_reference": "walkthrough_record",
    }
    materials = base / "walkthrough-materials.txt"
    materials.write_text("Synthetic learner materials")
    check_artifact = base / "walkthrough-operation.txt"
    check_artifact.write_text("Synthetic facilitator check")
    walkthrough_path = base / "walkthrough.json"
    walkthrough_path.write_text(json.dumps({
        "course_version": "0.1", "material_sha256": file_digest(materials),
        "checks": [{"objective_identifier": "objective_core", "path": path, "status": "passed",
                   "observed_result": "Synthetic result", "recorded_at": "2026-11-05T00:00:00Z",
                   "artifact_path": check_artifact.name, "artifact_sha256": file_digest(check_artifact)}
                  for path in ("normal", "help_revision", "return_reentry", "accessible_equivalent")],
    }))
    for identifier, kind, file in (("walkthrough_materials", "learner_materials", materials),
                                   ("walkthrough_record", "demo_walkthrough", walkthrough_path)):
        non_web["evidence_files"].append({
            "reference_identifier": identifier, "kind": kind, "path": file.name, "course_version": "0.1",
            "content_sha256": file_digest(file), "bound_identifiers": ["objective_core"],
        })
    confirm(non_web, base, "demo")
    # Preserve the walkthrough-only probe and verify the complete facilitated manifest too.
    from demo_contract import validate_non_web_demo
    from production_contract import Checks
    c = Checks(base)
    validate_non_web_demo(c, non_web, {row["reference_identifier"]: row for row in non_web["evidence_files"]}, "0.1")
    check("F1_non_web_Demo_has_legal_walkthrough_route", c.errors)
    event(non_web, "invalidate", "design_confirmed", ["media_sample_hardest_loop"])
    non_web["approval_gates"]["media_sample_confirmation"]["status"] = "pending"
    non_web["representative_sample"].update(
        media_modes=[], covered_asset_identifiers=[], candidate_asset_versions={})
    non_web["representative_sample"]["risk_coverage"] = [
        {"risk_identifier": identifier, "critical": True, "selection_reason": "Synthetic walkthrough risk",
         "status": "passed", "evidence_references": ["verification"]}
        for identifier in ("content", "facilitator_handoff", "representative_delivery", "equivalent_path")
    ]
    confirm(non_web, base, "media_sample")
    event(non_web, "advance", "media_sample_confirmed")
    non_web["approval_gates"]["media_sample_confirmation"]["status"] = "confirmed"
    check("F1_non_web_complete_manifest_with_Demo_gate", validate(non_web, base))
    screen = {"items": [
        {"public_skill_identifier": f"source_{i}", "body_sha256": f"{i:064x}", "catalogue_position": i,
         "title": "视频方法", "body_character_count": 1, "reference_names": []} for i in range(332)],
        "catalogue_url": "https://example.test/catalogue", "retrieved_on": "2026-11-05",
        "retrieval_method": "Synthetic fixture"}
    check("F7_first_unread_video_no_exception", [] if build(screen, {})["coverage"]["reference_contents_read"] == 0 else ["count"])
    key = ("source_0", f"{0:064x}")
    log = {key: {"main_read_depth": "complete_main_body_read", "reference_contents_read": ["attachment"],
                 "capability": "synthetic", "decision": "synthetic", "disposition": "synthetic"}}
    built = build(screen, log)
    check("F7_read_then_unread_no_leak", [] if built["items"][1]["reference_contents_read"] == [] else ["leaked"])
    check("F7_actual_reference_count", [] if built["coverage"]["reference_contents_read"] == 1 else ["count"])
    changed = copy.deepcopy(screen)
    changed["items"][0]["body_sha256"] = "f" * 64
    check("F7_changed_body_revokes_read_claim", [] if build(changed, log)["coverage"]["reference_contents_read"] == 0 else ["stale"])
    reordered = copy.deepcopy(screen)
    reordered["items"].reverse()
    check("F7_reorder_preserves_identity", [] if build(reordered, log)["items"][-1]["reference_contents_read"] == ["attachment"] else ["order"])
    screen_path = base / "screen.json"
    screen_path.write_text(json.dumps(screen))
    result = subprocess.run([sys.executable, str(ROOT / "scripts/build_flova_review_index.py"), str(screen_path),
                             "--output", str(base / "index.json")], capture_output=True, text=True)
    check("F7_actual_historical_builder_CLI", [] if result.returncode == 0 else [result.stderr])
    # Preserve the legitimate Demo package for optional isolated browser template checks.
    (base / "accepted-demo.json").write_text(json.dumps(data))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture-directory", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.fixture_directory:
        assert args.fixture_directory.is_dir(), "Fixture directory must already exist"
        run(args.fixture_directory)
    else:
        with tempfile.TemporaryDirectory(prefix="workflow-demo-check-") as directory:
            run(Path(directory))
    result = {"passed": len(RESULTS), "cases": RESULTS,
              "limits": "Synthetic approvals and browser records; checks contracts, not teaching or human identity."}
    if args.output:
        assert args.output.parent.is_dir()
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
