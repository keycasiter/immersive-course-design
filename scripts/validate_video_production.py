#!/usr/bin/env python3
"""Check a video plan and actual media. Never creates course approval evidence."""

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import sys
import tempfile

from contract_checks import placeholder_paths
from video_character_contract import validate_character_plan, validate_character_reviews
from submission_contract import validate_submission
from video_seam_contract import validate_seams

SHA256 = re.compile(r"^[0-9a-f]{64}$")
SPEECH = {"dialogue", "narration"}
MODES = {"live_action", "graphic_animation", "instructional_static", "interaction_wait"}
ADJUSTMENTS = {"none", "cut", "hold", "loop", "reverse", "speed", "digital_zoom"}
MANUAL_CHECKS = {
    "content", "voice_identity", "lip_synchronization", "subtitles_and_events",
    "continuity", "listening",
}


def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def rows(value):
    return [row for row in value if isinstance(row, dict)] if isinstance(value, list) else []


def overlap(first, second):
    return max(0, min(first[1], second[1]) - max(first[0], second[0]))


def span(row, prefix=""):
    start, end = row.get(prefix + "start_seconds"), row.get(prefix + "end_seconds")
    return (start, end) if number(start) and number(end) and 0 <= start < end else None


def covered(interval, intervals, tolerance=0.02):
    position = interval[0]
    for start, end in sorted(intervals):
        if start > position + tolerance:
            break
        position = max(position, end)
        if position + tolerance >= interval[1]:
            return True
    return False


class Audit:
    def __init__(self, base):
        self.base = Path(base)
        self.errors = []
        self.warnings = []
        self.measurements = []

    def need(self, condition, message):
        if not condition:
            self.errors.append(message)

    def path(self, value):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Expected a non-empty file path")
        path = Path(value)
        return path if path.is_absolute() else self.base / path

    def file(self, value, checksum, label):
        try:
            path = self.path(value)
            if not isinstance(checksum, str) or not SHA256.fullmatch(checksum):
                raise ValueError("Missing valid SHA256")
            if digest(path) != checksum:
                raise ValueError("File fingerprint differs")
            return path
        except (ValueError, OSError) as exc:
            self.errors.append(f"{label}: {exc}")
            return None

    def collection(self, value, label, key, allow_empty=False):
        self.need(isinstance(value, list), f"{label} must be an array")
        entries = rows(value)
        self.need(isinstance(value, list) and len(entries) == len(value),
                  f"{label} requires object entries")
        self.need(allow_empty or bool(entries), f"{label} must not be empty")
        identifiers = [row.get(key) for row in entries]
        valid = all(isinstance(item, str) and bool(item.strip()) for item in identifiers)
        self.need(valid, f"{label} has a missing identifier")
        if valid:
            self.need(len(set(identifiers)) == len(identifiers), f"{label} has duplicate identifiers")
        return {row[key]: row for row in entries if isinstance(row.get(key), str)}

    def evidence(self, row, label, bound_hash=None):
        if not isinstance(row, dict):
            self.errors.append(f"{label}: evidence must be an object")
            return False
        self.need(row.get("status") == "passed", f"{label}: review has not passed")
        self.need(isinstance(row.get("reviewer"), str) and bool(row["reviewer"].strip()),
                  f"{label}: reviewer is required")
        if bound_hash:
            self.need(row.get("bound_sha256") == bound_hash, f"{label}: review is for another file")
        return self.file(row.get("evidence_file"), row.get("evidence_sha256"), label) is not None


