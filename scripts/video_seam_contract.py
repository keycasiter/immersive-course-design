"""Plan seam coverage and source-PTS checks; semantic continuity requires actual review."""
import json
from fractions import Fraction
import subprocess


def objects(value):
    if not isinstance(value, list) or any(not isinstance(row, dict) for row in value):
        raise ValueError("Expected an array of objects")
    return value


def text(value):
    return isinstance(value, str) and bool(value.strip())


def expected_seams(plan):
    clips = {row["clip_identifier"]: row for row in objects(plan.get("clips"))}
    expected = {}
    for timeline in objects(plan.get("timelines")):
        identifier = timeline["timeline_identifier"]
        ordered = sorted((row for row in clips.values() if row.get("timeline_identifier") == identifier),
                         key=lambda row: row["start_seconds"])
        for first, second in zip(ordered, ordered[1:]):
            expected[(f"timeline:{identifier}", first["clip_identifier"], second["clip_identifier"])] = "adjacent"
    route_ids = set()
    for route in objects(plan.get("continuity_routes")):
        identifier = route.get("route_identifier")
        chain, kind = route.get("clip_identifiers"), route.get("transition_type")
        if not text(identifier) or identifier.startswith("timeline:") or identifier in route_ids:
            raise ValueError("Invalid or duplicate continuity route identifier")
        route_ids.add(identifier)
        if (kind not in ("branch_merge", "resume") or not isinstance(chain, list) or len(chain) < 2
                or any(not isinstance(item, str) or item not in clips for item in chain)):
            raise ValueError("Continuity route requires known clips and branch_merge/resume")
        for first, second in zip(chain, chain[1:]):
            key = (identifier, first, second)
            if key in expected:
                raise ValueError("Duplicate route edge")
            expected[key] = kind
    return clips, expected


def frame_clock(path):
    result = subprocess.run([
        "ffprobe", "-v", "error", "-select_streams", "v:0", "-show_frames", "-show_streams",
        "-show_entries", "frame=best_effort_timestamp:stream=time_base",
        "-of", "json", str(path),
    ], capture_output=True, timeout=120)
    if result.returncode:
        raise ValueError("Cannot inspect actual source presentation timestamps")
    document = json.loads(result.stdout)
    time_base = Fraction(document["streams"][0]["time_base"])
    timestamps = [int(row["best_effort_timestamp"]) for row in document.get("frames", [])
                  if row.get("best_effort_timestamp") not in (None, "N/A")]
    if (time_base <= 0 or not timestamps or timestamps != sorted(set(timestamps))):
        raise ValueError("Source requires a valid monotonic presentation clock")
    return time_base, timestamps


def visual_state(value):
    if not isinstance(value, dict) or not text(value.get("lighting")):
        raise ValueError("Visual state requires actual lighting and entity states")
    entries = objects(value.get("entities"))
    if not entries:
        raise ValueError("Visual state must describe the relevant visible entities")
    seen = set()
    for row in entries:
        identifier = row.get("entity_identifier")
        held = row.get("holding_identifiers")
        if (not text(identifier) or identifier in seen or type(row.get("count")) is not int
                or row["count"] < 0 or not all(text(row.get(key))
                for key in ("position", "orientation", "condition", "motion_phase")) or
                not isinstance(held, list) or any(not text(item) for item in held) or
                len(set(held)) != len(held)):
            raise ValueError("Incomplete, duplicate or invalid observed entity state")
        seen.add(identifier)


