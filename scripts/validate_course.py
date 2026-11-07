#!/usr/bin/env python3
"""Validate a portable immersive-course blueprint using only the standard library."""

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse
from contract_checks import placeholder_paths
from instructional_cycle_contract import (
    INSTRUCTIONAL_EXTENSION_FIELDS,
    validate_instructional_cycle,
)
from opening_contract import OPENING_EXTENSION_FIELDS, validate_opening


IDENTIFIER = re.compile(r"^[a-z][a-z0-9]*(?:[_-][a-z0-9]+)*$")
PLACEHOLDER = re.compile(r"\{\{.+?\}\}|\[(?:TBD|Assumption, TBD)\]", re.IGNORECASE)
SCENE_KINDS = {"introduction", "macro", "instruction", "practice", "transfer", "summary"}
MEDIA_TYPES = {"video", "panorama", "three_dimensional", "diagram", "audio", "document"}
TEACHING_ROLES = {
    "progression", "macro_narrative", "local_exploration", "explanation", "evidence", "support"
}
RESPONSE_TYPES = {
    "choice", "numeric", "ordering", "variables", "pathway",
    "evidence", "constructed_response", "performance"
}
PEDAGOGICAL_ROLES = {
    "core_reasoning", "evidence_collection", "orientation",
    "operation_support", "independent_assessment"
}
PRACTICE_ROLES = {"core_reasoning", "evidence_collection"}
EVALUATION_STATUSES = {"planned", "not_evaluated", "completed"}
RECORD_FIELDS = {
    "material_version", "first_response", "assistance_used", "operation_help",
    "knowledge_help", "feedback_revision", "independent_result"
}
KNOWLEDGE_RELATIONS = {"prerequisite", "part_of", "causal", "contrast", "representation"}
LEARNING_RECORD_FIELDS = {"evidence_interpretation", "instructional_action", "recheck_result"}
CONTENT_FUNCTIONS = {
    "orientation", "instruction", "guided_practice",
    "independent_application", "synthesis",
}


