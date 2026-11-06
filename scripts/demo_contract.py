"""Executable clarification, Demo and current runtime evidence contracts."""

import json
import re
from pathlib import Path
import subprocess
import sys

GATE_BY_KIND = {
    "design": "design_confirmation",
    "media_contract": "media_sample_confirmation",
    "media_sample": "media_sample_confirmation",
    "clarification": "clarification_confirmation",
    "demo": "demo_confirmation",
}
COMMON_PATHS = {"normal", "close_return", "refresh_recovery", "replay",
                "keyboard", "touch", "accessible_equivalent"}
JUDGMENT_PATHS = COMMON_PATHS | {"incorrect", "help", "revision"}


def require_human(c, value, label):
    c.text(value, label)
    c.need(not isinstance(value, str) or not re.search(
        r"\b(agent|script|generator|bot|assistant|codex|chatgpt)\b|机器人|脚本|生成器|智能体",
        value, re.I), f"{label}: explicit Agent/script self-signature is not human confirmation")


def workflow_state(data, active, subjects, rank):
    kinds = {subjects[key].get("kind") for key in active}
    if "clarification" not in kinds:
        return "clarification_in_progress"
    if rank < 1:
        return "design_draft"
    if "demo" not in kinds:
        return "demo_in_progress" if data.get("demo_runtime") or data.get("demo_delivery") else "design_confirmed"
    if rank < 3:
        return "demo_accepted"
    return data["current_status"]


def validate_workflow(c, data, subjects, active, rank, evidence):
    by_kind = {kind: {key for key, row in subjects.items() if row.get("kind") == kind}
               for kind in GATE_BY_KIND}
    for kind in ("clarification", "demo"):
        c.need(len(by_kind[kind]) == 1, f"workflow requires exactly one {kind} approval subject")
    clarification = c.obj(data.get("clarification"), "clarification")
    c.need(isinstance(clarification.get("confirmation_basis"), str) and
           clarification["confirmation_basis"] in {
        "sufficient_explicit_input", "user_summary_confirmed"},
        "clarification.confirmation_basis must identify actual user authorization")
    c.need(clarification.get("unresolved_decision_identifiers") == [],
           "clarification has unresolved design-changing decisions")
    intake = clarification.get("intake_reference")
    c.need(isinstance(intake, str) and evidence.get(intake, {}).get("kind") == "clarification_intake",
           "clarification requires registered clarification_intake evidence")
    for key, subject in subjects.items():
        kind = subject.get("kind")
        dependencies = set(c.strings(subject.get("depends_on_scope_identifiers"), f"{key}.dependencies"))
        if kind == "design":
            c.need(by_kind["clarification"].issubset(dependencies),
                   f"{key}: design must depend on clarification")
        if kind == "demo":
            c.need((by_kind["clarification"] | by_kind["design"]).issubset(dependencies),
                   f"{key}: Demo must depend on clarification and all design scopes")
        if kind in {"clarification", "demo"}:
            for field in ("scope_identifier", "subject_version", "scope"):
                c.text(subject.get(field), f"{key}.{field}")
            covered = c.strings(subject.get("covered_identifiers"), f"{key}.covered_identifiers", False)
            c.need(set(covered) == set(c.strings(
                data["work_scope"].get("covered_objective_identifiers"), "workflow objectives", False)),
                f"{key}: checkpoint must cover the whole scoped objective set")
            materials = c.rows(subject.get("materials"), f"{key}.materials",
                               empty=kind == "demo")
            for material in materials:
                c.need(material.get("source") == "evidence_file" and
                       material.get("fingerprint_mode") == "bytes",
                       f"{key}: checkpoint materials must bind evidence file bytes")
                c.need(material.get("reference_identifier") in evidence,
                       f"{key}: unknown checkpoint material")
            if kind == "clarification":
                c.need(any(row.get("reference_identifier") == intake for row in materials),
                       f"{key}: clarification must bind its intake")
            c.need(subject.get("editorial_changes") == [],
                   f"{key}: checkpoint changes require invalidate/reconfirm")
    if rank >= 1 or data.get("demo_runtime") or data.get("demo_delivery"):
        c.need(by_kind["clarification"].issubset(active),
               "Demo/design requires active clarification confirmation")
    if data.get("demo_runtime"):
        c.need(rank >= 1, "Demo runtime requires design_confirmed")
    if data.get("demo_delivery"):
        c.need(rank >= 1, "Demo walkthrough requires design_confirmed")
    if by_kind["demo"].intersection(active) and \
            data["work_scope"]["learner_delivery_type"] != "interactive_web":
        validate_non_web_demo(c, data, evidence, subjects[next(iter(by_kind["demo"]))]["subject_version"])
    if rank >= 3:
        c.need(by_kind["demo"].issubset(active) and bool(by_kind["demo"]),
               "production requires active Demo confirmation")
    if data.get("delivery_endpoint") == "interaction_complete_prototype" and \
            data.get("acceptance_status") == "accepted":
        c.need(bool(by_kind["demo"]) and by_kind["demo"].issubset(active),
               "accepted Demo requires active demo_confirmation")
        for key in by_kind["demo"] & active.keys():
            record = active[key]
            acceptance = c.obj(data.get("acceptance_evidence"), "acceptance_evidence")
            c.need(acceptance.get("confirmation_identifier") == record.get("confirmation_identifier"),
                   "Demo acceptance must reference its active confirmation")
            c.need(acceptance.get("review_owner") == record.get("confirmed_by"),
                   "Demo acceptance owner differs from confirmation")
    expected = workflow_state(data, active, subjects, rank)
    c.need(data.get("workflow_state") == expected, f"workflow_state must be replay-derived {expected}")


