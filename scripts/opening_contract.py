"""Check declared opening content and ordering; no semantic or runtime approval."""

import re


IDENTIFIER = re.compile(r"^[a-z][a-z0-9]*(?:[_-][a-z0-9]+)*$")
OPENING_EXTENSION_FIELDS = {
    "contract_version", "course_introduction", "entry_mode", "first_task_identifiers",
    "information_units", "essential_terms", "reentry_policy", "experience_entry",
    "orientation_bootstrap",
}
BASE_PURPOSES = {
    "course_introduction", "background", "problem", "learner_role", "first_action",
}
ORIENTATION_PURPOSES = {"host_welcome", "world_model", "journey_preview"}
PURPOSES = BASE_PURPOSES | ORIENTATION_PURPOSES
LEARNING_ROLES = {"core_reasoning", "evidence_collection", "independent_assessment"}
ENTRY_INTENSITIES = {"compact", "standard", "extended"}
EXPERIENCE_ENTRY_TEXT_FIELDS = (
    "reality_anchor",
    "inciting_event",
    "threshold_transition",
    "identity_landing",
    "first_consequential_action",
    "persistent_carrier",
    "world_rule_continuity",
    "accessibility_equivalent",
    "skip_replay_reentry",
    "design_rationale",
)
ORIENTATION_BOOTSTRAP_TEXT_FIELDS = (
    "assumed_entry_state",
    "host_welcome",
    "minimal_world_model",
    "key_objects_and_terms",
    "learning_journey_preview",
    "role_and_collaboration",
    "first_action_handoff",
    "comprehension_safeguard",
)


