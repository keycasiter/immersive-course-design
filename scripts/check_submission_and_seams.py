#!/usr/bin/env python3
"""Isolated request and encoded-PTS regressions; fixtures are not course approvals."""

import argparse
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch

from check_video_production import ROOT, fixture, make_media
from submission_contract import (
    canonical_digest, expected_contract, inspect_attempt, normalize_request,
    validate_submission,
)
from validate_registries import validate as validate_registries
from validate_video_production import Audit, digest, validate_delivery, validate_plan
from video_seam_contract import frame_clock, validate_seams


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def request_attempt(raw_path, raw, manifest, plan, registry, base):
    write_json(raw_path, raw)
    normalized = normalize_request(raw, "trae_generate_video_v1", manifest, base)
    _, speech, contract_hash = expected_contract(plan, plan["generation_units"][0], registry)
    prompt = normalized["prompt"]
    bindings = []
    for line in speech:
        start = prompt.find(line["text"]) if line["audio_source"] == "embedded_native" else None
        bindings.append({
            "event_identifier": line["event_identifier"],
            **{key: line[key] for key in ("utterance_identifier", "utterance_version", "text_sha256")},
            "prompt_start": start,
            "prompt_end": start + len(line["text"]) if start is not None else None,
        })
    return {
        "attempt_identifier": "attempt_1", "request_sha256": canonical_digest(normalized),
        "submission_readback": {
            "adapter_identifier": "trae_generate_video_v1", "provider_identifier": "trae_video",
            "serialized_request_file": raw_path.name, "serialized_request_sha256": digest(raw_path),
            "normalized_request": normalized, "reference_manifest": copy.deepcopy(manifest),
            "production_contract_sha256": contract_hash, "utterance_bindings": bindings,
        },
    }


def boundary(base, media, timestamp, time_base, label):
    evidence = base / (label + ".txt")
    evidence.write_text("Synthetic boundary observation; no semantic acceptance.\n")
    return {
        "source_sha256": digest(media), "presentation_timestamp": timestamp,
        "time_base": str(time_base), "evidence_file": evidence.name, "evidence_sha256": digest(evidence),
    }


