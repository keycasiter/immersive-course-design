"""Schema 1.1 checks owned by character-reference-and-introduction.md.

Checks declared identity, coverage and file-bound records, not visual truth.
"""

import math


def text(value):
    return isinstance(value, str) and bool(value.strip())


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def objects(value):
    return [row for row in value if isinstance(row, dict)] if isinstance(value, list) else []


def identifier_list(value, known, audit, label):
    valid = (isinstance(value, list) and all(text(item) and item in known for item in value))
    audit.need(valid, f"{label}: expected registered identifiers")
    if not valid:
        return []
    audit.need(len(value) == len(set(value)), f"{label}: duplicate identifiers")
    return value


def lookup(mapping, value):
    return mapping.get(value, {}) if isinstance(value, str) else {}


def interval_covered(start, end, intervals):
    cursor = start
    for visible, hidden in sorted(intervals):
        if visible > cursor + 0.02:
            return False
        cursor = max(cursor, hidden)
        if cursor >= end - 0.02:
            return True
    return False


def validate_character_plan(plan, audit, shots, timelines, references, events):
    sources = audit.collection(plan.get("character_sources"), "character_sources",
                               "source_identifier", True)
    characters = audit.collection(plan.get("characters"), "characters", "character_identifier", True)
    introductions = audit.collection(plan.get("character_introductions"),
                                     "character_introductions", "introduction_identifier", True)
    for identifier, source in sources.items():
        kind = source.get("source_type")
        audit.need(isinstance(kind, str) and kind in {
            "primary_text", "historical_material", "screen_adaptation", "context_research", "other",
        }, f"{identifier}: invalid character source type")
        audit.need(text(source.get("title")) and text(source.get("locator")),
                   f"{identifier}: source title and locator are required")
        audit.file(source.get("research_file"), source.get("research_sha256"),
                   identifier + ".research")

    for identifier, character in characters.items():
        for field in ("display_name", "current_identity", "reference_search", "appearance_constraints"):
            audit.need(text(character.get(field)), f"{identifier}: missing {field}")
        status = character.get("reference_status")
        audit.need(status in ("referenced", "no_suitable_reference"),
                   f"{identifier}: invalid reference status")
        source_ids = identifier_list(character.get("source_identifiers"), sources, audit,
                                     identifier + ".source_identifiers")
        if status == "referenced":
            audit.need(bool(source_ids), f"{identifier}: referenced character lacks sources")
        elif status == "no_suitable_reference":
            audit.need(text(character.get("creative_fallback_reason")),
                       f"{identifier}: free design requires a documented fallback reason")
        visual_ids = identifier_list(character.get("visual_reference_identifiers"), references, audit,
                                     identifier + ".visual_reference_identifiers")
        for reference_identifier in visual_ids:
            audit.need(references[reference_identifier].get("kind") in ("image", "video"),
                       f"{identifier}: visual reference must be an image or video file")

    first_appearances = {}
    visible_intervals = {}
    for identifier, shot in shots.items():
        character_ids = identifier_list(shot.get("character_identifiers"), characters, audit,
                                        identifier + ".character_identifiers")
        start, end = shot.get("start_seconds"), shot.get("end_seconds")
        if not (finite(start) and finite(end) and 0 <= start < end):
            continue
        timeline, branch = shot.get("timeline_identifier"), shot.get("branch_identifier")
        if not text(timeline) or timeline not in timelines or not text(branch):
            continue
        appearances = shot.get("character_appearances")
        offsets = {character_identifier: start for character_identifier in character_ids}
        if appearances is not None:
            actual = audit.collection(appearances, identifier + ".character_appearances",
                                      "character_identifier", True)
            audit.need(set(actual) == set(character_ids),
                       f"{identifier}: appearance mapping must match shot characters")
            offsets = {key: row.get("first_visible_seconds") for key, row in actual.items()
                       if key in character_ids}
        for character_identifier, visible in offsets.items():
            valid = finite(visible) and start <= visible < end
            audit.need(valid, f"{identifier}: first visible time must be within shot")
            if not valid:
                continue
            key = (timeline, branch, character_identifier)
            visible_intervals.setdefault(key, []).append((visible, end))
            previous = first_appearances.get(key)
            if previous is None or visible < previous[0]:
                first_appearances[key] = (visible, identifier, end)

    for identifier, event in events.items():
        kind, on_screen = event.get("kind"), event.get("on_screen") is True
        speaker = event.get("speaker_identifier")
        if kind == "dialogue":
            audit.need(bool(lookup(characters, speaker)),
                       f"{identifier}: dialogue speaker must be a registered character")
        elif kind == "narration" and on_screen:
            audit.need(bool(lookup(characters, speaker)),
                       f"{identifier}: on-screen narrator must be a registered character")
        if kind not in ("dialogue", "narration") or not on_screen:
            continue
        start, end = event.get("start_seconds"), event.get("end_seconds")
        if not (finite(start) and finite(end) and 0 <= start < end):
            continue  # The sound contract reports invalid intervals.
        candidates = [
            intervals for (timeline, branch, character), intervals in visible_intervals.items()
            if timeline == event.get("timeline_identifier") and character == speaker
        ]
        audit.need(any(interval_covered(start, end, intervals) for intervals in candidates),
                   f"{identifier}: on-screen speaker must remain visible throughout sound event "
                   "in one timeline/branch")

    coverage = {}
    for identifier, introduction in introductions.items():
        character_identifier = introduction.get("character_identifier")
        character = lookup(characters, character_identifier)
        shot = lookup(shots, introduction.get("shot_identifier"))
        timeline, branch = introduction.get("timeline_identifier"), introduction.get("branch_identifier")
        valid_key = text(timeline) and text(branch) and text(character_identifier)
        key = (timeline, branch, character_identifier) if valid_key else None
        first = first_appearances.get(key) if key else None
        audit.need(bool(character) and bool(shot) and first is not None,
                   f"{identifier}: introduction has no registered first appearance")
        if first:
            coverage.setdefault(key, []).append(identifier)
            audit.need(introduction.get("shot_identifier") == first[1],
                       f"{identifier}: introduction must use the first appearance shot")
            audit.need(timeline == shot.get("timeline_identifier") and branch == shot.get("branch_identifier"),
                       f"{identifier}: introduction timeline/branch differs from shot")
        for field in ("display_name", "current_identity"):
            audit.need(text(introduction.get(field)) and introduction.get(field) == character.get(field),
                       f"{identifier}: introduction {field} differs from character")
        audit.need(introduction.get("render_mode") == "burned_in_video",
                   f"{identifier}: introduction must be rendered inside actual video")
        audit.need(text(introduction.get("placement")), f"{identifier}: missing safe placement")
        start, end = introduction.get("start_seconds"), introduction.get("end_seconds")
        valid_interval = finite(start) and finite(end) and 0 <= start < end
        audit.need(valid_interval, f"{identifier}: invalid introduction interval")
        if first and valid_interval:
            audit.need(abs(start - first[0]) <= 0.02 and end <= first[2] + 0.02,
                       f"{identifier}: introduction must begin at first visibility and end within its shot")
    for key in first_appearances:
        audit.need(len(coverage.get(key, [])) == 1,
                   f"{'/'.join(key)}: requires exactly one first-appearance introduction")


