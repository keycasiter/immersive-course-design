#!/usr/bin/env python3
"""Validate immersive-course production status and governance metadata."""

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from contract_checks import placeholder_paths


IDENTIFIER = re.compile(r"^[a-z][a-z0-9]*(?:[_-][a-z0-9]+)*$")
PLACEHOLDER = re.compile(r"\{\{.+?\}\}|\bTBD\b", re.IGNORECASE)
STATUSES = [
    "design_draft",
    "design_confirmed",
    "media_sample_confirmed",
    "production_complete",
    "functional_accepted",
    "learner_trial_complete",
    "effect_evaluated",
]
EVIDENCE_TYPES = {
    "sourced_fact", "reasoned_inference", "teaching_scenario", "unverified"
}
ASSET_STATUSES = ["planned", "draft", "ready", "accepted"]
PRIVACY_STATUSES = {"pending", "not_applicable", "reviewed"}
ACCESSIBILITY_STATUSES = {"planned", "tested", "accepted"}
SUBJECT_GATES = {
    "design": "design_confirmation",
    "media_contract": "media_sample_confirmation",
    "media_sample": "media_sample_confirmation",
}
DESIGN_COMPONENTS = {
    "learning_objectives", "teaching_content", "task_evaluation",
    "remediation", "independent_application",
}
SHA256 = re.compile(r"^[0-9a-f]{64}$")


def json_pointer(value, pointer):
    """Select an explicit JSON subtree; never silently ignore missing content."""
    if not isinstance(pointer, str) or (pointer and not pointer.startswith("/")):
        raise ValueError(f"Invalid JSON pointer: {pointer!r}")
    for token in pointer.split("/")[1:] if pointer else []:
        if re.search(r"~(?![01])", token):
            raise ValueError(f"Invalid JSON pointer escape: {pointer!r}")
        token = token.replace("~1", "/").replace("~0", "~")
        if isinstance(value, dict):
            value = value[token]
        elif isinstance(value, list) and re.fullmatch(r"0|[1-9][0-9]*", token):
            value = value[int(token)]
        else:
            raise ValueError(f"JSON pointer does not resolve: {pointer!r}")
    return value


def canonical_digest(value):
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def file_digest(path):
    checksum = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            checksum.update(chunk)
    return checksum.hexdigest()


