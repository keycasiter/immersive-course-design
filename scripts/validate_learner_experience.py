#!/usr/bin/env python3
"""Lint learner-facing blueprint copy for generic shells and leaked internal workflow language."""

import argparse
import json
from pathlib import Path
import sys


LEAKED_WORKFLOW_PHRASES = (
    "继续核查", "进入核查", "核查完成", "全部核查完成",
    "继续验证", "进入验证", "验证完成",
    "进入证据收集", "证据收集完成", "目标状态",
    "任务完成", "完成任务",
)
GENERIC_FRAMING_TERMS = (
    "审核台", "观察台", "实验台", "工作台", "控制台",
    "指挥中心", "研究中心", "调度中心",
)
VISIBLE_PAGE_SECTIONS = {
    "可审阅线框", "开篇信息与首任务开放", "状态与自然文案",
}


def learner_copy(blueprint):
    values = []

    def add(path, value):
        if isinstance(value, str) and value.strip():
            values.append((path, value))

    add("course_title", blueprint.get("course_title"))
    opening = blueprint.get("opening") if isinstance(blueprint.get("opening"), dict) else {}
    for key in (
        "course_introduction", "background_input", "motivating_problem",
        "learner_role", "first_action", "transition", "understanding_check",
    ):
        add(f"opening.{key}", opening.get(key))
    orientation = opening.get("orientation_bootstrap")
    if isinstance(orientation, dict):
        for key in (
            "host_welcome", "minimal_world_model", "key_objects_and_terms",
            "learning_journey_preview", "role_and_collaboration",
            "first_action_handoff", "comprehension_safeguard",
        ):
            add(f"opening.orientation_bootstrap.{key}", orientation.get(key))
    for index, scene in enumerate(blueprint.get("scenes", [])):
        if not isinstance(scene, dict):
            continue
        add(f"scenes[{index}].title", scene.get("title"))
        add(f"scenes[{index}].narration", scene.get("narration"))
        task = scene.get("task")
        if not isinstance(task, dict):
            continue
        add(f"scenes[{index}].task.prompt", task.get("prompt"))
        feedback = task.get("feedback")
        if isinstance(feedback, dict):
            add(f"scenes[{index}].task.feedback.success", feedback.get("success"))
            add(f"scenes[{index}].task.feedback.needs_help", feedback.get("needs_help"))
        recovery = task.get("recovery")
        if isinstance(recovery, dict):
            add(f"scenes[{index}].task.recovery.explanation", recovery.get("explanation"))
            for hint_index, hint in enumerate(recovery.get("hints", [])):
                add(f"scenes[{index}].task.recovery.hints[{hint_index}]", hint)
    return values


def parse_exceptions(entries):
    exceptions = {}
    for entry in entries:
        term, separator, reason = entry.partition("=")
        if not separator or not term.strip() or not reason.strip():
            raise ValueError(
                "--allow-framing must use TERM=RATIONALE with a non-empty rationale"
            )
        exceptions[term.strip()] = reason.strip()
    return exceptions


def validate(blueprint, exceptions):
    errors = []
    copy = learner_copy(blueprint)
    for path, value in copy:
        for phrase in LEAKED_WORKFLOW_PHRASES:
            if phrase in value:
                errors.append(
                    f"{path}: learner-facing copy leaks internal workflow phrase {phrase!r}"
                )
    framing_paths = {"course_title"}
    framing_paths.update(
        path for path, _ in copy
        if path.endswith(".title") or path.endswith(".host_welcome")
    )
    for path, value in copy:
        if path not in framing_paths:
            continue
        for term in GENERIC_FRAMING_TERMS:
            if term in value and term not in exceptions:
                errors.append(
                    f"{path}: generic framing term {term!r} requires "
                    f"--allow-framing '{term}=<authentic task rationale>'"
                )
    return errors


def visible_page_copy(markdown):
    """Return copy from registered learner-visible sections and explicit markers."""
    visible = []
    in_fence = False
    in_explicit_region = False
    active_section = None
    for line_number, line in enumerate(markdown.splitlines(), start=1):
        stripped = line.strip()
        if stripped == "<!-- learner-visible-copy:start -->":
            in_explicit_region = True
            continue
        if stripped == "<!-- learner-visible-copy:end -->":
            in_explicit_region = False
            continue
        if stripped.startswith("#"):
            heading = stripped.lstrip("#").strip()
            active_section = heading if heading in VISIBLE_PAGE_SECTIONS else None
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        table_content = stripped.replace("|", "").replace("-", "").replace(":", "").strip()
        is_visible_table_row = (
            active_section is not None and stripped.startswith("|") and bool(table_content)
        )
        if stripped and (in_fence or in_explicit_region or is_visible_table_row):
            visible.append((f"page_design.line_{line_number}", line))
    return visible


def validate_page(markdown, exceptions):
    errors = []
    for path, value in visible_page_copy(markdown):
        for phrase in LEAKED_WORKFLOW_PHRASES:
            if phrase in value:
                errors.append(
                    f"{path}: learner-facing wireframe leaks internal workflow phrase {phrase!r}"
                )
        for term in GENERIC_FRAMING_TERMS:
            if term in value and term not in exceptions:
                errors.append(
                    f"{path}: generic framing term {term!r} requires "
                    f"--allow-framing '{term}=<authentic task rationale>'"
                )
    return errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("blueprint")
    parser.add_argument("--page-design")
    parser.add_argument(
        "--allow-framing", action="append", default=[], metavar="TERM=RATIONALE"
    )
    arguments = parser.parse_args()
    try:
        exceptions = parse_exceptions(arguments.allow_framing)
        blueprint = json.loads(Path(arguments.blueprint).read_text(encoding="utf-8"))
        page_design = (
            Path(arguments.page_design).read_text(encoding="utf-8")
            if arguments.page_design else None
        )
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"ERROR: {error}")
        return 2
    errors = validate(blueprint, exceptions)
    if page_design is not None:
        errors.extend(validate_page(page_design, exceptions))
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        print(f"FAIL: {len(errors)} learner-experience language issue(s)")
        return 1
    page_coverage = (
        "blueprint registered fields"
        + ("; page-design fenced copy, registered visible-section tables, and explicit "
           "learner-visible-copy regions" if page_design is not None else "")
    )
    print(
        "PASS: learner-facing copy avoids generic shells and hard internal workflow "
        f"language; scanned {page_coverage}"
    )
    if exceptions:
        print("Contextual framing exceptions:")
        for term, reason in exceptions.items():
            print(f"- {term}: {reason}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