def validate_plan(plan, environment, base, delivery=False):
    audit = Audit(base)
    if not isinstance(plan, dict) or not isinstance(environment, dict):
        audit.errors.append("Plan and environment must be JSON objects")
        return audit
    audit.need(plan.get("schema_version") in ("1.0", "1.1", "1.2"), "Unsupported video plan schema")
    if plan.get("schema_version") == "1.0":
        audit.warnings.append("Schema 1.0: character references and first-appearance introductions "
                              "have not been validated; migrate authorized revisions to 1.2.")
    if plan.get("schema_version") in ("1.0", "1.1"):
        audit.warnings.append("Legacy plan: final submitted request and source-PTS seams are not "
                              "validated; authorized revisions use schema 1.2.")
    audit.need(environment.get("schema_version") == "1.0", "Unsupported video environment schema")
    for label, value in (("plan", plan), ("environment", environment)):
        for field in placeholder_paths(value):
            audit.errors.append(f"{label}{field}: unfilled placeholder")
    providers = audit.collection(environment.get("providers"), "providers", "provider_identifier")
    timelines = audit.collection(plan.get("timelines"), "timelines", "timeline_identifier")
    shots = audit.collection(plan.get("shots"), "shots", "shot_identifier")
    units = audit.collection(plan.get("generation_units"), "generation_units", "unit_identifier")
    references = audit.collection(plan.get("references"), "references", "reference_identifier", True)
    events = audit.collection(plan.get("sound_events"), "sound_events", "event_identifier")
    clips = audit.collection(plan.get("clips"), "clips", "clip_identifier")
    for identifier, reference in references.items():
        audit.file(reference.get("path"), reference.get("content_sha256"), identifier)
    for identifier, timeline in timelines.items():
        audit.need(number(timeline.get("duration_seconds")) and timeline["duration_seconds"] > 0,
                   f"{identifier}: invalid timeline duration")
        audit.need(isinstance(timeline.get("asset_identifier"), str),
                   f"{identifier}: asset_identifier is required")

    for identifier, unit in units.items():
        provider = providers.get(unit.get("provider_identifier"), {})
        audit.need(bool(provider), f"{identifier}: unknown provider")
        constraints = provider.get("duration_seconds", {})
        constraints = constraints if isinstance(constraints, dict) else {}
        duration = unit.get("requested_duration_seconds")
        lower, upper = constraints.get("minimum"), constraints.get("maximum")
        valid = number(duration) and number(lower) and number(upper) and 0 < lower <= duration <= upper
        audit.need(valid, f"{identifier}: requested duration is outside verified provider bounds")
        allowed = constraints.get("allowed_values", [])
        audit.need(isinstance(allowed, list) and all(number(item) for item in allowed),
                   f"{identifier}: invalid discrete durations")
        if allowed:
            audit.need(duration in allowed, f"{identifier}: requested duration is not a supported slot")
        capabilities = provider.get("capabilities", {})
        capabilities = capabilities if isinstance(capabilities, dict) else {}
        required = unit.get("required_capabilities")
        audit.need(isinstance(required, list) and bool(required) and
                   all(isinstance(item, str) for item in required),
                   f"{identifier}: required_capabilities must be explicit")
        for name in required if isinstance(required, list) else []:
            capability = capabilities.get(name, {}) if isinstance(name, str) else {}
            capability = capability if isinstance(capability, dict) else {}
            audit.need(capability.get("status") == "verified",
                       f"{identifier}: capability {name} is not verified")
            evidence = rows(capability.get("evidence"))
            audit.need(bool(evidence), f"{identifier}: {name} lacks capability evidence")
            for entry in evidence:
                audit.file(entry.get("path"), entry.get("content_sha256"), f"{identifier}.{name}")
        shot_ids, event_ids = unit.get("shot_identifiers"), unit.get("sound_event_identifiers")
        audit.need(isinstance(shot_ids, list) and bool(shot_ids) and
                   all(isinstance(item, str) and item in shots for item in shot_ids),
                   f"{identifier}: unknown or missing shots")
        audit.need(isinstance(event_ids, list) and
                   all(isinstance(item, str) and item in events for item in event_ids),
                   f"{identifier}: unknown sound events")
        offsets = audit.collection(unit.get("sound_event_offsets"),
                                   identifier + ".sound_event_offsets", "event_identifier", True)
        audit.need(isinstance(event_ids, list) and set(offsets) == set(event_ids),
                   f"{identifier}: absolute/relative sound mappings are incomplete")
        for event_identifier, offset in offsets.items():
            relative = span(offset)
            audit.need(relative is not None and number(duration) and relative[1] <= duration,
                       f"{identifier}.{event_identifier}: relative sound exceeds generation unit")
        if isinstance(shot_ids, list) and len(shot_ids) > 1:
            audit.need(isinstance(required, list) and "multi_shot" in required,
                       f"{identifier}: multiple shots require verified multi_shot")
        bindings = unit.get("reference_bindings", [])
        audit.need(isinstance(bindings, list) and len(rows(bindings)) == len(bindings),
                   f"{identifier}: invalid reference bindings")
        slots = set()
        for binding in rows(bindings):
            reference = binding.get("reference_identifier")
            slot, purpose = binding.get("slot"), binding.get("purpose")
            audit.need(isinstance(reference, str) and reference in references,
                       f"{identifier}: reference is not an actual registered file")
            audit.need(isinstance(slot, str) and slot not in slots,
                       f"{identifier}: missing or duplicate reference slot")
            if isinstance(slot, str):
                slots.add(slot)
            capability_name = {
                "identity": "image_reference", "scene": "image_reference", "prop": "image_reference",
                "first_frame": "first_frame", "last_frame": "last_frame",
                "voice": "voice_reference", "timing": "audio_timing",
                "previous_clip": "video_reference",
            }.get(purpose) if isinstance(purpose, str) else None
            audit.need(capability_name is not None and isinstance(required, list) and
                       capability_name in required, f"{identifier}: reference purpose lacks capability")
        audit.need(isinstance(unit.get("prompt"), str) and bool(unit["prompt"].strip()),
                   f"{identifier}: missing compiled prompt")

    for identifier, shot in shots.items():
        interval = span(shot)
        timeline = timelines.get(shot.get("timeline_identifier"), {})
        unit = units.get(shot.get("unit_identifier"), {})
        audit.need(interval is not None, f"{identifier}: invalid shot interval")
        audit.need(bool(timeline) and bool(unit), f"{identifier}: missing timeline or unit")
        audit.need(identifier in unit.get("shot_identifiers", []),
                   f"{identifier}: unit does not map back to shot")
        for field in ("scene_identifier", "branch_identifier", "teaching_purpose", "camera",
                      "start_state", "end_state"):
            audit.need(isinstance(shot.get(field), str) and bool(shot[field].strip()),
                       f"{identifier}: missing {field}")
        if interval and number(timeline.get("duration_seconds")):
            audit.need(interval[1] <= timeline["duration_seconds"] + 0.02,
                       f"{identifier}: shot exceeds timeline")

    speaker_references = {}
    for identifier, event in events.items():
        interval = span(event)
        timeline = timelines.get(event.get("timeline_identifier"), {})
        audit.need(bool(timeline) and interval is not None, f"{identifier}: invalid sound interval")
        if interval and number(timeline.get("duration_seconds")):
            audit.need(interval[1] <= timeline["duration_seconds"] + 0.02,
                       f"{identifier}: sound outlasts video")
        kind = event.get("kind")
        audit.need(isinstance(kind, str) and kind in SPEECH | {"environment", "action", "music"},
                   f"{identifier}: invalid sound kind")
        mapped_units = [unit for unit in units.values()
                        if identifier in unit.get("sound_event_identifiers", [])]
        audit.need(bool(mapped_units), f"{identifier}: sound not assigned to a generation unit")
        if kind not in SPEECH:
            continue
        speaker, reference = event.get("speaker_identifier"), event.get("voice_reference_identifier")
        audit.need(isinstance(speaker, str) and bool(speaker), f"{identifier}: missing speaker")
        audit.need(isinstance(event.get("text"), str) and bool(event["text"].strip()),
                   f"{identifier}: missing complete speech text")
        audit.need(isinstance(reference, str) and reference in references and
                   references[reference].get("kind") == "audio", f"{identifier}: missing fixed voice file")
        if isinstance(speaker, str):
            previous = speaker_references.setdefault(speaker, reference)
            audit.need(previous == reference, f"{identifier}: speaker voice reference changed")
        method, source = event.get("synchronization_method"), event.get("audio_source")
        audit.need(isinstance(event.get("on_screen"), bool), f"{identifier}: on_screen must be boolean")
        audit.need(source in ("embedded_native", "external_stem"),
                   f"{identifier}: choose one principal voice source")
        if event.get("on_screen") is True:
            audit.need((method == "native" and source == "embedded_native") or
                       (method == "audio_driven" and source == "external_stem"),
                       f"{identifier}: replacement speech must drive on-screen lips")
            capability = "native_audio" if method == "native" else "audio_driven_lip_synchronization"
            audit.need(all(capability in unit.get("required_capabilities", []) for unit in mapped_units),
                       f"{identifier}: lip synchronization route lacks verified capability")
            if method == "native":
                audit.need(all(any(binding.get("purpose") == "voice" and
                                   binding.get("reference_identifier") == reference
                                   for binding in rows(unit.get("reference_bindings")))
                               for unit in mapped_units),
                           f"{identifier}: native fixed voice lacks actual reference binding")
        if source == "embedded_native":
            audit.need(all("native_audio" in unit.get("required_capabilities", [])
                           for unit in mapped_units),
                       f"{identifier}: embedded speech route lacks native audio capability")
        elif event.get("on_screen") is False:
            audit.need(method == "off_screen", f"{identifier}: off-screen speech route is unclear")
        audit.need(event.get("timing_status") in ("estimated", "measured"),
                   f"{identifier}: invalid timing status")
        if delivery:
            audit.need(event.get("timing_status") == "measured",
                       f"{identifier}: actual recording timing is required")
        speech_spans = event.get("speech_spans")
        audit.need(isinstance(speech_spans, list) and bool(speech_spans),
                   f"{identifier}: actual speech spans are required")
        valid_spans = []
        for item in speech_spans if isinstance(speech_spans, list) else []:
            valid_span = (isinstance(item, list) and len(item) == 2 and all(number(x) for x in item)
                          and interval and interval[0] <= item[0] < item[1] <= interval[1])
            audit.need(valid_span, f"{identifier}: invalid speech span")
            if valid_span:
                valid_spans.append(item)
        audit.need(all(a[1] <= b[0] for a, b in zip(valid_spans, valid_spans[1:])),
                   f"{identifier}: speech spans overlap or are out of order")
        if source == "external_stem":
            audit.file(event.get("source_file"), event.get("source_sha256"), identifier + ".speech")
            source_interval = span(event, "source_")
            audit.need(source_interval is not None, f"{identifier}: missing speech source interval")
            if source_interval and interval:
                audit.need(abs((interval[1] - interval[0]) -
                               (source_interval[1] - source_interval[0])) < 0.1,
                           f"{identifier}: speech was stretched or shortened")

    speech_events = [event for event in events.values() if event.get("kind") in SPEECH and span(event)]
    for index, first in enumerate(speech_events):
        for second in speech_events[index + 1:]:
            if first.get("timeline_identifier") != second.get("timeline_identifier"):
                continue
            spans_a, spans_b = first.get("speech_spans", []), second.get("speech_spans", [])
            simultaneous = any(overlap(a, b) > 0.05 for a in spans_a for b in spans_b
                               if isinstance(a, list) and len(a) == 2 and all(number(v) for v in a)
                               and isinstance(b, list) and len(b) == 2 and all(number(v) for v in b))
            audit.need(not simultaneous or bool(first.get("parallel_speech_reason")) or
                       bool(second.get("parallel_speech_reason")), "Unplanned overlapping principal speech")

    for identifier, clip in clips.items():
        interval, source_interval = span(clip), span(clip, "source_")
        unit = units.get(clip.get("unit_identifier"), {})
        timeline = timelines.get(clip.get("timeline_identifier"), {})
        adjustment, mode = clip.get("adjustment"), clip.get("visual_mode")
        audit.need(interval is not None and source_interval is not None and bool(unit) and bool(timeline),
                   f"{identifier}: invalid source or target clip")
        audit.need(isinstance(mode, str) and mode in MODES, f"{identifier}: invalid visual mode")
        audit.need(isinstance(adjustment, str) and adjustment in ADJUSTMENTS,
                   f"{identifier}: unknown clip adjustment")
        audit.need(bool(clip.get("purpose")), f"{identifier}: actual visual purpose is required")
        if interval and source_interval and adjustment in ("none", "cut"):
            audit.need(abs((interval[1] - interval[0]) -
                           (source_interval[1] - source_interval[0])) < 0.1,
                       f"{identifier}: unrecorded frame padding or retiming")
        if source_interval and number(unit.get("requested_duration_seconds")):
            audit.need(source_interval[1] <= unit["requested_duration_seconds"] + 0.1,
                       f"{identifier}: planned source coverage exceeds submitted duration")
        if mode == "live_action":
            audit.need(adjustment in ("none", "cut"),
                       f"{identifier}: artificial padding cannot supply live action")
        if interval and number(timeline.get("duration_seconds")):
            audit.need(interval[1] <= timeline["duration_seconds"] + 0.02,
                       f"{identifier}: clip exceeds timeline")
        if mode == "interaction_wait" and interval:
            audit.need(not any(event.get("on_screen") is True and
                               event.get("timeline_identifier") == clip.get("timeline_identifier") and
                               span(event) and overlap(interval, span(event)) > 0
                               for event in speech_events),
                       f"{identifier}: interaction wait cannot carry on-screen speech")
        if interval:
            native_overlap = any(event.get("audio_source") == "embedded_native" and
                                 event.get("timeline_identifier") == clip.get("timeline_identifier") and
                                 span(event) and overlap(interval, span(event)) > 0.02
                                 for event in speech_events)
            audit.need(not native_overlap or clip.get("retain_embedded_audio") is True,
                       f"{identifier}: principal native speech must be retained")
    for identifier, timeline in timelines.items():
        timeline_clips = [clip for clip in clips.values()
                          if clip.get("timeline_identifier") == identifier and span(clip)]
        if number(timeline.get("duration_seconds")):
            audit.need(covered((0, timeline["duration_seconds"]), [span(clip) for clip in timeline_clips]),
                       f"{identifier}: visual coverage has gaps")
        for event in events.values():
            if event.get("timeline_identifier") == identifier and span(event):
                audit.need(covered(span(event), [span(clip) for clip in timeline_clips]),
                           f"{event.get('event_identifier')}: speech lacks visual coverage")
                assigned = {unit_identifier for unit_identifier, unit in units.items()
                            if event.get("event_identifier") in unit.get("sound_event_identifiers", [])}
                audit.need(covered(span(event), [span(clip) for clip in timeline_clips
                                                if clip.get("unit_identifier") in assigned]),
                           f"{event.get('event_identifier')}: sound/production unit time mapping differs")
                mapped_intervals = []
                for clip in timeline_clips:
                    unit = units.get(clip.get("unit_identifier"), {})
                    for offset in rows(unit.get("sound_event_offsets")):
                        relative, source = span(offset), span(clip, "source_")
                        if (offset.get("event_identifier") == event.get("event_identifier") and
                                relative and source and overlap(relative, source) > 0):
                            mapped_intervals.append((
                                clip["start_seconds"] + max(relative[0], source[0]) - source[0],
                                clip["start_seconds"] + min(relative[1], source[1]) - source[0],
                            ))
                audit.need(covered(span(event), mapped_intervals),
                           f"{event.get('event_identifier')}: relative sound offset differs from final clock")
        for index, first in enumerate(timeline_clips):
            for second in timeline_clips[index + 1:]:
                if overlap(span(first), span(second)) > 0.02:
                    audit.errors.append(f"{identifier}: visual clips overlap; flatten transition mapping")
                if (first.get("unit_identifier") == second.get("unit_identifier") and
                        span(first, "source_") and span(second, "source_") and
                        overlap(span(first, "source_"), span(second, "source_")) > 0.02):
                    audit.need(bool(first.get("replay_reason")) or bool(second.get("replay_reason")),
                               f"{identifier}: generation output source interval assembled twice")
        for shot in shots.values():
            if shot.get("timeline_identifier") == identifier and span(shot):
                audit.need(covered(span(shot), [span(clip) for clip in timeline_clips
                                              if clip.get("unit_identifier") == shot.get("unit_identifier")]),
                           f"{shot.get('shot_identifier')}: shots/clip unit mapping differs")
    if plan.get("schema_version") in ("1.1", "1.2"):
        validate_character_plan(plan, audit, shots, timelines, references, events)
    if plan.get("schema_version") == "1.2":
        audit.need(isinstance(plan.get("utterance_registry_file"), str) and
                   bool(plan["utterance_registry_file"].strip()), "Missing authority registry path")
        for unit in units.values():
            audit.need(isinstance(unit.get("submission_expectations"), dict),
                       f"{unit['unit_identifier']}: missing submission_expectations")
        validate_seams(plan, audit)
    return audit