def approval_fingerprint(data, subject, base_directory):
    """Hash current scoped content. This never creates or updates an approval."""
    evidence = {entry["reference_identifier"]: entry for entry in data["evidence_files"]}

    def resolve(path_value):
        path = Path(path_value)
        return path if path.is_absolute() else base_directory / path

    materials = []
    for material in subject["materials"]:
        source = material["source"]
        mode = material["fingerprint_mode"]
        if source not in ("manifest", "evidence_file") or mode not in ("bytes", "json"):
            raise ValueError("Invalid approval material source or fingerprint mode")
        if source == "manifest" and mode != "json":
            raise ValueError("Manifest approval material requires json mode")
        if source == "manifest":
            value = data
        else:
            path = resolve(evidence[material["reference_identifier"]]["path"])
            if mode == "bytes":
                digest = file_digest(path)
            else:
                value = json.loads(path.read_text(encoding="utf-8"))
        if mode == "json":
            pointers = material["json_pointers"]
            digest = canonical_digest([
                {"pointer": pointer, "value": json_pointer(value, pointer)}
                for pointer in pointers
            ])
        materials.append({**material, "content_sha256": digest})

    payload = {
        "course_identifier": data["course_identifier"],
        "scope_identifier": subject["scope_identifier"],
        "kind": subject["kind"],
        "subject_version": subject["subject_version"],
        "scope": subject["scope"],
        "covered_identifiers": subject["covered_identifiers"],
        "components": subject.get("components", []),
        "materials": materials,
    }
    if "depends_on_scope_identifiers" in subject:
        payload["depends_on_scope_identifiers"] = subject["depends_on_scope_identifiers"]
    if subject["kind"] == "design" and "content_design" in data:
        from validate_content_quality import manifest_content_fingerprint
        payload["content_design"] = manifest_content_fingerprint(data, base_directory)
    if subject["kind"] == "media_contract":
        payload["visual_bible"] = data["visual_bible"]
        contract = data["media_production_contract"]
        payload["media_production_contract"] = contract
        for reference_kind in ("voice", "visual"):
            payload[f"{reference_kind}_references"] = [
                {"reference_identifier": reference,
                 "content_sha256": file_digest(resolve(evidence[reference]["path"]))}
                for reference in contract[f"{reference_kind}_reference_identifiers"]
            ]
    elif subject["kind"] == "media_sample":
        sample = data["representative_sample"]
        delivery_type = data.get("work_scope", {}).get("learner_delivery_type")
        if not sample["covered_asset_identifiers"] and \
                delivery_type in ("interactive_web", "linear_media"):
            raise ValueError("Representative sample has no covered assets")
        payload["sample"] = {
            key: sample[key] for key in (
                "sample_identifier", "interaction_path", "covered_asset_identifiers")
        }
        for key in ("media_modes", "candidate_asset_versions", "risk_coverage"):
            if key in sample:
                payload["sample"][key] = sample[key]
        assets = {asset["asset_identifier"]: asset for asset in data["assets"]}
        payload["sample_files"] = []
        for identifier in sample["covered_asset_identifiers"]:
            asset = assets[identifier]
            if not asset["files"]:
                raise ValueError(f"Sample asset has no files: {identifier}")
            payload["sample_files"].append({
                "asset_identifier": identifier,
                "files": [
                    {**entry, "content_sha256": file_digest(resolve(entry["path"]))}
                    for entry in asset["files"]
                ],
            })
        payload["sample_evidence"] = [
            {
                "reference_identifier": reference,
                "content_sha256": file_digest(resolve(evidence[reference]["path"])),
            }
            for reference in sample.get("acceptance_evidence_references", [])
        ]
    elif subject["kind"] == "demo":
        from demo_contract import demo_fingerprint_payload
        payload["demo_delivery"] = demo_fingerprint_payload(data, base_directory)
    return canonical_digest(payload)


def validate(data, base_directory, allow_placeholders=False, allow_missing_files=False):
    if isinstance(data, dict) and "work_scope" in data:
        from production_contract import validate_contract
        return validate_contract(data, base_directory, allow_placeholders,
                                 allow_missing_files, validate_structure)
    return ["Manifest must use the current production-manifest structure"]


