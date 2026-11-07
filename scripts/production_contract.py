"""Current lifecycle, media acceptance and cross-file checks."""

import copy
import json
from pathlib import Path
import subprocess

from contract_checks import placeholder_paths
from validate_production import approval_fingerprint, canonical_digest, file_digest, SHA256

STAGES = [
    "design_draft", "design_confirmed", "media_sample_confirmed",
    "production_complete", "functional_accepted", "learner_trial_complete", "effect_evaluated",
]
SCOPE_TYPES = {
    "full_course", "local_design", "media_assets", "illustrative_prototype",
    "course_implementation",
}
LEARNER_DELIVERY_TYPES = {
    "interactive_web", "facilitated_instruction", "linear_media", "print_or_document",
}
ASSET_KINDS = {
    "linear_video", "audio", "panorama", "three_dimensional", "diagram",
    "document", "image", "runtime",
}
MEDIA_KINDS = {
    "video": {"linear_video"}, "audio": {"audio"}, "panorama": {"panorama"},
    "three_dimensional": {"three_dimensional"}, "diagram": {"diagram"},
    "document": {"document"},
}
DELIVERY_ENDPOINTS = {
    "design_draft", "interaction_complete_prototype", "media_sample",
    "functional_course", "learner_trial_ready",
}
ACCEPTANCE_STATUSES = {
    "not_started", "structure_checked", "browser_verified",
    "media_verified", "human_review_pending", "accepted",
}
ACCEPTED_SCOPES = {"design", "interaction", "media", "function", "trial_ready"}
ENDPOINT_MIN_STATUS = {
    "design_draft": "design_draft",
    "interaction_complete_prototype": "design_confirmed",
    "media_sample": "design_confirmed",
    "functional_course": "production_complete",
    "learner_trial_ready": "functional_accepted",
}
ENDPOINT_ACCEPTANCE = {
    "design_draft": {"not_started", "structure_checked", "human_review_pending"},
    "interaction_complete_prototype": {
        "browser_verified", "human_review_pending", "accepted",
    },
    "media_sample": {
        "not_started", "structure_checked", "browser_verified",
        "media_verified", "human_review_pending", "accepted",
    },
    "functional_course": {
        "not_started", "structure_checked", "browser_verified",
        "media_verified", "human_review_pending", "accepted",
    },
    "learner_trial_ready": {
        "not_started", "structure_checked", "browser_verified",
        "media_verified", "human_review_pending", "accepted",
    },
}
ENDPOINT_ACCEPTED_SCOPE = {
    "design_draft": "design",
    "interaction_complete_prototype": "interaction",
    "media_sample": "media",
    "functional_course": "function",
    "learner_trial_ready": "trial_ready",
}
DEMO_NON_VIDEO_REQUIREMENTS = {
    "course_content",
    "scene_and_beat_sequence",
    "page_and_responsive_layout",
    "interactions_and_feedback",
    "state_and_recovery",
    "accessibility_equivalents",
    "non_video_assets",
    "browser_verification",
}
DEMO_DEFERRED_KINDS = {
    "formal_video_generation",
    "video_runtime_binding",
    "post_video_integration_verification",
}
DEMO_PRESERVED_CONTRACTS = {
    "course_content", "layout", "interactions",
    "feedback", "state_and_recovery", "accessibility",
}
DEMO_POST_REPLACEMENT_CHECKS = {
    "media_timing", "hotspot_timing", "caption_sync",
    "return_state", "responsive_layout", "accessibility",
}


class Checks:
    def __init__(self, base):
        self.base = Path(base)
        self.errors = []

    def need(self, condition, label):
        if not condition:
            self.errors.append(label)

    def obj(self, value, label):
        self.need(isinstance(value, dict), f"{label} must be an object")
        return value if isinstance(value, dict) else {}

    def rows(self, value, label, empty=True):
        self.need(isinstance(value, list), f"{label} must be a list")
        values = value if isinstance(value, list) else []
        self.need(empty or bool(values), f"{label} cannot be empty")
        return [self.obj(row, f"{label}[{index}]") for index, row in enumerate(values)]

    def strings(self, value, label, empty=True):
        self.need(isinstance(value, list), f"{label} must be a list")
        values = value if isinstance(value, list) else []
        self.need(empty or bool(values), f"{label} cannot be empty")
        self.need(all(isinstance(item, str) and item.strip() for item in values),
                  f"{label} requires non-empty strings")
        result = [item for item in values if isinstance(item, str) and item.strip()]
        self.need(len(set(result)) == len(result), f"{label} contains duplicate identifiers")
        return result

    def text(self, value, label):
        self.need(isinstance(value, str) and bool(value.strip()), f"{label} requires text")

    def digest(self, value, label):
        self.need(isinstance(value, str) and bool(SHA256.fullmatch(value)), f"{label} invalid SHA256")

    def path(self, value):
        if not isinstance(value, str) or not value:
            raise ValueError("file path must be text")
        path = Path(value)
        return path if path.is_absolute() else self.base / path

    def matches(self, path, digest, label):
        self.digest(digest, label)
        try:
            self.need(file_digest(self.path(path)) == digest, f"{label}: file content changed")
        except (OSError, ValueError) as exc:
            self.need(False, f"{label}: {exc}")


def event_digest(event):
    return canonical_digest({key: value for key, value in event.items() if key != "event_sha256"})