def load_evidence(c, evidence, reference, kind, version=None):
    entry = evidence.get(reference, {}) if isinstance(reference, str) else {}
    c.need(bool(entry) and entry.get("kind") == kind, f"{kind}: missing or wrong evidence kind: {reference}")
    if not entry:
        return {}
    if version is not None:
        c.need(entry.get("course_version") == version, f"{reference}: outdated evidence version")
    c.matches(entry.get("path"), entry.get("content_sha256"), str(reference))
    try:
        return json.loads(c.path(entry.get("path")).read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError) as exc:
        c.need(False, f"{reference}: cannot read JSON evidence: {exc}")
        return {}


def runtime_fingerprints(data, base, runtime):
    """Actual bytes of the runtime, matrix and its declared asset dependencies."""
    from validate_production import file_digest
    evidence = {row["reference_identifier"]: row for row in data["evidence_files"]}
    assets = {row["asset_identifier"]: row for row in data["assets"]}
    def resolve(path):
        return Path(path) if Path(path).is_absolute() else Path(base) / path
    references = [runtime[key] for key in (
        "entry_reference", "source_reference", "event_map_reference", "knowledge_matrix_reference")]
    if runtime.get("presentation_reference"):
        references.append(runtime["presentation_reference"])
    return {
        "evidence": {reference: file_digest(resolve(evidence[reference]["path"]))
                     for reference in references},
        "assets": {identifier: {
            "asset_version": assets[identifier]["asset_version"],
            "files": [{"path": row["path"], "content_sha256": file_digest(resolve(row["path"]))}
                      for row in assets[identifier]["files"]],
        } for identifier in runtime["bound_asset_identifiers"]},
    }


def demo_fingerprint_payload(data, base):
    """Keep the accepted Demo separate from the later formal video runtime."""
    evidence = {row["reference_identifier"]: row for row in data["evidence_files"]}
    from validate_production import file_digest
    def digest(reference):
        path = Path(evidence[reference]["path"])
        return file_digest(path if path.is_absolute() else Path(base) / path)
    if data["work_scope"]["learner_delivery_type"] != "interactive_web":
        delivery = data["demo_delivery"]
        return {"delivery": delivery, "files": {
            key: digest(delivery[key]) for key in ("content_reference", "walkthrough_reference")
        }}
    runtime = data["demo_runtime"]
    return {
        "runtime": runtime, "completion": data["demo_completion"],
        "runtime_fingerprints": runtime_fingerprints(data, base, runtime),
        "browser_sha256": digest(runtime["browser_evidence_reference"]),
        "visual_gate_sha256": digest(runtime["visual_gate_reference"])
            if runtime.get("visual_gate_reference") else None,
    }


