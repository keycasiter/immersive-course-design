#!/usr/bin/env python3
"""Check immersion review evidence/coverage, never score experience or sign acceptance."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "assets/immersion-evaluation-criteria.v2.json"
RUBRIC = ROOT / "assets/immersion-review-rubric.v2.json"
STAGES = ("design", "media_review", "controlled_runtime", "learner_trial")
ROLES = ("author_self_review", "human_review", "model_judge", "learner_observer")
CONSTRUCTS = ("orientation", "spatial_presence", "event_credibility", "narrative_engagement",
              "agency", "emotion", "attention_pacing", "continuity", "background_increment", "full_journey")
KINDS = ("video", "audio", "document", "image", "runtime_log", "learner_record")


def digest(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def read_json(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result
    return json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=unique,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError(f"nonfinite JSON: {value}")))


def text(value):
    return isinstance(value, str) and bool(value.strip()) and not re.search(r"REPLACE|\{\{", value)


def number(value):
    return type(value) in (int, float) and math.isfinite(value)


class Checker:
    def __init__(self, base):
        self.base = Path(base)
        self.errors = []
        self.catalog_hash, self.rubric_hash = digest(CATALOG), digest(RUBRIC)
        self.tasks = {row["identifier"]: row for row in read_json(CATALOG)["tasks"]}
        self.eligibility = read_json(RUBRIC)["eligibility"]
        self.files = {}

    def need(self, ok, message):
        if not ok:
            self.errors.append(message)
        return ok

    def rows(self, value, label):
        if not self.need(isinstance(value, list) and all(isinstance(row, dict) for row in value),
                         f"{label}: expected object list"):
            return []
        return value

    def strings(self, value, label, required=False):
        ok = (isinstance(value, list) and all(text(item) for item in value)
              and len(set(value)) == len(value) and (bool(value) or not required))
        self.need(ok, f"{label}: expected unique strings" + (" (nonempty)" if required else ""))
        return value if ok else []

    def index(self, rows, label, key="identifier"):
        result = {}
        for row in rows:
            value = row.get(key)
            if not self.need(text(value), f"{label}: invalid {key}"):
                continue
            self.need(value not in result, f"{label}: duplicate {key} {value}")
            result[value] = row
        return result

    def identity(self, data, label):
        self.need(data.get("schema_version") == "2.0", f"{label}: schema_version must be 2.0")
        for key, expected in (("catalog_sha256", self.catalog_hash), ("rubric_sha256", self.rubric_hash)):
            self.need(data.get(key) == expected, f"{label}: stale {key}")
        for key in ("course_identifier", "course_version"):
            self.need(text(data.get(key)), f"{label}: invalid {key}")

    def bound_file(self, ref, label):
        if not self.need(isinstance(ref, dict) and text(ref.get("path")), f"{label}: invalid file path"):
            return None
        declared = ref.get("sha256")
        if not self.need(isinstance(declared, str) and re.fullmatch("[0-9a-f]{64}", declared),
                         f"{label}: invalid sha256"):
            return None
        path = (self.base / ref["path"]).resolve()
        try:
            self.need(path.is_file() and digest(path) == declared, f"{label}: missing file or stale sha256")
            return path if path.is_file() else None
        except OSError as exc:
            self.errors.append(f"{label}: cannot read file: {exc}")
            return None

    def plan(self, data):
        self.identity(data, "plan")
        self.need(data.get("scope") in ("complete_course", "local_revision"), "plan: invalid scope")
        self.need(text(data.get("scope_description")), "plan: missing scope_description")
        units = self.index(self.rows(data.get("units"), "plan.units"), "plan.units")
        coverage = self.index(self.rows(data.get("coverage"), "plan.coverage"), "plan.coverage", "atom_identifier")
        self.need(set(coverage) == set(self.tasks), "plan: coverage must contain every catalogue identifier exactly once")
        assigned = []
        for atom, row in coverage.items():
            app = row.get("applicability")
            self.need(app in self.eligibility, f"{atom}: invalid applicability")
            self.need(text(row.get("applicability_reason")), f"{atom}: missing applicability_reason")
            ids = self.strings(row.get("unit_identifiers"), f"{atom}.unit_identifiers", app == "applicable")
            self.need(app == "applicable" or not ids, f"{atom}: inactive coverage cannot claim units")
            if data.get("scope") == "complete_course" and atom == "M18-C01-v2":
                self.need(app != "not_applicable_with_reason", "complete course cannot exclude full journey")
            for identifier in ids:
                self.need(identifier in units and units[identifier].get("atom_identifier") == atom,
                          f"{atom}: unknown/mismatched unit {identifier}")
            assigned.extend(ids)
        self.need(len(assigned) == len(set(assigned)) and set(assigned) == set(units),
                  "plan: each unit must be assigned once")
        for identifier, unit in units.items():
            atom, stage = unit.get("atom_identifier"), unit.get("evaluation_stage")
            self.need(isinstance(atom, str) and atom in self.tasks, f"{identifier}: unknown atom")
            self.need(stage in STAGES, f"{identifier}: invalid evaluation_stage")
            if isinstance(atom, str) and atom in self.tasks:
                method = self.tasks[atom]["method"]
                if method == "learner":
                    self.need(stage == "learner_trial", f"{identifier}: learner atom requires learner_trial")
                elif method == "composite":
                    self.need(stage in ("controlled_runtime", "learner_trial"), f"{identifier}: full journey requires actual run stage")
                else:
                    self.need(stage != "learner_trial", f"{identifier}: semantic review cannot stand for learner evidence")
            self.need(unit.get("construct") in CONSTRUCTS, f"{identifier}: invalid construct")
            for key in ("experience_intent", "observable_success", "observable_failure", "comparison_plan"):
                self.need(text(unit.get(key)), f"{identifier}: missing {key}")
            for key in ("element_identifiers", "scene_identifiers", "beat_identifiers", "shot_identifiers", "asset_identifiers"):
                self.strings(unit.get(key), f"{identifier}.{key}")
            self.need(bool(unit.get("scene_identifiers")) or bool(unit.get("beat_identifiers")),
                      f"{identifier}: needs scene or Beat mapping")
            self.strings(unit.get("design_decisions"), f"{identifier}.design_decisions", True)
            self.strings(unit.get("required_routes"), f"{identifier}.required_routes", True)
        return units, coverage

    def artifacts(self, rows):
        for identifier, row in self.index(rows, "artifacts").items():
            self.need(row.get("kind") in KINDS, f"{identifier}: invalid artifact kind")
            path = self.bound_file(row, identifier)
            self.files[identifier] = dict(row, resolved_path=path)
            if path and row.get("kind") in ("video", "audio"):
                duration = row.get("duration_seconds")
                self.need(number(duration) and duration > 0, f"{identifier}: invalid media duration")
                try:
                    process = subprocess.run(
                        ["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type",
                         "-of", "json", str(path)], capture_output=True, text=True, check=True, timeout=30)
                    metadata = json.loads(process.stdout)
                    actual = float(metadata["format"]["duration"])
                    expected = row["kind"]
                    self.need(any(stream.get("codec_type") == expected for stream in metadata.get("streams", [])),
                              f"{identifier}: media stream kind differs")
                    self.need(number(actual) and actual > 0 and number(duration) and abs(actual - duration) <= .05,
                              f"{identifier}: media duration differs")
                    self.files[identifier]["actual_duration"] = actual
                except (OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
                    self.errors.append(f"{identifier}: actual media probe failed: {exc}")

    def references(self, refs, label, required=False):
        rows = self.rows(refs, label)
        self.need(bool(rows) or not required, f"{label}: observation needs evidence")
        valid, keys, kinds = [], set(), set()
        for ref in rows:
            identifier, locator = ref.get("artifact_identifier"), ref.get("locator")
            if not self.need(isinstance(identifier, str) and identifier in self.files, f"{label}: unknown artifact"):
                continue
            artifact = self.files[identifier]
            if not self.need(isinstance(locator, dict), f"{label}: invalid locator"):
                continue
            path, kind = artifact["resolved_path"], locator.get("kind")
            if path is None:
                continue
            try:
                if artifact["kind"] in ("video", "audio"):
                    a, b, duration = locator.get("start_seconds"), locator.get("end_seconds"), artifact.get("actual_duration")
                    ok = kind == "time_range" and number(a) and number(b) and number(duration) and 0 <= a < b <= duration
                elif kind == "line_range":
                    a, b = locator.get("start_line"), locator.get("end_line")
                    ok = type(a) is int and type(b) is int and 1 <= a <= b <= len(path.read_text(encoding="utf-8").splitlines())
                elif kind == "json_pointer":
                    pointer = locator.get("value")
                    ok = isinstance(pointer, str) and (pointer == "" or pointer.startswith("/"))
                    value = read_json(path)
                    if ok and pointer:
                        for token in pointer.split("/")[1:]:
                            if re.search(r"~(?![01])", token):
                                raise ValueError("invalid JSON pointer escape")
                            token = token.replace("~1", "/").replace("~0", "~")
                            if isinstance(value, dict):
                                value = value[token]
                            elif isinstance(value, list) and re.fullmatch(r"0|[1-9][0-9]*", token):
                                value = value[int(token)]
                            else:
                                raise ValueError("JSON pointer cannot resolve")
                else:
                    ok = False
            except (OSError, ValueError, KeyError, IndexError, UnicodeError):
                ok = False
            self.need(ok, f"{label}: invalid/out-of-bounds locator")
            if ok:
                key = (identifier, json.dumps(locator, sort_keys=True))
                self.need(key not in keys, f"{label}: duplicate evidence locator")
                keys.add(key)
                kinds.add(artifact["kind"])
                valid.append(ref)
        return valid, kinds

    def calibrations(self, rows):
        result = self.index(rows, "calibrations")
        for identifier, row in result.items():
            self.need(row.get("status") in ("pending", "completed"), f"{identifier}: invalid calibration status")
            for key in ("reviewer_identifier", "disagreement_resolution", "limitations"):
                self.need(text(row.get(key)), f"{identifier}: missing {key}")
            self.need(row.get("reviewer_role") in ROLES, f"{identifier}: invalid reviewer_role")
            for key, expected in (("catalog_sha256", self.catalog_hash), ("rubric_sha256", self.rubric_hash)):
                self.need(row.get(key) == expected, f"{identifier}: stale {key}")
            completed = row.get("status") == "completed"
            for key in ("evidence_references", "paired_specimen_references", "independent_example_references"):
                valid, _ = self.references(row.get(key), f"{identifier}.{key}", completed)
                if key == "paired_specimen_references" and completed:
                    self.need(len(valid) >= 2, f"{identifier}: calibration needs two paired specimens")
            if completed:
                def reference_keys(values):
                    return {json.dumps(ref, sort_keys=True) for ref in values} if isinstance(values, list) else set()
                paired = reference_keys(row.get("paired_specimen_references"))
                independent = reference_keys(row.get("independent_example_references"))
                self.need(not paired & independent, f"{identifier}: independent examples overlap paired specimens")
            if row.get("reviewer_role") == "model_judge" and completed:
                self.references(row.get("authorization_reference"), f"{identifier}.authorization_reference", True)
        return result

    def packet(self, data):
        if not self.need(isinstance(data, dict), "packet: expected object"):
            return self.report({}, {}, [])
        self.identity(data, "packet")
        self.need(data.get("purpose") in ("diagnostic", "acceptance"), "packet: invalid purpose")
        plan_path = self.bound_file(data.get("plan"), "plan reference")
        units, coverage = {}, {}
        if plan_path:
            try:
                plan = read_json(plan_path)
                if self.need(isinstance(plan, dict), "plan: expected object"):
                    units, coverage = self.plan(plan)
                    for key in ("course_identifier", "course_version"):
                        self.need(plan.get(key) == data.get(key), f"packet: {key} differs from plan")
            except (OSError, ValueError) as exc:
                self.errors.append(f"plan cannot be read: {exc}")
        if self.errors:
            return self.report(units, coverage, [])
        self.artifacts(self.rows(data.get("artifacts"), "artifacts"))
        if self.errors:
            return self.report(units, coverage, [])
        calibrations = self.calibrations(self.rows(data.get("calibrations"), "calibrations"))
        records = self.index(self.rows(data.get("records"), "records"), "records")
        results, seen = [], set()
        for identifier, row in records.items():
            for key in ("atom_identifier", "catalog_sha256", "rubric_sha256", "evaluation_stage", "applicability",
                        "applicability_reason", "score", "reviewer_role", "reviewer_identifier", "artifact_sha256",
                        "time_range_or_locator", "observed_behavior", "criterion_rationale", "limitation_or_counterexample",
                        "status", "finding", "evidence_references", "observed_routes", "calibration_identifier"):
                self.need(key in row, f"{identifier}: missing {key}")
            uid = row.get("unit_identifier")
            if not self.need(isinstance(uid, str) and uid in units, f"{identifier}: unknown unit"):
                continue
            unit = units[uid]
            atom = unit["atom_identifier"]
            method = self.tasks.get(atom, {}).get("method")
            for key, expected in (("atom_identifier", atom), ("evaluation_stage", unit.get("evaluation_stage")),
                                  ("catalog_sha256", self.catalog_hash), ("rubric_sha256", self.rubric_hash),
                                  ("applicability", "applicable")):
                self.need(row.get(key) == expected, f"{identifier}: mismatched {key}")
            self.need(text(row.get("applicability_reason")), f"{identifier}: missing applicability_reason")
            role, reviewer = row.get("reviewer_role"), row.get("reviewer_identifier")
            self.need(role in ROLES and text(reviewer), f"{identifier}: invalid reviewer")
            if text(reviewer):
                identity = (uid, reviewer)
                self.need(identity not in seen, f"{identifier}: duplicate unit/reviewer")
                seen.add(identity)
            status, score, finding = row.get("status"), row.get("score"), row.get("finding")
            self.need(status in ("observed", "not_evaluated", "review_pending"), f"{identifier}: invalid status")
            observed = status == "observed"
            refs, kinds = self.references(row.get("evidence_references"), f"{identifier}.evidence", observed)
            routes = self.strings(row.get("observed_routes"), f"{identifier}.observed_routes", observed)
            required = self.strings(unit.get("required_routes"), f"{uid}.required_routes", True)
            self.need(set(routes) <= set(required), f"{identifier}: undeclared observed route")
            for key in ("observed_behavior", "criterion_rationale", "limitation_or_counterexample"):
                self.need(key in row and (text(row[key]) or not observed and row[key] is None), f"{identifier}: missing {key}")
            if refs:
                first = self.files[refs[0]["artifact_identifier"]]
                self.need(row.get("artifact_sha256") == first.get("sha256") and
                          row.get("time_range_or_locator") == refs[0]["locator"], f"{identifier}: primary evidence differs")
            else:
                self.need(row.get("artifact_sha256") is None and row.get("time_range_or_locator") is None,
                          f"{identifier}: empty evidence must have null primary binding")
            if observed:
                if method == "semantic":
                    self.need(type(score) is int and 0 <= score <= 4, f"{identifier}: semantic score must be integer 0..4")
                    expected = "contradicted" if score == 0 else "weak" if score == 1 else "established"
                    self.need(finding == expected, f"{identifier}: score/finding mismatch")
                    if type(score) is int and score >= 3:
                        self.need(len(refs) >= 2, f"{identifier}: sustained score needs two evidence locators")
                    if score == 4:
                        self.need(set(routes) == set(required), f"{identifier}: score four needs all declared routes")
                else:
                    self.need(score is None and finding in ("supported_in_observed_conditions", "not_supported", "inconclusive"),
                              f"{identifier}: learner/full journey needs separate finding and null score")
                stage = row.get("evaluation_stage")
                if stage == "learner_trial":
                    self.need("learner_record" in kinds and role == "learner_observer",
                              f"{identifier}: learner trial needs actual learner record and observer")
                if method == "composite":
                    self.need(bool(kinds & {"runtime_log", "learner_record"}), f"{identifier}: full journey needs actual trace")
                if stage == "media_review":
                    self.need(bool(kinds & {"video", "audio", "image", "runtime_log"}),
                              f"{identifier}: media review needs actual media/operation evidence")
                if stage == "controlled_runtime":
                    self.need("runtime_log" in kinds, f"{identifier}: controlled runtime needs actual trace")
                if atom in ("M13-A05", "M13-A07"):
                    self.need(bool(kinds & {"video", "audio"}), f"{identifier}: sound criterion needs actual audio/video")
            else:
                self.need(score is None and finding == status, f"{identifier}: unobserved score/finding must be null/status")
                self.need(not routes, f"{identifier}: unobserved review cannot claim routes")
            calibration_id = row.get("calibration_identifier")
            self.need("calibration_identifier" in row and (calibration_id is None or
                      isinstance(calibration_id, str) and calibration_id in calibrations),
                      f"{identifier}: unknown calibration")
            calibration = calibrations.get(calibration_id, {}) if isinstance(calibration_id, str) else {}
            if calibration:
                self.need(calibration.get("reviewer_identifier") == reviewer and calibration.get("reviewer_role") == role,
                          f"{identifier}: calibration reviewer differs")
            eligible = observed and (role == "learner_observer" and row.get("evaluation_stage") == "learner_trial" or
                        role in ("human_review", "model_judge") and calibration.get("status") == "completed")
            results.append({"identifier": identifier, "unit_identifier": uid, "status": status, "finding": finding,
                            "reviewer_role": role, "observed_routes": routes, "missing_routes": sorted(set(required) - set(routes)),
                            "acceptance_record_requirements_met": bool(eligible)})
        return self.report(units, coverage, results)

    def report(self, units, coverage, records):
        unit_results = []
        for identifier, unit in units.items():
            matching = [row for row in records if row["unit_identifier"] == identifier]
            observed = [row for row in matching if row["status"] == "observed"]
            routes = {route for row in observed for route in row["observed_routes"]}
            required = unit.get("required_routes", [])
            required = required if isinstance(required, list) and all(isinstance(x, str) for x in required) else []
            unit_results.append({"unit_identifier": identifier, "atom_identifier": unit.get("atom_identifier"),
                                 "record_identifiers": [row["identifier"] for row in matching],
                                 "has_observation": bool(observed), "missing_routes": sorted(set(required) - routes)})
        unknown = [key for key, row in coverage.items() if row.get("applicability") == "not_evaluated"]
        valid = not self.errors
        if not valid:
            for row in records:
                row["acceptance_record_requirements_met"] = False
        complete = valid and not unknown and all(row["has_observation"] and not row["missing_routes"] for row in unit_results)
        return {"schema_version": "2.0", "record_contract_status": "valid" if valid else "invalid",
                "errors": self.errors, "review_coverage_complete": complete,
                "coverage": {"unknown_applicability": unknown, "units": unit_results,
                             "missing_records": [row["unit_identifier"] for row in unit_results if not row["record_identifiers"]],
                             "not_evaluated": [row["identifier"] for row in records if row["status"] == "not_evaluated"],
                             "review_pending": [row["identifier"] for row in records if row["status"] == "review_pending"],
                             "contradicted_or_weak": [row["identifier"] for row in records if row["finding"] in ("contradicted", "weak", "not_supported")],
                             "acceptance_use_pending": [row["identifier"] for row in records if row["status"] == "observed" and not row["acceptance_record_requirements_met"]]},
                "records": records, "semantic_acceptance": "not_computed", "learner_effect": "not_computed",
                "limits": "Valid means file/record contract only. Reviewer identity, semantic observation, route execution and learner authenticity require actual review. No immersion score or signed acceptance."}


def validate(data, base):
    return Checker(base).packet(data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("packet", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        result = validate(read_json(args.packet), args.packet.resolve().parent)
    except (OSError, ValueError) as exc:
        result = {"record_contract_status": "invalid", "errors": [str(exc)],
                  "review_coverage_complete": False, "semantic_acceptance": "not_computed", "learner_effect": "not_computed"}
    encoded = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)
    if args.output:
        args.output.write_text(encoded + "\n", encoding="utf-8")
    print(encoded)
    raise SystemExit(0 if result["record_contract_status"] == "valid" else 1)


if __name__ == "__main__":
    main()