def validate_structure(data, base_directory, allow_placeholders=False, allow_missing_files=False):
    errors = []

    def require(condition, message):
        if not condition:
            errors.append(message)

    def text(value):
        return isinstance(value, str) and bool(value.strip())

    def obj(value, label):
        require(isinstance(value, dict), f"{label} must be an object")
        return value if isinstance(value, dict) else {}

    def items(value, label, allow_empty=False):
        require(isinstance(value, list), f"{label} must be a list")
        result = value if isinstance(value, list) else []
        require(allow_empty or bool(result), f"{label} cannot be empty")
        return result

    if not isinstance(data, dict):
        return ["Manifest must be a JSON object"]

    identifier = data.get("course_identifier")
    require(isinstance(identifier, str) and bool(IDENTIFIER.fullmatch(identifier)),
            "Invalid course_identifier")
    require(text(data.get("course_version")), "course_version must be non-empty text")

    current_status = data.get("current_status")
    require(current_status in STATUSES, "Invalid current_status")
    current_index = STATUSES.index(current_status) if current_status in STATUSES else 0
    history = items(data.get("status_history"), "status_history")
    history_statuses = [
        entry.get("status") for entry in history if isinstance(entry, dict)
    ]
    require(history_statuses == STATUSES[:current_index + 1],
            "status_history must be the exact non-skipping prefix through current_status")

    evidence_files = {}
    for index, raw in enumerate(items(data.get("evidence_files"), "evidence_files")):
        entry = obj(raw, f"evidence_files[{index}]")
        reference = entry.get("reference_identifier")
        require(isinstance(reference, str) and bool(IDENTIFIER.fullmatch(reference)),
                f"evidence_files[{index}] has invalid reference_identifier")
        if isinstance(reference, str):
            require(reference not in evidence_files, f"Duplicate evidence reference: {reference}")
            evidence_files[reference] = entry
        require(text(entry.get("kind")), f"evidence_files[{index}] missing kind")
        path_value = entry.get("path")
        require(text(path_value), f"evidence_files[{index}] missing path")
        if text(path_value):
            path = Path(path_value)
            path = path if path.is_absolute() else base_directory / path
            if not allow_missing_files:
                require(path.is_file(), f"Evidence file does not exist: {path_value}")

    def evidence_refs(value, label, allow_empty=False):
        refs = items(value, label, allow_empty)
        for reference in refs:
            require(isinstance(reference, str) and reference in evidence_files,
                    f"{label} unknown evidence reference: {reference}")

    for index, raw in enumerate(history):
        entry = obj(raw, f"status_history[{index}]")
        require(text(entry.get("recorded_at")), f"status_history[{index}] missing recorded_at")
        evidence_refs(entry.get("evidence_references"),
                      f"status_history[{index}].evidence_references")

    learner = obj(data.get("learner_profile"), "learner_profile")
    for key in ("prior_knowledge", "device_and_context", "accessibility_needs", "unknowns"):
        values = items(learner.get(key), f"learner_profile.{key}")
        require(all(text(value) for value in values),
                f"learner_profile.{key} requires non-empty text entries")
    require(text(learner.get("language")), "learner_profile.language must be non-empty")

    registry = items(data.get("evidence_registry"), "evidence_registry")
    seen_evidence = set()
    for index, raw in enumerate(registry):
        entry = obj(raw, f"evidence_registry[{index}]")
        evidence_identifier = entry.get("evidence_identifier")
        require(isinstance(evidence_identifier, str) and
                bool(IDENTIFIER.fullmatch(evidence_identifier)),
                f"evidence_registry[{index}] has invalid evidence_identifier")
        if isinstance(evidence_identifier, str):
            require(evidence_identifier not in seen_evidence,
                    f"Duplicate evidence identifier: {evidence_identifier}")
            seen_evidence.add(evidence_identifier)
        evidence_type = entry.get("type")
        require(isinstance(evidence_type, str) and evidence_type in EVIDENCE_TYPES,
                f"evidence_registry[{index}] has invalid type")
        require(text(entry.get("statement")), f"evidence_registry[{index}] missing statement")
        sources = items(entry.get("source_references"),
                        f"evidence_registry[{index}].source_references", True)
        if evidence_type == "sourced_fact":
            require(bool(sources), f"{evidence_identifier} sourced_fact needs source_references")
        if isinstance(evidence_type, str) and evidence_type in {"reasoned_inference", "teaching_scenario"}:
            require(text(entry.get("basis")), f"{evidence_identifier} needs basis")
        if evidence_type == "unverified":
            require(text(entry.get("follow_up")), f"{evidence_identifier} needs follow_up")

    gates = obj(data.get("approval_gates"), "approval_gates")
    for key, required_index in (
            ("design_confirmation", 1), ("media_sample_confirmation", 2)):
        gate = obj(gates.get(key), f"approval_gates.{key}")
        expected_confirmed = current_index >= required_index
        expected_status = "confirmed" if expected_confirmed else "pending"
        require(gate.get("status") == expected_status,
                f"approval_gates.{key}.status must be {expected_status}")

    visual_bible = obj(data.get("visual_bible"), "visual_bible")
    require(text(visual_bible.get("style_goal")), "visual_bible.style_goal is required")
    for key in ("character_references", "environment_references",
                "camera_and_composition", "exclusions"):
        values = items(visual_bible.get(key), f"visual_bible.{key}")
        require(all(text(value) for value in values),
                f"visual_bible.{key} requires non-empty text entries")
    evidence_refs(visual_bible.get("evidence_references"),
                  "visual_bible.evidence_references")

    sample = obj(data.get("representative_sample"), "representative_sample")
    require(text(sample.get("sample_identifier")),
            "representative_sample.sample_identifier is required")
    require(text(sample.get("selection_reason")),
            "representative_sample.selection_reason is required")
    path = items(sample.get("interaction_path"), "representative_sample.interaction_path")
    require(all(text(value) for value in path),
            "representative_sample.interaction_path requires non-empty entries")
    sample_assets = items(sample.get("covered_asset_identifiers"),
                          "representative_sample.covered_asset_identifiers", True)
    if current_index >= 2:
        delivery_type = data.get("learner_delivery_type")
        require(
            bool(sample_assets) or
            delivery_type in ("facilitated_instruction", "print_or_document"),
            "Confirmed representative sample must cover assets unless delivery uses "
            "a representative implementation or document walkthrough",
        )
        evidence_refs(sample.get("acceptance_evidence_references"),
                      "representative_sample.acceptance_evidence_references")

    assets = {}
    for index, raw in enumerate(items(data.get("assets"), "assets")):
        asset = obj(raw, f"assets[{index}]")
        asset_identifier = asset.get("asset_identifier")
        require(isinstance(asset_identifier, str) and
                bool(IDENTIFIER.fullmatch(asset_identifier)),
                f"assets[{index}] has invalid asset_identifier")
        if isinstance(asset_identifier, str):
            require(asset_identifier not in assets, f"Duplicate asset: {asset_identifier}")
            assets[asset_identifier] = asset
        require(text(asset.get("kind")), f"{asset_identifier} missing kind")
        require(isinstance(asset.get("required"), bool), f"{asset_identifier} required must be boolean")
        require(text(asset.get("teaching_role")), f"{asset_identifier} missing teaching_role")
        status = asset.get("status")
        require(status in ASSET_STATUSES, f"{asset_identifier} invalid status")

        provenance = obj(asset.get("provenance"), f"{asset_identifier}.provenance")
        governance = obj(asset.get("governance"), f"{asset_identifier}.governance")
        accessibility = obj(asset.get("accessibility"), f"{asset_identifier}.accessibility")
        acceptance = obj(asset.get("acceptance"), f"{asset_identifier}.acceptance")
        for field in ("origin", "tool_and_model", "prompt_or_process_reference"):
            require(text(provenance.get(field)), f"{asset_identifier}.provenance missing {field}")
        items(provenance.get("source_assets"), f"{asset_identifier}.provenance.source_assets", True)
        for field in ("rights_basis", "learner_disclosure", "retention"):
            require(text(governance.get(field)), f"{asset_identifier}.governance missing {field}")
        require(isinstance(governance.get("privacy_review_status"), str) and
                governance.get("privacy_review_status") in PRIVACY_STATUSES,
                f"{asset_identifier} invalid privacy_review_status")
        for field in ("learning_goal", "equivalent_path"):
            require(text(accessibility.get(field)),
                    f"{asset_identifier}.accessibility missing {field}")
        require(isinstance(accessibility.get("status"), str) and
                accessibility.get("status") in ACCESSIBILITY_STATUSES,
                f"{asset_identifier} invalid accessibility status")

        files = items(asset.get("files"), f"{asset_identifier}.files", True)
        if isinstance(status, str) and status in {"ready", "accepted"}:
            require(bool(files), f"{asset_identifier} {status} asset needs files")
            for file_index, file_entry in enumerate(files):
                file_obj = obj(file_entry, f"{asset_identifier}.files[{file_index}]")
                file_path = file_obj.get("path")
                require(text(file_path), f"{asset_identifier} file missing path")
                if text(file_path):
                    resolved = Path(file_path)
                    resolved = resolved if resolved.is_absolute() else base_directory / resolved
                    if not allow_missing_files:
                        require(resolved.is_file(),
                                f"{asset_identifier} file does not exist: {file_path}")
        if status == "accepted":
            checks = items(acceptance.get("checks"), f"{asset_identifier}.acceptance.checks")
            require(all(text(value) for value in checks),
                    f"{asset_identifier}.acceptance.checks needs text")
            evidence_refs(acceptance.get("evidence_references"),
                          f"{asset_identifier}.acceptance.evidence_references")
            require(isinstance(governance.get("privacy_review_status"), str) and
                    governance.get("privacy_review_status") in {"not_applicable", "reviewed"},
                    f"{asset_identifier} accepted asset needs privacy review")
            require(accessibility.get("status") == "accepted",
                    f"{asset_identifier} accepted asset needs accepted equivalent path")
        if asset.get("kind") == "linear_video":
            delivery = obj(asset.get("delivery"), f"{asset_identifier}.delivery")
            if delivery.get("formal_linear_video") is True and status == "accepted":
                for field in ("embedded_voice", "environment_and_action_audio",
                              "separate_web_audio_stems", "separate_branch_audio"):
                    require(delivery.get(field) is True,
                            f"{asset_identifier} accepted formal video requires {field}=true")

    for asset_identifier in sample_assets:
        require(isinstance(asset_identifier, str) and asset_identifier in assets,
                f"representative_sample unknown asset: {asset_identifier}")
    if current_index >= 3:
        for asset_identifier, asset in assets.items():
            if asset.get("required") is True:
                require(asset.get("status") == "accepted",
                        f"production_complete requires accepted asset: {asset_identifier}")

    contract = obj(data.get("media_production_contract"), "media_production_contract")
    for key in ("voice_rules", "lip_synchronization_rules", "continuity_rules",
                "equivalent_path_rules"):
        require(text(contract.get(key)), f"media_production_contract missing {key}")
    require(isinstance(contract.get("voice_present"), bool),
            "media_production_contract.voice_present must be boolean")
    evidence_refs(contract.get("voice_reference_identifiers"),
                  "media_production_contract.voice_reference_identifiers", True)
    evidence_refs(contract.get("visual_reference_identifiers"),
                  "media_production_contract.visual_reference_identifiers", True)
    if current_index >= 0:
        if current_index >= 2 and contract.get("voice_present") is True:
            require(bool(contract.get("voice_reference_identifiers")),
                    "Confirmed media contract with voices requires actual voice references")

        subjects = {}
        subject_kinds = set()
        for index, raw in enumerate(items(data.get("approval_subjects"), "approval_subjects")):
            label = f"approval_subjects[{index}]"
            subject = obj(raw, label)
            scope_identifier = subject.get("scope_identifier")
            require(isinstance(scope_identifier, str) and
                    bool(IDENTIFIER.fullmatch(scope_identifier)),
                    f"{label} has invalid scope_identifier")
            if isinstance(scope_identifier, str):
                require(scope_identifier not in subjects,
                        f"Duplicate approval scope: {scope_identifier}")
                subjects[scope_identifier] = subject
            kind = subject.get("kind")
            require(isinstance(kind, str) and kind in SUBJECT_GATES,
                    f"{label} invalid kind")
            if isinstance(kind, str):
                subject_kinds.add(kind)
            for field in ("subject_version", "scope"):
                require(text(subject.get(field)), f"{label} missing {field}")
            covered = items(subject.get("covered_identifiers"), f"{label}.covered_identifiers")
            require(all(text(value) for value in covered),
                    f"{label}.covered_identifiers needs non-empty text")
            if kind == "design":
                components = items(subject.get("components"), f"{label}.components")
                require(all(isinstance(value, str) for value in components) and
                        DESIGN_COMPONENTS.issubset(
                            value for value in components if isinstance(value, str)),
                        f"{label}.components must cover goals, content, task evaluation, "
                        "remediation and independent application")
            materials = items(subject.get("materials"), f"{label}.materials",
                              kind in ("media_contract", "media_sample") and current_index < 2)
            for material_index, raw_material in enumerate(materials):
                material_label = f"{label}.materials[{material_index}]"
                material = obj(raw_material, material_label)
                source = material.get("source")
                mode = material.get("fingerprint_mode")
                require(source in ("evidence_file", "manifest"),
                        f"{material_label} invalid source")
                require(mode in ("bytes", "json"), f"{material_label} invalid fingerprint_mode")
                if source == "evidence_file":
                    reference = material.get("reference_identifier")
                    require(isinstance(reference, str) and reference in evidence_files,
                            f"{material_label} unknown evidence reference: {reference}")
                elif source == "manifest":
                    require(mode == "json", f"{material_label} manifest source requires json mode")
                if mode == "json":
                    pointers = items(material.get("json_pointers"),
                                     f"{material_label}.json_pointers")
                    require(all(isinstance(pointer, str) and
                                (not pointer or pointer.startswith("/")) for pointer in pointers),
                            f"{material_label} invalid JSON pointers")
                    if source == "manifest":
                        permitted = ("/learner_profile", "/visual_bible",
                                     "/media_production_contract", "/evaluation_capabilities",
                                     "/experience_profile/profile_identifier",
                                     "/experience_profile/outline_reference",
                                     "/experience_profile/beat_identifiers",
                                     "/experience_profile/trace_matrix_reference")
                        require(all(isinstance(pointer, str) and
                                    any(pointer == prefix or pointer.startswith(prefix + "/")
                                        for prefix in permitted) for pointer in pointers),
                                f"{material_label} manifest pointers must select subject content, "
                                "not approval or status metadata")
            changes = items(subject.get("editorial_changes"), f"{label}.editorial_changes", True)
            require(kind != "media_sample" or not changes,
                    f"{label}: actual sample changes cannot use an editorial exception")
            for change_index, raw_change in enumerate(changes):
                change_label = f"{label}.editorial_changes[{change_index}]"
                change = obj(raw_change, change_label)
                for field in ("approved_sha256", "current_sha256"):
                    value = change.get(field)
                    require(isinstance(value, str) and bool(SHA256.fullmatch(value)),
                            f"{change_label} invalid {field}")
                for field in ("recorded_by", "recorded_at", "reason"):
                    require(text(change.get(field)), f"{change_label} missing {field}")
                require(change.get("classification") == "non_semantic_editorial",
                        f"{change_label} only non_semantic_editorial changes qualify")
                evidence_refs(change.get("evidence_references"),
                              f"{change_label}.evidence_references")
        require(set(SUBJECT_GATES).issubset(subject_kinds),
                "approval_subjects must include design, media_contract and media_sample scopes")

        for gate_key, required_index in (
                ("design_confirmation", 1), ("media_sample_confirmation", 2)):
            gate = obj(gates.get(gate_key), f"approval_gates.{gate_key}")
            confirmations = items(gate.get("confirmations"),
                                  f"approval_gates.{gate_key}.confirmations", True)
            by_scope = {}
            for confirmation_index, raw_confirmation in enumerate(confirmations):
                label = f"approval_gates.{gate_key}.confirmations[{confirmation_index}]"
                confirmation = obj(raw_confirmation, label)
                scope_identifier = confirmation.get("scope_identifier")
                require(isinstance(scope_identifier, str) and scope_identifier in subjects,
                        f"{label} unknown approval scope")
                if not isinstance(scope_identifier, str) or scope_identifier not in subjects:
                    continue
                require(scope_identifier not in by_scope,
                        f"{label} duplicate confirmation for {scope_identifier}")
                by_scope[scope_identifier] = confirmation
                subject = subjects[scope_identifier]
                kind = subject.get("kind")
                require(isinstance(kind, str) and SUBJECT_GATES.get(kind) == gate_key,
                        f"{label} scope belongs to another gate")
                for field in ("confirmed_by", "confirmed_at", "confirmed_version"):
                    require(text(confirmation.get(field)), f"{label} missing {field}")
                approved_digest = confirmation.get("content_sha256")
                require(isinstance(approved_digest, str) and
                        bool(SHA256.fullmatch(approved_digest)),
                        f"{label} invalid content_sha256")
                evidence_refs(confirmation.get("evidence_references"),
                              f"{label}.evidence_references")
                require(confirmation.get("confirmed_version") == subject.get("subject_version"),
                        f"{scope_identifier}: confirmed_version does not match subject_version")
                try:
                    actual_digest = approval_fingerprint(data, subject, base_directory)
                except (OSError, ValueError, KeyError, IndexError, TypeError) as exc:
                    require(False, f"{scope_identifier}: cannot fingerprint approval content: {exc}")
                    continue
                changes = subject.get("editorial_changes")
                changes = changes if isinstance(changes, list) else []
                editorial_matches = [
                    change for change in changes
                    if isinstance(change, dict) and
                    change.get("approved_sha256") == approved_digest and
                    change.get("current_sha256") == actual_digest and
                    change.get("classification") == "non_semantic_editorial"
                ]
                require(actual_digest == approved_digest or
                        (kind != "media_sample" and len(editorial_matches) == 1),
                        f"{scope_identifier}: approval content changed; "
                        "affected scope requires reconfirmation")
            if current_index >= required_index:
                expected_scopes = {
                    identifier for identifier, subject in subjects.items()
                    if isinstance(subject.get("kind"), str) and
                    SUBJECT_GATES.get(subject["kind"]) == gate_key
                }
                require(expected_scopes.issubset(by_scope),
                        f"{gate_key}: missing confirmations for "
                        f"{sorted(expected_scopes.difference(by_scope))}")

    capabilities = obj(data.get("evaluation_capabilities"), "evaluation_capabilities")
    deterministic = items(capabilities.get("deterministic_checks"),
                          "evaluation_capabilities.deterministic_checks", True)
    require(all(text(value) for value in deterministic),
            "deterministic_checks requires text entries")
    open_review = obj(capabilities.get("open_response_review"), "open_response_review")
    require(isinstance(open_review.get("mode"), str) and
            open_review.get("mode") in {"self_review", "human_review", "verified_ai"},
            "open_response_review.mode is invalid")
    require(text(open_review.get("rubric_reference")),
            "open_response_review.rubric_reference is required")
    ai_evaluation = obj(capabilities.get("ai_evaluation"), "ai_evaluation")
    require(isinstance(ai_evaluation.get("enabled"), bool),
            "ai_evaluation.enabled must be boolean")
    require(text(ai_evaluation.get("uncertainty_statement")),
            "ai_evaluation.uncertainty_statement is required")
    require(text(ai_evaluation.get("fallback")), "ai_evaluation.fallback is required")
    if ai_evaluation.get("enabled") is True:
        evidence_refs(ai_evaluation.get("validation_evidence_references"),
                      "ai_evaluation.validation_evidence_references")
    require((open_review.get("mode") == "verified_ai") ==
            (ai_evaluation.get("enabled") is True),
            "verified_ai mode and ai_evaluation.enabled must agree")

    records = obj(data.get("learning_records"), "learning_records")
    require(isinstance(records.get("storage"), str) and
            records.get("storage") in {"local_only", "remote"},
            "learning_records.storage is invalid")
    for field in ("purpose_and_disclosure", "retention", "export_path", "deletion_path"):
        require(text(records.get(field)), f"learning_records missing {field}")
    require(isinstance(records.get("identity_linked"), bool),
            "learning_records.identity_linked must be boolean")
    require(isinstance(records.get("upload_enabled"), bool),
            "learning_records.upload_enabled must be boolean")
    minimum_fields = items(records.get("minimum_fields"), "learning_records.minimum_fields")
    require(all(text(value) for value in minimum_fields),
            "learning_records.minimum_fields requires text")
    if records.get("storage") == "local_only":
        require(records.get("upload_enabled") is False,
                "local_only learning records cannot enable upload")
    if records.get("upload_enabled") is True or records.get("identity_linked") is True:
        require(records.get("storage") == "remote",
                "uploaded or identity-linked records require remote storage declaration")

    if current_index >= 4:
        require(any(entry.get("kind") == "functional_acceptance"
                    for entry in evidence_files.values()),
                "functional_accepted requires a functional_acceptance evidence file")
    if current_index >= 5:
        require(any(entry.get("kind") == "learner_trial"
                    for entry in evidence_files.values()),
                "learner_trial_complete requires a learner_trial evidence file")
    if current_index >= 6:
        require(any(entry.get("kind") == "effect_evaluation"
                    for entry in evidence_files.values()),
                "effect_evaluated requires an effect_evaluation evidence file")

    if not allow_placeholders:
        for field in placeholder_paths(data):
            errors.append(f"{field}: unfilled template or TBD marker")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest")
    parser.add_argument("--allow-placeholders", action="store_true")
    parser.add_argument("--allow-missing-files", action="store_true")
    parser.add_argument("--show-approval-fingerprints", action="store_true",
                        help="Print current scope fingerprints without changing any confirmations")
    parser.add_argument("--previous-manifest", type=Path,
                        help="Compare against the preserved previous manifest; detect rewritten history")
    parser.add_argument("--joint", action="store_true",
                        help="Validate the referenced blueprint and cross-file contract")
    parser.add_argument("--show-event-fingerprints", action="store_true",
                        help="Print event hashes without changing history")
    args = parser.parse_args()
    try:
        path = Path(args.manifest)
        data = json.loads(path.read_text(encoding="utf-8"))
        errors = validate(
            data,
            path.resolve().parent,
            args.allow_placeholders,
            args.allow_missing_files,
        )
        if args.previous_manifest:
            from production_contract import check_previous
            previous = json.loads(args.previous_manifest.read_text(encoding="utf-8"))
            errors.extend(check_previous(previous, data))
        if args.joint:
            from production_contract import validate_joint
            errors.extend(validate_joint(data, path.resolve().parent,
                                         not args.allow_placeholders))
        if args.show_event_fingerprints:
            from production_contract import event_digest
            for event in data.get("status_history", []) if isinstance(data, dict) else []:
                if isinstance(event, dict):
                    print(f"EVENT: {event.get('event_identifier', '?')} sha256={event_digest(event)}")
        if args.show_approval_fingerprints:
            raw_subjects = data.get("approval_subjects", []) if isinstance(data, dict) else []
            for subject in raw_subjects if isinstance(raw_subjects, list) else []:
                try:
                    digest = approval_fingerprint(data, subject, path.resolve().parent)
                    print(f"FINGERPRINT: {subject['scope_identifier']} "
                          f"version={subject['subject_version']} sha256={digest}")
                except (OSError, ValueError, KeyError, IndexError, TypeError) as exc:
                    label = subject.get("scope_identifier", "?") if isinstance(subject, dict) else "?"
                    print(f"UNAVAILABLE: {label}: {exc}")
    except (OSError, ValueError) as exc:
        errors = [str(exc)]
    for message in errors:
        print(f"ERROR: {message}")
    if errors:
        print(f"FAIL: {len(errors)} production manifest error(s)")
        return 1
    print("PASS: production status, evidence, assets and governance are structurally valid")
    if args.allow_placeholders or args.allow_missing_files:
        print("TEMPLATE CHECK: relaxed checks are not formal production acceptance.")
    print("Teaching quality, media quality, legal rights and learning effects require human evidence.")
    print("Fingerprints check content integrity, not human identity or semantic equivalence.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