def command(arguments, timeout=600):
    result = subprocess.run(arguments, capture_output=True, timeout=timeout)
    if result.returncode:
        raise ValueError(result.stderr.decode("utf-8", errors="replace")[-2000:])
    return result


def probe(path):
    return json.loads(command([
        "ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path),
    ]).stdout)


def stream_end(stream, info):
    duration = stream.get("duration")
    # Reject unknown stream duration rather than substituting container duration.
    if duration is None:
        tags = stream.get("tags", {})
        text = tags.get("DURATION", "")
        if re.fullmatch(r"\d+:\d+:\d+(?:\.\d+)?", text):
            hours, minutes, seconds = text.split(":")
            duration = float(hours) * 3600 + float(minutes) * 60 + float(seconds)
    if duration is None:
        raise ValueError("Stream end could not be measured")
    return float(stream.get("start_time", 0)) + float(duration)


def decode(path):
    command(["ffmpeg", "-nostdin", "-v", "error", "-xerror", "-i", str(path),
             "-map", "0:v?", "-map", "0:a?", "-f", "null", "-"])


def freeze_intervals(path, settings, motion_regions=()):
    import numpy as np
    width = settings.get("scan_width_pixels", 480)
    if not isinstance(width, int) or not 240 <= width <= 1920:
        raise ValueError("scan_width_pixels must be between 240 and 1920")
    info = probe(path)
    stream = next(row for row in info["streams"] if row.get("codec_type") == "video")
    height = max(2, round(stream["height"] * width / stream["width"] / 2) * 2)
    rate = 24
    intervals, start, previous, index = [], None, None, 0
    arguments = ["ffmpeg", "-nostdin", "-v", "error", "-i", str(path), "-an",
                 "-vf", f"fps={rate},scale={width}:{height},format=gray",
                 "-f", "rawvideo", "-pix_fmt", "gray", "-"]
    with tempfile.TemporaryFile() as stderr:
        process = subprocess.Popen(arguments, stdout=subprocess.PIPE, stderr=stderr)
        try:
            while True:
                raw = process.stdout.read(width * height)
                if not raw:
                    break
                if len(raw) != width * height:
                    raise ValueError("Incomplete frame during motion scan")
                current = np.frombuffer(raw, dtype=np.uint8).reshape(height, width).astype(np.int16)
                time = index / rate
                if previous is not None:
                    delta = np.abs(current - previous)
                    still = (float(delta.mean()) <= settings.get("maximum_mean_difference", 0.015) and
                             float(np.mean(delta > settings.get("pixel_change_threshold", 8))) <=
                             settings.get("maximum_changed_pixel_fraction", 0.000004))
                    # Speech/hand regions preserve low-amplitude local motion while the
                    # whole-frame threshold tolerates re-encoding noise on cloned frames.
                    for region in motion_regions:
                        x, y, region_width, region_height = region["normalized_rectangle"]
                        local = delta[int(y * height):max(int(y * height) + 1, int((y + region_height) * height)),
                                      int(x * width):max(int(x * width) + 1, int((x + region_width) * width))]
                        if local.size and (float(local.mean()) > 0.08 or
                                           float(np.mean(local > 2)) > 0.01):
                            still = False
                    if still and start is None:
                        start = (index - 1) / rate
                    if not still and start is not None:
                        if time - start >= settings.get("minimum_freeze_seconds", 0.5):
                            intervals.append([round(start, 4), round(time, 4)])
                        start = None
                previous, index = current, index + 1
            end = index / rate
            if start is not None and end - start >= settings.get("minimum_freeze_seconds", 0.5):
                intervals.append([round(start, 4), round(end, 4)])
            if process.wait(timeout=30):
                stderr.seek(0)
                raise ValueError(stderr.read().decode("utf-8", errors="replace")[-2000:])
        finally:
            process.stdout.close()
            if process.poll() is None:
                process.kill()
                process.wait()
    return intervals


