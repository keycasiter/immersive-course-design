#!/usr/bin/env python3
"""Validate cross-file identifiers for a video-led course package."""

import argparse
import json
from pathlib import Path


def load(path, label, errors):
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"{label}: cannot read JSON: {exc}")
        return {}
    if not isinstance(value, dict):
        errors.append(f"{label}: root must be an object")
        return {}
    return value


def validate(manifest, blueprint, participation, event_map, video_plan):
    errors = []

    def need(condition, message):
        if not condition:
            errors.append(message)

    course_id = manifest.get("course_identifier")
    course_version = manifest.get("course_version")
    for label, document in (("blueprint", blueprint), ("video_plan", video_plan)):
        need(document.get("course_identifier") == course_id, f"{label}: course_identifier differs")
        need(document.get("course_version") == course_version, f"{label}: course_version differs")

    manifest_beats = manifest.get("experience_profile", {}).get("beat_identifiers", [])
    blueprint_beats = [
        beat for scene in blueprint.get("scenes", []) if isinstance(scene, dict)
        for beat in scene.get("beat_identifiers", []) if isinstance(beat, str)
    ]
    need(manifest_beats == blueprint_beats,
         "manifest and blueprint beat IDs/order must match exactly")

    participation_events = participation.get("events", [])
    event_rows = event_map.get("events", [])
    participation_beats = [
        row.get("beat_identifier") for row in participation_events if isinstance(row, dict)
    ]
    event_beats = [row.get("beat_id") for row in event_rows if isinstance(row, dict)]
    if participation.get("coverage_scope") == "full_course":
        need(participation_beats == event_beats,
             "full-course participation and event-map beat IDs/order must match")
    else:
        need([beat for beat in event_beats if beat in participation_beats] == participation_beats,
             "selected participation beats must be an ordered event-map subset")
    by_participation = {
        row.get("beat_identifier"): row for row in participation_events if isinstance(row, dict)
    }
    for row in event_rows:
        if not isinstance(row, dict):
            continue
        beat = row.get("beat_id")
        linked = by_participation.get(beat)
        need(linked is not None, f"event_map.{beat}: beat absent from participation plan")
        if linked is not None:
            need(row.get("interaction_id") == linked.get("interaction_identifier"),
                 f"event_map.{beat}: interaction ID differs")

    manifest_assets = {
        row.get("asset_identifier") for row in manifest.get("assets", [])
        if isinstance(row, dict) and isinstance(row.get("asset_identifier"), str)
    }
    blueprint_assets = {
        row.get("resource_identifier") for row in blueprint.get("media_resources", [])
        if isinstance(row, dict) and isinstance(row.get("resource_identifier"), str)
    }
    timelines = {
        row.get("timeline_identifier"): row for row in video_plan.get("timelines", [])
        if isinstance(row, dict) and isinstance(row.get("timeline_identifier"), str)
    }
    clips = {
        row.get("clip_identifier"): row for row in video_plan.get("clips", [])
        if isinstance(row, dict) and isinstance(row.get("clip_identifier"), str)
    }
    for row in event_rows:
        if not isinstance(row, dict):
            continue
        beat = row.get("beat_id")
        asset = row.get("media_source_identifier")
        timeline = row.get("timeline_identifier")
        clip = row.get("clip_identifier")
        need(asset in manifest_assets and asset in blueprint_assets,
             f"event_map.{beat}: media source must exist in manifest and blueprint")
        need(timeline in timelines, f"event_map.{beat}: unknown video timeline")
        need(clip in clips, f"event_map.{beat}: unknown video clip")
        if clip in clips:
            need(clips[clip].get("timeline_identifier") == timeline,
                 f"event_map.{beat}: clip belongs to another timeline")

    produced_beats = [
        beat for row in video_plan.get("timelines", []) if isinstance(row, dict)
        for beat in row.get("beat_identifiers", []) if isinstance(beat, str)
    ]
    need(all(beat in manifest_beats for beat in produced_beats),
         "video plan contains beat IDs absent from manifest/blueprint")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("blueprint", type=Path)
    parser.add_argument("participation", type=Path)
    parser.add_argument("event_map", type=Path)
    parser.add_argument("video_plan", type=Path)
    args = parser.parse_args()
    errors = []
    documents = [
        load(path, label, errors) for path, label in (
            (args.manifest, "manifest"), (args.blueprint, "blueprint"),
            (args.participation, "participation"), (args.event_map, "event_map"),
            (args.video_plan, "video_plan"),
        )
    ]
    if not errors:
        errors.extend(validate(*documents))
    if errors:
        print("INVALID:\n" + "\n".join(f"- {error}" for error in errors))
        return 1
    print("VALID: course package identifiers align across five contracts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