def validate_seams(plan, audit, inspect_media=False):
    try:
        clips, expected = expected_seams(plan)
        rows = objects(plan.get("continuity_seams"))
        keys, identifiers = set(), set()
        timelines = {row["timeline_identifier"]: row for row in objects(plan.get("timelines"))}
        units = {row["unit_identifier"]: row for row in objects(plan.get("generation_units"))}
        events = {row["event_identifier"]: row for row in objects(plan.get("sound_events"))}
        clocks = {}
        for row in rows:
            label = row.get("seam_identifier", "seam")
            try:
                if not text(label) or label in identifiers:
                    raise ValueError("Missing or duplicate seam identifier")
                identifiers.add(label)
                key = (row.get("route_identifier"), row.get("preceding_clip_identifier"),
                       row.get("following_clip_identifier"))
                if key not in expected or key in keys:
                    raise ValueError("Seam does not match an actual predecessor/route edge")
                keys.add(key)
                kind = row.get("transition_type")
                if expected[key] == "adjacent":
                    if kind not in ("continuous", "time_jump"):
                        raise ValueError("Adjacent clips require continuous/time_jump")
                elif kind != expected[key]:
                    raise ValueError("Seam transition differs from declared route")
                if not text(row.get("transition_reason")):
                    raise ValueError("Transition purpose and state changes require a reason")
                if not inspect_media:
                    if row.get("status") not in ("planned", "observed"):
                        raise ValueError("Seam status must be planned or observed")
                    continue
                if row.get("status") != "observed":
                    raise ValueError("Actual boundary observations are missing")
                preceding, following = clips[key[1]], clips[key[2]]
                hashes = row.get("delivery_sha256_by_timeline")
                involved = {preceding["timeline_identifier"], following["timeline_identifier"]}
                if not isinstance(hashes, dict) or set(hashes) != involved:
                    raise ValueError("Seam must bind both participating final timelines")
                for timeline in involved:
                    if hashes[timeline] != timelines[timeline].get("content_sha256"):
                        raise ValueError("Seam review is for an obsolete final timeline")
                    audit.file(timelines[timeline].get("path"), hashes[timeline], label + ".delivery")
                for side, clip in (("preceding", preceding), ("following", following)):
                    unit = units[clip["unit_identifier"]]
                    source = audit.file(unit.get("output_file"), unit.get("output_sha256"),
                                        label + "." + side + ".source")
                    boundary = row.get(side + "_boundary")
                    if not isinstance(boundary, dict) or source is None:
                        raise ValueError("Missing source boundary observation")
                    if boundary.get("source_sha256") != unit.get("output_sha256"):
                        raise ValueError("Boundary observes an obsolete source")
                    audit.file(boundary.get("evidence_file"), boundary.get("evidence_sha256"),
                               label + "." + side + ".frame_evidence")
                    if source not in clocks:
                        clocks[source] = frame_clock(source)
                    time_base, timestamps = clocks[source]
                    recorded = boundary.get("presentation_timestamp")
                    if (type(recorded) is not int or
                            Fraction(boundary.get("time_base")) != time_base or recorded not in timestamps):
                        raise ValueError("Boundary lacks actual source PTS/time_base")
                    start, end = Fraction(str(clip["source_start_seconds"])), Fraction(str(clip["source_end_seconds"]))
                    adopted = [value for value in timestamps
                               if start <= (value - timestamps[0]) * time_base < end]
                    if not adopted:
                        raise ValueError("Selected source interval includes no presented frames")
                    expected_timestamp = adopted[-1] if side == "preceding" else adopted[0]
                    if kind == "resume" and side == "following":
                        resume = Fraction(str(row.get("resume_source_seconds")))
                        if not start <= resume < end:
                            raise ValueError("Resume position is outside adopted clip")
                        at_resume = [value for value in adopted
                                     if (value - timestamps[0]) * time_base <= resume]
                        if not at_resume:
                            raise ValueError("Resume point precedes the first adopted frame")
                        expected_timestamp = at_resume[-1]
                    if recorded != expected_timestamp:
                        raise ValueError("Evidence is not the actual adopted boundary frame")
                    visual_state(row.get(side + "_visual_state"))
                audible = row.get("audible_state")
                if not isinstance(audible, dict):
                    raise ValueError("Missing actual audible state")
                for field in ("completed_event_identifiers", "continuing_event_identifiers"):
                    values = audible.get(field)
                    if (not isinstance(values, list) or any(not isinstance(item, str) or item not in events
                                                           for item in values) or len(set(values)) != len(values)):
                        raise ValueError("Audible state requires known unique event identifiers")
                if set(audible["completed_event_identifiers"]) & set(audible["continuing_event_identifiers"]):
                    raise ValueError("Sound event cannot be completed and continuing")
                next_event = audible.get("next_event_identifier")
                if next_event is not None and (not isinstance(next_event, str) or next_event not in events):
                    raise ValueError("Unknown next sound event")
                checksum = timelines[following["timeline_identifier"]]["content_sha256"]
                audit.evidence(audible.get("listening_review"), label + ".listening", checksum)
                audit.evidence(row.get("continuity_review"), label + ".continuity", checksum)
                audit.measurements.append({"seam_identifier": label, "route_identifier": key[0],
                                           "status": "source_pts_and_review_records_checked"})
            except (OSError, ValueError, TypeError, KeyError, ZeroDivisionError,
                    subprocess.SubprocessError) as exc:
                audit.errors.append(f"{label}.seam: {exc}")
        if keys != set(expected):
            audit.errors.append("continuity_seams: missing actual adjacent/branch/resume route edges")
    except (ValueError, TypeError, KeyError) as exc:
        audit.errors.append(f"continuity_seams: {exc}")
