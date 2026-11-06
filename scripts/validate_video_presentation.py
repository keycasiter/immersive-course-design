#!/usr/bin/env python3
"""Validate the bounded presentation contract; does not inspect pixels or experiential quality."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess


def validate(data, asset_identifiers=None, beat_identifiers=None):
    errors = []
    if not isinstance(data, dict):
        return ["presentation contract must be an object"]
    def need(ok, label):
        if not ok:
            errors.append(label)
    def number(value):
        return type(value) in (int, float) and math.isfinite(value)
    def rows(value, label):
        if not isinstance(value, list) or any(not isinstance(row, dict) for row in value):
            errors.append(f"{label} must be an object list")
            return []
        return value
    def identifier(value, label):
        need(isinstance(value, str) and bool(value.strip()), f"{label} must be text")
    def interval(row, duration, label):
        a, b = row.get("start_seconds"), row.get("end_seconds")
        ok = number(a) and number(b) and 0 <= a < b <= duration
        need(ok, f"{label}: invalid half-open interval")
        return (a, b) if ok else None
    need(data.get("contract_version") == "1.0", "presentation contract_version must be 1.0")
    need(data.get("timeline_mode") == "composed_single_file", "only composed_single_file is supported")
    duration = data.get("duration_seconds")
    if not number(duration) or duration <= 0:
        return errors + ["presentation duration must be positive"]
    identifier(data.get("main_video_asset_identifier"), "main_video_asset_identifier")
    if asset_identifiers is not None:
        need(isinstance(data.get("main_video_asset_identifier"), str) and
             data["main_video_asset_identifier"] in asset_identifiers, "unknown main video asset")
    need(isinstance(data.get("main_video_sha256"), str) and
         bool(re.fullmatch("[0-9a-f]{64}", data["main_video_sha256"])), "invalid main_video_sha256")
    dimensions = data.get("source_dimensions", {})
    need(isinstance(dimensions, dict) and all(type(dimensions.get(k)) is int and dimensions[k] > 0
         for k in ("width", "height")), "source_dimensions must be positive integers")
    need(data.get("projection") == "centered_contain", "only centered_contain is supported")
    atmosphere = data.get("atmosphere")
    if not isinstance(atmosphere, dict):
        return errors + ["atmosphere must be an object; declare disabled when unused"]
    need(type(atmosphere.get("enabled")) is bool, "atmosphere.enabled must be boolean")
    if atmosphere.get("enabled"):
        need(atmosphere.get("purpose") == "atmosphere_only" and
             atmosphere.get("required_for_learning") is False, "atmosphere must remain optional")
        previous_end, seen, prior_states = 0, set(), set()
        cues = rows(atmosphere.get("cues"), "atmosphere.cues")
        need(bool(cues), "enabled atmosphere needs cues")
        for cue in cues:
            key = cue.get("identifier")
            identifier(key, "cue.identifier")
            if isinstance(key, str):
                need(key not in seen, "duplicate atmosphere cue")
                seen.add(key)
            identifier(cue.get("scene_identifier"), "cue.scene_identifier")
            bounds = interval(cue, duration, "cue")
            if bounds:
                need(abs(bounds[0] - previous_end) < 1e-9, "atmosphere cues must partition without gaps/overlap")
                previous_end = bounds[1]
            need(cue.get("motion") in ("ambient_loop", "still"), "unsupported atmosphere motion")
            cycle, transition = cue.get("cycle_seconds"), cue.get("transition_seconds")
            need(number(cycle) and cycle > 0, "cycle_seconds must be positive")
            need(number(transition) and 0 <= transition <= 2 and
                 (not bounds or transition <= bounds[1] - bounds[0]), "transition_seconds is invalid")
            states = rows(cue.get("states"), "cue.states")
            current_states = set()
            need(bool(states), "cue needs world-state variants")
            for state in states:
                sid = state.get("world_state_identifier")
                identifier(sid, "world_state_identifier")
                if isinstance(sid, str):
                    need(sid not in current_states, "duplicate world-state variant")
                    current_states.add(sid)
                for field in ("asset_identifier", "still_asset_identifier"):
                    value = state.get(field)
                    identifier(value, field)
                    if asset_identifiers is not None:
                        need(isinstance(value, str) and value in asset_identifiers, "unknown atmosphere asset")
                    need(value != data.get("main_video_asset_identifier"), "atmosphere cannot alias main video")
            if prior_states and number(transition) and transition > 0:
                need(current_states == prior_states, "crossfade requires matching world-state variants")
            prior_states = current_states
        need(abs(previous_end - duration) < 1e-9, "atmosphere must cover the entire video")
    seen = set()
    for track in rows(data.get("anchors"), "anchors"):
        key = track.get("identifier")
        identifier(key, "anchor.identifier")
        if isinstance(key, str):
            need(key not in seen, "duplicate anchor")
            seen.add(key)
        for field in ("beat_identifier", "object_identifier"):
            identifier(track.get(field), field)
        if beat_identifiers is not None:
            need(isinstance(track.get("beat_identifier"), str) and
                 track["beat_identifier"] in beat_identifiers, "unknown anchor Beat")
        bounds = interval(track, duration, "anchor")
        need(track.get("interpolation") == "linear" and
             track.get("coordinate_space") == "normalized_source_rectangle", "unsupported anchor coordinates/interpolation")
        need(track.get("fallback") == "same_object_accessible_entry", "anchor needs an accessible fallback")
        points = rows(track.get("keyframes"), "anchor.keyframes")
        need(len(points) >= 2, "anchor needs at least two keyframes")
        previous = -1
        for point in points:
            t = point.get("presentation_seconds")
            need(number(t) and t > previous and (not bounds or bounds[0] <= t <= bounds[1]), "invalid source PTS order/range")
            if number(t):
                previous = t
            rect = point.get("rectangle")
            ok = isinstance(rect, dict) and all(number(rect.get(k)) for k in ("x", "y", "width", "height"))
            need(ok and 0 <= rect["x"] < 1 and 0 <= rect["y"] < 1 and
                 rect["width"] > 0 and rect["height"] > 0 and
                 rect["x"] + rect["width"] <= 1 and rect["y"] + rect["height"] <= 1,
                 "rectangle must fit normalized source")
        if bounds and points:
            need(points[0].get("presentation_seconds") == bounds[0] and
                 points[-1].get("presentation_seconds") == bounds[1], "keyframes must bracket the anchor interval")
        previous_end = -1
        for occlusion in rows(track.get("occlusions"), "anchor.occlusions"):
            hidden = interval(occlusion, duration, "occlusion")
            if hidden and bounds:
                need(bounds[0] <= hidden[0] < hidden[1] <= bounds[1] and hidden[0] >= previous_end,
                     "occlusion intervals must be ordered and inside the anchor")
                previous_end = hidden[1]
    return errors


def validate_bound_video(data, video):
    """Read actual bound bytes and video metadata; this does not verify anchor pixels."""
    errors = []
    try:
        video = Path(video)
        if hashlib.sha256(video.read_bytes()).hexdigest() != data.get("main_video_sha256"):
            errors.append("main video hash differs")
        result = subprocess.run([
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height,duration,avg_frame_rate:format=duration",
            "-of", "json", str(video),
        ], capture_output=True, text=True, check=True, timeout=30)
        probe = json.loads(result.stdout)
        stream = probe["streams"][0]
        if data.get("source_dimensions") != {key: stream[key] for key in ("width", "height")}:
            errors.append("presentation source dimensions differ from main video")
        duration = float(stream.get("duration", probe.get("format", {}).get("duration", 0)))
        rate = stream.get("avg_frame_rate", "0/1").split("/")
        fps = float(rate[0]) / float(rate[1]) if float(rate[1]) else 0
        tolerance = max(.05, 1 / fps) if fps > 0 else .05
        declared = data.get("duration_seconds")
        if not (type(declared) in (int, float) and math.isfinite(declared) and
                math.isfinite(duration) and duration > 0 and abs(duration - declared) <= tolerance):
            errors.append("presentation duration differs from actual main video")
    except (OSError, ValueError, KeyError, IndexError, TypeError, subprocess.SubprocessError) as exc:
        errors.append(f"bound main video metadata cannot be read: {exc}")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("contract", type=Path)
    parser.add_argument("--video", type=Path, help="Read back main video hash, dimensions and duration")
    args = parser.parse_args()
    try:
        data = json.loads(args.contract.read_text())
        errors = validate(data)
        if args.video and isinstance(data, dict):
            errors.extend(validate_bound_video(data, args.video))
    except (OSError, ValueError) as exc:
        errors = [str(exc)]
    if errors:
        raise SystemExit("\n".join(errors))
    print("presentation structure passed; PTS/content/pixels/browser/experience still require actual review")


if __name__ == "__main__":
    main()