def validate_runtime_delivery(data, base, formal=None):
    from production_contract import Checks
    from validate_production import file_digest
    from validate_video_led_runtime import validate_storyboard_runtime
    c = Checks(base)
    if formal is None:
        formal = data.get("current_status") in {
            "production_complete", "functional_accepted", "learner_trial_complete", "effect_evaluated"}
    runtime = c.obj(data.get("runtime_delivery" if formal else "demo_runtime"), "runtime_delivery")
    c.need(runtime.get("contract_version") == "1.0", "runtime_delivery.contract_version must be 1.0")
    mode = runtime.get("runtime_mode")
    c.need(isinstance(mode, str) and mode in {"storyboard_events", "video_clock"},
           "runtime_mode must be storyboard_events or video_clock")
    if formal:
        c.need(mode == "video_clock", "formal video runtime requires video_clock; storyboard evidence is not media acceptance")
    version = runtime.get("course_version")
    c.text(version, "runtime_delivery.course_version")
    if formal or data.get("delivery_endpoint") == "interaction_complete_prototype":
        c.need(version == data.get("course_version"), "runtime delivery version differs from current course")
    for key in ("runtime_version", "event_graph_version"):
        c.text(runtime.get(key), f"runtime_delivery.{key}")
    evidence = {row.get("reference_identifier"): row for row in
                c.rows(data.get("evidence_files"), "evidence_files")
                if isinstance(row.get("reference_identifier"), str)}
    entry_text = source_text = ""
    runtime_paths = set()
    for key, kind, suffixes in (
        ("entry_reference", "runtime_entry", {".html"}),
        ("source_reference", "runtime_source", {".js", ".ts", ".jsx", ".tsx"}),
    ):
        reference = runtime.get(key)
        item = evidence.get(reference, {}) if isinstance(reference, str) else {}
        c.need(item.get("kind") == kind, f"runtime requires {kind} evidence")
        c.need(item.get("course_version") == version, f"{kind}: outdated evidence version")
        c.matches(item.get("path"), item.get("content_sha256"), kind)
        try:
            path = c.path(item.get("path"))
            c.need(path.suffix.lower() in suffixes, f"{kind}: requires actual runtime file")
            text = path.read_text(encoding="utf-8")
            c.need(bool(text.strip()), f"{kind}: empty runtime file")
            runtime_paths.add(path.resolve())
            if key == "entry_reference":
                entry_text = text
            else:
                source_text = text
        except (OSError, ValueError) as exc:
            c.need(False, f"{kind}: {exc}")
    event_map = load_evidence(c, evidence, runtime.get("event_map_reference"), "runtime_event_map", version)
    event_map = c.obj(event_map, "runtime_event_map")
    import re
    presentation_required = bool(re.search(r'data-atmosphere=["\']synchronized["\']|data-presentation-anchor=', entry_text))
    c.need(not presentation_required or bool(runtime.get("presentation_reference")),
           "marked atmosphere/anchor runtime requires presentation_reference")
    presentation = None
    if runtime.get("presentation_reference"):
        from validate_video_presentation import validate as presentation_check, validate_bound_video
        presentation_reference = runtime["presentation_reference"]
        c.text(presentation_reference, "presentation_reference")
        presentation_reference = presentation_reference if isinstance(presentation_reference, str) else ""
        presentation = c.obj(load_evidence(c, evidence, presentation_reference,
                                           "video_presentation_contract", version), "presentation contract")
        c.need(mode == "video_clock", "real presentation binding requires video_clock; storyboard is not frame timing")
        assets = {row.get("asset_identifier"): row for row in c.rows(data.get("assets"), "assets")
                  if isinstance(row.get("asset_identifier"), str)}
        profile = c.obj(data.get("experience_profile"), "experience_profile")
        c.errors.extend(presentation_check(presentation, set(assets),
                                          set(c.strings(profile.get("beat_identifiers"), "presentation Beats"))))
        c.need(presentation.get("duration_seconds") == event_map.get("duration_seconds"),
               "presentation/event-map duration differs")
        main_identifier = presentation.get("main_video_asset_identifier")
        main = assets.get(main_identifier, {}) if isinstance(main_identifier, str) else {}
        c.need(main.get("kind") == "linear_video", "presentation main asset must be linear_video")
        try:
            files = c.rows(main.get("files"), "presentation main files", False)
            matched = next((c.path(row["path"]) for row in files
                            if file_digest(c.path(row["path"])) == presentation.get("main_video_sha256")), None)
            c.need(matched is not None, "presentation main video hash differs")
            if matched is not None:
                c.errors.extend(validate_bound_video(presentation, matched))
        except (KeyError, OSError, ValueError):
            c.need(False, "presentation main video file cannot be read")
        used = {main_identifier} if isinstance(main_identifier, str) else set()
        atmosphere = c.obj(presentation.get("atmosphere"), "presentation atmosphere")
        if isinstance(atmosphere, dict) and atmosphere.get("enabled"):
            for cue in c.rows(atmosphere.get("cues"), "atmosphere cues"):
                for state in c.rows(cue.get("states"), "atmosphere states"):
                    for key in ("asset_identifier", "still_asset_identifier"):
                        if isinstance(state.get(key), str):
                            used.add(state[key])
                            c.need(assets.get(state[key], {}).get("kind") == "image",
                                   "initial atmosphere adapter requires image assets")
        c.need(used.issubset(c.strings(runtime.get("bound_asset_identifiers"), "presentation bound assets")),
               "runtime asset fingerprints omit presentation dependencies")
        for track in c.rows(presentation.get("anchors"), "presentation anchors"):
            c.need(any(row.get("beat_id") == track.get("beat_identifier") for row in c.rows(event_map.get("events"), "events")),
                   "presentation anchor Beat is absent from event map")
        if presentation.get("anchors"):
            from validate_scene_interaction_plan import validate_plan
            plans = [row for row in evidence.values() if row.get("kind") == "scene_interaction_plan"]
            referenced = set()
            for row in plans:
                plan = c.obj(load_evidence(c, evidence, row["reference_identifier"],
                                          "scene_interaction_plan", version), "participation plan")
                c.errors.extend(validate_plan(plan, event_map, presentation, presentation_reference))
                for event in c.rows(plan.get("events"), "participation events"):
                    anchor = c.obj(event.get("scene_anchor"), "participation scene anchor")
                    reference = anchor.get("presentation_anchor_reference")
                    if isinstance(reference, str):
                        referenced.add(reference)
            expected = {presentation_reference + "#" + track["identifier"]
                        for track in c.rows(presentation.get("anchors"), "presentation anchors")
                        if isinstance(track.get("identifier"), str)}
            c.need(expected.issubset(referenced), "presentation anchors lack participation-plan references")
    c.need(event_map.get("runtime_mode", "video_clock") == mode, "runtime/event map mode differs")
    c.need(event_map.get("event_graph_version") == runtime.get("event_graph_version"),
           "event graph version differs")
    if mode == "storyboard_events":
        c.errors.extend(validate_storyboard_runtime(event_map, entry_text, source_text))
    elif mode == "video_clock":
        try:
            result = subprocess.run([
                sys.executable, str(Path(__file__).with_name("validate_video_led_runtime.py")),
                str(c.path(evidence[runtime["event_map_reference"]]["path"])),
                str(c.path(evidence[runtime["entry_reference"]]["path"])),
                str(c.path(evidence[runtime["source_reference"]]["path"])),
            ], capture_output=True, text=True, timeout=30)
            c.need(result.returncode == 0, "video_clock structural binding failed: " + result.stdout.strip())
        except (OSError, KeyError, ValueError, subprocess.SubprocessError) as exc:
            c.need(False, f"video_clock check failed: {exc}")
    matrix = c.obj(load_evidence(c, evidence, runtime.get("knowledge_matrix_reference"),
                                "knowledge_surface_matrix", version), "knowledge matrix")
    from contract_checks import placeholder_paths
    c.errors.extend(f"knowledge matrix {path}: unfilled template" for path in placeholder_paths(matrix))
    c.need(matrix.get("course_version") == version, "knowledge matrix course version differs")
    c.need(matrix.get("matrix_version") == "1.1", "knowledge matrix version must be 1.1")
    matrix_rows = c.rows(matrix.get("rows"), "knowledge matrix rows", False)
    assets = {row.get("asset_identifier"): row for row in c.rows(data.get("assets"), "assets")
              if isinstance(row.get("asset_identifier"), str)}
    bound = set(c.strings(runtime.get("bound_asset_identifiers"), "runtime bound assets", False))
    needed = {key for key, row in assets.items() if row.get("required") is True and
              row.get("delivery_class") == "formal" and (formal or row.get("kind") != "linear_video")}
    if not formal:
        needed.update(data.get("demo_completion", {}).get("video_replacement_contract", {}).get(
            "substitute_asset_identifiers", []))
    c.need(needed.issubset(bound), "runtime bindings omit required assets")
    runtime_files = set()
    for identifier in bound:
        asset = assets.get(identifier, {})
        c.need(asset.get("status") == "accepted", f"runtime dependency must be accepted: {identifier}")
        if asset.get("kind") == "runtime":
            for row in c.rows(asset.get("files"), f"{identifier}.files", False):
                try:
                    runtime_files.add(c.path(row.get("path")).resolve())
                except ValueError:
                    pass
    c.need(runtime_paths.issubset(runtime_files) and bool(runtime_paths),
           "runtime entry/source must be files of accepted runtime assets")
    try:
        fingerprints = runtime_fingerprints(data, base, runtime)
    except (KeyError, OSError, ValueError, TypeError) as exc:
        c.need(False, f"runtime fingerprints unavailable: {exc}")
        fingerprints = None
    browser = c.obj(load_evidence(c, evidence, runtime.get("browser_evidence_reference"),
                                 "browser_execution", version), "browser execution")
    c.need(browser.get("contract_version") == "1.0" and browser.get("course_version") == version,
           "browser evidence contract/version differs")
    c.need(browser.get("runtime_mode") == mode, "browser evidence runtime mode differs")
    c.need(fingerprints is not None and browser.get("runtime_fingerprints") == fingerprints,
           "browser evidence is stale for runtime files/assets/matrix")
    tests = {}
    for row in c.rows(browser.get("tests"), "browser tests", False):
        identifier = row.get("test_identifier")
        c.text(identifier, "browser test identifier")
        if isinstance(identifier, str):
            c.need(identifier not in tests, "duplicate browser test identifier")
            tests[identifier] = row
        c.need(row.get("status") == "passed", f"{identifier}: browser test did not pass")
        c.need(isinstance(row.get("viewport_class"), str) and
               row.get("viewport_class") in {"desktop", "narrow"}, f"{identifier}: invalid viewport class")
        viewport = c.obj(row.get("viewport"), f"{identifier}.viewport")
        width, height = viewport.get("width"), viewport.get("height")
        c.need(type(width) is int and type(height) is int and width > 0 and height > 0 and
               ((width <= 600) == (row.get("viewport_class") == "narrow")),
               f"{identifier}: viewport dimensions differ from class")
        for key in ("browser", "captured_at", "entry_action", "expected_result", "observed_result"):
            c.text(row.get(key), f"{identifier}.{key}")
        for key in ("beat_identifiers", "objective_identifiers", "knowledge_object_identifiers"):
            c.strings(row.get(key), f"{identifier}.{key}")
        artifacts = c.rows(row.get("artifacts"), f"{identifier}.artifacts", False)
        for artifact in artifacts:
            c.need(isinstance(artifact.get("kind"), str) and
                   artifact["kind"] in {"screenshot", "trace", "operation_log"},
                   f"{identifier}: unsupported browser artifact")
            c.matches(artifact.get("path"), artifact.get("content_sha256"), f"{identifier}.artifact")
    if formal:
        for path in ("media_timing", "hotspot_timing", "caption_sync", "return_state",
                     "responsive_layout", "accessibility"):
            c.need(all(any(row.get("path_category") == path and
                               row.get("viewport_class") == viewport for row in tests.values())
                           for viewport in ("desktop", "narrow")),
                   f"formal runtime requires new media integration evidence: {path}")
    if presentation is not None:
        if presentation.get("anchors"):
            for viewport in ("desktop", "narrow"):
                c.need(any(row.get("path_category") == "anchor_projection" and
                           row.get("viewport_class") == viewport for row in tests.values()),
                       "presentation requires anchor_projection browser evidence for both viewports")
        atmosphere = presentation.get("atmosphere", {})
        if isinstance(atmosphere, dict) and atmosphere.get("enabled"):
            required_actions = {"pause", "interaction", "seek", "replay", "restore", "rate_change", "background_failure"}
            for viewport in ("desktop", "narrow"):
                for motion in ("normal", "reduced"):
                    records = [row for row in tests.values() if row.get("path_category") == "atmosphere_sync" and
                               row.get("viewport_class") == viewport and row.get("motion_preference") == motion]
                    observed = set()
                    for row in records:
                        observed.update(c.strings(row.get("event_kinds"), "atmosphere event coverage"))
                    c.need(required_actions.issubset(observed),
                           "presentation atmosphere evidence omits viewport/motion/recovery actions")
    for index, row in enumerate(matrix_rows):
        label = f"matrix[{index}]"
        for key in ("knowledge_object_id", "objective_identifier", "beat_id", "interaction_id",
                    "success_criteria", "input_contract", "feedback_contract", "help_contract",
                    "revision_contract", "return_state", "accessibility_equivalent", "learner_action"):
            c.text(row.get(key), f"{label}.{key}")
        c.need(isinstance(row.get("event_class"), str) and
               row.get("event_class") in {"observation", "exploration", "judgment"},
               f"{label}: invalid event_class")
        c.need(row.get("demo_status") == "implemented", f"{label}: knowledge target not implemented")
        window = c.obj(row.get("media_cue_or_scene_window"), f"{label}.media_cue_or_scene_window")
        for key in ("entry", "pause", "resume"):
            c.text(window.get(key), f"{label}.media_cue_or_scene_window.{key}")
        for mapping in c.rows(row.get("incorrect_response_mapping"), f"{label}.incorrect_response_mapping",
                              empty=row.get("event_class") == "observation"):
            for key in ("response_id", "misconception", "feedback", "revision_action"):
                c.text(mapping.get(key), f"{label}.incorrect_response_mapping.{key}")
        locator = c.obj(row.get("runtime_locator"), f"{label}.runtime_locator")
        for key in ("page", "selector_or_component", "state_key"):
            c.text(locator.get(key), f"{label}.runtime_locator.{key}")
        review = c.obj(row.get("content_review"), f"{label}.content_review")
        require_human(c, review.get("owner"), f"{label}.content_review.owner")
        c.need(review.get("status") == "approved" and review.get("reviewed_version") == version,
               f"{label}: content review not current/approved")
        review_reference = review.get("evidence_reference")
        review_evidence = evidence.get(review_reference, {}) if isinstance(review_reference, str) else {}
        c.need(review_evidence.get("kind") == "content_review" and
               review_evidence.get("course_version") == version, f"{label}: content review evidence missing")
        c.matches(review_evidence.get("path"), review_evidence.get("content_sha256"), label + ".review")
        references = c.strings(row.get("browser_test_identifiers"), f"{label}.browser tests", False)
        required_paths = JUDGMENT_PATHS if row.get("event_class") != "observation" else COMMON_PATHS
        coverage = set()
        for reference in references:
            test = tests.get(reference, {})
            c.need(bool(test), f"{label}: unknown browser test {reference}")
            c.need(row.get("objective_identifier") in test.get("objective_identifiers", []) and
                   row.get("knowledge_object_id") in test.get("knowledge_object_identifiers", []) and
                   row.get("beat_id") in test.get("beat_identifiers", []) and
                   test.get("runtime_locator") == locator,
                   f"{label}: browser test does not bind target/Beat/runtime locator")
            if isinstance(test.get("path_category"), str) and isinstance(test.get("viewport_class"), str):
                coverage.add((test.get("path_category"), test.get("viewport_class")))
        c.need({(path, viewport) for path in required_paths for viewport in ("desktop", "narrow")}
               .issubset(coverage), f"{label}: browser evidence omits required target paths/viewports")
    if data.get("experience_profile", {}).get("profile_identifier") == "video_led_web":
        gate = c.obj(load_evidence(c, evidence, runtime.get("visual_gate_reference"),
                                  "video_led_visual_gate", version), "visual gate")
        from check_video_led_visual_gate import validate as visual_check
        c.errors.extend(visual_check(gate, c.base, fingerprints))
        c.need(gate.get("status") == "passed", "runtime requires passed visual gate")
    return c.errors


