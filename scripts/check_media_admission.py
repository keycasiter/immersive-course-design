#!/usr/bin/env python3
"""Isolated real decoding and identity regressions; synthetic content is not course QA."""

import argparse
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch

from check_video_production import make_media
from check_submission_and_seams import request_attempt
from submission_contract import expected_contract, validate_submission
from validate_video_production import Audit
from validate_media_admission import (
    digest, extract_frame, inspect_media, validate_reuse, validate_sources,
)


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    results = []

    def check(name, errors, expected=None):
        assert (any(expected in error for error in errors) if expected else not errors), (name, errors)
        results.append({"case": name, "status": "passed"})

    with tempfile.TemporaryDirectory(prefix="media-admission-regression-") as temporary:
        base = Path(temporary)
        video = make_media(base, "moving.mp4", "testsrc2=size=160x96:rate=12:duration=4")
        other = make_media(base, "other.mp4", "color=c=blue:size=160x96:rate=12:duration=4")
        image = base / "still.png"
        extract_frame(video, 0, image)
        audio = base / "sound.wav"
        subprocess.run(["ffmpeg", "-v", "error", "-nostdin", "-i", str(video),
                        "-map", "0:a:0", str(audio)], check=True, capture_output=True, timeout=60)
        evidence = base / "observations.txt"
        evidence.write_text("Synthetic test signal observation only; not learner or course acceptance.\n")
        review = lambda media: {
            "status": "passed", "reviewer": "Synthetic regression fixture",
            "bound_sha256": digest(media), "evidence_file": evidence.name,
            "evidence_sha256": digest(evidence), "observations": ["Synthetic test signal in actual fixture."],
        }
        sources, reviews = [], []
        for identifier, kind, media in (
                ("first_video", "video", video), ("second_video", "video", other),
                ("still", "image", image), ("sound", "audio", audio)):
            sources.append({"source_identifier": identifier, "kind": kind, "path": media.name,
                            "content_sha256": digest(media), "purpose": "Synthetic identity regression"})
            samples = []
            if kind == "video":
                sample = base / (identifier + ".png")
                extract_frame(media, 0.5, sample)
                samples = [{"source_identifier": identifier, "source_sha256": digest(media),
                            "at_seconds": 0.5, "path": sample.name, "content_sha256": digest(sample)}]
            reviews.append({"source_identifier": identifier, "status": "passed",
                            "source_sha256": digest(media), "content_review": review(media),
                            "frame_samples": samples, "failure_reason": None})
        record = {"schema_version": "1.0", "input_state": "supplied",
                  "declared_sources": sources, "reviews": reviews}
        check("real_image_audio_and_two_videos_admitted", validate_sources(record, base)[0])
        empty = {"schema_version": "1.0", "input_state": "not_supplied", "declared_sources": [], "reviews": []}
        check("genuine_no_input_admitted", validate_sources(empty, base)[0])
        bad = copy.deepcopy(empty)
        bad["input_state"] = "supplied"
        check("empty_supplied_is_failure", validate_sources(bad, base)[0], "empty inventory")
        bad = copy.deepcopy(record)
        bad["input_state"] = "not_supplied"
        check("no_input_cannot_conceal_declared_sources", validate_sources(bad, base)[0], "cannot conceal")
        for key in ("declared_sources", "reviews"):
            bad = copy.deepcopy(record)
            bad[key] = None
            check("null_" + key + "_has_diagnostic", validate_sources(bad, base)[0], "array of objects")
        bad = copy.deepcopy(record)
        bad["reviews"].pop()
        check("every_input_requires_review", validate_sources(bad, base)[0], "exactly one review")
        bad = copy.deepcopy(record)
        bad["declared_sources"].append(copy.deepcopy(sources[0]))
        check("duplicate_source_rejected", validate_sources(bad, base)[0], "duplicate")
        mutations = [
            ("failed_probe_cannot_be_reviewed", lambda row: row.update(
                status="failed", failure_reason="Acquisition failed"), "input review failed"),
            ("stale_source_sha_rejected", lambda row: row.update(source_sha256="0" * 64), "old file"),
            ("technical_only_review_rejected", lambda row: row.update(content_review=None), "content review"),
            ("empty_observations_rejected", lambda row: row["content_review"].update(observations=[]), "observations"),
            ("missing_observation_evidence_rejected", lambda row: row["content_review"].update(
                evidence_file="missing.txt"), "missing actual file"),
            ("stale_observation_evidence_rejected", lambda row: row["content_review"].update(
                evidence_sha256="0" * 64), "SHA256"),
            ("missing_video_sample_rejected", lambda row: row.update(frame_samples=[]), "frame evidence"),
            ("foreign_sample_identity_rejected", lambda row: row["frame_samples"][0].update(
                source_identifier="second_video"), "another source"),
            ("out_of_range_sample_rejected", lambda row: row["frame_samples"][0].update(at_seconds=999), "outside"),
            ("nonfinite_sample_rejected", lambda row: row["frame_samples"][0].update(at_seconds=float("nan")), "outside"),
        ]
        for name, mutate, expected in mutations:
            bad = copy.deepcopy(record)
            mutate(bad["reviews"][0])
            check(name, validate_sources(bad, base)[0], expected)
        bad = copy.deepcopy(record)
        bad["reviews"][0]["frame_samples"][0].update(
            path=reviews[1]["frame_samples"][0]["path"],
            content_sha256=reviews[1]["frame_samples"][0]["content_sha256"])
        check("foreign_pixels_fail_even_with_correct_source_label", validate_sources(bad, base)[0], "frame pixels")
        bad = copy.deepcopy(record)
        bad["reviews"][0]["frame_samples"].append(copy.deepcopy(bad["reviews"][0]["frame_samples"][0]))
        check("shared_frame_path_rejected", validate_sources(bad, base)[0], "path reused")
        bad = copy.deepcopy(record)
        bad["declared_sources"][3]["kind"] = "video"
        check("extension_does_not_prove_video_stream", validate_sources(bad, base)[0], "missing video")
        broken = base / "broken.mp4"
        broken.write_text("Not a video.")
        bad = copy.deepcopy(record)
        bad["declared_sources"][0].update(path=broken.name, content_sha256=digest(broken))
        bad["reviews"][0].update(source_sha256=digest(broken), content_review=review(broken))
        check("corrupt_actual_media_is_blocked", validate_sources(bad, base)[0], "inspection failed")
        with patch("validate_media_admission.subprocess.run", side_effect=FileNotFoundError("ffmpeg unavailable")):
            check("missing_tool_is_failure", validate_sources(record, base)[0], "unavailable")

        registry = {"utterances": [{
            "utterance_identifier": "line", "utterance_version": "1", "authority": "Synthetic script",
            "speaker_identifier": "narrator", "text": "比较两次变化。",
            "text_sha256": hashlib.sha256("比较两次变化。".encode()).hexdigest(),
        }]}
        write_json(base / "utterances.json", registry)
        unit = {
            "unit_identifier": "unit", "provider_identifier": "trae_video",
            "prompt": "以<图片1>为参考，旁白说：比较两次变化。",
            "requested_duration_seconds": 4,
            "reference_bindings": [{"reference_identifier": "reference", "slot": "image_paths[0]", "purpose": "scene"}],
            "sound_event_identifiers": ["speech"], "job_file": "job.json",
            "asset_reuse_file": "reuse-record.json",
            "output_attempt_identifier": "attempt_1", "output_file": video.name, "output_sha256": digest(video),
            "submission_expectations": {
                "adapter_identifier": "trae_generate_video_v1", "model": "unknown",
                "parameters": {"duration": 4, "resolution": "720p", "ratio": "16:9"},
                "output_contract": {"file_name": video.name},
            },
        }
        plan = {
            "schema_version": "1.2", "generation_units": [unit],
            "utterance_registry_file": "utterances.json", "utterance_registry_sha256": digest(base / "utterances.json"),
            "references": [{"reference_identifier": "reference", "kind": "image",
                            "path": image.name, "content_sha256": digest(image)}],
            "sound_events": [{"event_identifier": "speech", "kind": "narration", "speaker_identifier": "narrator",
                              "utterance_identifier": "line", "text": "比较两次变化。", "audio_source": "embedded_native"}],
        }
        raw = {"tool": "functions.GenerateVideo", "arguments": {
            "prompt": unit["prompt"], "image_paths": [image.name], "video_paths": [],
            "duration": 4, "ratio": "16:9", "resolution": "720p", "file_path": video.name,
        }}
        manifest = [{**plan["references"][0], "slot": "image_paths[0]", "purpose": "scene"}]
        attempt = request_attempt(base / "request.json", raw, manifest, plan, registry, base)
        job = {
            "schema_version": "1.1", "job_identifier": "job", "asset_identifier": "asset",
            "asset_version": "1", "provider": "trae_video", "phase": "accepted", "terminal_phase": "accepted",
            "attempts": [attempt], "request_sha256": attempt["request_sha256"],
            "active_attempt_identifier": "attempt_1", "output_paths": [video.name],
            "output_sha256": {video.name: digest(video)}, "output_attempt_identifiers": {video.name: "attempt_1"},
        }
        write_json(base / "job.json", job)
        write_json(base / "plan.json", plan)
        reuse = {
            "schema_version": "1.0", "operation": "reuse_selected_asset", "source_job_file": "job.json",
            "source_job_sha256": digest(base / "job.json"), "source_attempt_identifier": "attempt_1",
            "source_output_path": video.name, "output_sha256": digest(video), "destination_path": "adopted.mp4",
            "current_plan_file": "plan.json", "current_plan_sha256": digest(base / "plan.json"),
            "current_unit_identifier": "unit",
            "current_production_contract_sha256": expected_contract(plan, unit, registry)[2],
            "reuse_review": review(video),
        }
        check("accepted_video_reuse_retains_attempt", validate_reuse(reuse, base)[0])
        check("preflight_does_not_materialize_destination",
              [] if not (base / "adopted.mp4").exists() else ["unexpected copy"])
        check("materialized_requires_actual_file", validate_reuse(reuse, base, True)[0], "materialized")
        (base / "adopted.mp4").write_bytes(video.read_bytes())
        check("materialized_matching_copy_admitted", validate_reuse(reuse, base, True)[0])
        (base / "adopted.mp4").write_text("Unrelated user's output")
        check("existing_other_content_preserved", validate_reuse(reuse, base)[0], "preserve it")
        assert (base / "adopted.mp4").read_text() == "Unrelated user's output"
        (base / "adopted.mp4").unlink()
        for name, updates, expected in [
                ("legacy_job_not_falsely_verified", {"schema_version": "1.0"}, "Job 1.1"),
                ("nonaccepted_job_rejected", {"terminal_phase": "failed"}, "not accepted"),
                ("changed_provider_identity_rejected", {"provider": "other"}, "provider differs"),
                ("wrong_output_attempt_rejected", {"output_attempt_identifiers": {video.name: "other"}}, "wrong original"),
                ("missing_output_hash_rejected", {"output_sha256": {}}, "SHA mismatch")]:
            changed = {**job, **updates}
            write_json(base / "job.json", changed)
            candidate = {**reuse, "source_job_sha256": digest(base / "job.json")}
            check(name, validate_reuse(candidate, base)[0], expected)
        write_json(base / "job.json", job)
        for name, updates, expected in [
                ("stale_job_snapshot_rejected", {"source_job_sha256": "0" * 64}, "SHA256"),
                ("unknown_original_attempt_rejected", {"source_attempt_identifier": "unknown"}, "unknown original"),
                ("format_change_rejected", {"destination_path": "adopted.webm"}, "format suffix"),
                ("seed_is_not_determinism", {"operation": "seeded_cache"}, "unverified reuse"),
                ("stale_current_plan_rejected", {"current_plan_sha256": "0" * 64}, "SHA256"),
                ("stale_current_contract_rejected", {"current_production_contract_sha256": "0" * 64}, "identity changed")]:
            check(name, validate_reuse({**reuse, **updates}, base)[0], expected)
        changed_plan = copy.deepcopy(plan)
        changed_plan["generation_units"][0]["prompt"] += "改用另一种动作。"
        write_json(base / "plan.json", changed_plan)
        check("same_filename_changed_request_rejected",
              validate_reuse({**reuse, "current_plan_sha256": digest(base / "plan.json")}, base)[0], "current request")
        write_json(base / "plan.json", plan)
        old_image = image.read_bytes()
        image.write_text("Changed reference")
        check("changed_actual_reference_rejected", validate_reuse(reuse, base)[0], "differs")
        image.write_bytes(old_image)
        changed_registry = copy.deepcopy(registry)
        changed_registry["utterances"][0]["utterance_version"] = "2"
        write_json(base / "utterances.json", changed_registry)
        changed_plan = {**plan, "utterance_registry_sha256": digest(base / "utterances.json")}
        write_json(base / "plan.json", changed_plan)
        candidate = {**reuse, "current_plan_sha256": digest(base / "plan.json"),
                     "current_production_contract_sha256": expected_contract(
                         changed_plan, changed_plan["generation_units"][0], changed_registry)[2]}
        check("changed_authority_version_rejected", validate_reuse(candidate, base)[0], "authority")
        write_json(base / "utterances.json", registry)
        write_json(base / "plan.json", plan)
        original_bytes = video.read_bytes()
        video.write_text("Changed output bytes")
        check("changed_actual_output_rejected", validate_reuse(reuse, base)[0], "SHA256")
        video.write_bytes(original_bytes)
        adopted_plan = copy.deepcopy(plan)
        adopted_plan["generation_units"][0]["output_file"] = reuse["destination_path"]
        write_json(base / "plan.json", adopted_plan)
        adopted = {**reuse, "current_plan_sha256": digest(base / "plan.json")}
        write_json(base / "reuse-record.json", adopted)
        check("preflight_accepts_declared_future_destination", validate_reuse(adopted, base)[0])
        audit = Audit(base)
        validate_submission(adopted_plan, audit, delivery=True)
        check("delivery_rejects_unmaterialized_alias", audit.errors, "materialized")
        (base / "adopted.mp4").write_bytes(video.read_bytes())
        audit = Audit(base)
        validate_submission(adopted_plan, audit, delivery=True)
        check("existing_delivery_accepts_verified_copy_with_original_attempt", audit.errors)
        materialized_report = base / "materialized-cli-report.json"
        result = subprocess.run([sys.executable, str(Path(__file__).with_name("validate_media_admission.py")),
                                 "reuse", str(base / "reuse-record.json"), "--materialized",
                                 "--report", str(materialized_report)],
                                capture_output=True, text=True, timeout=60)
        assert result.returncode == 0 and json.loads(materialized_report.read_text())["stage"] == "materialized"
        results.append({"case": "actual_cli_materialized_alias_passed", "status": "passed"})
        wrong_plan = copy.deepcopy(adopted_plan)
        wrong_plan["generation_units"][0]["asset_reuse_file"] = "missing-reuse.json"
        audit = Audit(base)
        validate_submission(wrong_plan, audit, delivery=True)
        check("delivery_rejects_missing_reuse_record", audit.errors, "No such file")
        wrong_record = {**adopted, "source_attempt_identifier": "other"}
        write_json(base / "reuse-record.json", wrong_record)
        audit = Audit(base)
        validate_submission(adopted_plan, audit, delivery=True)
        check("delivery_rejects_rebound_attempt", audit.errors, "does not bind")
        write_json(base / "reuse-record.json", adopted)
        write_json(base / "plan.json", plan)
        baseline = {path.name: digest(path) for path in (video, image, base / "job.json", base / "request.json")}
        for branch, content, extra in (("source", record, []), ("reuse", reuse, []),
                                       ("source", {"declared_sources": []}, [])):
            path = base / (branch + "-record.json")
            write_json(path, content)
            report_path = base / (branch + "-report.json")
            result = subprocess.run([sys.executable, str(Path(__file__).with_name("validate_media_admission.py")),
                                     branch, str(path), *extra, "--report", str(report_path)],
                                    capture_output=True, text=True, timeout=60)
            expected_status = "passed" if "schema_version" in content else "failed"
            report = json.loads(report_path.read_text())
            assert report["status"] == expected_status and result.returncode == (expected_status == "failed")
            results.append({"case": "actual_cli_" + branch + "_" + expected_status, "status": "passed"})
        malformed = base / "malformed.json"
        malformed.write_text("{")
        result = subprocess.run([sys.executable, str(Path(__file__).with_name("validate_media_admission.py")),
                                 "source", str(malformed), "--report", str(base / "malformed-report.json")],
                                capture_output=True, text=True, timeout=60)
        assert result.returncode == 1 and json.loads((base / "malformed-report.json").read_text())["errors"]
        results.append({"case": "malformed_json_cli_reports_failure", "status": "passed"})
        assert baseline == {path.name: digest(path) for path in (video, image, base / "job.json", base / "request.json")}
        results.append({"case": "inspection_preserves_sources_and_job_history", "status": "passed"})
        assert inspect_media(audio, "audio")["duration_seconds"] > 0
    report = {"status": "passed", "cases": results, "count": len(results),
              "limits": "Synthetic encoded fixtures and records; no provider generation or real course acceptance."}
    if args.report:
        assert args.report.parent.is_dir()
        write_json(args.report, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