def observed_seam(base, media, before, after, review, route="timeline:mainline",
                  transition="continuous", clock=None):
    time_base, timestamps = clock or frame_clock(media)
    def adopted(clip):
        return [pts for pts in timestamps
                if clip["source_start_seconds"] <= float((pts - timestamps[0]) * time_base)
                < clip["source_end_seconds"]]
    state = {
        "lighting": "Synthetic steady illumination",
        "entities": [{
            "entity_identifier": "object", "count": 1, "position": "Synthetic center",
            "orientation": "Synthetic front", "holding_identifiers": [],
            "condition": "Synthetic intact", "motion_phase": "Synthetic moving",
        }],
    }
    return {
        "seam_identifier": route + ":" + before["clip_identifier"] + ":" + after["clip_identifier"],
        "route_identifier": route, "preceding_clip_identifier": before["clip_identifier"],
        "following_clip_identifier": after["clip_identifier"], "transition_type": transition,
        "transition_reason": "Synthetic same event", "status": "observed",
        "delivery_sha256_by_timeline": {
            before["timeline_identifier"]: digest(media), after["timeline_identifier"]: digest(media),
        },
        "preceding_boundary": boundary(base, media, adopted(before)[-1], time_base, "before-" + route.replace(":", "-")),
        "following_boundary": boundary(base, media, adopted(after)[0], time_base, "after-" + route.replace(":", "-")),
        "preceding_visual_state": copy.deepcopy(state), "following_visual_state": copy.deepcopy(state),
        "audible_state": {
            "completed_event_identifiers": [], "continuing_event_identifiers": ["speech"],
            "next_event_identifier": None, "listening_review": copy.deepcopy(review),
        },
        "continuity_review": copy.deepcopy(review),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    results = []
    def passed(name):
        results.append({"case": name, "status": "passed"})
    def assert_errors(name, errors, expected=None):
        assert any(expected in error for error in errors) if expected else not errors, (name, errors)
        passed(name)

    with tempfile.TemporaryDirectory(prefix="submission-seam-contract-") as temporary:
        base = Path(temporary)
        media = make_media(base, "moving.mp4", "testsrc2=size=320x180:rate=24:duration=4")
        still = base / "identity.png"
        subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", str(media),
                        "-frames:v", "1", str(still)], check=True, capture_output=True, timeout=60)
        plan, environment, evidence = fixture(base, media)
        plan.update(schema_version="1.2", character_sources=[], characters=[], character_introductions=[],
                    continuity_routes=[], continuity_seams=[], utterance_registry_file="utterances.json")
        plan["shots"][0]["character_identifiers"] = []
        plan["references"].append({
            "reference_identifier": "identity", "kind": "image", "path": still.name,
            "content_sha256": digest(still),
        })
        line = "请比较这两次变化。"
        registry = {"utterances": [{
            "utterance_identifier": "line", "utterance_version": "1", "authority": "Synthetic script",
            "speaker_identifier": "speaker", "purpose": "Synthetic comparison", "text": line,
            "text_sha256": hashlib.sha256(line.encode()).hexdigest(), "usage_references": ["speech"],
        }]}
        write_json(base / "utterances.json", registry)
        plan["utterance_registry_sha256"] = digest(base / "utterances.json")
        unit = plan["generation_units"][0]
        unit.update(
            required_capabilities=["text_to_video", "image_reference"],
            reference_bindings=[{"reference_identifier": "identity", "slot": "image_paths[0]", "purpose": "identity"}],
            prompt="参照<图片1>中的对象。保持物件移动；无原生台词，采用外配旁白。",
            job_file="job.json", output_attempt_identifier="attempt_1",
            submission_expectations={
                "adapter_identifier": "trae_generate_video_v1", "model": "unknown",
                "parameters": {"duration": 4, "resolution": "720p", "ratio": "16:9"},
                "output_contract": {"file_name": media.name},
            },
        )
        plan["sound_events"][0].update(
            kind="narration", on_screen=False, synchronization_method="off_screen",
            text=line, utterance_identifier="line", audio_source="external_stem",
            source_file=media.name, source_sha256=digest(media), source_start_seconds=0.3,
            source_end_seconds=3.7,
        )
        first = plan["clips"][0]
        first.update(end_seconds=2, source_end_seconds=2)
        second = copy.deepcopy(first)
        second.update(clip_identifier="clip_second", start_seconds=2, end_seconds=4,
                      source_start_seconds=2, source_end_seconds=4)
        plan["clips"].append(second)
        plan["continuity_seams"] = [observed_seam(base, media, first, second, plan["manual_reviews"][0])]
        raw = {"tool": "functions.GenerateVideo", "arguments": {
            "prompt": unit["prompt"], "duration": 4, "resolution": "720p", "ratio": "16:9",
            "image_paths": [still.name], "video_paths": [], "file_path": media.name,
        }}
        manifest = [{**plan["references"][-1], "slot": "image_paths[0]", "purpose": "identity"}]
        raw_path = base / "request.json"
        attempt = request_attempt(raw_path, raw, manifest, plan, registry, base)
        job = {
            "schema_version": "1.1", "job_identifier": "job", "asset_identifier": "video_main",
            "asset_version": "1", "provider": "trae_video", "phase": "preflight",
            "active_attempt_identifier": "attempt_1", "request_sha256": attempt["request_sha256"],
            "attempts": [attempt], "terminal_phase": None, "output_paths": [],
            "output_sha256": {}, "output_attempt_identifiers": {},
        }
        write_json(base / "environment.json", environment)
        plan["environment_sha256"] = digest(base / "environment.json")

        def submit(name, candidate=None, candidate_job=None, expected=None, delivery=False):
            write_json(base / "job.json", candidate_job if candidate_job is not None else job)
            audit = Audit(base)
            validate_submission(candidate if candidate is not None else plan, audit,
                                None if delivery else "unit", delivery)
            assert_errors(name, audit.errors, expected)
            return audit
        def seam(name, candidate=None, expected=None, actual=True):
            audit = Audit(base)
            validate_seams(candidate if candidate is not None else plan, audit, actual)
            assert_errors(name, audit.errors, expected)
            return audit
        def cli(name, candidate, options, expected=None):
            write_json(base / "plan.json", candidate)
            report = base / (name + ".json")
            result = subprocess.run([sys.executable, str(ROOT / "scripts/validate_video_production.py"),
                                     str(base / "plan.json"), *options, "--report", str(report)],
                                    capture_output=True, text=True, timeout=60)
            value = json.loads(report.read_text())
            assert result.returncode == (1 if expected else 0), (name, result.stdout, result.stderr)
            assert_errors(name, value["errors"], expected)
            return value

        submit("actual_serialized_request_matches_plan")
        assert_errors("job_registry_reads_actual_request", validate_registries(
            {"decisions": []}, registry, [job], [base]))
        write_json(base / "decisions.json", {"decisions": []})
        write_json(base / "job.json", job)
        registry_cli = subprocess.run([
            sys.executable, str(ROOT / "scripts/validate_registries.py"),
            str(base / "decisions.json"), str(base / "utterances.json"), str(base / "job.json"),
        ], capture_output=True, text=True, timeout=60)
        assert registry_cli.returncode == 0 and "VALID:" in registry_cli.stdout, (
            registry_cli.stdout, registry_cli.stderr)
        passed("registry_cli_resolves_request_paths_relative_to_job")
        cli("cli_pre_submit_valid_external_narration", plan, ["--pre-submit", "--unit", "unit"])
        # A request snapshot is read once: parsing cannot see different bytes than hashing.
        original_read = Path.read_bytes
        request_reads = []
        def tracked_read(path):
            if path.resolve() == raw_path.resolve():
                request_reads.append(path)
            return original_read(path)
        with patch.object(Path, "read_bytes", tracked_read):
            inspect_attempt(attempt, base)
            assert len(request_reads) == 1, request_reads
        passed("request_hash_and_parse_use_same_bytes")

        write_json(raw_path, {**raw, "arguments": {**raw["arguments"], "prompt": "旧稿"}})
        submit("snapshot_modified_after_readback", expected="changed after readback")
        write_json(raw_path, raw)
        bad = copy.deepcopy(plan)
        bad["generation_units"][0]["prompt"] += " 新稿"
        submit("current_prompt_changed", bad, expected="Final request differs")
        bad = copy.deepcopy(plan)
        bad["generation_units"][0]["submission_expectations"]["parameters"]["ratio"] = "9:16"
        submit("current_output_parameters_changed", bad, expected="Final request differs")
        bad = copy.deepcopy(plan)
        bad["generation_units"][0]["submission_expectations"]["output_contract"]["file_name"] = "other.mp4"
        submit("current_output_name_changed", bad, expected="Final request differs")
        bad_job = copy.deepcopy(job)
        bad_job["attempts"][0]["request_sha256"] = "0" * 64
        submit("attempt_request_fingerprint_changed", candidate_job=bad_job, expected="request_sha256 differs")
        bad_job = copy.deepcopy(job)
        bad_job["attempts"][0]["submission_readback"]["adapter_identifier"] = "unknown_adapter"
        submit("unknown_adapter_is_unverified", candidate_job=bad_job, expected="unverified submission adapter")
        bad_job = copy.deepcopy(job)
        bad_job["attempts"][0]["submission_readback"]["reference_manifest"][0]["path"] = media.name
        submit("reference_file_does_not_match_actual_slot", candidate_job=bad_job, expected="differs at")
        bad_job = copy.deepcopy(job)
        bad_job["attempts"][0]["submission_readback"]["reference_manifest"][0].update(kind="audio", purpose="voice")
        submit("audio_cannot_be_disguised_as_image_slot", candidate_job=bad_job, expected="cannot carry")
        bad_job = copy.deepcopy(job)
        bad_job["attempts"][0]["submission_readback"]["reference_manifest"][0]["slot"] = "image_paths[1]"
        submit("actual_reference_slot_missing", candidate_job=bad_job, expected="Undeclared actual reference slot")
        bad_job = copy.deepcopy(job)
        bad_job["attempts"][0]["submission_readback"]["utterance_bindings"] = []
        submit("authority_binding_missing", candidate_job=bad_job, expected="incomplete or duplicated")
        bad_job = copy.deepcopy(job)
        bad_job["attempts"][0]["submission_readback"]["utterance_bindings"][0]["prompt_start"] = 0
        submit("external_voice_is_not_native_submitted_text", candidate_job=bad_job, expected="External voice")
        bad_job = copy.deepcopy(job)
        bad_job["phase"] = "running"
        submit("already_submitted_task_must_be_recovered", candidate_job=bad_job, expected="recover original attempt")
        bad_job = copy.deepcopy(job)
        bad_job["schema_version"] = "1.0"
        submit("historical_job_is_not_new_readback", candidate_job=bad_job, expected="job schema 1.1")
        bad_job = copy.deepcopy(job)
        bad_job["attempts"].append(copy.deepcopy(attempt))
        submit("duplicate_attempt_is_rejected", candidate_job=bad_job, expected="unique")

        bad_registry = copy.deepcopy(registry)
        bad_registry["utterances"][0]["utterance_version"] = "2"
        write_json(base / "utterances.json", bad_registry)
        bad = copy.deepcopy(plan)
        bad["utterance_registry_sha256"] = digest(base / "utterances.json")
        submit("authority_version_changed_invalidates_readback", bad, expected="contract changed")
        bad_registry["utterances"][0]["authority"] = None
        write_json(base / "utterances.json", bad_registry)
        bad["utterance_registry_sha256"] = digest(base / "utterances.json")
        submit("authority_source_is_required", bad, expected="authority requires")
        unused = copy.deepcopy(registry["utterances"][0])
        unused.update(utterance_identifier="unrelated", utterance_version="99")
        write_json(base / "utterances.json", {"utterances": registry["utterances"] + [unused]})
        good = copy.deepcopy(plan)
        good["utterance_registry_sha256"] = digest(base / "utterances.json")
        submit("unrelated_utterance_does_not_invalidate_unit", good)
        write_json(base / "utterances.json", registry)

        native = copy.deepcopy(plan)
        native["sound_events"][0]["audio_source"] = "embedded_native"
        native["generation_units"][0]["prompt"] = "对象继续移动，旁白逐字说：" + line
        native_raw = copy.deepcopy(raw)
        native_raw["arguments"]["prompt"] = native["generation_units"][0]["prompt"]
        native_job = copy.deepcopy(job)
        native_job["attempts"] = [request_attempt(raw_path, native_raw, manifest, native, registry, base)]
        native_job["request_sha256"] = native_job["attempts"][0]["request_sha256"]
        submit("native_dialogue_unicode_offsets_match_exact_authority", native, native_job)
        altered = copy.deepcopy(native)
        altered["generation_units"][0]["prompt"] = altered["generation_units"][0]["prompt"].replace("变化", "改变")
        altered_raw = copy.deepcopy(native_raw)
        altered_raw["arguments"]["prompt"] = altered["generation_units"][0]["prompt"]
        altered_job = copy.deepcopy(native_job)
        altered_job["attempts"] = [request_attempt(raw_path, altered_raw, manifest, altered, registry, base)]
        altered_job["request_sha256"] = altered_job["attempts"][0]["request_sha256"]
        submit("native_one_word_change_cannot_pass_self_consistent_hash", altered, altered_job,
               "character-for-character")
        write_json(raw_path, raw)

        accepted = copy.deepcopy(job)
        accepted.update(phase="accepted", terminal_phase="accepted", output_paths=[media.name],
                        output_sha256={media.name: digest(media)},
                        output_attempt_identifiers={media.name: "attempt_1"})
        submit("adopted_output_binds_checked_attempt", candidate_job=accepted, delivery=True)
        bad_job = copy.deepcopy(accepted)
        bad_job["output_attempt_identifiers"][media.name] = "attempt_other"
        submit("adopted_output_wrong_attempt", candidate_job=bad_job, expected="does not bind", delivery=True)
        bad_job = copy.deepcopy(accepted)
        bad_job["output_sha256"][media.name] = "0" * 64
        submit("adopted_output_wrong_hash", candidate_job=bad_job, expected="does not bind", delivery=True)
        bad_job = copy.deepcopy(accepted)
        bad_job["output_attempt_identifiers"] = None
        submit("malformed_output_bindings_fail_without_crash", candidate_job=bad_job, expected="does not bind", delivery=True)
        bad_job = copy.deepcopy(job)
        bad_job["attempts"][0].pop("submission_readback")
        assert_errors("job_1_1_missing_readback_is_unverified", validate_registries(
            {"decisions": []}, registry, [bad_job], [base]), "historical evidence is unverified")

        seam("actual_adopted_source_boundary_not_full_source_tail")
        seam("planned_seam_has_coverage_only", actual=False)
        bad = copy.deepcopy(plan)
        bad["continuity_seams"] = []
        seam("every_actual_adjacent_edge_requires_record", bad, "missing actual")
        bad = copy.deepcopy(plan)
        bad["continuity_seams"][0]["preceding_clip_identifier"] = "clip_second"
        seam("wrong_predecessor_is_rejected", bad, "predecessor")
        clock, timestamps = frame_clock(media)
        bad = copy.deepcopy(plan)
        bad["continuity_seams"][0]["preceding_boundary"]["presentation_timestamp"] = timestamps[-1]
        seam("full_generated_tail_is_not_selected_out_point", bad, "actual adopted boundary")
        bad = copy.deepcopy(plan)
        bad["continuity_seams"][0]["preceding_boundary"]["time_base"] = "1/24"
        seam("averaged_frame_rate_is_not_source_time_base", bad, "actual source PTS")
        bad = copy.deepcopy(plan)
        bad["continuity_seams"][0]["preceding_boundary"]["source_sha256"] = "0" * 64
        seam("obsolete_source_boundary_is_rejected", bad, "obsolete source")
        bad = copy.deepcopy(plan)
        bad["continuity_seams"][0]["delivery_sha256_by_timeline"]["mainline"] = "0" * 64
        seam("obsolete_final_timeline_is_rejected", bad, "obsolete final")
        bad = copy.deepcopy(plan)
        bad["continuity_seams"][0]["following_visual_state"] = {}
        seam("both_visual_states_are_required", bad, "Visual state")
        bad = copy.deepcopy(plan)
        bad["continuity_seams"][0]["audible_state"] = {}
        seam("audible_state_is_required", bad, "Audible state")
        bad = copy.deepcopy(plan)
        bad["continuity_seams"][0]["continuity_review"]["bound_sha256"] = "0" * 64
        seam("old_continuity_review_cannot_pass_new_timeline", bad, "another file")
        bad = copy.deepcopy(plan)
        bad["continuity_seams"][0]["status"] = "planned"
        seam("planned_state_is_not_observed_acceptance", bad, "observations are missing")
        # A manual description can be wrong despite valid file/clock bindings.
        semantic = copy.deepcopy(plan)
        semantic["continuity_seams"][0]["following_visual_state"]["entities"][0]["count"] = 7
        seam("mechanical_checks_do_not_claim_semantic_continuity", semantic)

        routes = copy.deepcopy(plan)
        branch = copy.deepcopy(second)
        branch.update(clip_identifier="branch", timeline_identifier="feedback")
        routes["clips"].append(branch)
        routes["timelines"].append({**plan["timelines"][0], "timeline_identifier": "feedback"})
        routes["continuity_routes"] = [{
            "route_identifier": "branch_to_main", "clip_identifiers": ["branch", "clip_second"],
            "transition_type": "branch_merge",
        }]
        routes["continuity_seams"].append(observed_seam(
            base, media, branch, second, plan["manual_reviews"][0], "branch_to_main", "branch_merge"))
        seam("declared_branch_merge_requires_both_timeline_hashes", routes)
        bad = copy.deepcopy(routes)
        bad["continuity_seams"][-1]["delivery_sha256_by_timeline"].pop("feedback")
        seam("branch_merge_missing_preceding_timeline_hash", bad, "both participating")
        resume = copy.deepcopy(routes)
        resume["continuity_routes"][0].update(route_identifier="resume_main", transition_type="resume")
        resume_seam = observed_seam(base, media, branch, second, plan["manual_reviews"][0], "resume_main", "resume")
        resume_seam["resume_source_seconds"] = 2.5
        resume_seam["following_boundary"]["presentation_timestamp"] = [
            pts for pts in timestamps if float((pts - timestamps[0]) * clock) <= 2.5][-1]
        resume["continuity_seams"][-1] = resume_seam
        seam("resume_checks_predecessor_end_and_following_resume_frame", resume)
        bad = copy.deepcopy(resume)
        bad["continuity_seams"][-1]["resume_source_seconds"] = 4
        seam("resume_outside_adopted_interval_is_rejected", bad, "outside adopted")
        bad = copy.deepcopy(routes)
        bad["continuity_seams"].pop()
        seam("declared_branch_route_missing_seam", bad, "missing actual")

        vfr = base / "vfr.mp4"
        subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "lavfi", "-i",
                        "testsrc2=size=320x180:rate=24:duration=4", "-vf",
                        "select='if(lt(t,2),not(mod(n,3)),not(mod(n,2)))'",
                        "-fps_mode", "vfr", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(vfr)],
                       check=True, capture_output=True, timeout=60)
        vfr_clock = frame_clock(vfr)
        assert len(set(b - a for a, b in zip(vfr_clock[1], vfr_clock[1][1:]))) > 1
        vfr_plan = copy.deepcopy(plan)
        vfr_plan["generation_units"][0].update(output_file=vfr.name, output_sha256=digest(vfr))
        vfr_plan["timelines"][0].update(path=vfr.name, content_sha256=digest(vfr))
        review = {**plan["manual_reviews"][0], "bound_sha256": digest(vfr)}
        vfr_plan["continuity_seams"] = [observed_seam(base, vfr, first, second, review, clock=vfr_clock)]
        seam("variable_frame_rate_uses_actual_presentation_clock", vfr_plan)

        write_json(base / "job.json", accepted)
        audit = validate_plan(plan, environment, base, delivery=True)
        assert not audit.errors, audit.errors
        validate_delivery(plan, environment, audit)
        assert_errors("integrated_delivery_includes_submission_and_seams", audit.errors)
        report = cli("cli_delivery_reports_checked_contracts", plan, ["--delivery"])
        assert report["submission_contract_status"] == "actual_arguments_compared"
        assert report["seam_contract_status"] == "source_pts_and_review_records_checked"
        legacy = copy.deepcopy(plan)
        legacy["schema_version"] = "1.1"
        report = cli("legacy_plan_reports_new_contracts_unvalidated", legacy, [])
        assert report["submission_contract_status"] == "not_validated_legacy"
        assert report["seam_contract_status"] == "not_validated_legacy"
        cli("legacy_cannot_claim_new_pre_submit", legacy, ["--pre-submit", "--unit", "unit"],
            "requires schema 1.2")
        cli("cli_requires_selected_unit", plan, ["--pre-submit"], "must be used together")

    value = {
        "passed": len(results), "cases": results,
        "limits": "Synthetic requests, media and review records. No provider call, reviewer identity proof, "
                  "visual/speech semantic validation, course approval or learner trial.",
    }
    if args.report:
        write_json(args.report, value)
    print(json.dumps(value, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
