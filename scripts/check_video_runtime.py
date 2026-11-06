#!/usr/bin/env python3
"""Synthetic regressions for the video-led runtime contract."""

import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/validate_video_led_runtime.py"


def event_map():
    return {
        "schema_version": "1.1",
        "duration_seconds": 10,
        "media": {"timeline_identifier": "main", "source": "course.mp4"},
        "timeline_mapping": {
            "mode": "composed_single_file",
            "main_timeline_identifier": "main",
            "completed_event_seek_policy": "restore_completed_state_without_reopening",
            "branch_return_policy": "return_to_declared_global_resume_seconds",
        },
        "resource_admission": {
            "course_entry": {"checks": ["video"], "failure_policy": "retry_or_block"},
            "event_entry": {
                "checks": ["object"], "failure_policy": "retry_or_block",
                "degraded_path": False,
            },
        },
        "events": [{
            "beat_id": "B01",
            "timeline_identifier": "main",
            "clip_identifier": "clip_B01",
            "media_source_identifier": "video",
            "global_offset_seconds": 0,
            "cue_seconds": 1,
            "pause_seconds": 2,
            "resume_seconds": 2,
            "event_class": "judgment",
            "interaction_id": "I01",
            "evidence_required": True,
            "required_asset_identifiers": ["video"],
            "retry_policy": {"on_exhausted": "block_progression"},
            "resume_state": {"video_time": 2},
        }],
    }


def run(mapping, inline=None):
    with tempfile.TemporaryDirectory(prefix="video-runtime-") as directory:
        base = Path(directory)
        map_path = base / "event-map.json"
        html_path = base / "index.html"
        js_path = base / "runtime.js"
        map_path.write_text(json.dumps(mapping), encoding="utf-8")
        html_path.write_text(
            '<main id="course-stage"><div id="scene-media">'
            '<video id="course-video" data-media-clock="course">'
            '<source src="course.mp4"></video></div></main>'
            '<script id="video-event-map" type="application/json">'
            + json.dumps(mapping if inline is None else inline)
            + "</script>",
            encoding="utf-8",
        )
        js_path.write_text(
            'video.addEventListener("timeupdate", useEvents);'
            'video.addEventListener("seeking", useEvents);'
            'video.currentTime = eventMap.events[0].resume_seconds;',
            encoding="utf-8",
        )
        return subprocess.run(
            [sys.executable, str(VALIDATOR), str(map_path), str(html_path), str(js_path)],
            capture_output=True, text=True,
        )


def main():
    base = event_map()
    assert run(base).returncode == 0
    for value in (True, float("nan"), float("inf")):
        changed = copy.deepcopy(base)
        changed["duration_seconds"] = value
        result = run(changed)
        assert result.returncode == 1 and "positive finite number" in result.stdout, result.stdout
    changed = copy.deepcopy(base)
    changed["events"] = [None]
    result = run(changed)
    assert result.returncode == 1 and "entries must be objects" in result.stdout, result.stdout
    inline = copy.deepcopy(base)
    inline["duration_seconds"] = 11
    inline["media"]["source"] = "different.mp4"
    result = run(base, inline)
    assert result.returncode == 1 and "exactly match" in result.stdout, result.stdout
    print("PASS: video runtime rejects malformed numbers, objects, and embedded contract drift")


if __name__ == "__main__":
    main()
