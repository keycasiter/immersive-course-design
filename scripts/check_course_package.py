#!/usr/bin/env python3
"""Synthetic regressions for cross-file course package identifiers."""

import copy
import json
from pathlib import Path
import re

from validate_course_package import validate


ROOT = Path(__file__).resolve().parents[1]


def fill(value):
    if isinstance(value, str):
        return re.sub(r"\{\{.*?\}\}", "synthetic", value)
    if isinstance(value, list):
        return [fill(item) for item in value]
    if isinstance(value, dict):
        return {key: fill(item) for key, item in value.items()}
    return value


def main():
    manifest = fill(json.loads((ROOT / "assets/production-manifest.template.json").read_text()))
    blueprint = fill(json.loads((ROOT / "assets/course-blueprint.template.json").read_text()))
    participation = fill(json.loads((ROOT / "assets/scene-interaction-plan.template.json").read_text()))
    event_map = fill(json.loads((ROOT / "assets/video-event-map.template.json").read_text()))
    video_plan = fill(json.loads((ROOT / "assets/video-production-plan.template.json").read_text()))
    course_id, version = "synthetic_course", "0.1"
    manifest.update(course_identifier=course_id, course_version=version)
    blueprint.update(course_identifier=course_id, course_version=version)
    video_plan.update(course_identifier=course_id, course_version=version)
    participation["events"][0]["objective_identifiers"] = ["objective_core"]
    assert not validate(manifest, blueprint, participation, event_map, video_plan)

    changed = copy.deepcopy(event_map)
    changed["events"][0]["clip_identifier"] = "wrong_clip"
    errors = validate(manifest, blueprint, participation, changed, video_plan)
    assert any("unknown video clip" in error for error in errors), errors
    changed = copy.deepcopy(participation)
    changed["events"][0]["interaction_identifier"] = "wrong_interaction"
    errors = validate(manifest, blueprint, changed, event_map, video_plan)
    assert any("interaction ID differs" in error for error in errors), errors
    changed = copy.deepcopy(manifest)
    changed["experience_profile"]["beat_identifiers"].reverse()
    errors = validate(changed, blueprint, participation, event_map, video_plan)
    assert any("beat IDs/order" in error for error in errors), errors
    print("PASS: unified course package identifier regressions")


if __name__ == "__main__":
    main()