def validate_video_only_demo_contract(data, assets):
    """Require a full web Demo to differ from the final course only by formal video."""
    c = Checks(Path.cwd())
    scope = c.obj(data.get("work_scope"), "work_scope")
    profile = data.get("experience_profile")
    profile_identifier = profile.get("profile_identifier") if isinstance(profile, dict) else None
    applies = (
        scope.get("scope_type") == "full_course" and
        scope.get("learner_delivery_type") == "interactive_web" and
        profile_identifier == "video_led_web" and
        data.get("delivery_endpoint") == "interaction_complete_prototype"
    )
    if not applies:
        return c.errors

    c.need(data.get("acceptance_status") in {
        "browser_verified", "human_review_pending", "accepted",
    }, "video-only Demo requires browser verification before delivery")
    demo = c.obj(data.get("demo_completion"), "demo_completion")
    c.need(demo.get("contract_version") == "1.0",
           "demo_completion.contract_version must be 1.0")
    c.need(demo.get("completion_policy") == "video_only_delta",
           "demo_completion.completion_policy must be video_only_delta")

    completion = c.obj(demo.get("non_video_completion"),
                       "demo_completion.non_video_completion")
    c.need(set(completion) == DEMO_NON_VIDEO_REQUIREMENTS,
           "demo_completion.non_video_completion must declare every required final surface")
    for requirement in DEMO_NON_VIDEO_REQUIREMENTS:
        c.need(completion.get(requirement) == "complete",
               f"demo_completion non-video requirement is incomplete: {requirement}")

    required_formal_videos = {
        identifier for identifier, asset in assets.items()
        if asset.get("required") is True and
        asset.get("delivery_class") == "formal" and
        asset.get("kind") == "linear_video"
    }
    required_non_video_assets = {
        identifier for identifier, asset in assets.items()
        if asset.get("required") is True and
        asset.get("delivery_class") == "formal" and
        asset.get("kind") != "linear_video"
    }
    c.need(bool(required_formal_videos),
           "video-led Demo requires at least one required formal linear_video asset")
    for identifier in required_non_video_assets:
        c.need(assets[identifier].get("status") == "accepted",
               f"video-only Demo requires accepted non-video asset: {identifier}")

    deferred_asset_ids = set()
    deferred_identifiers = set()
    deferred = c.rows(demo.get("deferred_items"), "demo_completion.deferred_items", False)
    for index, row in enumerate(deferred):
        label = f"demo_completion.deferred_items[{index}]"
        identifier = row.get("deferred_identifier")
        c.text(identifier, f"{label}.deferred_identifier")
        if isinstance(identifier, str):
            c.need(identifier not in deferred_identifiers,
                   f"Duplicate deferred_identifier: {identifier}")
            deferred_identifiers.add(identifier)
        kind = row.get("kind")
        c.need(kind in DEMO_DEFERRED_KINDS,
               f"{label}.kind must be video-only deferred work")
        c.text(row.get("reason"), f"{label}.reason")
        references = c.strings(row.get("asset_identifiers"),
                               f"{label}.asset_identifiers", False)
        for reference in references:
            asset = assets.get(reference)
            c.need(asset is not None, f"{label} unknown asset: {reference}")
            if asset is not None:
                c.need(asset.get("kind") == "linear_video" and
                       asset.get("delivery_class") == "formal",
                       f"{label} may reference only formal linear_video assets")
                if kind == "formal_video_generation":
                    c.need(asset.get("status") != "accepted",
                           f"{label} cannot defer generation of an accepted formal video")
                deferred_asset_ids.add(reference)
    c.need(required_formal_videos.issubset(deferred_asset_ids),
           "Every unfinished required formal video must be declared in deferred_items")

    replacement = c.obj(demo.get("video_replacement_contract"),
                        "demo_completion.video_replacement_contract")
    formal_video_ids = set(c.strings(
        replacement.get("formal_video_asset_identifiers"),
        "video_replacement_contract.formal_video_asset_identifiers",
        False,
    ))
    c.need(formal_video_ids == required_formal_videos,
           "video replacement contract must list every required formal video exactly")
    substitutes = c.strings(
        replacement.get("substitute_asset_identifiers"),
        "video_replacement_contract.substitute_asset_identifiers",
        False,
    )
    for identifier in substitutes:
        asset = assets.get(identifier)
        c.need(asset is not None, f"Unknown storyboard substitute asset: {identifier}")
        if asset is not None:
            c.need(asset.get("kind") != "linear_video",
                   f"Storyboard substitute cannot be a formal video: {identifier}")
            c.need(asset.get("status") == "accepted",
                   f"Storyboard substitute must be accepted: {identifier}")
    preserved = set(c.strings(
        replacement.get("preserved_contracts"),
        "video_replacement_contract.preserved_contracts",
        False,
    ))
    c.need(DEMO_PRESERVED_CONTRACTS.issubset(preserved),
           "video replacement must preserve content, layout, interaction, feedback, state and accessibility")
    checks = set(c.strings(
        replacement.get("post_replacement_checks"),
        "video_replacement_contract.post_replacement_checks",
        False,
    ))
    c.need(DEMO_POST_REPLACEMENT_CHECKS.issubset(checks),
           "video replacement contract is missing required integration regressions")
    return c.errors


def check_previous(previous, current):
    """A hash chain alone cannot detect removal of an entire historical prefix."""
    c = Checks(Path.cwd())
    previous = c.obj(previous, "previous_manifest")
    current = c.obj(current, "manifest")
    for key in ("course_identifier",):
        c.need(previous.get(key) == current.get(key), f"previous_manifest {key} differs")
    old = previous.get("status_history")
    new = current.get("status_history")
    c.need(isinstance(old, list) and isinstance(new, list) and new[:len(old)] == old,
           "status_history must preserve the previous snapshot as an exact prefix")
    old_gates = c.obj(previous.get("approval_gates"), "previous.approval_gates")
    new_gates = c.obj(current.get("approval_gates"), "approval_gates")
    for name, gate in old_gates.items():
        old_records = c.obj(gate, name).get("confirmations", [])
        new_records = c.obj(new_gates.get(name), name).get("confirmations", [])
        c.need(isinstance(old_records, list) and isinstance(new_records, list) and
               new_records[:len(old_records)] == old_records,
               f"{name}: confirmation archive must be append-only")
    old_scopes = previous.get("approval_subjects", [])
    new_scopes = current.get("approval_subjects", [])
    if isinstance(old_scopes, list) and isinstance(new_scopes, list):
        new_by_id = {
            row.get("scope_identifier"): row for row in new_scopes
            if isinstance(row, dict) and isinstance(row.get("scope_identifier"), str)
        }
        for row in old_scopes:
            if isinstance(row, dict):
                c.need(isinstance(row.get("scope_identifier"), str) and
                       row.get("scope_identifier") in new_by_id,
                       "approval scopes cannot be deleted; preserve the scope and append its invalidation")
                current_row = new_by_id.get(row.get("scope_identifier"), {})
                c.need(
                    row.get("depends_on_scope_identifiers") ==
                    current_row.get("depends_on_scope_identifiers"),
                    f"{row.get('scope_identifier')}: approval dependencies are immutable; "
                    "create a versioned scope instead",
                )
    return c.errors


