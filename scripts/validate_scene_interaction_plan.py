#!/usr/bin/env python3
"""Check participation-plan structure and optional event-map alignment, not learning quality."""

import argparse
import json
import math
from pathlib import Path
import re


SURFACES = (
    "video_only", "scene_control", "object_inspection", "document_reading",
    "guided_experiment", "deterministic_tool", "simulation", "spatial_360",
    "spatial_3d", "scene_card",
)
STATE_FIELDS = {"video_time", "viewpoint", "object_state", "learner_response",
                "focus", "audio", "captions", "completion"}
ACTION_METADATA = {"click", "clicked", "click_count", "opened", "visited",
                   "elapsed_time", "duration", "rotation_count", "drag_count"}
TRIGGER_TYPES = {"scene_object", "npc_action", "audio_cue", "event_hotspot"}
POINTS_OF_VIEW = {
    "learner_first_person", "macro_observational", "documentary_observer",
    "system_observer", "object_viewpoint", "multiple_explicit",
}
BRANCH_POLICIES = {
    "linear_no_branch", "local_consequence_then_rejoin",
    "branching_with_rejoin", "persistent_branch",
}


def validate_plan(data, event_map=None, presentation=None, presentation_reference=None):
    errors = []

    def error(path, message):
        errors.append(f"{path}: {message}")

    def obj(value, path):
        if not isinstance(value, dict):
            error(path, "must be an object")
            return {}
        return value

    def text(value, path):
        if not isinstance(value, str) or not value.strip():
            error(path, "must be non-empty text")

    def strings(value, path, allow_empty=False):
        if not isinstance(value, list):
            error(path, "must be an array")
            return []
        if not allow_empty and not value:
            error(path, "must not be empty")
        for i, item in enumerate(value):
            text(item, f"{path}[{i}]")
        valid = [item for item in value if isinstance(item, str) and item.strip()]
        if len(set(valid)) != len(valid):
            error(path, "values must be unique")
        return valid

    def placeholders(value, path):
        if isinstance(value, str) and ("{{" in value or "}}" in value):
            error(path, "unresolved template content")
        elif isinstance(value, dict):
            for key, child in value.items():
                placeholders(child, f"{path}.{key}")
        elif isinstance(value, list):
            for i, child in enumerate(value):
                placeholders(child, f"{path}[{i}]")

    data = obj(data, "plan")
    placeholders(data, "plan")
    schema_version = data.get("schema_version")
    if schema_version not in ("1.0", "1.1"):
        error("schema_version", "must be 1.0 or 1.1")
    modern = schema_version == "1.1"
    if data.get("experience_profile") != "video_led_web":
        error("experience_profile", "must be video_led_web")
    if modern:
        continuity = obj(data.get("continuity"), "continuity")
        point_of_view = continuity.get("primary_point_of_view")
        if not isinstance(point_of_view, str) or point_of_view not in POINTS_OF_VIEW:
            error(
                "continuity.primary_point_of_view",
                f"must be one of {', '.join(sorted(POINTS_OF_VIEW))}",
            )
        if point_of_view == "learner_first_person":
            for key in ("primary_guide_identifier", "primary_guide_role"):
                text(continuity.get(key), f"continuity.{key}")
        else:
            for key in ("continuity_anchor_identifier", "continuity_anchor_role"):
                text(continuity.get(key), f"continuity.{key}")
        for key in ("point_of_view_return_rule", "learner_language_policy"):
            text(continuity.get(key), f"continuity.{key}")
        branch_policy = continuity.get("branch_policy")
        if not isinstance(branch_policy, str) or branch_policy not in BRANCH_POLICIES:
            error(
                "continuity.branch_policy",
                f"must be one of {', '.join(sorted(BRANCH_POLICIES))}",
            )
    scope = data.get("coverage_scope")
    if scope not in ("full_course", "selected_events"):
        error("coverage_scope", "must be full_course or selected_events")
    events = data.get("events")
    if not isinstance(events, list) or not events:
        error("events", "must be a non-empty array")
        return errors

    beat_ids, interaction_ids = [], []
    for index, value in enumerate(events):
        path = f"events[{index}]"
        entry = obj(value, path)
        beat = entry.get("beat_identifier")
        text(beat, f"{path}.beat_identifier")
        if isinstance(beat, str):
            beat_ids.append(beat)
        strings(entry.get("objective_identifiers"), f"{path}.objective_identifiers")
        event_class = entry.get("event_class")
        if event_class not in ("observation", "exploration", "judgment"):
            error(f"{path}.event_class", "must be observation, exploration or judgment")
        observation = event_class == "observation"
        interaction = entry.get("interaction_identifier")
        if observation:
            if interaction is not None or entry.get("knowledge_action") is not None:
                error(path, "observation needs null interaction_identifier and knowledge_action")
        else:
            text(interaction, f"{path}.interaction_identifier")
            text(entry.get("knowledge_action"), f"{path}.knowledge_action")
            if isinstance(interaction, str):
                interaction_ids.append(interaction)
        strings(entry.get("evidence_to_notice"), f"{path}.evidence_to_notice")
        anchor = obj(entry.get("scene_anchor"), f"{path}.scene_anchor")
        for key in ("object_identifier", "recognition_cue", "availability"):
            text(anchor.get(key), f"{path}.scene_anchor.{key}")
        reference = anchor.get("presentation_anchor_reference")
        if reference is not None:
            valid_reference = isinstance(reference, str) and bool(re.fullmatch(r"[^#\s]+#[^#\s]+", reference))
            if not valid_reference:
                error(f"{path}.scene_anchor.presentation_anchor_reference", "must be presentation_reference#anchor_identifier or null")
            elif presentation is not None:
                document, identifier = reference.split("#")
                if document != presentation_reference:
                    error(path, "presentation reference differs from runtime binding")
                tracks = obj(presentation, "presentation").get("anchors", [])
                tracks = tracks if isinstance(tracks, list) else []
                track = next((row for row in tracks if isinstance(row, dict) and row.get("identifier") == identifier), None)
                if track is None:
                    error(path, "presentation anchor is absent")
                elif track.get("beat_identifier") != beat or track.get("object_identifier") != anchor.get("object_identifier"):
                    error(path, "presentation anchor Beat/object differs from participation plan")
        if modern:
            if anchor.get("trigger_type") not in TRIGGER_TYPES:
                error(f"{path}.scene_anchor.trigger_type",
                      f"must be one of {', '.join(sorted(TRIGGER_TYPES))}")
            text(anchor.get("trigger_description"), f"{path}.scene_anchor.trigger_description")
        surface = obj(entry.get("surface"), f"{path}.surface")
        kind = surface.get("kind")
        if kind not in SURFACES:
            error(f"{path}.surface.kind", f"must be one of {', '.join(SURFACES)}")
        if (kind == "video_only") != observation:
            error(f"{path}.surface.kind", "video_only is for observation; active events need a surface")
        for key in ("selection_reason", "simpler_representation"):
            text(surface.get(key), f"{path}.surface.{key}")

        layers = obj(entry.get("information_layers"), f"{path}.information_layers")
        for layer_name in ("before_action", "on_demand", "after_action"):
            layer = layers.get(layer_name)
            if not isinstance(layer, list):
                error(f"{path}.information_layers.{layer_name}", "must be an array")
                continue
            for i, unit in enumerate(layer):
                unit_path = f"{path}.information_layers.{layer_name}[{i}]"
                unit = obj(unit, unit_path)
                text(unit.get("content"), f"{unit_path}.content")
                text(unit.get("purpose"), f"{unit_path}.purpose")
                if unit.get("delivery") not in (
                        "video", "scene_object", "control_label", "deep_view", "scene_card"):
                    error(
                        f"{unit_path}.delivery",
                        "must name video, scene_object, control_label, deep_view or scene_card",
                    )
        text(layers.get("source_access"), f"{path}.information_layers.source_access")
        attention = obj(entry.get("attention"), f"{path}.attention")
        for key in ("primary_focus", "budget_basis"):
            text(attention.get(key), f"{path}.attention.{key}")
        limit = attention.get("initial_unit_limit")
        if type(limit) is not int or limit < 0:
            error(f"{path}.attention.initial_unit_limit", "must be a non-negative integer")
        elif isinstance(layers.get("before_action"), list) and len(layers["before_action"]) > limit:
            error(f"{path}.attention.initial_unit_limit", "before_action exceeds the declared local budget")
        if attention.get("pause_policy") != ("continue" if observation else "pause_on_entry"):
            error(f"{path}.attention.pause_policy", "observe continuously; pause active tasks on entry")
        if attention.get("conflicting_narration") != ("not_applicable" if observation else "pause"):
            error(f"{path}.attention.conflicting_narration", "active reading/operation must pause conflicting narration")

        feedback = entry.get("feedback")
        if observation:
            if feedback is not None:
                error(f"{path}.feedback", "observation needs null feedback; explanations belong in information layers")
        else:
            feedback = obj(feedback, f"{path}.feedback")
            keys = ["visible_response", "knowledge_response", "repair_action", "scene_connection"]
            if modern:
                keys.extend(("story_consequence", "branch_rejoin"))
            for key in keys:
                text(feedback.get(key), f"{path}.feedback.{key}")
        completion = obj(entry.get("completion"), f"{path}.completion")
        mode = completion.get("mode")
        modes = {"observation": ("content_presented",), "exploration": ("optional_exploration",),
                 "judgment": ("practice_with_feedback", "independent_submission")}
        if mode not in modes.get(event_class if isinstance(event_class, str) else "", ()):
            error(f"{path}.completion.mode", "must match event class and assessment use")
        required = event_class == "judgment"
        if completion.get("evidence_required") is not required:
            error(f"{path}.completion.evidence_required", "only judgment events require completion evidence")
        fields = strings(completion.get("evidence_fields"), f"{path}.completion.evidence_fields",
                         allow_empty=not required)
        if required and fields and all(field.casefold() in ACTION_METADATA for field in fields):
            error(f"{path}.completion.evidence_fields", "action-only metadata is not judgment evidence")
        if observation and fields:
            error(f"{path}.completion.evidence_fields", "content presentation is not mastery evidence")
        text(completion.get("decision_rule"), f"{path}.completion.decision_rule")
        if completion.get("action_only_is_mastery") is not False:
            error(f"{path}.completion.action_only_is_mastery", "must be false")
        close = "hold_pending" if required else ("not_applicable" if observation else "return_optional")
        if completion.get("close_behavior") != close:
            error(f"{path}.completion.close_behavior", f"must be {close}")
        restoration = obj(entry.get("restoration"), f"{path}.restoration")
        text(restoration.get("return_anchor_identifier"), f"{path}.restoration.return_anchor_identifier")
        if restoration.get("resume_interval_reason") is not None:
            text(restoration["resume_interval_reason"], f"{path}.restoration.resume_interval_reason")
        if restoration.get("resume_time_reference") != f"video-event-map.json#{beat}":
            error(f"{path}.restoration.resume_time_reference", "must reference the same beat in video-event-map.json")
        state_fields = strings(restoration.get("state_fields"), f"{path}.restoration.state_fields")
        missing = STATE_FIELDS - set(state_fields)
        if missing:
            error(f"{path}.restoration.state_fields", f"missing {', '.join(sorted(missing))}")
        accessibility = obj(entry.get("accessibility"), f"{path}.accessibility")
        methods = strings(accessibility.get("input_methods"), f"{path}.accessibility.input_methods")
        if not {"keyboard", "touch"}.issubset(methods):
            error(f"{path}.accessibility.input_methods", "must include keyboard and touch")
        for key in ("equivalent_action", "equivalent_evidence"):
            text(accessibility.get(key), f"{path}.accessibility.{key}")
    if len(set(beat_ids)) != len(beat_ids):
        error("events", "beat_identifier values must be unique")
    if len(set(interaction_ids)) != len(interaction_ids):
        error("events", "interaction_identifier values must be unique")

    if event_map is not None:
        mapped = obj(event_map, "event_map").get("events")
        if not isinstance(mapped, list) or not mapped or any(not isinstance(row, dict) for row in mapped):
            error("event_map.events", "must be a non-empty array of objects")
            return errors
        map_ids = [row.get("beat_id") for row in mapped]
        if any(not isinstance(beat, str) or not beat for beat in map_ids) or len(set(map_ids)) != len(map_ids):
            error("event_map.events", "beat_id values must be non-empty and unique")
            return errors
        if scope == "full_course" and beat_ids != map_ids:
            error("coverage_scope", "full_course beat IDs/order must exactly match event map")
        if scope == "selected_events" and [beat for beat in map_ids if beat in beat_ids] != beat_ids:
            error("coverage_scope", "selected_events must be an ordered subset of event map")
        by_beat = {row["beat_id"]: row for row in mapped}
        for entry in events:
            if not isinstance(entry, dict) or not isinstance(entry.get("beat_identifier"), str):
                continue
            beat = entry["beat_identifier"]
            mapped_entry = by_beat.get(beat)
            if mapped_entry is None:
                error(f"events.{beat}", "beat is absent from event map")
                continue
            if entry.get("interaction_identifier") != mapped_entry.get("interaction_id"):
                error(f"events.{beat}", "interaction identifier differs from event map")
            if entry.get("event_class") != mapped_entry.get("event_class"):
                error(f"events.{beat}", "event class differs from event map")
            completion = obj(entry.get("completion"), f"events.{beat}.completion")
            if completion.get("evidence_required") is not mapped_entry.get("evidence_required"):
                error(f"events.{beat}", "evidence gate differs from event map")
            if entry.get("event_class") != "observation":
                pause, resume = mapped_entry.get("pause_seconds"), mapped_entry.get("resume_seconds")
                if any(type(time) not in (int, float) or not math.isfinite(time) for time in (pause, resume)):
                    error(f"events.{beat}", "event map needs finite pause_seconds and resume_seconds")
                elif resume < pause:
                    error(f"events.{beat}", "resume time cannot precede pause time")
                elif resume != pause:
                    restoration = obj(entry.get("restoration"), f"events.{beat}.restoration")
                    text(restoration.get("resume_interval_reason"), f"events.{beat}.restoration.resume_interval_reason")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    parser.add_argument("--event-map", type=Path)
    parser.add_argument("--presentation", type=Path)
    parser.add_argument("--presentation-reference", help="Registered evidence identifier used before #anchor")
    args = parser.parse_args()
    try:
        data = json.loads(args.plan.read_text(encoding="utf-8"))
        event_map = json.loads(args.event_map.read_text(encoding="utf-8")) if args.event_map else None
        if args.event_map and not isinstance(event_map, dict):
            raise ValueError("event map root must be an object")
        presentation = json.loads(args.presentation.read_text(encoding="utf-8")) if args.presentation else None
        if args.presentation and (not isinstance(presentation, dict) or not args.presentation_reference):
            raise ValueError("--presentation requires an object and --presentation-reference")
        errors = validate_plan(data, event_map, presentation, args.presentation_reference)
        if presentation is not None:
            from validate_video_presentation import validate
            errors.extend(validate(presentation))
    except (OSError, ValueError) as exc:
        errors = [str(exc)]
    if errors:
        print("INVALID:\n" + "\n".join(f"- {error}" for error in errors))
        return 1
    print(f"VALID: {len(data['events'])} participation events; structure"
          + (" and event-map alignment checked" if args.event_map else " checked"))
    print("Content, reading load, browser behavior and learning effects require separate review.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
