"""Isolated synthetic evidence builders, never real course/human approval records."""

import copy
import json
from pathlib import Path

from validate_production import file_digest
from demo_contract import GATE_BY_KIND, runtime_fingerprints, COMMON_PATHS, JUDGMENT_PATHS, workflow_state

ROOT = Path(__file__).resolve().parents[1]

def install_content_quality(data, base, blueprint):
    """Five candidates per objective with file-bound synthetic review, only in regression."""
    from validate_content_quality import content_fingerprint, SCORES
    content = json.loads((ROOT / "assets/content-design-quality.template.json").read_text())
    content["course_version"] = data["course_version"]
    content["core_objective_identifiers"] = [
        row["objective_identifier"] for row in blueprint["learning_objectives"]]
    content["source_identifiers"] = [row["source_identifier"] for row in blueprint["sources"]]
    template = content["content_candidates"][0]
    content["content_candidates"], content["selected_candidate_ids"] = [], []
    for objective in content["core_objective_identifiers"]:
        for i, problem_type in enumerate(("observation", "explanation", "decision", "repair", "transfer")):
            candidate = copy.deepcopy(template)
            candidate.update(candidate_id=f"{objective}_candidate_{i}", objective_identifier=objective,
                             problem_type=problem_type, grade_band="Synthetic grade",
                             source_boundary=content["source_identifiers"],
                             quality_scores={key: 4 for key in SCORES},
                             quality_decision="content_approved")
            content["content_candidates"].append(candidate)
        content["selected_candidate_ids"].append(f"{objective}_candidate_1")
    reference = "quality_teacher_review"
    review_path = Path(base) / "quality-teacher-review.txt"
    review_path.write_text("SYNTHETIC regression record; never an actual teacher approval.")
    snapshot = {"reference_identifier": reference, "path": review_path.name,
                "content_sha256": file_digest(review_path)}
    content["content_review"] = {
        "status": "approved", "review_owner": "Synthetic teacher",
        "reviewed_version": data["course_version"],
        "reviewed_content_sha256": content_fingerprint(content),
        "reviewed_at": "2026-11-05T00:00:00Z",
        "evidence_references": [reference], "evidence_files": [snapshot],
    }
    quality_path = Path(base) / "content-design-quality.json"
    quality_path.write_text(json.dumps(content))
    data["evidence_files"] = [row for row in data["evidence_files"]
                              if row["reference_identifier"] not in {"content_quality", reference}]
    for key, kind, path in (("content_quality", "content_design_quality", quality_path),
                            (reference, "content_review", review_path)):
        data["evidence_files"].append({
            "reference_identifier": key, "kind": kind, "path": path.name,
            "course_version": data["course_version"], "content_sha256": file_digest(path),
            "bound_identifiers": content["core_objective_identifiers"]})
    data["content_design"] = {
        "reference_identifier": "content_quality", "experience_design_mode": content["experience_design_mode"],
        "status": "content_approved", "selected_candidate_ids": content["selected_candidate_ids"],
        "quality_review_evidence_references": [reference]}
    return content


def sync_workflow(data):
    subjects = {row["scope_identifier"]: row for row in data["approval_subjects"]}
    records = {row["confirmation_identifier"]: row
               for gate in data["approval_gates"].values() for row in gate["confirmations"]}
    active = {}
    for event in data["status_history"]:
        if event["event_type"] == "reconfirm":
            for identifier in event["confirmation_identifiers"]:
                active[records[identifier]["scope_identifier"]] = records[identifier]
        elif event["event_type"] == "invalidate":
            invalid = set(event["scope_identifiers"])
            while True:
                expanded = invalid | {key for key, row in subjects.items()
                                      if invalid.intersection(row["depends_on_scope_identifiers"])}
                if expanded == invalid:
                    break
                invalid = expanded
            active = {key: row for key, row in active.items() if key not in invalid}
    from production_contract import STAGES
    rank = STAGES.index(data["current_status"])
    data["workflow_state"] = workflow_state(data, active, subjects, rank)
    for kind in ("clarification", "demo"):
        data["approval_gates"][GATE_BY_KIND[kind]]["status"] = (
            "confirmed" if any(subjects[key]["kind"] == kind for key in active) else "pending")