def validate_contract(data, base, allow_placeholders, allow_missing_files, structure_validator,
                      replay_result=None, ancestor_paths=frozenset()):
    c = Checks(base)
    scope = c.obj(data.get("work_scope"), "work_scope")
    scope_type = scope.get("scope_type")
    if scope_type != "media_assets":
        from validate_content_quality import validate_manifest_content
        c.errors.extend(validate_manifest_content(
            data, c.base, approved=data.get("current_status") in STAGES[1:]))
    c.need(isinstance(scope_type, str) and scope_type in SCOPE_TYPES, "Invalid work_scope.scope_type")
    delivery_type = scope.get("learner_delivery_type")
    c.need(
        isinstance(delivery_type, str) and delivery_type in LEARNER_DELIVERY_TYPES,
        "Invalid work_scope.learner_delivery_type",
    )
    for key in ("scope_identifier", "endpoint", "description"):
        c.text(scope.get(key), f"work_scope.{key}")
    for key in ("covered_objective_identifiers", "excluded_objective_identifiers",
                "covered_asset_identifiers", "excluded_asset_identifiers"):
        c.strings(scope.get(key), f"work_scope.{key}")
    delivery_endpoint = data.get("delivery_endpoint")
    acceptance_status = data.get("acceptance_status")
    accepted_scope = data.get("accepted_scope")
    if scope_type != "media_assets":
        c.need(delivery_endpoint in DELIVERY_ENDPOINTS, "Invalid delivery_endpoint")
        c.need(acceptance_status in ACCEPTANCE_STATUSES, "Invalid acceptance_status")
        if delivery_endpoint in DELIVERY_ENDPOINTS:
            c.need(acceptance_status in ENDPOINT_ACCEPTANCE[delivery_endpoint],
                   "acceptance_status is not allowed for delivery_endpoint")
            required_status = ENDPOINT_MIN_STATUS[delivery_endpoint]
            if required_status in STAGES and data.get("current_status") in STAGES:
                c.need(STAGES.index(data["current_status"]) >= STAGES.index(required_status),
                       "delivery_endpoint requires a later formal current_status")
            if scope.get("endpoint") in STAGES:
                c.need(STAGES.index(scope["endpoint"]) >= STAGES.index(required_status),
                       "delivery_endpoint exceeds work_scope.endpoint authorization")
        c.need(accepted_scope is None or accepted_scope in ACCEPTED_SCOPES,
               "Invalid accepted_scope")
        if acceptance_status == "accepted":
            c.need(delivery_endpoint in ENDPOINT_ACCEPTED_SCOPE and
                   accepted_scope == ENDPOINT_ACCEPTED_SCOPE.get(delivery_endpoint),
                   "accepted_scope does not match delivery_endpoint")
        else:
            c.need(accepted_scope is None, "accepted_scope must be null unless accepted")
    inherited_confirmations = c.rows(
        scope.get("inherited_confirmations"), "work_scope.inherited_confirmations"
    )
    if inherited_confirmations:
        parent_reference = scope.get("parent_manifest_reference")
        c.text(parent_reference, "work_scope.parent_manifest_reference")
        parent = {}
        parent_digest = None
        try:
            parent_path = c.path(parent_reference)
            parent_digest = file_digest(parent_path)
            parent = json.loads(parent_path.read_text(encoding="utf-8"))
            c.need(isinstance(parent, dict), "parent manifest root must be an object")
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            c.need(False, f"work_scope.parent_manifest_reference: {exc}")
            parent = {}
        parent_subjects = {
            row.get("scope_identifier"): row
            for row in parent.get("approval_subjects", [])
            if isinstance(row, dict) and isinstance(row.get("scope_identifier"), str)
        } if isinstance(parent, dict) else {}
        parent_records = {}
        for gate in parent.get("approval_gates", {}).values() \
                if isinstance(parent.get("approval_gates"), dict) else []:
            if not isinstance(gate, dict):
                continue
            for record in gate.get("confirmations", []):
                if isinstance(record, dict) and \
                        isinstance(record.get("confirmation_identifier"), str):
                    parent_records[record["confirmation_identifier"]] = record
        # Use the parent's complete validation and authoritative event replay.
        # File identity alone cannot make a revoked or stale approval active.
        parent_replay = {}
        if parent:
            resolved_parent = parent_path.resolve()
            if resolved_parent in ancestor_paths:
                c.need(False, "parent manifest inheritance cycle")
            else:
                parent_errors = validate_contract(
                    parent, parent_path.parent, False, False, structure_validator,
                    parent_replay, ancestor_paths | {resolved_parent})
                c.errors.extend(f"parent manifest: {error}" for error in parent_errors)
        active_parent_confirmations = {
            row.get("confirmation_identifier")
            for row in parent_replay.get("active", {}).values()
        }
        for index, inherited in enumerate(inherited_confirmations):
            label = f"work_scope.inherited_confirmations[{index}]"
            for key in (
                    "confirmation_identifier", "scope_identifier", "subject_version",
                    "content_sha256", "parent_manifest_sha256"):
                c.text(inherited.get(key), f"{label}.{key}")
            c.digest(inherited.get("content_sha256"), f"{label}.content_sha256")
            c.digest(inherited.get("parent_manifest_sha256"), f"{label}.parent_manifest_sha256")
            confirmation_id = inherited.get("confirmation_identifier")
            scope_id = inherited.get("scope_identifier")
            record = parent_records.get(confirmation_id)
            subject = parent_subjects.get(scope_id)
            c.need(record is not None, f"{label}: confirmation is absent from parent manifest")
            c.need(confirmation_id in active_parent_confirmations,
                   f"{label}: parent confirmation is not active")
            c.need(subject is not None, f"{label}: scope is absent from parent manifest")
            if record is not None:
                c.need(record.get("scope_identifier") == scope_id,
                       f"{label}: confirmation scope differs")
                c.need(record.get("content_sha256") == inherited.get("content_sha256"),
                       f"{label}: confirmation content fingerprint differs")
            if subject is not None:
                c.need(subject.get("subject_version") == inherited.get("subject_version"),
                       f"{label}: subject version differs")
            c.need(parent_digest == inherited.get("parent_manifest_sha256"),
                   f"{label}: parent manifest file changed")
    covered = scope.get("covered_asset_identifiers", [])
    excluded = scope.get("excluded_asset_identifiers", [])
    if isinstance(covered, list) and isinstance(excluded, list):
        c.need(not any(item in excluded for item in covered), "covered/excluded assets overlap")
    goals = scope.get("covered_objective_identifiers", [])
    excluded_goals = scope.get("excluded_objective_identifiers", [])
    if isinstance(goals, list) and isinstance(excluded_goals, list):
        c.need(not any(item in excluded_goals for item in goals), "covered/excluded objectives overlap")

    evidence = {}
    for entry in c.rows(data.get("evidence_files"), "evidence_files", False):
        reference = entry.get("reference_identifier")
        c.text(reference, "evidence_files.reference_identifier")
        if isinstance(reference, str):
            c.need(reference not in evidence, f"Duplicate evidence reference: {reference}")
            evidence[reference] = entry
        c.text(entry.get("path"), f"{reference}.path")
    if scope_type != "media_assets":
        acceptance_evidence = c.obj(data.get("acceptance_evidence"), "acceptance_evidence")
        acceptance_refs = c.strings(
            acceptance_evidence.get("evidence_references"),
            "acceptance_evidence.evidence_references",
            True,
        )
        for reference in acceptance_refs:
            c.need(reference in evidence,
                   f"acceptance_evidence unknown evidence reference: {reference}")
        if acceptance_status == "accepted":
            c.text(acceptance_evidence.get("review_owner"), "acceptance_evidence.review_owner")
            from demo_contract import require_human
            require_human(c, acceptance_evidence.get("review_owner"),
                          "acceptance_evidence.review_owner")
            c.text(acceptance_evidence.get("accepted_at"), "acceptance_evidence.accepted_at")
            c.need(acceptance_evidence.get("reviewed_version") == data.get("course_version"),
                   "acceptance_evidence.reviewed_version must match course_version")
            c.need(bool(acceptance_refs), "accepted delivery requires acceptance evidence")
        else:
            c.need(acceptance_evidence.get("review_owner") in (None, ""),
                   "acceptance_evidence.review_owner requires accepted status")
            c.need(acceptance_evidence.get("accepted_at") in (None, ""),
                   "acceptance_evidence.accepted_at requires accepted status")
            c.need(acceptance_evidence.get("reviewed_version") in (None, ""),
                   "acceptance_evidence.reviewed_version requires accepted status")

    # A video-led web course is not design-complete when it only has prose
    # teaching notes. Require the artifacts that make the proposed experience
    # inspectable by curriculum, media, design, and frontend reviewers.
    experience_profile = data.get("experience_profile", {})
    profile_identifier = experience_profile.get("profile_identifier") \
        if isinstance(experience_profile, dict) else None
    if delivery_type == "interactive_web" and profile_identifier == "video_led_web":
        required_design_evidence = {
            "clarification_intake": "clarification_intake",
            "experience_blueprint": "experience_blueprint",
            "storyboard": "storyboard",
            "interaction_visual_spec": "interaction_visual_spec",
        }
        for reference, kind in required_design_evidence.items():
            entry = evidence.get(reference)
            c.need(entry is not None,
                   f"video_led_web requires evidence file: {reference}")
            if entry is not None:
                c.need(entry.get("kind") == kind,
                       f"{reference}: expected evidence kind {kind}")

    if delivery_type == "interactive_web" and profile_identifier in {"spatial_native_web", "hybrid_web"}:
        plans = [entry for entry in evidence.values() if entry.get("kind") == "spatial_learning_plan"]
        blueprints = [entry for entry in evidence.values() if entry.get("kind") == "course_blueprint"]
        c.need(len(plans) == 1, "spatial course requires one spatial_learning_plan evidence file")
        c.need(len(blueprints) == 1, "spatial course requires one course_blueprint evidence file")
        if len(plans) == 1 and len(blueprints) == 1:
            from validate_spatial_learning import validate as spatial_check
            try:
                for entry in (plans[0], blueprints[0]):
                    c.matches(entry.get("path"), entry.get("content_sha256"), "spatial design evidence")
                plan = c.obj(json.loads(c.path(plans[0]["path"]).read_text(encoding="utf-8")), "spatial plan")
                blueprint = c.obj(json.loads(c.path(blueprints[0]["path"]).read_text(encoding="utf-8")), "spatial blueprint")
                c.errors.extend(spatial_check(plan, blueprint, c.base))
                c.need(plan.get("experience_profile") == profile_identifier, "spatial design/profile differs")
            except (OSError, ValueError, KeyError) as exc:
                c.need(False, "spatial design evidence: " + str(exc))

    def version_binding(entry, label):
        """Package versions may change while the bound subject/asset stays identical."""
        if entry.get("course_version") == data.get("course_version"):
            return
        bound = c.obj(entry.get("bound_versions"), f"{label}.bound_versions")
        current_versions = {}
        for field, key, version_key in (
                ("approval_subjects", "scope_identifier", "subject_version"),
                ("assets", "asset_identifier", "asset_version")):
            for row in c.rows(data.get(field), field):
                if isinstance(row.get(key), str):
                    current_versions[row[key]] = row.get(version_key)
        c.need(bool(bound) and all(isinstance(identifier, str) and
                                 current_versions.get(identifier) == version
                                 for identifier, version in bound.items()),
               f"{label}: evidence course_version differs without unchanged scope/asset bindings")

    def refs(value, label, empty=False, binding=False):
        references = c.strings(value, label, empty)
        for reference in references:
            c.need(reference in evidence, f"{label}: unknown evidence reference {reference}")
            if reference in evidence and binding:
                entry = evidence[reference]
                version_binding(entry, reference)
                c.matches(entry.get("path"), entry.get("content_sha256"), f"{reference}.content_sha256")
        return references

    assets = {}
    for asset in c.rows(data.get("assets"), "assets"):
        identifier = asset.get("asset_identifier")
        c.text(identifier, "assets.asset_identifier")
        if isinstance(identifier, str):
            c.need(identifier not in assets, f"Duplicate asset {identifier}")
            assets[identifier] = asset
        kind = asset.get("kind")
        c.need(isinstance(kind, str) and kind in ASSET_KINDS, f"{identifier}: invalid asset kind")
        purpose = asset.get("delivery_class")
        c.need(purpose in ("formal", "intermediate"), f"{identifier}: invalid delivery_class")
        c.text(asset.get("asset_version"), f"{identifier}.asset_version")
        status = asset.get("status")
        c.need(status in ("planned", "draft", "ready", "accepted"), f"{identifier}: invalid asset status")
        c.need(isinstance(asset.get("required"), bool), f"{identifier}.required must be boolean")
        if asset.get("required") is True:
            c.need(purpose == "formal", f"{identifier}: required resource cannot be intermediate")
        files = c.rows(asset.get("files"), f"{identifier}.files")
        if status in ("ready", "accepted"):
            c.need(bool(files), f"{identifier}: ready/accepted asset requires files")
        for entry in files:
            c.text(entry.get("path"), f"{identifier}.files.path")
        if scope_type == "media_assets":
            for section, keys in (
                ("provenance", ("origin", "tool_and_model", "prompt_or_process_reference")),
                ("governance", ("rights_basis", "learner_disclosure", "retention")),
                ("accessibility", ("learning_goal", "equivalent_path")),
            ):
                values = c.obj(asset.get(section), f"{identifier}.{section}")
                for key in keys:
                    c.text(values.get(key), f"{identifier}.{section}.{key}")
        if status == "accepted":
            c.need(c.obj(asset.get("governance"), "governance").get("privacy_review_status")
                   in ("reviewed", "not_applicable"), f"{identifier}: privacy review not completed")
            c.need(c.obj(asset.get("accessibility"), "accessibility").get("status") == "accepted",
                   f"{identifier}: equivalent path not accepted")
            acceptance = c.obj(asset.get("acceptance"), f"{identifier}.acceptance")
            c.need(acceptance.get("asset_version") == asset.get("asset_version"),
                   f"{identifier}: acceptance version differs")
            snapshots = c.rows(acceptance.get("file_snapshots"), f"{identifier}.file_snapshots", False)
            actual_paths = [entry.get("path") for entry in files]
            c.need([entry.get("path") for entry in snapshots] == actual_paths,
                   f"{identifier}: acceptance must bind every file in the same order")
            for entry in snapshots:
                c.matches(entry.get("path"), entry.get("content_sha256"), f"{identifier}.file_snapshot")
            checks = c.strings(acceptance.get("checks"), f"{identifier}.checks", False)
            c.need({"decodable", "content_correct", "continuity", "equivalent_path"}.issubset(checks),
                   f"{identifier}: acceptance missing core quality checks")
            refs(acceptance.get("evidence_references"), f"{identifier}.acceptance.evidence", binding=True)
            if kind == "linear_video" and purpose == "formal":
                delivery = c.obj(asset.get("delivery"), f"{identifier}.delivery")
                for key in ("embedded_voice", "environment_and_action_audio", "separate_web_audio_stems"):
                    c.need(delivery.get(key) is True, f"{identifier}: formal video requires {key}")
                branch = delivery.get("separate_branch_audio")
                c.need(branch is True or branch == "not_applicable",
                       f"{identifier}: branch audio must be true or not_applicable")
                if branch == "not_applicable":
                    c.text(delivery.get("branch_audio_not_applicable_reason"),
                           f"{identifier}.branch_audio_not_applicable_reason")
                for key in ("voice_content", "lip_synchronization", "timbre_continuity", "mix"):
                    c.need(key in checks, f"{identifier}: missing actual {key} review")
                refs(delivery.get("audio_probe_evidence_references"),
                     f"{identifier}.audio_probe_evidence", binding=True)
                video_files = [entry for entry in files
                               if isinstance(entry.get("path"), str) and
                               Path(entry["path"]).suffix.lower() in (".mp4", ".mov", ".webm", ".mkv")]
                c.need(bool(video_files), f"{identifier}: formal video requires an actual video file")
                for entry in video_files:
                    try:
                        probe = subprocess.run(
                            ["ffprobe", "-v", "error",
                             "-show_entries", "stream=codec_type,duration:format=duration",
                             "-of", "json", str(c.path(entry["path"]))],
                            capture_output=True, text=True, timeout=30, check=True)
                        info = json.loads(probe.stdout)
                        c.need(bool(info.get("streams")) and
                               any(stream.get("codec_type") == "audio" for stream in info.get("streams", [])
                                   if isinstance(stream, dict)) and
                               float(info.get("format", {}).get("duration", 0)) > 0,
                               f"{identifier}: no real audio stream")
                        c.need(any(stream.get("codec_type") == "video" for stream in info.get("streams", [])
                                   if isinstance(stream, dict)),
                               f"{identifier}: no real video stream")
                    except (OSError, subprocess.SubprocessError, ValueError, TypeError) as exc:
                        c.need(False, f"{identifier}: audio probe failed: {exc}")
    for identifier in c.strings(scope.get("covered_asset_identifiers"), "scope.assets"):
        c.need(identifier in assets, f"work_scope: unknown covered asset {identifier}")
    c.errors.extend(validate_video_only_demo_contract(data, assets))
    if scope_type == "media_assets":
        c.text(data.get("course_identifier"), "course_identifier")
        c.text(data.get("course_version"), "course_version")
        c.need(scope.get("endpoint") == "assets_accepted", "media_assets endpoint must be assets_accepted")
        c.need(data.get("current_status") is None,
               "asset maintenance must not claim or change the parent's course lifecycle status")
        c.text(scope.get("parent_manifest_reference"), "scope.parent_manifest_reference")
        if data.get("work_status") == "complete":
            for identifier in c.strings(scope.get("covered_asset_identifiers"), "scope.assets", False):
                c.need(assets.get(identifier, {}).get("status") == "accepted",
                       f"media work incomplete: {identifier}")
        c.need(data.get("work_status") in ("in_progress", "complete"), "Invalid work_status")
        if not allow_placeholders:
            c.errors.extend(f"{field}: unfilled template or TBD marker" for field in placeholder_paths(data))
        return c.errors

    c.need(scope.get("endpoint") in STAGES, "course scope endpoint must be a lifecycle stage")
    endpoint_limits = {"local_design": 1, "illustrative_prototype": 0, "course_implementation": 4}
    if isinstance(scope_type, str) and scope_type in endpoint_limits and scope.get("endpoint") in STAGES:
        c.need(STAGES.index(scope["endpoint"]) <= endpoint_limits[scope_type],
               f"{scope_type}: endpoint exceeds the scope's applicable stages")
    subjects = {}
    from demo_contract import GATE_BY_KIND, validate_workflow, validate_runtime_delivery
    workflow_required = scope_type in {"full_course", "course_implementation"} or \
        delivery_endpoint == "interaction_complete_prototype"
    if workflow_required:
        c.need(data.get("workflow_contract_version") == "1.0",
               "workflow_contract_version must be 1.0; legacy gates are not current workflow acceptance")
    for subject in c.rows(data.get("approval_subjects"), "approval_subjects", False):
        identifier = subject.get("scope_identifier")
        if isinstance(identifier, str):
            subjects[identifier] = subject
        c.strings(subject.get("depends_on_scope_identifiers"), f"{identifier}.dependencies")
    for identifier, subject in subjects.items():
        dependencies = c.strings(subject.get("depends_on_scope_identifiers"), f"{identifier}.dependencies")
        c.need(all(item in subjects and item != identifier for item in dependencies),
               f"{identifier}: invalid dependency scope")
        for material_index, material in enumerate(subject.get("materials", [])
                                                   if isinstance(subject.get("materials"), list) else []):
            if material.get("source") == "manifest" and material.get("fingerprint_mode") == "json":
                pointers = material.get("json_pointers", [])
                c.need(isinstance(pointers, list), f"{identifier}.materials[{material_index}].json_pointers must be a list")
                for pointer in pointers if isinstance(pointers, list) else []:
                    c.need(pointer not in ("/experience_profile", "/experience_profile/coverage_status"),
                           f"{identifier}: manifest pointers cannot select review metadata")
        pending = list(dependencies)
        visited = set()
        while pending:
            item = pending.pop()
            if item == identifier:
                c.need(False, f"{identifier}: scope dependency cycle")
                break
            if item not in visited and item in subjects:
                visited.add(item)
                pending.extend(c.strings(subjects[item].get("depends_on_scope_identifiers"),
                                         f"{item}.dependencies"))
    confirmations = {}
    gates = c.obj(data.get("approval_gates"), "approval_gates")
    for name, gate in gates.items():
        for row in c.rows(c.obj(gate, name).get("confirmations"), f"{name}.confirmations"):
            identifier = row.get("confirmation_identifier")
            c.text(identifier, "confirmation_identifier")
            if isinstance(identifier, str):
                c.need(identifier not in confirmations, f"Duplicate confirmation {identifier}")
                confirmations[identifier] = row
            for key in ("confirmed_by", "confirmed_at", "confirmed_version", "scope_identifier"):
                c.text(row.get(key), f"{identifier}.{key}")
            c.digest(row.get("content_sha256"), f"{identifier}.content_sha256")
            refs(row.get("evidence_references"), f"{identifier}.evidence")
            subject = subjects.get(row.get("scope_identifier")) \
                if isinstance(row.get("scope_identifier"), str) else None
            c.need(subject is not None and GATE_BY_KIND.get(subject.get("kind")) == name,
                   f"{identifier}: confirmation scope belongs to another gate")
            from demo_contract import require_human
            require_human(c, row.get("confirmed_by"), f"{identifier}.confirmed_by")
            c.need(any(evidence.get(reference, {}).get("kind") == "human_confirmation"
                       for reference in row.get("evidence_references", [])
                       if isinstance(reference, str)),
                   f"{identifier}: confirmation requires human_confirmation evidence")

    active = {}
    rank = -1
    current_advances = {}
    previous_digest = None
    seen_events = set()
    history = c.rows(data.get("status_history"), "status_history", False)
    for event in history:
        identifier = event.get("event_identifier")
        c.text(identifier, "status_history.event_identifier")
        if isinstance(identifier, str):
            c.need(identifier not in seen_events, f"Duplicate event {identifier}")
            seen_events.add(identifier)
        for key in ("recorded_at", "recorded_by", "reason", "course_version"):
            c.text(event.get(key), f"{identifier}.{key}")
        refs(event.get("evidence_references"), f"{identifier}.evidence")
        c.need(event.get("previous_event_sha256") == previous_digest,
               f"{identifier}: broken history hash chain")
        digest = event_digest(event)
        if not (allow_placeholders and rank < 0 and
                isinstance(event.get("event_sha256"), str) and
                event["event_sha256"].startswith("{{")):
            c.need(event.get("event_sha256") == digest, f"{identifier}: event content changed")
        previous_digest = digest
        affected = c.strings(event.get("scope_identifiers"), f"{identifier}.scopes")
        c.need(all(item in subjects for item in affected), f"{identifier}: unknown scope")
        event_type = event.get("event_type")
        if event_type == "invalidate":
            affected_assets = c.strings(event.get("affected_asset_identifiers", []),
                                       f"{identifier}.affected_assets")
            c.need(all(item in assets for item in affected_assets), f"{identifier}: unknown affected asset")
            from_status = event.get("invalidated_from_status")
            stage_boundary = STAGES.index(from_status) if from_status in STAGES else -1
            asset_invalidation = bool(affected_assets) and stage_boundary >= 3
            c.need(bool(affected) or asset_invalidation,
                   f"{identifier}: invalidation requires scopes or assets with a downstream stage")
            invalid = set(affected)
            changed = True
            while changed:
                changed = False
                for scope_id, subject in subjects.items():
                    deps = c.strings(subject.get("depends_on_scope_identifiers"), f"{scope_id}.dependencies")
                    if scope_id not in invalid and any(item in invalid for item in deps):
                        invalid.add(scope_id)
                        changed = True
            for scope_id in invalid:
                active.pop(scope_id, None)
            boundary = min(
                ({"clarification": 0, "design": 0, "demo": 2}.get(
                    subjects[item].get("kind"), 1) for item in invalid),
                default=rank)
            if asset_invalidation:
                boundary = min(boundary, stage_boundary - 1)
            rank = min(rank, boundary)
            current_advances = {step: item for step, item in current_advances.items() if step <= rank}
            c.need(event.get("status") == STAGES[max(rank, 0)],
                   f"{identifier}: invalidate status does not match affected dependencies")
        elif event_type == "reconfirm":
            named = c.strings(event.get("confirmation_identifiers"), f"{identifier}.confirmations", False)
            confirmed_scopes = []
            for confirmation_id in named:
                row = confirmations.get(confirmation_id)
                c.need(row is not None, f"{identifier}: unknown confirmation {confirmation_id}")
                if row is not None:
                    scope_id = row.get("scope_identifier")
                    c.need(isinstance(scope_id, str) and scope_id in subjects,
                           f"{confirmation_id}: unknown subject")
                    if isinstance(scope_id, str) and scope_id in subjects:
                        kind = subjects[scope_id].get("kind")
                        dependencies = c.strings(subjects[scope_id].get("depends_on_scope_identifiers"),
                                                 f"{scope_id}.dependencies")
                        c.need(all(key in active for key in dependencies),
                               f"{identifier}: confirmation dependencies were not active at this event")
                        c.need(row.get("dependency_fingerprints") == {
                            key: active.get(key, {}).get("content_sha256") for key in dependencies
                        }, f"{identifier}: confirmation dependency fingerprints differ at this event")
                        if kind in {"design", "demo"} and workflow_required:
                            required = {"clarification"} if kind == "design" else {"clarification", "design"}
                            c.need(all(any(s.get("kind") == dependency_kind and key in active
                                           for key, s in subjects.items())
                                       for dependency_kind in required),
                                   f"{identifier}: {kind} confirmation lacks prerequisite gates")
                        if kind == "demo":
                            c.need(rank >= 1, f"{identifier}: Demo requires design_confirmed")
                        c.need(scope_id not in active or
                               active[scope_id].get("content_sha256") == row.get("content_sha256"),
                               f"{identifier}: invalidate changed scope before reconfirming it")
                        active[scope_id] = row
                        confirmed_scopes.append(scope_id)
            c.need(sorted(confirmed_scopes) == sorted(affected),
                   f"{identifier}: reconfirm scopes differ from confirmation records")
            c.need(event.get("status") == STAGES[max(rank, 0)],
                   f"{identifier}: reconfirm does not advance a lifecycle stage")
        elif event_type == "advance":
            target = event.get("status")
            next_rank = STAGES.index(target) if target in STAGES else -1
            c.need(next_rank == rank + 1, f"{identifier}: advance cannot skip or repeat stages")
            if next_rank == rank + 1:
                rank = next_rank
                current_advances[rank] = event
            required_kinds = {"design"} if rank == 1 else (
                {"design", "media_contract", "media_sample"} if rank >= 2 else set())
            if workflow_required and rank >= 1:
                required_kinds.add("clarification")
            if workflow_required and rank >= 3:
                required_kinds.add("demo")
                c.need(any(subject.get("kind") == "demo" for subject in subjects.values()),
                       f"{identifier}: production requires Demo confirmation")
            for scope_id, subject in subjects.items():
                if isinstance(subject.get("kind"), str) and subject.get("kind") in required_kinds:
                    c.need(scope_id in active, f"{identifier}: advance lacks active confirmation {scope_id}")
        else:
            c.need(False, f"{identifier}: event_type must be advance, invalidate or reconfirm")

    # Historical approvals remain archived; only the active ones bind current files.
    filtered_gates = {
        "design_confirmation": {"status": "confirmed" if rank >= 1 else "pending", "confirmations": []},
        "media_sample_confirmation": {"status": "confirmed" if rank >= 2 else "pending", "confirmations": []},
    }
    for kind in ("clarification", "demo"):
        if workflow_required or GATE_BY_KIND[kind] in gates:
            filtered_gates[GATE_BY_KIND[kind]] = {
                "status": "confirmed" if any(subjects[key].get("kind") == kind
                                            for key in active) else "pending",
                "confirmations": [],
            }
    live_digests = {}
    for scope_id, row in active.items():
        subject = subjects[scope_id]
        try:
            digest = approval_fingerprint(data, subject, c.base)
            live_digests[scope_id] = digest
        except (OSError, ValueError, KeyError, TypeError, IndexError) as exc:
            c.need(False, f"{scope_id}: cannot fingerprint current scope: {exc}")
        kind = subject.get("kind")
        name = GATE_BY_KIND.get(kind)
        if name in filtered_gates:
            filtered_gates[name]["confirmations"].append(row)
    for scope_id, row in active.items():
        expected = {
            item: active.get(item, {}).get("content_sha256")
            for item in c.strings(subjects[scope_id].get("depends_on_scope_identifiers"),
                                  f"{scope_id}.dependencies")
        }
        c.need(row.get("dependency_fingerprints") == expected and
               all(item in active for item in expected),
               f"{scope_id}: dependency approval changed or is missing")
    invalid_bindings = []
    for scope_id, row in active.items():
        subject = subjects[scope_id]
        digest = live_digests.get(scope_id)
        editorial = [
            change for change in c.rows(subject.get("editorial_changes"), f"{scope_id}.editorial_changes")
            if change.get("classification") == "non_semantic_editorial" and
            change.get("approved_sha256") == row.get("content_sha256") and
            change.get("current_sha256") == digest
        ]
        if (row.get("confirmed_version") != subject.get("subject_version") or
                (digest != row.get("content_sha256") and not (
                    subject.get("kind") not in {"media_sample", "demo", "clarification"} and len(editorial) == 1))):
            invalid_bindings.append(scope_id)
    if invalid_bindings:
        boundary = min({"clarification": 0, "design": 0, "demo": 2}.get(
            subjects[item].get("kind"), 1) for item in invalid_bindings)
        c.need(False, f"Current confirmation no longer valid for {invalid_bindings}; "
               f"append invalidate and derive current_status={STAGES[min(max(rank, 0), boundary)]}")
    for name, gate in filtered_gates.items():
        c.need(c.obj(gates.get(name), name).get("status") == gate["status"],
               f"{name}: status differs from event replay")
    derived = STAGES[max(rank, 0)]
    c.need(data.get("current_status") == derived, f"current_status must be replay-derived {derived}")
    c.need(scope.get("endpoint") not in STAGES or
           rank <= STAGES.index(scope["endpoint"]), "work_scope exceeds its authorized endpoint")
    for stage_rank, event in current_advances.items():
        stage_refs = refs(event.get("evidence_references"), f"{event.get('event_identifier')}.current_evidence",
                          binding=stage_rank >= 1)
        if stage_rank >= 1:
            fingerprints = c.obj(event.get("evidence_fingerprints"), "stage.evidence_fingerprints")
            c.need(set(fingerprints) == set(stage_refs), "stage evidence snapshots must match references")
            for reference in stage_refs:
                c.need(fingerprints.get(reference) == evidence.get(reference, {}).get("content_sha256"),
                       f"{reference}: evidence changed since the advance event")
        kind = {4: "functional_acceptance", 5: "learner_trial", 6: "effect_evaluation"}.get(stage_rank)
        if kind:
            c.need(any(evidence.get(reference, {}).get("kind") == kind
                       for reference in c.strings(event.get("evidence_references"), "stage.evidence")),
                   f"{event.get('event_identifier')}: advance must bind actual {kind} evidence")
        if stage_rank >= 3:
            expected_assets = {
                asset_id: {"asset_version": asset.get("asset_version"),
                           "file_snapshots": c.obj(asset.get("acceptance"), "acceptance").get("file_snapshots")}
                for asset_id, asset in assets.items()
                if asset.get("delivery_class") == "formal" and asset.get("status") == "accepted"
            }
            c.need(event.get("asset_snapshots") == expected_assets,
                   f"{event.get('event_identifier')}: delivered assets changed since stage acceptance; "
                   "invalidate the affected downstream stage and repeat its checks")
    if rank >= 3:
        for asset_id, asset in assets.items():
            if asset.get("required") is True:
                c.need(asset.get("status") == "accepted", f"production incomplete: {asset_id}")
    if workflow_required:
        validate_workflow(c, data, subjects, active, rank, evidence)
    if delivery_type == "interactive_web" and (
            delivery_endpoint == "interaction_complete_prototype" or rank >= 3 or
            any(subjects[key].get("kind") == "demo" for key in active)):
        c.errors.extend(validate_runtime_delivery(data, c.base))

    sample = c.obj(data.get("representative_sample"), "representative_sample")
    media_required = delivery_type in {"interactive_web", "linear_media"}
    modes = c.strings(
        sample.get("media_modes"), "representative_sample.media_modes",
        not media_required,
    )
    c.need(all(item in ASSET_KINDS for item in modes), "sample has unknown media mode")
    risks = c.rows(sample.get("risk_coverage"), "representative_sample.risk_coverage", False)
    for risk in risks:
        for key in ("risk_identifier", "selection_reason"):
            c.text(risk.get(key), f"risk.{key}")
        c.need(isinstance(risk.get("critical"), bool), "risk.critical must be boolean")
        status = risk.get("status")
        c.need(status in ("planned", "passed", "not_applicable"), "risk.status invalid")
        if status == "not_applicable":
            c.text(risk.get("not_applicable_reason"), "risk.not_applicable_reason")
        if rank >= 2 and risk.get("critical") is True:
            c.need(status in ("passed", "not_applicable"), "critical sample risk not covered")
            if status == "passed":
                refs(risk.get("evidence_references"), "risk.evidence", binding=True)
    if rank >= 2:
        covered_sample = c.strings(
            sample.get("covered_asset_identifiers"), "sample.covered_assets",
            not media_required,
        )
        versions = c.obj(sample.get("candidate_asset_versions"), "sample.candidate_asset_versions")
        c.need(set(versions) == set(covered_sample), "sample candidate versions must match covered assets")
        for asset_id in covered_sample:
            asset = assets.get(asset_id, {})
            c.need(asset.get("status") == "accepted", f"sample candidate not accepted: {asset_id}")
            c.need(versions.get(asset_id) == asset.get("asset_version"),
                   f"sample candidate version changed: {asset_id}")
        c.need(set(modes) == {assets[item].get("kind") for item in covered_sample
                             if item in assets and isinstance(assets[item].get("kind"), str)},
               "sample media_modes must match the actual covered asset kinds")
        required_risks = {
            "interactive_web": {
                "content", "continuity", "mobile", "equivalent_path", "return_and_recovery",
            },
            "linear_media": {
                "content", "continuity", "playback_navigation", "equivalent_path",
            },
            "facilitated_instruction": {
                "content", "facilitator_handoff", "representative_delivery", "equivalent_path",
            },
            "print_or_document": {
                "content", "document_readability", "representative_delivery", "equivalent_path",
            },
        }[delivery_type]
        c.need(required_risks.issubset(
            risk.get("risk_identifier") for risk in risks if isinstance(risk.get("risk_identifier"), str)),
            f"sample risk matrix missing required risks for {delivery_type}")
        for risk in risks:
            if risk.get("risk_identifier") in required_risks:
                c.need(risk.get("critical") is True and risk.get("status") == "passed",
                       "delivery-type sample risks must be critical and actually passed")
        risk_map = {row.get("risk_identifier"): row for row in risks
                    if isinstance(row.get("risk_identifier"), str)}
        needed = []
        if "linear_video" in modes:
            needed.append("voice_and_lip_synchronization")
        if "panorama" in modes:
            needed.append("projection")
        if "three_dimensional" in modes:
            needed.append("model_rules")
        for risk_id in needed:
            c.need(risk_map.get(risk_id, {}).get("critical") is True and
                   risk_map.get(risk_id, {}).get("status") == "passed",
                   f"sample media mode requires passed critical risk: {risk_id}")

    capabilities = c.obj(data.get("evaluation_capabilities"), "evaluation_capabilities")
    ai = c.obj(capabilities.get("ai_evaluation"), "ai_evaluation")
    if ai.get("enabled") is True:
        for key in ("evaluator_identifier", "evaluator_version", "prompt_version", "rubric_version"):
            c.text(ai.get(key), f"ai_evaluation.{key}")
        c.strings(ai.get("objective_identifiers"), "ai_evaluation.objectives", False)
        materials = c.strings(ai.get("configuration_evidence_references"), "ai.configuration", False)
        validation = c.obj(ai.get("validation_binding"), "ai.validation_binding")
        for key in ("evaluator_identifier", "evaluator_version", "prompt_version", "rubric_version",
                    "objective_identifiers"):
            c.need(validation.get(key) == ai.get(key), f"AI validation binding differs: {key}")
        expected = {}
        for reference in refs(materials, "AI configuration references", binding=True):
            try:
                expected[reference] = file_digest(c.path(evidence[reference]["path"]))
            except (OSError, ValueError):
                pass
        c.need(validation.get("configuration_fingerprints") == expected,
               "AI evaluator/prompt/rubric content changed")
        refs(ai.get("validation_evidence_references"), "AI validation evidence", binding=True)
        c.need(ai.get("fallback") in ("human_review", "self_review"), "AI fallback must be executable review mode")
    if rank >= 6:
        result = c.obj(data.get("effect_result"), "effect_result")
        c.need(result.get("conclusion") in ("supported", "not_supported", "inconclusive"),
               "effect_result.conclusion invalid")
        for key in ("conditions", "uncertainty", "retention_and_transfer_scope"):
            c.text(result.get(key), f"effect_result.{key}")
        c.strings(result.get("objective_identifiers"), "effect_result.objectives", False)
        refs(result.get("evidence_references"), "effect_result.evidence", binding=True)

    # Run the current structural checks after lifecycle checks. This is the
    # single current manifest contract; it is not a legacy migration path.
    normalized = copy.deepcopy(data)
    normalized["learner_delivery_type"] = delivery_type
    normalized_stages = STAGES[:-1] + ["effect_evaluated"]
    normalized["current_status"] = normalized_stages[max(rank, 0)]
    normalized["status_history"] = [
        {"status": stage, "recorded_at": "event-replay",
         "evidence_references": history[0].get("evidence_references", []) if history else []}
        for stage in normalized_stages[:max(rank, 0) + 1]
    ]
    normalized["approval_gates"] = filtered_gates
    # The base structural checker owns the established production fields.
    # Checkpoint schemas and bindings are checked above, outside its seven-stage view.
    normalized["approval_subjects"] = [
        row for row in normalized["approval_subjects"]
        if row.get("kind") not in {"clarification", "demo"}
    ]
    normalized["approval_gates"] = {
        key: value for key, value in filtered_gates.items()
        if key in {"design_confirmation", "media_sample_confirmation"}
    }
    for asset in normalized.get("assets", []) if isinstance(normalized.get("assets"), list) else []:
        if isinstance(asset, dict) and isinstance(asset.get("delivery"), dict):
            asset["delivery"]["formal_linear_video"] = False
    c.errors.extend(structure_validator(normalized, c.base, allow_placeholders, allow_missing_files))
    if replay_result is not None:
        replay_result.update(active=active, rank=rank)
    return c.errors