def validate_scope_coverage(data, sources, objectives, scenes):
    """Validate a declared full-course inventory and its implementation coverage."""
    errors = []

    def require(condition, message):
        if not condition:
            errors.append(message)

    def text(value):
        return isinstance(value, str) and bool(value.strip())

    coverage = data.get("scope_coverage")
    require(isinstance(coverage, dict), "Full course requires scope_coverage")
    if not isinstance(coverage, dict):
        return errors
    require(coverage.get("contract_version") == "1.0",
            "scope_coverage.contract_version must be 1.0")
    require(coverage.get("scope_claim") == "full_course",
            "scope_coverage.scope_claim must be full_course")
    for key in ("inventory_basis", "completeness_rationale"):
        require(text(coverage.get(key)), f"scope_coverage missing {key}")

    knowledge = {}
    organization = data.get("knowledge_organization")
    units = organization.get("units") if isinstance(organization, dict) else None
    require(isinstance(units, list) and bool(units),
            "scope_coverage requires non-empty knowledge_organization.units")
    for index, raw in enumerate(units if isinstance(units, list) else []):
        if not isinstance(raw, dict):
            continue
        identifier = raw.get("knowledge_identifier")
        if isinstance(identifier, str):
            knowledge[identifier] = raw

    scene_beats = {}
    all_beats = {}
    for scene_identifier, scene in scenes.items():
        beats = scene.get("beat_identifiers")
        require(isinstance(beats, list) and bool(beats),
                f"{scene_identifier}.beat_identifiers must be a non-empty list")
        valid = []
        for beat in beats if isinstance(beats, list) else []:
            require(isinstance(beat, str) and bool(IDENTIFIER.fullmatch(beat)),
                    f"{scene_identifier} has an invalid beat_identifier")
            if isinstance(beat, str) and IDENTIFIER.fullmatch(beat):
                require(beat not in all_beats, f"Duplicate beat_identifier: {beat}")
                all_beats[beat] = scene_identifier
                valid.append(beat)
        scene_beats[scene_identifier] = valid

    inventory = coverage.get("required_content_inventory")
    require(isinstance(inventory, list) and bool(inventory),
            "scope_coverage.required_content_inventory must be a non-empty list")
    content = {}
    inventory_objectives = set()
    for index, raw in enumerate(inventory if isinstance(inventory, list) else []):
        label = f"scope_coverage.required_content_inventory[{index}]"
        require(isinstance(raw, dict), f"{label} must be an object")
        if not isinstance(raw, dict):
            continue
        identifier = raw.get("content_identifier")
        require(isinstance(identifier, str) and bool(IDENTIFIER.fullmatch(identifier)),
                f"{label} has an invalid content_identifier")
        if not isinstance(identifier, str) or not IDENTIFIER.fullmatch(identifier):
            continue
        require(identifier not in content, f"Duplicate content_identifier: {identifier}")
        content[identifier] = raw
        for key in ("title", "requirement"):
            require(text(raw.get(key)), f"{identifier} missing {key}")
        source_refs = raw.get("source_identifiers")
        require(isinstance(source_refs, list) and bool(source_refs),
                f"{identifier}.source_identifiers must be a non-empty list")
        for reference in source_refs if isinstance(source_refs, list) else []:
            require(reference in sources, f"{identifier} unknown source reference: {reference}")
        objective_refs = raw.get("objective_identifiers")
        require(isinstance(objective_refs, list) and bool(objective_refs),
                f"{identifier}.objective_identifiers must be a non-empty list")
        for reference in objective_refs if isinstance(objective_refs, list) else []:
            require(reference in objectives, f"{identifier} unknown objective reference: {reference}")
            if reference in objectives:
                inventory_objectives.add(reference)

    mappings = coverage.get("coverage_map")
    require(isinstance(mappings, list) and bool(mappings),
            "scope_coverage.coverage_map must be a non-empty list")
    mapped_content = set()
    mapped_knowledge = set()
    mapped_scenes = set()
    mapped_beats = set()
    covered_functions = set()
    for index, raw in enumerate(mappings if isinstance(mappings, list) else []):
        label = f"scope_coverage.coverage_map[{index}]"
        require(isinstance(raw, dict), f"{label} must be an object")
        if not isinstance(raw, dict):
            continue
        identifier = raw.get("content_identifier")
        require(identifier in content, f"{label} unknown content_identifier: {identifier}")
        if identifier in content:
            require(identifier not in mapped_content,
                    f"Duplicate scope coverage mapping: {identifier}")
            mapped_content.add(identifier)
        require(raw.get("coverage_status") == "complete",
                f"{identifier}: full-course coverage_status must be complete")
        knowledge_refs = raw.get("knowledge_identifiers")
        require(isinstance(knowledge_refs, list) and bool(knowledge_refs),
                f"{identifier}.knowledge_identifiers must be a non-empty list")
        for reference in knowledge_refs if isinstance(knowledge_refs, list) else []:
            require(reference in knowledge, f"{identifier} unknown knowledge reference: {reference}")
            if reference in knowledge:
                mapped_knowledge.add(reference)
        scene_refs = raw.get("scene_identifiers")
        require(isinstance(scene_refs, list) and bool(scene_refs),
                f"{identifier}.scene_identifiers must be a non-empty list")
        valid_scene_refs = set()
        for reference in scene_refs if isinstance(scene_refs, list) else []:
            require(reference in scenes, f"{identifier} unknown scene reference: {reference}")
            if reference in scenes:
                mapped_scenes.add(reference)
                valid_scene_refs.add(reference)
        beat_refs = raw.get("beat_identifiers")
        require(isinstance(beat_refs, list) and bool(beat_refs),
                f"{identifier}.beat_identifiers must be a non-empty list")
        for reference in beat_refs if isinstance(beat_refs, list) else []:
            require(reference in all_beats, f"{identifier} unknown beat reference: {reference}")
            if reference in all_beats:
                require(all_beats[reference] in valid_scene_refs,
                        f"{identifier} beat is outside its mapped scenes: {reference}")
                mapped_beats.add(reference)
        functions = raw.get("content_functions")
        require(isinstance(functions, list) and bool(functions),
                f"{identifier}.content_functions must be a non-empty list")
        for function in functions if isinstance(functions, list) else []:
            require(function in CONTENT_FUNCTIONS,
                    f"{identifier} invalid content_function: {function}")
            if function in CONTENT_FUNCTIONS:
                covered_functions.add(function)

    require(mapped_content == set(content),
            "Every required content item must have exactly one complete coverage mapping")
    required_objectives = {
        identifier for identifier, objective in objectives.items()
        if objective.get("required") is True
    }
    require(required_objectives.issubset(inventory_objectives),
            "Full-course inventory omits one or more required objectives")
    required_knowledge = {
        identifier for identifier, unit in knowledge.items()
        if unit.get("assumed_known") is not True
    }
    require(required_knowledge.issubset(mapped_knowledge),
            "Full-course coverage omits one or more required knowledge units")
    required_scenes = {
        identifier for identifier, scene in scenes.items()
        if scene.get("required") is True
    }
    require(required_scenes.issubset(mapped_scenes),
            "Full-course coverage omits one or more required scenes")
    required_beats = {
        beat for scene_identifier in required_scenes
        for beat in scene_beats.get(scene_identifier, [])
    }
    require(required_beats.issubset(mapped_beats),
            "Full-course coverage omits one or more required Beats")
    require(CONTENT_FUNCTIONS.issubset(covered_functions),
            "Full-course coverage must include orientation, instruction, guided practice, "
            "independent application and synthesis")

    excluded = coverage.get("excluded_content")
    require(isinstance(excluded, list), "scope_coverage.excluded_content must be a list")
    for index, row in enumerate(excluded if isinstance(excluded, list) else []):
        label = f"scope_coverage.excluded_content[{index}]"
        require(isinstance(row, dict), f"{label} must be an object")
        if isinstance(row, dict):
            for key in ("content_identifier", "title", "rationale", "decision_reference"):
                require(text(row.get(key)), f"{label} missing {key}")
            require(row.get("content_identifier") not in content,
                    f"{label} overlaps required content")
    deferred = coverage.get("deferred_content")
    require(isinstance(deferred, list), "scope_coverage.deferred_content must be a list")
    require(deferred == [], "Full course cannot defer required content")
    return errors


