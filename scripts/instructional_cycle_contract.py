"""Validate the optional instructional-cycle extension for schema 1.2 blueprints."""


INSTRUCTIONAL_CYCLE_VERSION = "1.0"
INSTRUCTIONAL_EXTENSION_FIELDS = {"contract_version", "whole_task"}
SEQUENCING_STRATEGIES = {"demonstration_first", "attempt_first", "mixed"}
DEMONSTRATION_DECISIONS = {"included", "not_required"}
REFLECTION_DECISIONS = {"dedicated", "embedded", "not_required"}


def validate_instructional_cycle(data, objectives, scenes, tasks, required_objectives, graph):
    """Check references and declared coverage without judging instructional quality."""
    errors = []

    def require(condition, message):
        if not condition:
            errors.append(message)

    def text(value):
        return isinstance(value, str) and bool(value.strip())

    def obj(value, label):
        require(isinstance(value, dict), f"{label} must be an object")
        return value if isinstance(value, dict) else {}

    def rows(value, label):
        require(isinstance(value, list), f"{label} must be a list")
        values = value if isinstance(value, list) else []
        require(bool(values), f"{label} cannot be empty")
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

    def reachable(start, blocked=None):
        visited = set()
        pending = [start]
        while pending:
            current = pending.pop()
            if current == blocked or current in visited or current not in graph:
                continue
            visited.add(current)
            pending.extend(graph[current])
        return visited

    instruction = obj(data.get("instructional_design"), "instructional_design")
    require(instruction.get("contract_version") == INSTRUCTIONAL_CYCLE_VERSION,
            f"instructional_design.contract_version must be {INSTRUCTIONAL_CYCLE_VERSION}")

    whole_task = obj(instruction.get("whole_task"), "instructional_design.whole_task")
    for key in ("description", "learner_output", "success_standard", "sequencing_rationale"):
        require(text(whole_task.get(key)), f"instructional_design.whole_task missing {key}")
    strategy = whole_task.get("sequencing_strategy")
    require(isinstance(strategy, str) and strategy in SEQUENCING_STRATEGIES,
            "instructional_design.whole_task invalid sequencing_strategy")
    presentation = whole_task.get("presentation_scene_identifier")
    require(isinstance(presentation, str) and presentation in scenes,
            "instructional_design.whole_task unknown presentation_scene_identifier")
    if isinstance(presentation, str) and presentation in scenes:
        require(scenes[presentation].get("required") is True,
                "instructional_design.whole_task presentation scene must be required")

    plans = instruction.get("objective_plans")
    declared = set()
    for index, plan in enumerate(rows(plans, "instructional_design.objective_plans")):
        label = f"instructional_design.objective_plans[{index}]"
        objective = plan.get("objective_identifier")
        require(isinstance(objective, str) and objective in objectives,
                f"{label} unknown objective_identifier")
        if not isinstance(objective, str) or objective not in objectives:
            continue
        require(objective not in declared, f"Duplicate instructional objective plan: {objective}")
        declared.add(objective)

        demonstration = obj(plan.get("demonstration"), f"{label}.demonstration")
        decision = demonstration.get("decision")
        require(isinstance(decision, str) and decision in DEMONSTRATION_DECISIONS,
                f"{label}.demonstration invalid decision")
        require(text(demonstration.get("rationale")), f"{label}.demonstration missing rationale")
        demo_refs = refs(demonstration.get("scene_identifiers"), scenes,
                         f"{label}.demonstration.scene_identifiers",
                         allow_empty=decision == "not_required")
        if decision == "included":
            require(text(demonstration.get("content")), f"{label}.demonstration missing content")
            for scene_identifier in demo_refs:
                scene = scenes[scene_identifier]
                require(scene.get("required") is True and
                        scene.get("kind") in {"macro", "instruction"} and
                        objective in scene.get("objective_identifiers", []),
                        f"{label}.demonstration requires a linked teaching scene: {scene_identifier}")
        elif decision == "not_required":
            require(not demo_refs, f"{label}.demonstration not_required must not list scenes")

        guided_refs = refs(plan.get("guided_practice_task_identifiers"), tasks,
                           f"{label}.guided_practice_task_identifiers")
        for task_identifier in guided_refs:
            linked = tasks[task_identifier]
            require(linked["scene"].get("required") is True and
                    linked["scene"].get("kind") == "practice" and
                    objective in linked["objectives"],
                    f"{label}.guided practice requires a linked practice task: {task_identifier}")

        independent_refs = refs(plan.get("independent_task_identifiers"), tasks,
                                f"{label}.independent_task_identifiers")
        for task_identifier in independent_refs:
            linked = tasks[task_identifier]
            require(linked["scene"].get("required") is True and
                    linked["scene"].get("kind") == "transfer" and
                    linked["task"].get("pedagogical_role") == "independent_assessment" and
                    objective in linked["objectives"],
                    f"{label}.independent application requires a linked transfer task: {task_identifier}")

        require(text(plan.get("application_conditions")), f"{label} missing application_conditions")

        reflection = obj(plan.get("articulation_and_reflection"),
                         f"{label}.articulation_and_reflection")
        reflection_decision = reflection.get("decision")
        require(isinstance(reflection_decision, str) and
                reflection_decision in REFLECTION_DECISIONS,
                f"{label}.articulation_and_reflection invalid decision")
        require(text(reflection.get("rationale")),
                f"{label}.articulation_and_reflection missing rationale")
        reflection_refs = refs(reflection.get("task_identifiers"), tasks,
                               f"{label}.articulation_and_reflection.task_identifiers",
                               allow_empty=reflection_decision == "not_required")
        if isinstance(reflection_decision, str) and \
                reflection_decision in {"dedicated", "embedded"}:
            require(text(reflection.get("prompt")),
                    f"{label}.articulation_and_reflection missing prompt")
            for task_identifier in reflection_refs:
                require(objective in tasks[task_identifier]["objectives"],
                        f"{label}.articulation task does not cover objective: {task_identifier}")
        elif reflection_decision == "not_required":
            require(not reflection_refs,
                    f"{label}.articulation_and_reflection not_required must not list tasks")

        if isinstance(presentation, str) and presentation in scenes:
            for task_identifier in guided_refs + independent_refs:
                target = tasks[task_identifier]["scene"].get("scene_identifier")
                entry = data.get("entry_scene_identifier")
                if isinstance(entry, str) and target in reachable(entry, blocked=presentation):
                    errors.append(
                        f"{label} task can be reached before whole-task presentation: {task_identifier}")

    for objective in sorted(required_objectives - declared):
        errors.append(f"Required objective missing instructional cycle plan: {objective}")
    return errors