def validate_joint(data, base, complete=True):
    """Validate current blueprint, resources, evidence phases and record fields together."""
    from validate_course import validate as validate_blueprint
    c = Checks(base)
    data = c.obj(data, "manifest")
    scope = c.obj(data.get("work_scope"), "work_scope")
    if scope.get("scope_type") == "media_assets":
        c.need(False, "joint course validation requires the parent course manifest")
        return c.errors
    from demo_contract import validate_joint_demo
    c.errors.extend(validate_joint_demo(data, c.base))
    evidence = {}
    for row in c.rows(data.get("evidence_files"), "evidence_files"):
        if isinstance(row.get("reference_identifier"), str):
            evidence[row["reference_identifier"]] = row
    blueprints = [row for row in evidence.values() if row.get("kind") == "course_blueprint"]
    c.need(len(blueprints) == 1, "joint validation requires exactly one course_blueprint")
    if len(blueprints) != 1:
        return c.errors
    try:
        blueprint_path = c.path(blueprints[0].get("path"))
        blueprint = json.loads(blueprint_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return c.errors + [f"Cannot read blueprint: {exc}"]
    blueprint = c.obj(blueprint, "blueprint")
    status = data.get("current_status")
    rank = STAGES.index(status) if status in STAGES else 0
    c.errors.extend(validate_blueprint(
        blueprint,
        blueprint_path.parent,
        complete_design=complete,
        ready_media=rank >= 3,
        full_course=scope.get("scope_type") == "full_course",
    ))
    for key in ("course_identifier", "course_version"):
        c.need(data.get(key) == blueprint.get(key), f"blueprint/manifest {key} differs")
    objectives = {row.get("objective_identifier") for row in c.rows(
        blueprint.get("learning_objectives"), "blueprint.objectives")
        if isinstance(row.get("objective_identifier"), str)}
    included = c.strings(scope.get("covered_objective_identifiers"), "scope.objectives", False)
    c.need(set(included) == objectives, "scope objectives must exactly match this scoped blueprint")
    sources = {row.get("source_identifier"): row for row in c.rows(
        blueprint.get("sources"), "blueprint.sources") if isinstance(row.get("source_identifier"), str)}
    from validate_content_quality import validate_manifest_content
    c.errors.extend(validate_manifest_content(data, c.base, approved=rank >= 1,
                                             objectives=objectives, sources=set(sources)))
    for row in c.rows(data.get("evidence_registry"), "evidence_registry"):
        for reference in c.strings(row.get("source_references"), "registry.sources"):
            c.need(reference in sources, f"unknown source reference: {reference}")
    assets = {row.get("asset_identifier"): row for row in c.rows(data.get("assets"), "assets")
              if isinstance(row.get("asset_identifier"), str)}
    resources = c.rows(blueprint.get("media_resources"), "blueprint.media_resources")
    required_resources = set()
    for resource in resources:
        identifier = resource.get("resource_identifier")
        if resource.get("required") is not True:
            continue
        if isinstance(identifier, str):
            required_resources.add(identifier)
        asset = assets.get(identifier, {}) if isinstance(identifier, str) else {}
        c.need(bool(asset) and asset.get("required") is True, f"required resource lacks asset: {identifier}")
        media_type = resource.get("media_type")
        allowed = MEDIA_KINDS.get(media_type, set()) if isinstance(media_type, str) else set()
        c.need(asset.get("kind") in allowed if isinstance(asset.get("kind"), str) else False,
               f"{identifier}: blueprint media type differs from asset kind")
        if rank >= 3:
            c.need(asset.get("status") == "accepted" and resource.get("production_status") == "ready",
                   f"{identifier}: blueprint readiness and formal asset acceptance differ")
            files = c.rows(asset.get("files"), f"{identifier}.files")
            try:
                expected_path = blueprint_path.parent / resource.get("file_path")
                c.need(any(c.path(row.get("path")).resolve() == expected_path.resolve() for row in files),
                       f"{identifier}: blueprint file not present in asset files")
            except (TypeError, ValueError):
                c.need(False, f"{identifier}: missing or invalid file path")
    c.need(required_resources.issubset(c.strings(scope.get("covered_asset_identifiers"), "scope.assets")),
           "scope omits required blueprint resources")
    plan = c.obj(blueprint.get("evaluation_plan"), "evaluation_plan")
    records = c.obj(data.get("learning_records"), "learning_records")
    fields = c.strings(plan.get("record_fields"), "blueprint.record_fields")
    c.need(set(fields) == set(c.strings(records.get("minimum_fields"), "manifest.minimum_fields")),
           "blueprint and manifest learning record fields differ")
    required_states = {"submission_status", "evaluation_status", "assistance_status",
                       "objective_performance", "evaluation_source"}
    c.need(required_states.issubset(fields), "joint record contract missing separate answer/review/help states")
    for scene in c.rows(blueprint.get("scenes"), "scenes"):
        task = scene.get("task")
        if isinstance(task, dict):
            outcomes = c.obj(task.get("outcomes"), "task.outcomes")
            if "continue_after_review" in outcomes:
                conditions = c.obj(task.get("outcome_conditions"), "task.outcome_conditions")
                entries = c.strings(conditions.get("continue_after_review"), "continue_after_review", False)
                c.need({"attempt_saved", "feedback_viewed"}.issubset(entries),
                       "continue_after_review requires saved attempt and viewed feedback")
    for name, stage_rank, evidence_kind in (
        ("design_review", 1, "verification"), ("learner_trial", 5, "learner_trial"),
        ("learning_effectiveness", 6, "effect_evaluation"),
    ):
        phase = c.obj(plan.get(name), f"evaluation_plan.{name}")
        completed = phase.get("status") == "completed"
        c.need((completed == (rank >= stage_rank)) or (name == "design_review" and rank == 0),
               f"evaluation_plan.{name}: completion differs from current course stage")
        for reference in c.strings(phase.get("evidence_references"), f"{name}.evidence", not completed):
            entry = evidence.get(reference)
            c.need(entry is not None, f"{name}: evidence not registered: {reference}")
            if entry is not None and completed:
                c.need(entry.get("kind") == evidence_kind, f"{reference}: wrong phase evidence kind")
                if entry.get("course_version") != data.get("course_version"):
                    bound = c.obj(entry.get("bound_versions"), f"{reference}.bound_versions")
                    versions = {
                        row.get("scope_identifier"): row.get("subject_version") for row in c.rows(
                            data.get("approval_subjects"), "approval_subjects")
                        if isinstance(row.get("scope_identifier"), str)
                    }
                    c.need(bool(bound) and all(versions.get(key) == version for key, version in bound.items()),
                           f"{reference}: outdated evidence scope versions")
                c.need(set(included).issubset(c.strings(entry.get("bound_identifiers"),
                                                       f"{reference}.bound_identifiers")),
                       f"{reference}: evidence omits scoped objectives")
                c.matches(entry.get("path"), entry.get("content_sha256"), reference)
    return c.errors