def validate_learning_design(data, sources, objectives, scenes, tasks, required_objectives):
    """Check declared learning relationships, not their pedagogical validity."""
    errors = []

    def require(condition, message):
        if not condition:
            errors.append(message)

    def text(value):
        return isinstance(value, str) and bool(value.strip())

    def obj(value, label):
        require(isinstance(value, dict), f"{label} must be an object")
        return value if isinstance(value, dict) else {}

    def rows(value, label, allow_empty=False):
        require(isinstance(value, list), f"{label} must be a list")
        values = value if isinstance(value, list) else []
        require(allow_empty or bool(values), f"{label} cannot be empty")
        return [obj(item, f"{label}[{index}]") for index, item in enumerate(values)]

    def refs(value, known, label, allow_empty=False):
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

    def teaching_refs(value, objective_refs, label, allow_empty=False, combined=False):
        result = refs(value, scenes, label, allow_empty)
        covered_here = set()
        for identifier in result:
            scene = scenes[identifier]
            scene_objectives = scene.get("objective_identifiers")
            kind = scene.get("kind")
            require(scene.get("required") is True and isinstance(kind, str) and
                    kind in {"macro", "instruction"},
                    f"{label} requires a required teaching scene: {identifier}")
            selected = [item for item in scene_objectives if isinstance(item, str)] \
                if isinstance(scene_objectives, list) else []
            covered_here.update(selected)
            require(isinstance(scene_objectives, list) and
                    (bool(set(selected).intersection(objective_refs)) if combined else
                     all(item in selected for item in objective_refs)),
                    f"{label} scene does not cover linked objectives: {identifier}")
        if combined and not allow_empty:
            require(set(objective_refs).issubset(covered_here),
                    f"{label} combined teaching scenes do not cover linked objectives")
        return result

    def learning_task(identifier):
        linked = tasks.get(identifier)
        role = linked["task"].get("pedagogical_role") if linked else None
        return linked is not None and linked["scene"].get("required") is True and (
            (linked["scene"].get("kind") == "practice" and
             isinstance(role, str) and role in PRACTICE_ROLES) or
            (linked["scene"].get("kind") == "transfer" and
             role == "independent_assessment")
        )

    organization = obj(data.get("knowledge_organization"), "knowledge_organization")
    for key in ("prior_knowledge_check", "sequence_rationale"):
        require(text(organization.get(key)), f"knowledge_organization missing {key}")
    units = {}
    covered = set()
    for index, unit in enumerate(rows(organization.get("units"), "knowledge_organization.units")):
        label = f"knowledge_organization.units[{index}]"
        identifier = unit.get("knowledge_identifier")
        require(isinstance(identifier, str) and bool(IDENTIFIER.fullmatch(identifier)),
                f"{label} invalid knowledge_identifier")
        if not isinstance(identifier, str) or not IDENTIFIER.fullmatch(identifier):
            continue
        require(identifier not in units, f"Duplicate knowledge_identifier: {identifier}")
        units[identifier] = unit
        require(text(unit.get("description")), f"{label} missing description")
        refs(unit.get("source_identifiers"), sources, f"{label}.source_identifiers")
        linked_objectives = refs(unit.get("objective_identifiers"), objectives,
                                 f"{label}.objective_identifiers")
        covered.update(linked_objectives)
        require(isinstance(unit.get("assumed_known"), bool), f"{label} assumed_known must be boolean")
        teaching_refs(unit.get("teaching_scene_identifiers"), linked_objectives,
                      f"{label}.teaching_scene_identifiers", unit.get("assumed_known") is True,
                      combined=True)
    for identifier in sorted(required_objectives - covered):
        errors.append(f"Required objective missing knowledge unit: {identifier}")

    prerequisite_graph = {identifier: set() for identifier in units}
    for index, relation in enumerate(rows(organization.get("relations"),
                                           "knowledge_organization.relations", True)):
        label = f"knowledge_organization.relations[{index}]"
        source = refs([relation.get("from_knowledge_identifier")], units, f"{label}.from")
        target = refs([relation.get("to_knowledge_identifier")], units, f"{label}.to")
        kind = relation.get("relation_type")
        require(isinstance(kind, str) and kind in KNOWLEDGE_RELATIONS, f"{label} invalid relation_type")
        require(text(relation.get("rationale")), f"{label} missing rationale")
        if source and target:
            require(source[0] != target[0], f"{label} cannot relate a knowledge unit to itself")
            if kind == "prerequisite":
                prerequisite_graph[source[0]].add(target[0])
    # Only prerequisites must be acyclic. Mechanisms can contain feedback loops.
    for origin in prerequisite_graph:
        pending = list(prerequisite_graph[origin])
        visited = set()
        while pending:
            current = pending.pop()
            if current == origin:
                errors.append(f"Prerequisite cycle includes knowledge unit: {origin}")
                break
            if current not in visited:
                visited.add(current)
                pending.extend(prerequisite_graph[current])

    integration_refs = refs(organization.get("integration_task_identifiers"), tasks,
                            "knowledge_organization.integration_task_identifiers")
    integrated = set()
    for identifier in integration_refs:
        require(learning_task(identifier), f"Integration requires a learning task: {identifier}")
        if learning_task(identifier):
            integrated.update(tasks[identifier]["objectives"])
    for identifier in sorted(required_objectives - integrated):
        errors.append(f"Required objective missing integration task: {identifier}")

    instruction = obj(data.get("instructional_design"), "instructional_design")
    planned = set()
    for index, plan in enumerate(rows(instruction.get("objective_plans"),
                                      "instructional_design.objective_plans")):
        label = f"instructional_design.objective_plans[{index}]"
        objective_refs = refs([plan.get("objective_identifier")], objectives, f"{label}.objective")
        if not objective_refs:
            continue
        identifier = objective_refs[0]
        require(identifier not in planned, f"Duplicate instructional objective plan: {identifier}")
        planned.add(identifier)
        knowledge_refs = refs(plan.get("knowledge_identifiers"), units, f"{label}.knowledge_identifiers")
        for knowledge_identifier in knowledge_refs:
            linked = units[knowledge_identifier].get("objective_identifiers")
            require(isinstance(linked, list) and identifier in linked,
                    f"{label} knowledge does not cover objective: {knowledge_identifier}")
        teaching_refs(plan.get("teaching_scene_identifiers"), [identifier],
                      f"{label}.teaching_scene_identifiers")
        for key in ("guidance_and_fading", "retrieval_and_spacing", "transfer_change"):
            require(text(plan.get(key)), f"{label} missing {key}")
    for identifier in sorted(required_objectives - planned):
        errors.append(f"Required objective missing instructional plan: {identifier}")

    evaluation = obj(data.get("evaluation_plan"), "evaluation_plan")
    checkpoints = set()
    for index, checkpoint in enumerate(rows(evaluation.get("formative_assessment"),
                                            "evaluation_plan.formative_assessment")):
        label = f"evaluation_plan.formative_assessment[{index}]"
        task_refs = refs([checkpoint.get("task_identifier")], tasks, f"{label}.task")
        if not task_refs:
            continue
        identifier = task_refs[0]
        linked = tasks[identifier]
        require(identifier not in checkpoints, f"Duplicate formative checkpoint: {identifier}")
        checkpoints.add(identifier)
        require(learning_task(identifier) and linked["scene"].get("kind") == "practice",
                f"{label} must refer to a required reasoning or evidence practice task")
        for rule_index, rule in enumerate(rows(checkpoint.get("evidence_interpretations"),
                                                f"{label}.evidence_interpretations")):
            rule_label = f"{label}.evidence_interpretations[{rule_index}]"
            objective_refs = refs([rule.get("objective_identifier")], objectives, f"{rule_label}.objective")
            for objective in objective_refs:
                require(objective in linked["objectives"], f"{rule_label} objective not covered by checkpoint")
            for key in ("observed_response", "interpretation", "alternative_explanation", "instructional_action"):
                require(text(rule.get(key)), f"{rule_label} missing {key}")
            rechecks = refs([rule.get("recheck_task_identifier")], tasks, f"{rule_label}.recheck")
            for recheck in rechecks:
                require(learning_task(recheck), f"{rule_label} recheck requires a learning task")
                require(all(objective in tasks[recheck]["objectives"] for objective in objective_refs),
                        f"{rule_label} recheck does not cover objective")
    for identifier, linked in tasks.items():
        if learning_task(identifier) and linked["scene"].get("kind") == "practice":
            require(identifier in checkpoints, f"Practice task missing formative checkpoint: {identifier}")
    fields = evaluation.get("record_fields")
    for field in sorted(LEARNING_RECORD_FIELDS):
        require(isinstance(fields, list) and field in fields, f"evaluation_plan.record_fields missing {field}")
    return errors