def validate_opening(data, scenes, tasks, media, graph):
    """Validate references and predecessor declarations across every entry branch."""
    errors = []

    def require(condition, message):
        if not condition:
            errors.append("opening: " + message)

    def text(value):
        return isinstance(value, str) and bool(value.strip())

    def object_value(value, label):
        require(isinstance(value, dict), f"{label} must be an object")
        return value if isinstance(value, dict) else {}

    def rows(value, label, allow_empty=False):
        require(isinstance(value, list), f"{label} must be a list")
        values = value if isinstance(value, list) else []
        require(allow_empty or bool(values), f"{label} cannot be empty")
        return [object_value(item, f"{label}[{index}]") for index, item in enumerate(values)]

    def references(value, known, label, allow_empty=False):
        require(isinstance(value, list), f"{label} must be a list")
        values = value if isinstance(value, list) else []
        require(allow_empty or bool(values), f"{label} cannot be empty")
        result = []
        for item in values:
            require(isinstance(item, str) and item in known, f"{label} unknown reference: {item}")
            if isinstance(item, str) and item in known:
                require(item not in result, f"{label} duplicate reference: {item}")
                result.append(item)
        return result

    def reachable(start, blocked=None):
        visited = set()
        pending = [start]
        while pending:
            current = pending.pop()
            if not isinstance(current, str) or current == blocked or current in visited:
                continue
            if current in graph:
                visited.add(current)
                pending.extend(graph[current])
        return visited

    opening = object_value(data.get("opening"), "contract")
    version = opening.get("contract_version")
    require(version in {"1.0", "1.1", "1.2"},
            "contract_version must be 1.0, 1.1 or 1.2")
    for key in ("course_introduction", "reentry_policy"):
        require(text(opening.get(key)), f"missing {key}")
    if version in {"1.1", "1.2"}:
        experience_entry = object_value(opening.get("experience_entry"), "experience_entry")
        intensity = experience_entry.get("intensity")
        require(isinstance(intensity, str) and intensity in ENTRY_INTENSITIES,
                "experience_entry.intensity must be compact, standard or extended")
        for key in EXPERIENCE_ENTRY_TEXT_FIELDS:
            require(text(experience_entry.get(key)), f"experience_entry missing {key}")
    if version == "1.2":
        orientation_bootstrap = object_value(
            opening.get("orientation_bootstrap"), "orientation_bootstrap")
        for key in ORIENTATION_BOOTSTRAP_TEXT_FIELDS:
            require(text(orientation_bootstrap.get(key)),
                    f"orientation_bootstrap missing {key}")
    mode = opening.get("entry_mode")
    require(isinstance(mode, str) and mode in {"standalone", "embedded", "resumed"},
            "entry_mode must be standalone, embedded or resumed")
    entry = data.get("entry_scene_identifier")
    visited = reachable(entry)

    # Stop each branch at its first disciplinary task, including tasks in the entry scene.
    first_tasks = set()
    pending = [entry]
    explored = set()
    while pending:
        current = pending.pop()
        if not isinstance(current, str) or current in explored or current not in scenes:
            continue
        explored.add(current)
        task = scenes[current].get("task")
        role = task.get("pedagogical_role") if isinstance(task, dict) else None
        if isinstance(role, str) and role in LEARNING_ROLES:
            identifier = task.get("task_identifier")
            if isinstance(identifier, str) and identifier in tasks:
                first_tasks.add(identifier)
            continue
        pending.extend(graph.get(current, []))
    declared = set(references(opening.get("first_task_identifiers"), tasks,
                              "first_task_identifiers"))
    require(bool(first_tasks), "entry must lead to a disciplinary task")
    for identifier in sorted(first_tasks - declared):
        require(False, f"first_task_identifiers missing entry branch task: {identifier}")
    for identifier in sorted(declared - first_tasks):
        require(False, f"first_task_identifiers is not a first disciplinary task: {identifier}")

    units = {}
    covered = set()
    purposes_before_task = {identifier: set() for identifier in first_tasks}
    for index, unit in enumerate(rows(opening.get("information_units"), "information_units")):
        label = f"information_units[{index}]"
        identifier = unit.get("information_identifier")
        require(isinstance(identifier, str) and bool(IDENTIFIER.fullmatch(identifier)),
                f"{label} invalid information_identifier")
        if isinstance(identifier, str) and IDENTIFIER.fullmatch(identifier):
            require(identifier not in units, f"duplicate information_identifier: {identifier}")
            units[identifier] = unit
        purposes = references(unit.get("purposes"), PURPOSES, f"{label}.purposes")
        covered.update(purposes)
        for key in ("presentation_reference", "equivalent_content",
                    "equivalent_presentation_reference"):
            require(text(unit.get(key)), f"{label} missing {key}")
        scene_identifier = unit.get("scene_identifier")
        known_scene = isinstance(scene_identifier, str) and scene_identifier in scenes
        require(known_scene, f"{label} unknown scene_identifier")
        require(known_scene and scene_identifier in visited, f"{label} scene is not reachable")
        if known_scene:
            for task_identifier in sorted(first_tasks):
                target = tasks[task_identifier]["scene"].get("scene_identifier")
                if scene_identifier == target or target not in reachable(
                        entry, blocked=scene_identifier):
                    purposes_before_task[task_identifier].update(purposes)

        resource_refs = references(unit.get("media_resource_identifiers"), media,
                                   f"{label}.media_resource_identifiers", allow_empty=True)
        scene_resources = scenes[scene_identifier].get("media_resource_identifiers", []) \
            if known_scene else []
        for resource_identifier in resource_refs:
            require(isinstance(scene_resources, list) and resource_identifier in scene_resources,
                    f"{label} media is not linked to its scene: {resource_identifier}")

        delivery = unit.get("delivery")
        content_reference = unit.get("content_reference")
        event = unit.get("presentation_event")
        if delivery == "inline":
            require(isinstance(event, str) and event in {"scene_enter", "before_task_open"},
                    f"{label} inline content must precede task opening")
            require(unit.get("inherited_context") is None,
                    f"{label} inline delivery cannot claim inherited_context")
            require(isinstance(content_reference, str) and content_reference in {
                "opening.course_introduction", "scene.narration"},
                f"{label} invalid inline content_reference")
            content = opening.get("course_introduction") if \
                content_reference == "opening.course_introduction" else \
                scenes[scene_identifier].get("narration") if known_scene and \
                content_reference == "scene.narration" else None
        elif delivery == "inherited":
            require(isinstance(mode, str) and mode in {"embedded", "resumed"},
                    f"{label} standalone entry cannot inherit background")
            require(event == "verified_prior_context",
                    f"{label} inherited content needs verified_prior_context")
            require(content_reference == "inherited_context.content",
                    f"{label} invalid inherited content_reference")
            inherited = object_value(unit.get("inherited_context"),
                                     f"{label}.inherited_context")
            for key in ("course_identifier", "course_version", "presentation_reference",
                        "content", "replay_reference"):
                require(text(inherited.get(key)), f"{label}.inherited_context missing {key}")
            parent_identifier = inherited.get("course_identifier")
            require(isinstance(parent_identifier, str) and
                    bool(IDENTIFIER.fullmatch(parent_identifier)),
                    f"{label}.inherited_context invalid course_identifier")
            content = inherited.get("content")
        else:
            require(False, f"{label} delivery must be inline or inherited")
            content = None
        require(text(content), f"{label} content_reference must resolve to actual text")
        if "course_introduction" in purposes:
            introduction = opening.get("course_introduction")
            require(text(introduction) and text(content) and introduction.strip() in content,
                    f"{label} must present the declared course_introduction")
    required_purposes = BASE_PURPOSES | (
        ORIENTATION_PURPOSES if version == "1.2" else set())
    for purpose in sorted(required_purposes - covered):
        require(False, f"information_units missing purpose: {purpose}")
    for task_identifier in sorted(first_tasks):
        missing = required_purposes - purposes_before_task[task_identifier]
        for purpose in sorted(missing):
            require(
                False,
                f"entry path to {task_identifier} lacks information purpose before first task: "
                f"{purpose}",
            )

    terms = set()
    for index, term in enumerate(rows(opening.get("essential_terms"), "essential_terms",
                                      allow_empty=True)):
        label = f"essential_terms[{index}]"
        for key in ("term", "meaning"):
            require(text(term.get(key)), f"{label} missing {key}")
        name = term.get("term")
        if text(name):
            require(name not in terms, f"{label} duplicate term: {name}")
            terms.add(name)
        identifier = term.get("information_identifier")
        require(isinstance(identifier, str) and identifier in units,
                f"{label} unknown information_identifier")
    return errors