def silence_intervals(path, settings):
    level = settings.get("speech_silence_threshold_decibels", -50)
    minimum = settings.get("speech_silence_minimum_seconds", 0.3)
    result = command(["ffmpeg", "-nostdin", "-hide_banner", "-i", str(path), "-vn",
                      "-af", f"silencedetect=noise={level}dB:d={minimum}", "-f", "null", "-"])
    intervals, start = [], None
    for marker, value in re.findall(r"silence_(start|end):\s*([0-9.]+)",
                                    result.stderr.decode("utf-8", errors="replace")):
        if marker == "start":
            start = float(value)
        elif start is not None:
            intervals.append([start, float(value)])
            start = None
    return intervals


def validate_delivery(plan, environment, audit):
    if plan.get("schema_version") == "1.2":
        validate_submission(plan, audit, delivery=True)
        validate_seams(plan, audit, inspect_media=True)
    settings = environment.get("quality_detection", {})
    if not isinstance(settings, dict):
        audit.errors.append("quality_detection must be an object")
        return
    for key in ("pixel_change_threshold", "maximum_mean_difference", "maximum_changed_pixel_fraction",
                "minimum_freeze_seconds", "stream_end_tolerance_seconds",
                "speech_silence_threshold_decibels", "speech_silence_minimum_seconds"):
        audit.need(number(settings.get(key)), f"quality_detection.{key} is required and finite")
    audit.need(0 < settings.get("minimum_freeze_seconds", 0) <= 1,
               "Freeze duration threshold must preserve short speech stalls")
    audit.need(0 < settings.get("stream_end_tolerance_seconds", 0) <= 0.25,
               "Stream end tolerance cannot mask a missing phrase")
    audit.need(0 <= settings.get("maximum_mean_difference", -1) <= 0.1 and
               0 <= settings.get("maximum_changed_pixel_fraction", -1) <= 0.0001 and
               0 < settings.get("pixel_change_threshold", 0) <= 12,
               "Motion thresholds must preserve subtle facial motion")
    audit.need(-90 <= settings.get("speech_silence_threshold_decibels", 0) <= -20 and
               0.05 <= settings.get("speech_silence_minimum_seconds", 0) <= 0.5,
               "Speech silence thresholds are outside diagnostic bounds")
    if audit.errors:
        return
    units = {row["unit_identifier"]: row for row in rows(plan["generation_units"])}
    clips = rows(plan["clips"])
    events = rows(plan["sound_events"])
    for unit in units.values():
        path = audit.file(unit.get("output_file"), unit.get("output_sha256"),
                          unit["unit_identifier"] + ".output")
        if not path:
            continue
        try:
            info = probe(path)
            stream = next(row for row in info["streams"] if row.get("codec_type") == "video")
            end = stream_end(stream, info)
            decode(path)
            for clip in clips:
                if clip["unit_identifier"] == unit["unit_identifier"] and span(clip, "source_"):
                    audit.need(clip["source_end_seconds"] <= end + 0.02,
                               f"{clip['clip_identifier']}: source video ends before selected interval")
        except (OSError, ValueError, StopIteration, subprocess.SubprocessError) as exc:
            audit.errors.append(f"{unit['unit_identifier']}: source probe/decode failed: {exc}")

    for timeline in rows(plan["timelines"]):
        identifier, checksum = timeline["timeline_identifier"], timeline.get("content_sha256")
        path = audit.file(timeline.get("path"), checksum, identifier + ".delivery")
        if not path:
            continue
        try:
            info = probe(path)
            streams = info["streams"]
            video = next(row for row in streams if row.get("codec_type") == "video")
            audio = next(row for row in streams if row.get("codec_type") == "audio")
            video_end, audio_end = stream_end(video, info), stream_end(audio, info)
            tolerance = settings["stream_end_tolerance_seconds"]
            expected = timeline["duration_seconds"]
            audit.need(abs(video_end - expected) <= tolerance,
                       f"{identifier}: actual video endpoint differs from plan")
            timeline_events = [event for event in events if event["timeline_identifier"] == identifier]
            speech = [event for event in timeline_events if event["kind"] in SPEECH]
            audit.need(bool(speech), f"{identifier}: formal linear video lacks planned human speech")
            if speech:
                audit.need(max(event["end_seconds"] for event in speech) <=
                           min(video_end, audio_end) + tolerance,
                           f"{identifier}: speech outlasts actual video/audio stream")
            decode(path)
            regions = timeline.get("motion_regions", [])
            valid_regions = []
            for region in rows(regions):
                rectangle = region.get("normalized_rectangle")
                valid = (isinstance(rectangle, list) and len(rectangle) == 4 and
                         all(number(value) for value in rectangle) and
                         rectangle[0] >= 0 and rectangle[1] >= 0 and
                         rectangle[2] > 0 and rectangle[3] > 0 and
                         rectangle[0] + rectangle[2] <= 1 and rectangle[1] + rectangle[3] <= 1)
                audit.need(valid and bool(region.get("purpose")), f"{identifier}: invalid motion region")
                if valid:
                    valid_regions.append(region)
            freezes = freeze_intervals(path, settings, valid_regions)
            silences = silence_intervals(path, settings)
            audit.measurements.append({
                "timeline_identifier": identifier, "content_sha256": checksum,
                "video_end_seconds": video_end, "audio_end_seconds": audio_end,
                "freeze_intervals": freezes, "silence_intervals": silences,
                "detection_settings": settings, "motion_regions": valid_regions,
            })
            for interval in freezes:
                active_clips = [clip for clip in clips if clip["timeline_identifier"] == identifier and
                                overlap(interval, span(clip)) > 0.02]
                approved_static = covered(interval, [
                    span(clip) for clip in active_clips
                    if clip["visual_mode"] in ("instructional_static", "interaction_wait")
                ], 0.06)
                talking = any(overlap(interval, item) > 0.15 for event in speech
                              for item in event["speech_spans"])
                on_screen = any(event["on_screen"] and overlap(interval, span(event)) > 0.02
                                for event in speech)
                if approved_static and not on_screen:
                    continue
                if talking:
                    audit.errors.append(f"{identifier}: frozen visual overlaps speech at {interval}")
                    continue
                reviews = [row for row in rows(plan.get("freeze_reviews"))
                           if row.get("timeline_identifier") == identifier and span(row) and
                           covered(interval, [span(row)], 0.06) and bool(row.get("reason"))]
                audit.need(bool(reviews), f"{identifier}: unresolved still interval {interval}")
                for review in reviews:
                    audit.evidence(review, identifier + ".freeze_review", checksum)
            for event in speech:
                audio_path, source_hash = path, checksum
                offset = 0
                source_silences = silences
                if event["audio_source"] == "external_stem":
                    audio_path = audit.file(event.get("source_file"), event.get("source_sha256"),
                                            event["event_identifier"] + ".source")
                    source_hash = event.get("source_sha256")
                    if not audio_path:
                        continue
                    audio_info = probe(audio_path)
                    source_audio = next(row for row in audio_info["streams"]
                                        if row.get("codec_type") == "audio")
                    audit.need(event["source_end_seconds"] <= stream_end(source_audio, audio_info) + 0.02,
                               f"{event['event_identifier']}: speech source is truncated")
                    decode(audio_path)
                    offset = event["source_start_seconds"] - event["start_seconds"]
                    source_silences = silence_intervals(audio_path, settings)
                for item in event["speech_spans"]:
                    mapped = [item[0] + offset, item[1] + offset]
                    silent_overlap = any(overlap(mapped, silence) >=
                                         settings["speech_silence_minimum_seconds"]
                                         for silence in source_silences)
                    if silent_overlap:
                        review = event.get("silence_review")
                        audit.need(isinstance(review, dict) and span(review) is not None and
                                   covered(mapped, [span(review)]) and bool(review.get("reason")),
                                   f"{event['event_identifier']}: planned speech overlaps actual silence {item}")
                        if isinstance(review, dict):
                            audit.evidence(review, event["event_identifier"] + ".silence_review", source_hash)
            reviews = [row for row in rows(plan.get("manual_reviews"))
                       if row.get("timeline_identifier") == identifier]
            checks = {row.get("check") for row in reviews if isinstance(row.get("check"), str)}
            audit.need(MANUAL_CHECKS.issubset(checks),
                       f"{identifier}: missing file-bound manual content/voice/lips/subtitle/continuity/listening review")
            for review in reviews:
                if (plan.get("schema_version") in ("1.1", "1.2") and
                        review.get("check") in ("character_appearance", "character_introduction")):
                    continue
                audit.evidence(review, identifier + "." + str(review.get("check")), checksum)
            validate_character_reviews(plan, timeline, audit)
        except (OSError, ValueError, StopIteration, ImportError, KeyError,
                subprocess.SubprocessError) as exc:
            audit.errors.append(f"{identifier}: media inspection unavailable or failed: {exc}")


