#!/usr/bin/env python3
# Structural checks for a video-clock-driven immersive course runtime.
import json
import math
import re
import sys
from pathlib import Path


def validate_storyboard_runtime(event_map, html, js):
    """A deterministic event carrier; never a claim about video playback timing."""
    errors = []
    if event_map.get("runtime_mode") != "storyboard_events" or event_map.get("schema_version") != "1.2":
        errors.append("storyboard runtime requires schema 1.2 and storyboard_events mode")
    events = event_map.get("events")
    if not isinstance(events, list) or not events or not all(isinstance(row, dict) for row in events):
        return errors + ["storyboard events must be a non-empty object list"]
    identifiers = [row.get("beat_id") for row in events]
    if not all(isinstance(item, str) and item for item in identifiers) or \
            len(set(item for item in identifiers if isinstance(item, str))) != len(identifiers):
        errors.append("storyboard Beat identifiers must be non-empty and unique")
    if identifiers != event_map.get("approved_beat_ids"):
        errors.append("storyboard event order must exactly match approved_beat_ids")
    for row in events:
        for key in ("storyboard_asset_identifier", "return_event_identifier"):
            if not isinstance(row.get(key), str) or not row[key]:
                errors.append(f"storyboard event requires {key}")
        if row.get("return_event_identifier") != row.get("beat_id"):
            errors.append("storyboard interaction must return to the same event")
        if not isinstance(row.get("event_class"), str) or \
                row["event_class"] not in {"observation", "exploration", "judgment"}:
            errors.append("storyboard event_class is invalid")
        if type(row.get("evidence_required")) is not bool:
            errors.append("storyboard evidence_required must be boolean")
        if row.get("evidence_required") is True and not row.get("interaction_id"):
            errors.append("required storyboard action needs interaction_id")
        if row.get("on_incomplete_close") != "retain_draft_block_progression":
            errors.append("storyboard incomplete close must retain draft and block progression")
    embedded = re.search(r'<script\b[^>]*id=["\']video-event-map["\'][^>]*>(.*?)</script>', html, re.I | re.S)
    try:
        if not embedded or json.loads(embedded.group(1)) != event_map:
            errors.append("HTML must embed the identical storyboard event map")
    except ValueError:
        errors.append("HTML storyboard event map is not JSON")
    for token in ('id="course-stage"', 'id="scene-media"', 'data-runtime-mode="storyboard_events"'):
        if token not in html:
            errors.append(f"storyboard HTML requires {token}")
    for token in ("enterEvent", "openInteraction", "closeInteraction", "completeInteraction",
                  "restoreState", "localStorage", "eventMap", "course-event"):
        if token not in js:
            errors.append(f"storyboard runtime must implement {token}")
    return errors

def fail(message):
    print(f"INVALID: {message}")
    raise SystemExit(1)

def validate_required_windows(events):
    """Reserve [cue,resume) plus a unique pause point for each mandatory event."""
    errors = []
    required = [row for row in events if row.get("evidence_required") is True or
                row.get("interaction_required") is True or row.get("event_class") == "judgment"]
    for index, row in enumerate(required):
        for other in required[index + 1:]:
            if other["cue_seconds"] < row["resume_seconds"] or \
                    other["pause_seconds"] == row["pause_seconds"]:
                errors.append(f"required windows conflict: {row['beat_id']} / {other['beat_id']}")
    return errors