def validate(data, base_directory, complete_design=False, ready_media=False, learning_design=False,
             opening_design=False, instructional_cycle=False, full_course=False):
    errors = []

    def require(condition, message):
        if not condition:
            errors.append(message)

    def text(value):
        return isinstance(value, str) and bool(value.strip())

    def object_value(value, label):
        require(isinstance(value, dict), f"{label} must be an object")
        return value if isinstance(value, dict) else {}

    def text_list(value, label, allow_empty=False):
        require(isinstance(value, list), f"{label} must be a list")
        values = value if isinstance(value, list) else []
        require(allow_empty or bool(values), f"{label} cannot be empty")
        require(all(text(item) for item in values), f"{label} requires non-empty text entries")
        return [item for item in values if text(item)]

    def collection(name, identifier_key):
        raw = data.get(name)
        require(isinstance(raw, list) and bool(raw), f"{name} must be a non-empty list")
        result = {}
        for index, value in enumerate(raw if isinstance(raw, list) else []):
            item = object_value(value, f"{name}[{index}]")
            identifier = item.get(identifier_key)
            if not isinstance(identifier, str) or not IDENTIFIER.fullmatch(identifier):
                errors.append(f"{name}[{index}] has an invalid {identifier_key}")
                continue
            require(identifier not in result, f"Duplicate {identifier_key}: {identifier}")
            result[identifier] = item
        return result

    def references(values, known, label, allow_empty=True):
        require(isinstance(values, list), f"{label} must be a list")
        values = values if isinstance(values, list) else []
        require(allow_empty or bool(values), f"{label} cannot be empty")
        for value in values:
            require(isinstance(value, str) and value in known, f"{label} unknown reference: {value}")
        return [value for value in values if isinstance(value, str) and value in known]

    def reachable(start, graph, blocked=None):
        visited = set()
        pending = [start]
        while pending:
            current = pending.pop()
            if current == blocked or current in visited or current not in graph:
                continue
            visited.add(current)
            pending.extend(graph[current])
        return visited

    if not isinstance(data, dict):
        return ["Blueprint must be a JSON object"]
    schema_version = data.get("schema_version")
    require(schema_version in ("1.0", "1.1", "1.2", "1.3"),
            "schema_version must be 1.0, 1.1, 1.2 or 1.3")
    integrated_design = schema_version in ("1.1", "1.2", "1.3")
    if opening_design:
        complete_design = True
        require(integrated_design, "Opening design checks require schema 1.1, 1.2 or 1.3")
    if learning_design:
        complete_design = True
        require(schema_version in ("1.2", "1.3"),
                "Learning design checks require schema 1.2 or 1.3")
    if instructional_cycle:
        learning_design = True
        complete_design = True
        require(schema_version in ("1.2", "1.3"),
                "Instructional cycle checks require schema 1.2 or 1.3")
    if full_course:
        complete_design = True
        learning_design = True
        require(schema_version == "1.3",
                "Full-course coverage checks require schema 1.3")
    if complete_design or ready_media:
        require(integrated_design,
                "Complete design requires schema 1.1, 1.2 or 1.3 with opening and integrated evaluation")
    identifier = data.get("course_identifier")
    require(isinstance(identifier, str) and bool(IDENTIFIER.fullmatch(identifier)),
            "Invalid course_identifier")
    for key in ("course_title", "course_version", "completion_policy"):
        require(text(data.get(key)), f"{key} must be non-empty text")

    sources = collection("sources", "source_identifier")
    objectives = collection("learning_objectives", "objective_identifier")
    media = collection("media_resources", "resource_identifier")
    scenes = collection("scenes", "scene_identifier")
    if integrated_design:
        require(text(data.get("learning_core")), "learning_core must state the core learning ability")
        opening = object_value(data.get("opening"), "opening")
        opening_scene = opening.get("scene_identifier")
        require(isinstance(opening_scene, str) and opening_scene in scenes,
                "opening missing a valid scene_identifier")
        require(opening_scene == data.get("entry_scene_identifier"),
                "opening must describe the main entry scene")
        for key in ("background_input", "prior_knowledge_connection", "motivating_problem",
                    "learner_role", "first_action", "transition", "understanding_check"):
            require(text(opening.get(key)), f"opening missing {key}")
    required_objectives = set()
    for identifier, source in sources.items():
        for key in ("title", "location", "version"):
            require(text(source.get(key)), f"{identifier} missing {key}")
        status = source.get("verification_status")
        require(isinstance(status, str) and status in {"provided", "verified"},
                f"{identifier} invalid verification_status")
    for identifier, objective in objectives.items():
        require(text(objective.get("statement")), f"{identifier} missing statement")
        require(isinstance(objective.get("required"), bool), f"{identifier} required must be boolean")
        refs = references(objective.get("source_identifiers"), sources, identifier, False)
        if integrated_design:
            text_list(objective.get("success_criteria"), f"{identifier}.success_criteria")
            text_list(objective.get("anticipated_difficulties"), f"{identifier}.anticipated_difficulties")
        if objective.get("required") is True:
            required_objectives.add(identifier)
            if ready_media:
                for source_identifier in refs:
                    require(sources[source_identifier].get("verification_status") == "verified",
                            f"{identifier} source not verified: {source_identifier}")
    require(bool(required_objectives), "At least one objective must be required")

    for identifier, resource in media.items():
        media_type = resource.get("media_type")
        role = resource.get("teaching_role")
        require(isinstance(media_type, str) and media_type in MEDIA_TYPES,
                f"{identifier} invalid media_type")
        require(isinstance(role, str) and role in TEACHING_ROLES,
                f"{identifier} invalid teaching_role")
        require(isinstance(resource.get("required"), bool), f"{identifier} required must be boolean")
        status = resource.get("production_status")
        require(isinstance(status, str) and status in {"planned", "ready"},
                f"{identifier} invalid production_status")
        if media_type == "panorama":
            require(role == "macro_narrative", f"{identifier} panorama must support macro_narrative")
            require(text(resource.get("projection")), f"{identifier} panorama missing projection")
        if role == "progression":
            require(media_type in {"video", "three_dimensional", "diagram"},
                    f"{identifier} progression requires video, three_dimensional or diagram")
        if role == "macro_narrative":
            require(media_type == "panorama", f"{identifier} macro_narrative requires panorama")
        needs_file = resource.get("production_status") == "ready"
        if ready_media and resource.get("required") is True:
            require(needs_file, f"{identifier} required media is not ready")
        if needs_file:
            file_path = resource.get("file_path")
            require(text(file_path), f"{identifier} ready media missing file_path")
            if text(file_path):
                parsed = urlparse(file_path)
                if parsed.scheme == "file" and parsed.netloc in {"", "localhost"}:
                    path = Path(unquote(parsed.path))
                elif not parsed.scheme:
                    path = Path(file_path)
                    path = path if path.is_absolute() else base_directory / path
                else:
                    errors.append(f"{identifier} ready media requires a verified local file")
                    continue
                require(path.is_file(), f"{identifier} media file does not exist: {file_path}")

    graph = {}
    teaching = set()
    practice = set()
    transfer = set()
    task_identifiers = set()
    tasks = {}
    for identifier, scene in scenes.items():
        kind = scene.get("kind")
        require(isinstance(kind, str) and kind in SCENE_KINDS, f"{identifier} invalid kind")
        require(isinstance(scene.get("required"), bool), f"{identifier} required must be boolean")
        for key in ("title", "narration"):
            require(text(scene.get(key)), f"{identifier} missing {key}")
        objective_refs = references(scene.get("objective_identifiers"), objectives, identifier)
        media_refs = references(scene.get("media_resource_identifiers"), media, identifier)
        if kind == "macro":
            require(any(media[value].get("media_type") == "panorama" for value in media_refs),
                    f"{identifier} macro scene requires panorama media")
        teaching_kinds = {"macro", "instruction"} if integrated_design else {"introduction", "macro", "instruction"}
        if isinstance(kind, str) and kind in teaching_kinds and scene.get("required") is True:
            teaching.update(objective_refs)
        task = scene.get("task")
        edges = []
        if task is not None:
            task = object_value(task, f"{identifier}.task")
            task_identifier = task.get("task_identifier")
            require(isinstance(task_identifier, str) and bool(IDENTIFIER.fullmatch(task_identifier)),
                    f"{identifier} invalid task_identifier")
            if isinstance(task_identifier, str):
                require(task_identifier not in task_identifiers,
                        f"Duplicate task_identifier: {task_identifier}")
                task_identifiers.add(task_identifier)
                tasks[task_identifier] = {
                    "task": task,
                    "scene": scene,
                    "objectives": objective_refs
                }
            require(text(task.get("prompt")), f"{identifier} missing task prompt")
            response_type = task.get("response_type")
            require(isinstance(response_type, str) and response_type in RESPONSE_TYPES,
                    f"{identifier} invalid response_type")
            pedagogical_role = task.get("pedagogical_role")
            if integrated_design:
                require(isinstance(pedagogical_role, str) and pedagogical_role in PEDAGOGICAL_ROLES,
                        f"{identifier} invalid pedagogical_role")
                for key in ("cognitive_action", "learning_evidence", "removal_cost"):
                    require(text(task.get(key)), f"{identifier} task missing {key}")
                if pedagogical_role == "independent_assessment":
                    require(kind == "transfer",
                            f"{identifier} independent_assessment requires a transfer scene")
                if kind == "transfer":
                    require(pedagogical_role == "independent_assessment",
                            f"{identifier} transfer must contain independent_assessment")
            evaluation = object_value(task.get("evaluation"), f"{identifier}.evaluation")
            feedback = object_value(task.get("feedback"), f"{identifier}.feedback")
            recovery = object_value(task.get("recovery"), f"{identifier}.recovery")
            for key in ("expected_result", "explanation"):
                require(text(evaluation.get(key)), f"{identifier} evaluation missing {key}")
            for key in ("success", "needs_help"):
                require(text(feedback.get(key)), f"{identifier} feedback missing {key}")
            hints = recovery.get("hints")
            require(isinstance(hints, list) and bool(hints) and all(text(v) for v in hints),
                    f"{identifier} recovery needs non-empty hints")
            require(text(recovery.get("explanation")), f"{identifier} recovery missing explanation")
            require(recovery.get("retry_available") is True, f"{identifier} retry must be available")
            outcomes = object_value(task.get("outcomes"), f"{identifier}.outcomes")
            for key in ("success", "needs_help"):
                require(key in outcomes, f"{identifier} outcomes missing {key}")
            edges = list(outcomes.values())
            require(outcomes.get("success") != identifier,
                    f"{identifier}: atomic task success must advance to another scene; "
                    "model substeps as distinct scenes")
            if "continue_after_review" in outcomes and "outcome_conditions" in task:
                conditions = object_value(task["outcome_conditions"],
                                          f"{identifier}.outcome_conditions")
                required_conditions = conditions.get("continue_after_review")
                require(isinstance(required_conditions, list) and
                        "attempt_saved" in required_conditions and
                        "feedback_viewed" in required_conditions,
                        f"{identifier}: continue_after_review requires attempt_saved and feedback_viewed")
            require(scene.get("next_scene_identifier") is None,
                    f"{identifier} task paths must use outcomes only")
            practice_role_valid = not integrated_design or (
                isinstance(pedagogical_role, str) and pedagogical_role in PRACTICE_ROLES
            )
            if scene.get("required") is True and kind == "practice" and practice_role_valid:
                practice.update(objective_refs)
            if scene.get("required") is True and kind == "transfer" and (
                    not integrated_design or pedagogical_role == "independent_assessment"):
                transfer.update(objective_refs)
        else:
            if isinstance(kind, str) and kind in {"practice", "transfer"}:
                errors.append(f"{identifier} {kind} requires a task")
            target = scene.get("next_scene_identifier")
            if kind != "summary":
                require(isinstance(target, str), f"{identifier} missing next_scene_identifier")
            elif target is not None:
                errors.append(f"{identifier} summary must end the main learning flow")
            edges = [target] if target is not None else []
        if kind == "summary" and task is not None:
            errors.append(f"{identifier} summary cannot contain a main-flow task")
        graph[identifier] = references(edges, scenes, f"{identifier} outcome paths")

    entry = data.get("entry_scene_identifier")
    summary = data.get("summary_scene_identifier")
    require(isinstance(entry, str) and entry in scenes, "Invalid entry_scene_identifier")
    require(isinstance(summary, str) and summary in scenes, "Invalid summary_scene_identifier")
    if integrated_design and isinstance(entry, str) and entry in scenes:
        require(scenes[entry].get("required") is True, "Opening entry scene must be required")
    if isinstance(summary, str) and summary in scenes:
        require(scenes[summary].get("kind") == "summary", "Summary scene must have kind summary")
    if isinstance(entry, str) and isinstance(summary, str):
        visited = reachable(entry, graph)
        for identifier, scene in scenes.items():
            require(identifier in visited, f"Scene unreachable from entry: {identifier}")
            require(summary in reachable(identifier, graph), f"Scene cannot reach summary: {identifier}")
            if scene.get("required") is True and identifier not in {entry, summary}:
                require(summary not in reachable(entry, graph, blocked=identifier),
                        f"Main flow can bypass required scene: {identifier}")
        # Follow correct results only; a help route must not rescue a correct-answer cycle.
        correct_graph = {}
        for scene_identifier, scene in scenes.items():
            task = scene.get("task")
            outcomes = task.get("outcomes", {}) if isinstance(task, dict) else {}
            destination = outcomes.get("success") if isinstance(outcomes, dict) else None
            if task is None:
                destination = scene.get("next_scene_identifier")
            correct_graph[scene_identifier] = (
                [destination] if isinstance(destination, str) and destination in scenes else [])
        for scene_identifier in scenes:
            require(summary in reachable(scene_identifier, correct_graph),
                    f"{scene_identifier}: consecutive correct outcomes cannot reach summary")
    for identifier in sorted(required_objectives):
        require(identifier in teaching, f"Required objective missing teaching: {identifier}")
        require(identifier in practice, f"Required objective missing practice: {identifier}")
        require(identifier in transfer, f"Required objective missing transfer check: {identifier}")
    if integrated_design:
        plan = object_value(data.get("evaluation_plan"), "evaluation_plan")
        evaluations = plan.get("objective_evaluations")
        require(isinstance(evaluations, list) and bool(evaluations),
                "evaluation_plan needs non-empty objective_evaluations")
        evaluated_objectives = set()
        for index, raw in enumerate(evaluations if isinstance(evaluations, list) else []):
            label = f"evaluation_plan.objective_evaluations[{index}]"
            evaluation = object_value(raw, label)
            objective_identifier = evaluation.get("objective_identifier")
            require(isinstance(objective_identifier, str) and objective_identifier in objectives,
                    f"{label} unknown objective_identifier")
            if not isinstance(objective_identifier, str) or objective_identifier not in objectives:
                continue
            require(objective_identifier not in evaluated_objectives,
                    f"Duplicate objective evaluation: {objective_identifier}")
            evaluated_objectives.add(objective_identifier)
            for key in ("evidence", "independent_success_rule"):
                require(text(evaluation.get(key)), f"{label} missing {key}")
            if schema_version in ("1.2", "1.3"):
                for key in ("rubric_reference", "assessment_conditions"):
                    require(text(evaluation.get(key)), f"{label} missing {key}")
            for key, required_kind, allowed_roles in (
                    ("practice_task_identifiers", "practice", PRACTICE_ROLES),
                    ("independent_task_identifiers", "transfer", {"independent_assessment"})):
                task_refs = references(evaluation.get(key), tasks, f"{label}.{key}", False)
                for task_identifier in task_refs:
                    linked = tasks[task_identifier]
                    linked_scene = linked["scene"]
                    role = linked["task"].get("pedagogical_role")
                    require(objective_identifier in linked["objectives"],
                            f"{label}.{key} task does not cover objective: {task_identifier}")
                    require(linked_scene.get("required") is True and
                            linked_scene.get("kind") == required_kind and
                            isinstance(role, str) and role in allowed_roles,
                            f"{label}.{key} invalid teaching role or scene: {task_identifier}")
        for identifier in sorted(required_objectives):
            require(identifier in evaluated_objectives,
                    f"Required objective missing evaluation plan: {identifier}")
        for phase in ("design_review", "learner_trial", "learning_effectiveness"):
            phase_plan = object_value(plan.get(phase), f"evaluation_plan.{phase}")
            status = phase_plan.get("status")
            require(isinstance(status, str) and status in EVALUATION_STATUSES,
                    f"evaluation_plan.{phase} invalid status")
            require(text(phase_plan.get("method")), f"evaluation_plan.{phase} missing method")
            text_list(phase_plan.get("evidence_references"),
                      f"evaluation_plan.{phase}.evidence_references",
                      allow_empty=status != "completed")
        record_fields = text_list(plan.get("record_fields"), "evaluation_plan.record_fields")
        for field in sorted(RECORD_FIELDS):
            require(field in record_fields, f"evaluation_plan.record_fields missing {field}")
    if schema_version in ("1.2", "1.3"):
        errors.extend(validate_learning_design(data, sources, objectives, scenes, tasks, required_objectives))
    if full_course or (schema_version == "1.3" and isinstance(data.get("scope_coverage"), dict)):
        errors.extend(validate_scope_coverage(data, sources, objectives, scenes))
    declared_instruction = data.get("instructional_design")
    if instructional_cycle or (
            schema_version in ("1.2", "1.3") and isinstance(declared_instruction, dict) and
            INSTRUCTIONAL_EXTENSION_FIELDS.intersection(declared_instruction)):
        errors.extend(validate_instructional_cycle(
            data, objectives, scenes, tasks, required_objectives, graph))
    declared_opening = data.get("opening")
    if opening_design or (integrated_design and isinstance(declared_opening, dict) and
                          OPENING_EXTENSION_FIELDS.intersection(declared_opening)):
        errors.extend(validate_opening(data, scenes, tasks, media, graph))
    if complete_design:
        for field in placeholder_paths(data):
            errors.append(f"{field}: unfilled template or TBD marker")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("blueprint", help="JSON file, or - to read JSON from stdin")
    parser.add_argument("--base-directory", type=Path, default=Path.cwd(),
                        help="Resolve stdin media paths relative to this directory")
    parser.add_argument("--complete-design", action="store_true")
    parser.add_argument("--ready-media", action="store_true")
    parser.add_argument("--learning-design", action="store_true",
                        help="Require schema 1.2 or 1.3 and complete knowledge, instruction and formative plans")
    parser.add_argument("--opening-design", action="store_true",
                        help="Require complete opening contract, entry context and pre-task declarations")
    parser.add_argument("--instructional-cycle", action="store_true",
                        help="Require whole-task, demonstration, practice, application and reflection plans")
    parser.add_argument("--full-course", action="store_true",
                        help="Require schema 1.3 and complete source-to-content-to-Beat coverage")
    args = parser.parse_args()
    try:
        if args.blueprint == "-":
            data = json.load(sys.stdin)
            base = args.base_directory
        else:
            path = Path(args.blueprint)
            data = json.loads(path.read_text(encoding="utf-8"))
            base = path.resolve().parent
        errors = validate(data, base, args.complete_design or args.ready_media,
                          args.ready_media, args.learning_design, args.opening_design,
                          args.instructional_cycle, args.full_course)
    except (OSError, ValueError) as exc:
        errors = [str(exc)]
    for message in errors:
        print(f"ERROR: {message}")
    if errors:
        print(f"FAIL: {len(errors)} structural or readiness error(s)")
        return 1
    print("PASS: blueprint structure and requested readiness checks")
    opening = data.get("opening") if isinstance(data, dict) else None
    if isinstance(data, dict) and data.get("schema_version") in {"1.1", "1.2", "1.3"} and \
            isinstance(opening, dict) and not OPENING_EXTENSION_FIELDS.intersection(opening):
        print("LEGACY OPENING: original fields checked; new opening design contract not evaluated.")
    instruction = data.get("instructional_design") if isinstance(data, dict) else None
    if isinstance(data, dict) and data.get("schema_version") in {"1.2", "1.3"} and \
            isinstance(instruction, dict) and \
            not INSTRUCTIONAL_EXTENSION_FIELDS.intersection(instruction):
        print("LEGACY INSTRUCTION: original fields checked; instructional cycle contract not evaluated.")
    print("Content, media quality, browser behavior and learning outcomes require separate review.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