def install_runtime(data, base, formal=False):
    """Create structurally valid runtime/evidence fixtures with actual local bytes."""
    prefix = "formal" if formal else "demo"
    base = Path(base)
    version = data["course_version"]
    references = {key: prefix + "_" + key for key in
                  ("entry", "source", "event_map", "knowledge_matrix", "browser", "visual_gate")}
    runtime = {
        "contract_version": "1.0", "course_version": version,
        "runtime_mode": "video_clock" if formal else "storyboard_events",
        "runtime_version": "synthetic_1", "event_graph_version": "synthetic_1",
        "entry_reference": references["entry"], "source_reference": references["source"],
        "event_map_reference": references["event_map"],
        "knowledge_matrix_reference": references["knowledge_matrix"],
        "browser_evidence_reference": references["browser"],
        "visual_gate_reference": references["visual_gate"],
        "bound_asset_identifiers": [],
    }
    data["runtime_delivery" if formal else "demo_runtime"] = runtime
    def register(reference, kind, value, suffix=".json"):
        path = base / (reference + suffix)
        path.write_text(json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value)
        existing = next((row for row in data["evidence_files"]
                         if row["reference_identifier"] == reference), None)
        row = {"reference_identifier": reference, "kind": kind, "path": path.name,
               "course_version": version, "content_sha256": file_digest(path),
               "bound_identifiers": data["work_scope"]["covered_objective_identifiers"]}
        if existing is None:
            data["evidence_files"].append(row)
        else:
            existing.update(row)
        return path
    beats = data["experience_profile"]["beat_identifiers"]
    events = []
    for beat in beats:
        events.append({"beat_id": beat, "storyboard_asset_identifier": "diagram_core",
                       "return_event_identifier": beat, "event_class": "judgment",
                       "evidence_required": True, "interaction_id": "interaction_core",
                       "on_incomplete_close": "retain_draft_block_progression"})
    event_map = {"schema_version": "1.2", "runtime_mode": "storyboard_events",
                 "event_graph_version": runtime["event_graph_version"],
                 "approved_beat_ids": beats, "events": events}
    html = (ROOT / "assets/storyboard-demo.template.html").read_text()
    html = html.replace("{{与独立文件相同的完整事件JSON}}", json.dumps(event_map))
    import re
    html = re.sub(r"\{\{.*?\}\}", "Synthetic test content", html)
    html = html.replace('src="runtime.js"', f'src="{references["source"]}.js"')
    source = (ROOT / "assets/storyboard-runtime.template.js").read_text()
    if formal:
        event_map.update(schema_version="1.0", runtime_mode="video_clock", duration_seconds=10,
                         resource_admission={
                             "course_entry": {"checks": ["decode"], "failure_policy": "retry_or_block"},
                             "event_entry": {"checks": ["decode"], "failure_policy": "retry_or_block",
                                             "degraded_path": False}})
        for index, event in enumerate(events):
            event.update(cue_seconds=index, pause_seconds=index, resume_seconds=index,
                         resume_state={}, required_asset_identifiers=["video_introduction"],
                         retry_policy={"on_exhausted": "block_progression"})
        html = html.replace('data-runtime-mode="storyboard_events"', 'data-runtime-mode="video_clock"')
        html = re.sub(r'(<script id="video-event-map" type="application/json">).*?(</script>)',
                      lambda match: match[1] + json.dumps(event_map) + match[2], html)
        html = html.replace('<figure id="storyboard-frame">',
                            '<video id="course-video" data-media-clock="course"><source src="sound.mp4"></video>'
                            '<figure id="storyboard-frame">')
        source += '\nconst video = document.getElementById("course-video");\n'
        source += 'video.addEventListener("timeupdate", () => video.currentTime);\n'
        source += 'video.addEventListener("seeking", () => video.currentTime);\n'
    html_path = register(references["entry"], "runtime_entry", html, ".html")
    source_path = register(references["source"], "runtime_source", source, ".js")
    register(references["event_map"], "runtime_event_map", event_map)
    template_asset = copy.deepcopy(next(row for row in data["assets"] if row["kind"] == "diagram"))
    template_asset.update(asset_identifier=prefix + "_runtime", kind="runtime", status="accepted",
                          required=True, files=[{"path": html_path.name}, {"path": source_path.name}])
    template_asset["governance"]["privacy_review_status"] = "reviewed"
    template_asset["accessibility"]["status"] = "accepted"
    template_asset["acceptance"] = {
        "asset_version": template_asset["asset_version"],
        "file_snapshots": [{"path": path.name, "content_sha256": file_digest(path)}
                           for path in (html_path, source_path)],
        "checks": ["decodable", "content_correct", "continuity", "equivalent_path"],
        "evidence_references": ["verification"],
    }
    data["assets"].append(template_asset)
    data["work_scope"]["covered_asset_identifiers"].append(template_asset["asset_identifier"])
    runtime["bound_asset_identifiers"] = [
        row["asset_identifier"] for row in data["assets"]
        if row["required"] and (formal or row["kind"] != "linear_video")]
    register(prefix + "_content_review", "content_review", "Synthetic reviewer record", ".txt")
    matrix = json.loads((ROOT / "assets/knowledge-surface-matrix.template.json").read_text())
    def fill(value):
        if isinstance(value, str):
            return re.sub(r"\{\{.*?\}\}", "Synthetic criterion", value)
        if isinstance(value, list):
            return [fill(item) for item in value]
        if isinstance(value, dict):
            return {key: fill(item) for key, item in value.items()}
        return value
    matrix = fill(matrix)
    matrix.update(course_version=version)
    row = matrix["rows"][0]
    for key, value in list(row.items()):
        if isinstance(value, str) and "{{" in value:
            row[key] = "Synthetic criterion"
    row["demo_status"] = "implemented"
    row["content_review"].update(owner="Synthetic human", status="approved",
                                 reviewed_version=version, evidence_reference=prefix + "_content_review")
    tests = []
    artifact_path = register(prefix + "_operations", "operation_log", "Synthetic operation record", ".txt")
    artifact = {"kind": "operation_log", "path": artifact_path.name,
                "content_sha256": file_digest(artifact_path)}
    for viewport in ("desktop", "narrow"):
        for category in sorted(JUDGMENT_PATHS):
            identifier = f"{prefix}_{category}_{viewport}"
            row["browser_test_identifiers"].append(identifier)
            tests.append({
                "test_identifier": identifier, "status": "passed", "path_category": category,
                "viewport_class": viewport, "viewport": {"width": 390 if viewport == "narrow" else 1440,
                                                        "height": 900},
                "browser": "Synthetic browser", "captured_at": "2026-11-05T00:00:00Z",
                "entry_action": "Synthetic steps", "expected_result": "Synthetic expectation",
                "observed_result": "Synthetic observed state", "beat_identifiers": list(beats),
                "objective_identifiers": ["objective_core"], "knowledge_object_identifiers": ["knowledge_core"],
                "runtime_locator": copy.deepcopy(row["runtime_locator"]), "artifacts": [artifact],
            })
        if formal:
            for category in ("media_timing", "hotspot_timing", "caption_sync", "return_state",
                             "responsive_layout", "accessibility"):
                extra = copy.deepcopy(tests[-1])
                extra.update(test_identifier=f"formal_{category}_{viewport}", path_category=category)
                tests.append(extra)
    register(references["knowledge_matrix"], "knowledge_surface_matrix", matrix)
    fingerprints = runtime_fingerprints(data, base, runtime)
    browser = {"contract_version": "1.0", "course_version": version,
               "runtime_mode": runtime["runtime_mode"], "runtime_fingerprints": fingerprints, "tests": tests}
    register(references["browser"], "browser_execution", browser)
    gate = json.loads((ROOT / "assets/video-led-visual-gate.template.json").read_text())
    gate.update(course_version=version, status="passed", runtime_fingerprints=fingerprints, decorations=[], evidence=[],
                runtime_file_snapshots=[
                    {"reference_identifier": reference,
                     "path": next(item["path"] for item in data["evidence_files"]
                                  if item["reference_identifier"] == reference),
                     "content_sha256": digest}
                    for reference, digest in fingerprints["evidence"].items()
                ])
    for state in gate["states"]:
        state.update(evidence_status="passed", evidence_references=[])
        for viewport in ("desktop", "narrow"):
            identifier = f"{prefix}_visual_{state['state_identifier']}_{viewport}"
            state["evidence_references"].append(identifier)
            gate["evidence"].append({
                "evidence_identifier": identifier, "state_identifier": state["state_identifier"],
                "status": "passed", "viewport": "390x900" if viewport == "narrow" else "1440x900",
                "viewport_class": viewport, "browser": "Synthetic browser", "entry_action": "Synthetic entry",
                "result": "Synthetic result", "captured_at": "2026-11-05T00:00:00Z",
                "course_version": version, "runtime_fingerprints": fingerprints,
                "artifact": artifact,
            })
    register(references["visual_gate"], "video_led_visual_gate", gate)
    sync_workflow(data)
    return runtime