def validate_links(plan, manifest, blueprint, audit, delivery=False):
    planned = {row["asset_identifier"]: row for row in rows(plan.get("timelines"))}
    for label, document in (("manifest", manifest), ("blueprint", blueprint)):
        if document is None:
            continue
        if not isinstance(document, dict):
            audit.errors.append(f"{label} must be an object")
            continue
        for key in ("course_identifier", "course_version"):
            audit.need(document.get(key) == plan.get(key), f"video/{label} {key} differs")
        collection = "assets" if label == "manifest" else "media_resources"
        key = "asset_identifier" if label == "manifest" else "resource_identifier"
        for resource in rows(document.get(collection)):
            is_video = (resource.get("kind") == "linear_video" if label == "manifest"
                        else resource.get("media_type") == "video")
            if resource.get("required") is True and is_video:
                identifier = resource.get(key)
                audit.need(isinstance(identifier, str) and identifier in planned,
                           f"{label}: required video missing from complete plan: {identifier}")
                if delivery and identifier in planned:
                    path = planned[identifier].get("path")
                    expected = ([entry.get("path") for entry in rows(resource.get("files"))]
                                if label == "manifest" else [resource.get("file_path")])
                    try:
                        audit.need(any(audit.path(item).resolve() == audit.path(path).resolve()
                                       for item in expected),
                                   f"{identifier}: inspected file differs from {label} delivery")
                    except ValueError as exc:
                        audit.errors.append(f"{identifier}: {exc}")
        if label == "blueprint":
            scene_ids = {row.get("scene_identifier") for row in rows(document.get("scenes"))
                         if isinstance(row.get("scene_identifier"), str)}
            audit.need(all(row.get("scene_identifier") in scene_ids for row in rows(plan.get("shots"))),
                       "Video shots refer to unknown blueprint scenes")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    parser.add_argument("--delivery", action="store_true")
    parser.add_argument("--pre-submit", action="store_true",
                        help="Read actual serialized request for one unsubmitted unit; no generation")
    parser.add_argument("--unit", help="Generation unit selected for --pre-submit")
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--blueprint", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--template", action="store_true", help="Syntax only; never production acceptance")
    args = parser.parse_args()
    audit = Audit(args.plan.resolve().parent)
    plan = None
    try:
        if sum((args.template, args.delivery, args.pre_submit)) > 1:
            raise ValueError("--template, --delivery and --pre-submit are separate stages")
        if args.pre_submit != bool(args.unit):
            raise ValueError("--pre-submit and --unit must be used together")
        plan = json.loads(args.plan.read_text(encoding="utf-8"))
        if args.template:
            audit.need(isinstance(plan, dict) and plan.get("schema_version") in ("1.0", "1.1", "1.2"),
                       "Unsupported template")
            for name in ("references", "timelines", "shots", "generation_units", "sound_events", "clips"):
                audit.need(isinstance(plan.get(name), list), f"Template {name} must be an array")
            if plan.get("schema_version") in ("1.1", "1.2"):
                for name in ("character_sources", "characters", "character_introductions"):
                    audit.need(isinstance(plan.get(name), list), f"Template {name} must be an array")
                for shot in rows(plan.get("shots")):
                    audit.need(isinstance(shot.get("character_identifiers"), list),
                               "Template shot character_identifiers must be an array")
            if plan.get("schema_version") == "1.2":
                for name in ("continuity_routes", "continuity_seams"):
                    audit.need(isinstance(plan.get(name), list), f"Template {name} must be an array")
            if args.delivery:
                audit.errors.append("--template cannot be combined with --delivery")
        else:
            environment_path = audit.path(plan.get("environment_file"))
            environment = json.loads(environment_path.read_text(encoding="utf-8"))
            audit.file(plan.get("environment_file"), plan.get("environment_sha256"), "environment")
            structural = validate_plan(plan, environment, audit.base, args.delivery)
            audit.errors.extend(structural.errors)
            audit.warnings.extend(structural.warnings)
            documents = []
            for source in (args.manifest, args.blueprint):
                documents.append(json.loads(source.read_text(encoding="utf-8")) if source else None)
            # Paths in linked contracts are resolved relative to their own documents.
            for document, source in zip(documents, (args.manifest, args.blueprint)):
                if source and isinstance(document, dict):
                    for resource in rows(document.get("assets")):
                        for entry in rows(resource.get("files")):
                            if isinstance(entry.get("path"), str):
                                entry["path"] = str(source.resolve().parent / entry["path"])
                    for resource in rows(document.get("media_resources")):
                        if isinstance(resource.get("file_path"), str):
                            resource["file_path"] = str(source.resolve().parent / resource["file_path"])
            validate_links(plan, *documents, audit, args.delivery)
            if args.pre_submit:
                audit.need(plan.get("schema_version") == "1.2",
                           "Pre-submit requires schema 1.2; legacy readback is unverified")
                if not audit.errors:
                    validate_submission(plan, audit, args.unit)
            if args.delivery and not audit.errors:
                validate_delivery(plan, environment, audit)
    except (OSError, ValueError, TypeError, KeyError, subprocess.SubprocessError) as exc:
        audit.errors.append(f"Cannot validate input: {exc}")
    report = {
        "mode": "template" if args.template else "pre_submit" if args.pre_submit
                else "delivery" if args.delivery else "plan",
        "status": "failed" if audit.errors else "passed",
        "plan_sha256": digest(args.plan) if args.plan.is_file() else None,
        "measurements": audit.measurements, "errors": audit.errors,
        "warnings": audit.warnings,
        "character_contract_status": (
            "not_checked" if args.template else "not_validated_legacy"
            if isinstance(plan, dict) and plan.get("schema_version") == "1.0"
            else "failed" if audit.errors else "delivery_records_checked"
            if args.delivery else "plan_checked"
        ),
        "submission_contract_status": (
            "not_checked" if args.template else "not_validated_legacy"
            if not isinstance(plan, dict) or plan.get("schema_version") != "1.2"
            else "failed" if audit.errors else "actual_arguments_compared"
            if args.pre_submit or args.delivery else "not_checked_plan_only"
        ),
        "seam_contract_status": (
            "not_checked" if args.template else "not_validated_legacy"
            if not isinstance(plan, dict) or plan.get("schema_version") != "1.2"
            else "failed" if audit.errors else "source_pts_and_review_records_checked"
            if args.delivery else "plan_coverage_checked"
        ),
        "limits": "Automated inspection and file-bound review records do not prove reviewer identity, "
                  "semantic correctness, fine lip synchronization, or course approval.",
    }
    if args.report:
        if not args.report.parent.is_dir():
            audit.errors.append("Report parent directory must already exist")
            report["status"] = "failed"
        else:
            args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for error in audit.errors:
        print("ERROR:", error)
    for warning in audit.warnings:
        print("WARNING:", warning)
    print(("FAIL" if audit.errors else "PASS") + ": " + report["mode"] + " video production checks")
    if args.template:
        print("TEMPLATE ONLY: capabilities, timing, files and quality have not been accepted.")
    elif args.pre_submit:
        print("PRE-SUBMIT ONLY: submit the identical checked arguments; this is not a provider receipt.")
    elif not args.delivery:
        print("PLAN ONLY: actual media and human reviews have not been checked.")
    return 1 if audit.errors else 0


if __name__ == "__main__":
    sys.exit(main())