def validate_joint_demo(data, base):
    scope = data.get("work_scope", {})
    formal = data.get("current_status") in {
        "production_complete", "functional_accepted", "learner_trial_complete", "effect_evaluated"}
    if scope.get("learner_delivery_type") != "interactive_web" or not (
            formal or data.get("delivery_endpoint") == "interaction_complete_prototype"):
        return []
    from production_contract import Checks
    c = Checks(base)
    c.errors.extend(validate_runtime_delivery(data, base, formal))
    runtime = data.get("runtime_delivery" if formal else "demo_runtime", {})
    evidence = {row.get("reference_identifier"): row for row in c.rows(data.get("evidence_files"), "evidence_files")
                if isinstance(row.get("reference_identifier"), str)}
    blueprints = [row for row in evidence.values() if row.get("kind") == "course_blueprint"]
    if len(blueprints) != 1:
        return c.errors
    try:
        blueprint = json.loads(c.path(blueprints[0]["path"]).read_text(encoding="utf-8"))
        matrix = load_evidence(c, evidence, runtime.get("knowledge_matrix_reference"),
                               "knowledge_surface_matrix")
        browser = load_evidence(c, evidence, runtime.get("browser_evidence_reference"), "browser_execution")
        rows = c.rows(matrix.get("rows"), "matrix rows", False)
        objectives = {row["objective_identifier"] for row in blueprint["learning_objectives"]}
        knowledge = {row["knowledge_identifier"] for row in blueprint["knowledge_organization"]["units"]}
        sources = {row["source_identifier"] for row in blueprint["sources"]
                   if row.get("verification_status") == "verified"}
        beats = {beat for row in blueprint["scenes"] if row.get("required") is True
                 for beat in row["beat_identifiers"]}
        c.need({row.get("objective_identifier") for row in rows} == objectives,
               "knowledge matrix must cover exactly scoped blueprint objectives")
        c.need({row.get("knowledge_object_id") for row in rows} == knowledge,
               "knowledge matrix must cover exactly blueprint knowledge targets")
        for row in rows:
            c.need(row.get("beat_id") in beats, "knowledge matrix references unknown/nonrequired Beat")
            c.need(set(c.strings(row.get("source_ids"), "matrix source_ids", False)).issubset(sources),
                   "knowledge matrix requires verified blueprint sources")
        tests = c.rows(browser.get("tests"), "browser tests", False)
        for beat in beats:
            c.need(all(any(test.get("path_category") == "normal" and
                               test.get("viewport_class") == viewport and
                               beat in test.get("beat_identifiers", []) for test in tests)
                           for viewport in ("desktop", "narrow")),
                   f"browser evidence omits required Beat: {beat}")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        c.need(False, f"joint Demo coverage cannot be read: {exc}")
    return c.errors