def validate_character_reviews(plan, timeline, audit):
    if plan.get("schema_version") not in ("1.1", "1.2"):
        return
    identifier = timeline["timeline_identifier"]
    expected_characters = {
        item for shot in objects(plan.get("shots")) if shot.get("timeline_identifier") == identifier
        for item in shot.get("character_identifiers", []) if isinstance(item, str)
    }
    if not expected_characters:
        return
    expected_introductions = {
        row["introduction_identifier"] for row in objects(plan.get("character_introductions"))
        if row.get("timeline_identifier") == identifier
    }
    for check in ("character_appearance", "character_introduction"):
        reviews = [row for row in objects(plan.get("manual_reviews"))
                   if row.get("timeline_identifier") == identifier and row.get("check") == check]
        audit.need(len(reviews) == 1, f"{identifier}: requires one file-bound {check} review")
        for review in reviews:
            label = identifier + "." + check
            actual = identifier_list(review.get("character_identifiers"), expected_characters,
                                     audit, label + ".character_identifiers")
            audit.need(set(actual) == expected_characters, f"{label}: review omits visible characters")
            if check == "character_introduction":
                actual = identifier_list(review.get("introduction_identifiers"), expected_introductions,
                                         audit, label + ".introduction_identifiers")
                audit.need(set(actual) == expected_introductions, f"{label}: review omits introductions")
            audit.evidence(review, label, timeline.get("content_sha256"))