def main():
    if len(sys.argv) != 4:
        fail("usage: validate_video_led_runtime.py <event-map.json> <index.html> <runtime-source.ts-or-js>")
    map_path, html_path, js_path = map(Path, sys.argv[1:])
    try:
        event_map = json.loads(map_path.read_text())
    except Exception as exc:
        fail(f"cannot parse event map: {exc}")
    html = html_path.read_text()
    js = js_path.read_text()
    if event_map.get("runtime_mode") == "storyboard_events":
        errors = validate_storyboard_runtime(event_map, html, js)
        if errors:
            fail("; ".join(errors))
        print("VALID: deterministic storyboard events; real video playback/seek/caption timing NOT checked")
        return
    duration = event_map.get("duration_seconds")
    events = event_map.get("events")
    admission = event_map.get("resource_admission")
    schema_version = event_map.get("schema_version")
    if schema_version not in ("1.0", "1.1"):
        fail("schema_version must be 1.0 or 1.1")
    if schema_version == "1.1":
        mapping = event_map.get("timeline_mapping")
        if not isinstance(mapping, dict):
            fail("timeline_mapping must be an object for schema 1.1")
        if mapping.get("mode") not in ("composed_single_file", "segmented_media"):
            fail("timeline_mapping.mode must be composed_single_file or segmented_media")
        if not isinstance(mapping.get("main_timeline_identifier"), str) or \
                not mapping["main_timeline_identifier"].strip():
            fail("timeline_mapping.main_timeline_identifier must be non-empty text")
        if mapping.get("completed_event_seek_policy") not in (
                "restore_completed_state_without_reopening", "reopen_for_review"):
            fail("timeline_mapping.completed_event_seek_policy is invalid")
        if mapping.get("branch_return_policy") not in (
                "return_to_declared_global_resume_seconds", "remain_on_branch_timeline"):
            fail("timeline_mapping.branch_return_policy is invalid")
    if not isinstance(admission, dict):
        fail("resource_admission must declare course_entry and event_entry checks")
    for admission_key in ("course_entry", "event_entry"):
        entry = admission.get(admission_key)
        if not isinstance(entry, dict):
            fail(f"resource_admission.{admission_key} must be an object")
        if not isinstance(entry.get("checks"), list) or not entry.get("checks"):
            fail(f"resource_admission.{admission_key}.checks must be a non-empty array")
        if entry.get("failure_policy") != "retry_or_block":
            fail(f"resource_admission.{admission_key}.failure_policy must be retry_or_block")
    if admission["event_entry"].get("degraded_path") is not False:
        fail("resource_admission.event_entry.degraded_path must be false")
    if type(duration) not in (int, float) or not math.isfinite(duration) or duration <= 0:
        fail("duration_seconds must be a positive finite number")
    if not isinstance(events, list) or not events:
        fail("events must be a non-empty array")
    if any(not isinstance(event, dict) for event in events):
        fail("events entries must be objects")
    ids = [e.get("beat_id") for e in events]
    if any(not isinstance(i, str) or not i.strip() for i in ids) or len(set(ids)) != len(ids):
        fail("beat_id values must be non-empty and unique")
    prev_cue = -1
    for index, event in enumerate(events):
        if schema_version == "1.1":
            for key in ("timeline_identifier", "clip_identifier", "media_source_identifier"):
                if not isinstance(event.get(key), str) or not event[key].strip():
                    fail(f"event {ids[index]}: {key} must be non-empty text")
            offset = event.get("global_offset_seconds")
            if type(offset) not in (int, float) or not math.isfinite(offset) or offset < 0:
                fail(f"event {ids[index]}: global_offset_seconds must be a finite non-negative number")
        for key in ("cue_seconds", "pause_seconds", "resume_seconds"):
            value = event.get(key)
            if type(value) not in (int, float) or not math.isfinite(value) or \
                    value < 0 or value > duration:
                fail(
                    f"event {ids[index]}: {key} must be a finite number "
                    "between 0 and duration_seconds"
                )
        cue, pause, resume = (event[k] for k in ("cue_seconds", "pause_seconds", "resume_seconds"))
        if cue < prev_cue or pause < cue or resume < pause:
            fail(f"event {ids[index]}: cue/pause/resume must be ordered")
        prev_cue = cue
        if not isinstance(event.get("evidence_required"), bool):
            fail(f"event {ids[index]}: evidence_required must be boolean")
        if not isinstance(event.get("resume_state"), dict):
            fail(f"event {ids[index]}: resume_state must be an object")
        if event.get("evidence_required") and not event.get("interaction_id"):
            fail(f"event {ids[index]}: required evidence needs interaction_id")
        if event.get("event_class") not in ("observation", "exploration", "judgment"):
            fail(f"event {ids[index]}: event_class must be observation, exploration, or judgment")
        if not isinstance(event.get("required_asset_identifiers"), list):
            fail(f"event {ids[index]}: required_asset_identifiers must be an array")
        retry_policy = event.get("retry_policy")
        if not isinstance(retry_policy, dict) or retry_policy.get("on_exhausted") != "block_progression":
            fail(f"event {ids[index]}: retry_policy must block_progression when exhausted")
    window_errors = validate_required_windows(events)
    if window_errors:
        fail("; ".join(window_errors))
    approved_ids = event_map.get("approved_beat_ids")
    if approved_ids is not None and approved_ids != ids:
        fail("event beat IDs/order must exactly match approved_beat_ids")
    embedded = re.search(r'<script\b[^>]*id=["\']video-event-map["\'][^>]*>(.*?)</script>', html, re.I | re.S)
    if not embedded:
        fail("HTML must embed the event map as script#video-event-map[type=application/json]")
    try:
        inline_map = json.loads(embedded.group(1))
    except Exception as exc:
        fail(f"cannot parse HTML-embedded event map: {exc}")
    if inline_map != event_map:
        fail("HTML-embedded event map must exactly match video-event-map.json")
    if not re.search(r'<main\b[^>]*id=["\']course-stage["\']', html):
        fail("HTML must contain main#course-stage")
    video = re.search(r'<video\b(?=[^>]*\bid=["\']course-video["\'])(?=[^>]*\bdata-media-clock=["\']course["\'])[^>]*>(.*?)</video>', html, re.I | re.S)
    if not video or not re.search(r'<source\b[^>]*\bsrc=["\'][^"\']+["\']', video.group(1), re.I):
        fail("HTML must contain playable video#course-video with data-media-clock=course and a source")
    media_open = html.find('id="scene-media"')
    media_close = html.find('</div>', media_open)
    if media_open < 0 or not (media_open < html.find('<video') < media_close):
        fail("course video must be inside #scene-media")
    if not re.search(r'addEventListener\s*\(\s*["\']timeupdate["\']', js) or not re.search(r'addEventListener\s*\(\s*["\']seeking["\']', js):
        fail("runtime must listen to timeupdate and seeking")
    if not re.search(r'currentTime', js):
        fail("runtime must read/write video.currentTime")
    if not re.search(r'video-event-map|eventMap|events', js):
        fail("runtime must use the event map")
    print(f"VALID: {len(events)} video-clock events, duration {duration}s, playable video binding present")

if __name__ == "__main__":
    main()
