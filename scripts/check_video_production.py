#!/usr/bin/env python3
"""Isolated encoded-media probes; synthetic reviews are never acceptance evidence."""

import copy
from array import array
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import wave

from validate_video_production import (
    MANUAL_CHECKS, digest, freeze_intervals, validate_delivery, validate_links, validate_plan,
)

ROOT = Path(__file__).resolve().parents[1]


def make_media(base, filename, visual, visual_filter=None, audio=True):
    output = base / filename
    arguments = ["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "lavfi", "-i", visual]
    if audio:
        arguments += ["-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=4"]
    if visual_filter:
        arguments += ["-vf", visual_filter]
    arguments += ["-t", "4", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "15"]
    if audio:
        arguments += ["-c:a", "aac"]
    arguments += [str(output)]
    subprocess.run(arguments, check=True, capture_output=True, timeout=60)
    return output


def fixture(base, moving):
    evidence = base / "synthetic-evidence.txt"
    evidence.write_text("Synthetic capability and review fixture; not a course approval.", encoding="utf-8")
    checksum = digest(evidence)
    environment = json.loads((ROOT / "assets/video-production-environment.template.json").read_text())
    environment["recorded_on"] = "synthetic"
    provider = environment["providers"][0]
    provider["duration_seconds"] = {"minimum": 1, "maximum": 4, "allowed_values": [1, 2, 3, 4]}
    provider["execution"] = {
        "authorization_evidence": "synthetic", "polling_policy": "synthetic", "shared_gpu_policy": "synthetic",
    }
    for capability in provider["capabilities"].values():
        capability.update(status="verified", evidence=[{"path": evidence.name, "content_sha256": checksum}])
    plan = {
        "schema_version": "1.0", "course_identifier": "synthetic", "course_version": "1",
        "environment_file": "environment.json", "environment_sha256": None,
        "references": [{"reference_identifier": "voice", "kind": "audio",
                        "path": moving.name, "content_sha256": digest(moving)}],
        "timelines": [{"timeline_identifier": "mainline", "asset_identifier": "video_main",
                       "duration_seconds": 4, "path": moving.name, "content_sha256": digest(moving)}],
        "shots": [{
            "shot_identifier": "shot", "scene_identifier": "scene", "branch_identifier": "mainline",
            "timeline_identifier": "mainline", "unit_identifier": "unit",
            "start_seconds": 0, "end_seconds": 4, "teaching_purpose": "Synthetic mapping",
            "camera": "Synthetic camera", "start_state": "Synthetic start", "end_state": "Synthetic end",
        }],
        "generation_units": [{
            "unit_identifier": "unit", "provider_identifier": "trae_video", "requested_duration_seconds": 4,
            "shot_identifiers": ["shot"], "sound_event_identifiers": ["speech"],
            "sound_event_offsets": [{"event_identifier": "speech", "start_seconds": 0.3, "end_seconds": 3.7}],
            "required_capabilities": ["text_to_video", "native_audio", "voice_reference"],
            "reference_bindings": [{"reference_identifier": "voice", "slot": "audio_1", "purpose": "voice"}],
            "prompt": "Synthetic fixture", "output_file": moving.name, "output_sha256": digest(moving),
        }],
        "sound_events": [{
            "event_identifier": "speech", "timeline_identifier": "mainline", "kind": "dialogue",
            "speaker_identifier": "speaker", "voice_reference_identifier": "voice",
            "text": "Synthetic spoken content", "start_seconds": 0.3, "end_seconds": 3.7,
            "speech_spans": [[0.3, 3.7]], "timing_status": "measured",
            "audio_source": "embedded_native", "on_screen": True, "synchronization_method": "native",
        }],
        "clips": [{
            "clip_identifier": "clip", "timeline_identifier": "mainline", "unit_identifier": "unit",
            "start_seconds": 0, "end_seconds": 4, "source_start_seconds": 0, "source_end_seconds": 4,
            "adjustment": "none", "retain_embedded_audio": True, "visual_mode": "live_action",
            "purpose": "Synthetic moving visual",
        }],
        "manual_reviews": [
            {"timeline_identifier": "mainline", "check": name, "status": "passed",
             "reviewer": "Synthetic fixture only", "bound_sha256": digest(moving),
             "evidence_file": evidence.name, "evidence_sha256": checksum}
            for name in sorted(MANUAL_CHECKS)
        ], "freeze_reviews": [],
    }
    return plan, environment, evidence


def main():
    results = []

    def inspect(name, plan, environment, base, expected=None, actual=True):
        audit = validate_plan(plan, environment, base, delivery=actual)
        if actual and not audit.errors:
            validate_delivery(plan, environment, audit)
        if expected:
            assert any(expected in error for error in audit.errors), (name, audit.errors)
        else:
            assert not audit.errors, (name, audit.errors)
        results.append({"case": name, "status": "passed"})
        return audit

    with tempfile.TemporaryDirectory(prefix="video-contract-") as temporary:
        base = Path(temporary)
        moving = make_media(base, "moving.mp4", "testsrc2=size=320x180:rate=24:duration=4")
        frozen = make_media(base, "frozen.mp4", "testsrc2=size=320x180:rate=24:duration=2",
                            "tpad=stop_mode=clone:stop_duration=2")
        static = make_media(base, "static.mp4", "color=c=black:size=320x180:rate=24:duration=4")
        middle_freeze = make_media(base, "middle-freeze.mp4",
                                  "testsrc2=size=320x180:rate=24:duration=4",
                                  "select='not(between(t,1,2))'")
        tiny = make_media(base, "tiny.mp4", "color=c=black:size=320x180:rate=24:duration=4",
                          "geq=lum='if(between(X,150,154)*between(Y,88,92),255*mod(N,2),0)':cb=128:cr=128")
        silent = make_media(base, "silent.mp4", "testsrc2=size=320x180:rate=24:duration=4", audio=False)
        plan, environment, evidence = fixture(base, moving)
        environment_path = base / "environment.json"
        environment_path.write_text(json.dumps(environment), encoding="utf-8")
        plan["environment_sha256"] = digest(environment_path)
        inspect("moving_native_voice_retained", plan, environment, base)
        external = copy.deepcopy(plan)
        external["sound_events"][0].update(
            audio_source="external_stem",
            synchronization_method="audio_driven",
            source_file=moving.name,
            source_sha256=digest(moving),
            source_start_seconds=0.3,
            source_end_seconds=3.7,
        )
        external["generation_units"][0]["required_capabilities"] = [
            "text_to_video", "audio_driven_lip_synchronization", "voice_reference"
        ]
        inspect("external_stem_drives_on_screen_lips", external, environment, base, actual=False)
        assert not freeze_intervals(tiny, environment["quality_detection"]), "Subtle motion was lost"
        results.append({"case": "small_local_motion_is_not_a_freeze", "status": "passed"})

        bad = copy.deepcopy(plan)
        bad["sound_events"][0]["end_seconds"] = 5
        bad["sound_events"][0]["speech_spans"] = [[0.3, 5]]
        inspect("speech_outlasts_timeline", bad, environment, base, "sound outlasts video", False)
        bad = copy.deepcopy(plan)
        bad["clips"][0]["adjustment"] = "hold"
        inspect("declared_tail_hold_cannot_supply_live_action", bad, environment, base,
                "artificial padding", False)
        bad = copy.deepcopy(plan)
        bad["timelines"][0].update(path=frozen.name, content_sha256=digest(frozen))
        for row in bad["manual_reviews"]:
            row["bound_sha256"] = digest(frozen)
        inspect("undeclared_encoded_tail_freeze_rejected", bad, environment, base, "frozen visual")
        bad["freeze_reviews"] = [{
            "timeline_identifier": "mainline", "start_seconds": 1.9, "end_seconds": 4,
            "status": "passed", "reviewer": "Synthetic", "reason": "Generic approval",
            "bound_sha256": digest(frozen), "evidence_file": evidence.name,
            "evidence_sha256": digest(evidence),
        }]
        inspect("generic_review_cannot_waive_frozen_speech", bad, environment, base, "frozen visual")
        middle = copy.deepcopy(plan)
        middle["timelines"][0].update(path=middle_freeze.name, content_sha256=digest(middle_freeze))
        for row in middle["manual_reviews"]:
            row["bound_sha256"] = digest(middle_freeze)
        inspect("middle_freeze_is_checked_not_only_endpoints", middle, environment, base, "frozen visual")
        good = copy.deepcopy(plan)
        good["timelines"][0].update(path=static.name, content_sha256=digest(static))
        good["sound_events"][0].update(on_screen=False, synchronization_method="off_screen", kind="narration")
        good["clips"][0].update(visual_mode="instructional_static", purpose="Synthetic readable diagram")
        for row in good["manual_reviews"]:
            row["bound_sha256"] = digest(static)
        inspect("explicit_static_teaching_under_narration", good, environment, base)
        good["clips"][0]["visual_mode"] = "interaction_wait"
        inspect("same_scene_offscreen_wait", good, environment, base)
        good["sound_events"][0].update(on_screen=True, synchronization_method="native", kind="dialogue")
        inspect("wait_cannot_hide_onscreen_dialogue", good, environment, base,
                "interaction wait cannot", False)
        bad = copy.deepcopy(plan)
        bad["timelines"][0].update(path=silent.name, content_sha256=digest(silent))
        inspect("actual_silent_video_rejected", bad, environment, base, "media inspection")
        shortened_audio = base / "shortened-audio.mp4"
        padded_silence = base / "padded-silence.mp4"
        for output, duration in (
            (shortened_audio, 1),
            (padded_silence, 4),
        ):
            audio_file = output.with_suffix(".wav")
            samples = array("h", (
                round(4000 * math.sin(2 * math.pi * 440 * i / 48000)) if i < 48000 else 0
                for i in range(duration * 48000)
            ))
            if sys.byteorder != "little":
                samples.byteswap()
            with wave.open(str(audio_file), "wb") as stream:
                stream.setnchannels(1)
                stream.setsampwidth(2)
                stream.setframerate(48000)
                stream.writeframes(samples.tobytes())
            subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", str(moving),
                            "-i", str(audio_file), "-map", "0:v:0", "-map", "1:a:0",
                            "-c:v", "copy", "-c:a", "aac", "-t", "4", str(output)],
                           check=True, capture_output=True, timeout=60)
            bad = copy.deepcopy(plan)
            bad["timelines"][0].update(path=output.name, content_sha256=digest(output))
            for row in bad["manual_reviews"]:
                row["bound_sha256"] = digest(output)
            inspect("short_audio_endpoint" if output == shortened_audio else "silent_padding_is_not_speech",
                    bad, environment, base,
                    "outlasts actual" if output == shortened_audio else "overlaps actual silence")
        short_source = make_media(base, "short-source.mp4",
                                  "testsrc2=size=320x180:rate=24:duration=2")
        bad = copy.deepcopy(plan)
        bad["generation_units"][0].update(output_file=short_source.name, output_sha256=digest(short_source))
        inspect("raw_source_ends_before_selected_interval", bad, environment, base, "source video ends")
        bad = copy.deepcopy(plan)
        bad["generation_units"][0]["output_file"] = frozen.name
        bad["generation_units"][0]["output_sha256"] = "0" * 64
        inspect("source_file_hash_drift_rejected", bad, environment, base, "fingerprint differs")
        bad = copy.deepcopy(plan)
        bad["clips"][0]["retain_embedded_audio"] = False
        inspect("native_principal_voice_cannot_be_muted", bad, environment, base, "must be retained", False)
        bad = copy.deepcopy(plan)
        bad["generation_units"][0]["reference_bindings"] = []
        inspect("voice_description_is_not_actual_binding", bad, environment, base,
                "native fixed voice", False)
        bad_environment = copy.deepcopy(environment)
        bad_environment["providers"][0]["capabilities"]["native_audio"]["status"] = "unknown"
        inspect("unknown_provider_capability_rejected", plan, bad_environment, base, "not verified", False)
        bad = copy.deepcopy(plan)
        extra = copy.deepcopy(bad["sound_events"][0])
        extra["event_identifier"] = "second_speech"
        bad["sound_events"].append(extra)
        bad["generation_units"][0]["sound_event_identifiers"].append("second_speech")
        bad["generation_units"][0]["sound_event_offsets"].append({
            "event_identifier": "second_speech", "start_seconds": 0.3, "end_seconds": 3.7,
        })
        inspect("duplicate_principal_speech_overlap_rejected", bad, environment, base,
                "Unplanned overlapping", False)
        bad = copy.deepcopy(plan)
        bad["generation_units"][0]["requested_duration_seconds"] = 3
        inspect("submitted_duration_cannot_cover_longer_shot", bad, environment, base,
                "planned source coverage", False)
        bad = copy.deepcopy(plan)
        bad["generation_units"][0]["sound_event_offsets"][0]["start_seconds"] = 1
        inspect("absolute_relative_audio_clock_mismatch", bad, environment, base,
                "relative sound offset", False)
        bad = copy.deepcopy(plan)
        bad["clips"][0]["end_seconds"] = 2
        bad["clips"][0]["source_end_seconds"] = 2
        second = copy.deepcopy(bad["clips"][0])
        second.update(clip_identifier="clip_second", start_seconds=2, end_seconds=4)
        bad["clips"].append(second)
        inspect("source_interval_assembled_twice", bad, environment, base, "assembled twice", False)
        bad = copy.deepcopy(plan)
        bad["sound_events"][0].update(audio_source="external_stem", synchronization_method="off_screen",
                                      on_screen=False, source_file=moving.name, source_sha256=digest(moving),
                                      source_start_seconds=0.3, source_end_seconds=2)
        inspect("speech_cannot_be_shortened", bad, environment, base, "stretched or shortened", False)
        bad = copy.deepcopy(plan)
        bad["manual_reviews"][0]["bound_sha256"] = "0" * 64
        inspect("old_manual_review_cannot_pass_new_file", bad, environment, base, "another file")
        bad = copy.deepcopy(plan)
        bad["sound_events"][0]["timing_status"] = "estimated"
        inspect("delivery_requires_actual_audio_timing", bad, environment, base, "actual recording", True)
        manifest = {
            "course_identifier": "synthetic", "course_version": "1",
            "assets": [{"asset_identifier": "video_missing", "required": True, "kind": "linear_video"}],
        }
        audit = validate_plan(plan, environment, base)
        validate_links(plan, manifest, None, audit)
        assert any("required video missing" in error for error in audit.errors), audit.errors
        results.append({"case": "full_course_missing_video_rejected", "status": "passed"})
        blueprint = {
            "course_identifier": "synthetic", "course_version": "1",
            "scenes": [{"scene_identifier": "scene"}],
            "media_resources": [{"resource_identifier": "video_main", "required": True,
                                 "media_type": "video", "file_path": moving.name}],
        }
        audit = validate_plan(plan, environment, base)
        validate_links(plan, None, blueprint, audit, True)
        assert not audit.errors, audit.errors
        results.append({"case": "blueprint_actual_video_identity_matches", "status": "passed"})
        plan_path = base / "plan.json"
        plan_path.write_text(json.dumps(plan), encoding="utf-8")
        report_path = base / "report.json"
        subprocess.run([sys.executable, str(ROOT / "scripts/validate_video_production.py"),
                        str(plan_path), "--delivery", "--report", str(report_path)],
                       check=True, capture_output=True, timeout=60)
        report = json.loads(report_path.read_text())
        assert report["status"] == "passed" and report["measurements"]
        results.append({"case": "actual_cli_delivery_and_report", "status": "passed"})
    print(json.dumps({
        "passed": len(results), "cases": results,
        "limits": "Synthetic encoded fixtures and reviews; no voice inference, actual human lip/voice review or learner trial.",
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