def validate_non_web_demo(c, data, evidence, version):
    """Equivalent walkthrough evidence for facilitated, linear or document deliveries."""
    delivery = c.obj(data.get("demo_delivery"), "demo_delivery")
    c.need(delivery.get("learner_delivery_type") == data["work_scope"]["learner_delivery_type"],
           "Demo walkthrough delivery type differs")
    content_reference = delivery.get("content_reference")
    content = evidence.get(content_reference, {}) if isinstance(content_reference, str) else {}
    c.need(content.get("kind") == "learner_materials" and content.get("course_version") == version,
           "non-web Demo requires version-bound learner_materials")
    c.matches(content.get("path"), content.get("content_sha256"), "Demo learner materials")
    walkthrough = c.obj(load_evidence(c, evidence, delivery.get("walkthrough_reference"),
                                      "demo_walkthrough", version), "Demo walkthrough")
    c.need(walkthrough.get("course_version") == version, "Demo walkthrough version differs")
    c.need(walkthrough.get("material_sha256") == content.get("content_sha256"),
           "Demo walkthrough material fingerprint differs")
    check_rows = c.rows(walkthrough.get("checks"), "Demo walkthrough checks", False)
    for row in check_rows:
        c.need(row.get("status") == "passed", "Demo walkthrough check has not passed")
        for key in ("objective_identifier", "path", "observed_result", "recorded_at"):
            c.text(row.get(key), f"Demo walkthrough.{key}")
        c.matches(row.get("artifact_path"), row.get("artifact_sha256"), "Demo walkthrough artifact")
    for objective in data["work_scope"]["covered_objective_identifiers"]:
        for path in ("normal", "help_revision", "return_reentry", "accessible_equivalent"):
            c.need(any(row.get("objective_identifier") == objective and row.get("path") == path
                       for row in check_rows), f"Demo walkthrough omits {objective}/{path}")
