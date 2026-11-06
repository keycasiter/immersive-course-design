"""Read actual serialized tool arguments; compare them with the current video contract.

This is a pre-submit check, not a provider receipt or proof of generated content.
The canonical request contains semantic fields, not credentials or personal paths.
"""
import hashlib
import json
from pathlib import Path


def canonical_digest(value):
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                         allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def file_digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def local_path(base, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Expected a non-empty local file path")
    path = Path(value)
    return path if path.is_absolute() else Path(base) / path


def read_object(path):
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Expected a JSON object")
    return value


def object_rows(value):
    if not isinstance(value, list) or any(not isinstance(row, dict) for row in value):
        raise ValueError("Expected an array of objects")
    return value


def normalize_request(raw, adapter, manifest, base):
    """Derive from actual arguments; unknown adapters fail closed."""
    if adapter != "trae_generate_video_v1":
        raise ValueError("unverified submission adapter")
    if raw.get("tool") != "functions.GenerateVideo":
        raise ValueError("Adapter requires functions.GenerateVideo arguments")
    args = raw.get("arguments")
    allowed = {"prompt", "image_paths", "video_paths", "file_path", "resolution", "ratio", "duration"}
    if not isinstance(args, dict) or set(args) - allowed:
        raise ValueError("Unsupported or unknown tool arguments")
    if not isinstance(args.get("prompt"), str) or not args["prompt"].strip():
        raise ValueError("Missing serialized prompt")
    duration = args.get("duration", 5)
    if isinstance(duration, bool) or not isinstance(duration, int) or not 4 <= duration <= 15:
        raise ValueError("Formal request requires a concrete supported duration")
    resolution, ratio = args.get("resolution", "720p"), args.get("ratio", "adaptive")
    if resolution not in ("480p", "720p") or ratio not in (
            "16:9", "4:3", "1:1", "3:4", "9:16", "21:9", "adaptive"):
        raise ValueError("Unsupported serialized output parameters")
    destination = local_path(base, args.get("file_path"))
    references = []
    bindings = {}
    for row in object_rows(manifest):
        slot = row.get("slot")
        if not isinstance(slot, str) or not slot or slot in bindings:
            raise ValueError("Missing or duplicate reference slot")
        bindings[slot] = row
    for kind, limit in (("image_paths", 9), ("video_paths", 3)):
        paths = args.get(kind, [])
        if not isinstance(paths, list) or len(paths) > limit:
            raise ValueError("Invalid serialized reference array")
        for index, value in enumerate(paths):
            slot = f"{kind}[{index}]"
            row = bindings.pop(slot, None)
            if row is None:
                raise ValueError(f"Undeclared actual reference slot {slot}")
            actual = local_path(base, value)
            registered = local_path(base, row.get("path"))
            checksum = file_digest(actual)
            if actual.resolve() != registered.resolve() or checksum != row.get("content_sha256"):
                raise ValueError(f"Actual reference file differs at {slot}")
            if not all(isinstance(row.get(key), str) and row[key].strip()
                       for key in ("reference_identifier", "purpose")):
                raise ValueError("Reference identity and purpose are required")
            expected_kind = "image" if kind == "image_paths" else "video"
            purposes = {"identity", "scene", "prop", "first_frame", "last_frame"} if expected_kind == "image" else {"previous_clip"}
            if row.get("kind") != expected_kind or row["purpose"] not in purposes:
                raise ValueError("Tool slot cannot carry the declared reference kind or purpose")
            references.append({
                "reference_identifier": row["reference_identifier"], "slot": slot,
                "purpose": row["purpose"], "content_sha256": checksum,
            })
    if bindings:
        raise ValueError("Declared reference slots were not actually submitted")
    # GenerateVideo exposes no model-selection or audio-reference argument.
    # Never manufacture either capability from metadata or voice descriptions.
    return {
        "adapter_identifier": adapter,
        "tool": raw["tool"],
        "model": "unknown",
        "parameters": {"duration": duration, "resolution": resolution, "ratio": ratio},
        "prompt": args["prompt"],
        "reference_bindings": references,
        "output_contract": {"file_name": destination.name if destination.suffix
                            else destination.name + ".mp4"},
    }


def inspect_attempt(attempt, base):
    """Return a recomputed request and readback; never trust a passed label."""
    record = attempt.get("submission_readback")
    if not isinstance(record, dict):
        raise ValueError("Missing submission_readback")
    path = local_path(base, record.get("serialized_request_file"))
    serialized = path.read_bytes()
    if hashlib.sha256(serialized).hexdigest() != record.get("serialized_request_sha256"):
        raise ValueError("Serialized request changed after readback")
    raw = json.loads(serialized)
    if not isinstance(raw, dict):
        raise ValueError("Expected a serialized request object")
    normalized = normalize_request(
        raw, record.get("adapter_identifier"), record.get("reference_manifest"), base)
    if record.get("normalized_request") != normalized:
        raise ValueError("Stored normalized request differs from actual serialized arguments")
    if attempt.get("request_sha256") != canonical_digest(normalized):
        raise ValueError("request_sha256 differs from the recomputed request")
    return normalized, record


def validate_job_readbacks(job, base, errors, label):
    attempts = job.get("attempts", [])
    if not isinstance(attempts, list):
        return
    active = job.get("active_attempt_identifier")
    known = {row.get("attempt_identifier"): row for row in attempts if isinstance(row, dict)
             and isinstance(row.get("attempt_identifier"), str)}
    if active is not None and active not in known:
        errors.append(f"{label}: unknown active attempt")
    for identifier, attempt in known.items():
        if attempt.get("submission_readback") is None:
            if job.get("schema_version") == "1.1":
                errors.append(f"{label}.{identifier}: missing submission_readback; historical evidence is unverified")
            continue
        try:
            inspect_attempt(attempt, base)
            if identifier == active and job.get("request_sha256") != attempt.get("request_sha256"):
                raise ValueError("Active request differs from job request_sha256")
        except (OSError, ValueError, TypeError, KeyError) as exc:
            errors.append(f"{label}.{identifier}: {exc}")


def expected_contract(plan, unit, registry):
    declarations = unit.get("submission_expectations")
    if not isinstance(declarations, dict):
        raise ValueError("Missing submission_expectations")
    references = {row["reference_identifier"]: row for row in object_rows(plan.get("references"))}
    bindings = []
    for binding in object_rows(unit.get("reference_bindings")):
        reference = references[binding["reference_identifier"]]
        bindings.append({key: binding[key] for key in ("reference_identifier", "slot", "purpose")} |
                        {"content_sha256": reference["content_sha256"]})
    # Sort by the actual tool's positional arrays; document order is not a new slot order.
    def slot_order(row):
        slot = row["slot"]
        kind, _, index = slot.partition("[")
        return (0 if kind == "image_paths" else 1, int(index.rstrip("]")))
    bindings.sort(key=slot_order)
    expected = {
        "adapter_identifier": declarations.get("adapter_identifier"),
        "tool": "functions.GenerateVideo", "model": declarations.get("model"),
        "parameters": declarations.get("parameters"), "prompt": unit.get("prompt"),
        "reference_bindings": bindings, "output_contract": declarations.get("output_contract"),
    }
    utterances = {row["utterance_identifier"]: row
                  for row in object_rows(registry.get("utterances"))}
    events = {row["event_identifier"]: row for row in object_rows(plan.get("sound_events"))}
    speech = []
    for identifier in unit.get("sound_event_identifiers", []):
        event = events[identifier]
        if event.get("kind") not in ("dialogue", "narration"):
            continue
        utterance = utterances[event["utterance_identifier"]]
        if not all(isinstance(utterance.get(key), str) and utterance[key].strip()
                   for key in ("utterance_version", "authority", "speaker_identifier", "text")):
            raise ValueError(f"{identifier}: authority requires version, source, speaker and text")
        checksum = hashlib.sha256(utterance["text"].encode("utf-8")).hexdigest()
        if (checksum != utterance.get("text_sha256") or event.get("text") != utterance["text"]
                or event.get("speaker_identifier") != utterance.get("speaker_identifier")):
            raise ValueError(f"{identifier}: current authority text or speaker differs")
        speech.append({
            "event_identifier": identifier, "utterance_identifier": event["utterance_identifier"],
            "utterance_version": utterance["utterance_version"], "text_sha256": checksum,
            "speaker_identifier": utterance["speaker_identifier"], "text": utterance["text"],
            "audio_source": event.get("audio_source"),
        })
    contract = {"unit_identifier": unit["unit_identifier"], "request": expected, "speech": speech}
    return expected, speech, canonical_digest(contract)


def validate_submission(plan, audit, selected_unit=None, delivery=False):
    """Compare current unit content, exact authority text and actual input bindings."""
    try:
        registry_path = audit.file(plan.get("utterance_registry_file"),
                                   plan.get("utterance_registry_sha256"), "utterance_registry")
        if registry_path is None:
            return
        registry = read_object(registry_path)
        identifiers = [row.get("utterance_identifier") for row in object_rows(registry.get("utterances"))]
        if any(not isinstance(item, str) or not item for item in identifiers) or len(set(identifiers)) != len(identifiers):
            raise ValueError("Invalid or duplicate authority utterance identifiers")
        units = object_rows(plan.get("generation_units"))
        if selected_unit is not None:
            units = [row for row in units if row.get("unit_identifier") == selected_unit]
            if len(units) != 1:
                raise ValueError("Pre-submit requires exactly one known unit")
        for unit in units:
            label = unit.get("unit_identifier", "unit")
            try:
                job_path = local_path(audit.base, unit.get("job_file"))
                job = read_object(job_path)
                if job.get("schema_version") != "1.1":
                    raise ValueError("Submission requires job schema 1.1")
                expected, speech, contract_hash = expected_contract(plan, unit, registry)
                attempts = object_rows(job.get("attempts"))
                attempt_ids = [row.get("attempt_identifier") for row in attempts]
                if (any(not isinstance(item, str) or not item for item in attempt_ids) or
                        len(set(attempt_ids)) != len(attempt_ids)):
                    raise ValueError("Attempt identifiers must be non-empty and unique")
                chosen = unit.get("output_attempt_identifier") if delivery else job.get("active_attempt_identifier")
                matches = [row for row in attempts if row.get("attempt_identifier") == chosen]
                if not isinstance(chosen, str) or not chosen or len(matches) != 1:
                    raise ValueError("Missing or ambiguous adopted/active attempt")
                normalized, record = inspect_attempt(matches[0], job_path.parent)
                if normalized != expected:
                    raise ValueError("Final request differs from current prompt, parameters, output or reference slots")
                if normalized["parameters"]["duration"] != unit.get("requested_duration_seconds"):
                    raise ValueError("Serialized duration differs from generation unit")
                if record.get("production_contract_sha256") != contract_hash:
                    raise ValueError("Current production contract changed after readback")
                provider = record.get("provider_identifier")
                if provider != unit.get("provider_identifier") or provider != job.get("provider"):
                    raise ValueError("Submission provider differs from current unit/job")
                bindings = object_rows(record.get("utterance_bindings"))
                bound = {row.get("event_identifier"): row for row in bindings}
                if len(bound) != len(bindings) or set(bound) != {row["event_identifier"] for row in speech}:
                    raise ValueError("Exact utterance bindings are incomplete or duplicated")
                for utterance in speech:
                    binding = bound[utterance["event_identifier"]]
                    for key in ("utterance_identifier", "utterance_version", "text_sha256"):
                        if binding.get(key) != utterance[key]:
                            raise ValueError("Submitted utterance binding differs from current authority")
                    if utterance["audio_source"] == "embedded_native":
                        start, end = binding.get("prompt_start"), binding.get("prompt_end")
                        if (type(start) is not int or type(end) is not int or
                                not 0 <= start < end <= len(normalized["prompt"]) or
                                normalized["prompt"][start:end] != utterance["text"]):
                            raise ValueError("Serialized dialogue differs character-for-character from authority")
                    elif binding.get("prompt_start") is not None or binding.get("prompt_end") is not None:
                        raise ValueError("External voice must not be misreported as submitted native dialogue")
                if delivery:
                    output = local_path(audit.base, unit.get("output_file"))
                    paths = job.get("output_paths", [])
                    matching = [item for item in paths if local_path(job_path.parent, item).resolve() == output.resolve()]
                    reused = False
                    if not matching and unit.get("asset_reuse_file"):
                        # The plan points to the sidecar; the sidecar binds this plan.
                        # No reverse sidecar SHA is added to the plan (a hash cycle).
                        from validate_media_admission import validate_reuse
                        reuse_path = local_path(audit.base, unit["asset_reuse_file"])
                        reuse = read_object(reuse_path)
                        if (read_object(local_path(reuse_path.parent, reuse.get("current_plan_file"))) != plan
                                or reuse.get("current_unit_identifier") != label
                                or reuse.get("source_attempt_identifier") != chosen
                                or local_path(reuse_path.parent, reuse.get("destination_path")).resolve()
                                != output.resolve()):
                            raise ValueError("Reuse sidecar does not bind this current plan and adopted output")
                        reuse_errors, _ = validate_reuse(
                            reuse, reuse_path.parent, materialized=True, record_path=reuse_path)
                        if reuse_errors:
                            raise ValueError("Reused output failed admission: " + "; ".join(reuse_errors))
                        reused = True
                    if not reused and (job.get("terminal_phase") != "accepted" or len(matching) != 1 or
                            not isinstance(job.get("output_attempt_identifiers"), dict) or
                            job["output_attempt_identifiers"].get(matching[0]) != chosen or
                            not isinstance(job.get("output_sha256"), dict) or
                            job["output_sha256"].get(matching[0]) != unit.get("output_sha256") or
                            file_digest(output) != unit.get("output_sha256")):
                        raise ValueError("Adopted output does not bind to the checked attempt and actual file")
                else:
                    if job.get("phase") not in ("planned", "preflight"):
                        raise ValueError("Already submitted task: recover original attempt instead of submitting again")
                    if job.get("request_sha256") != matches[0].get("request_sha256"):
                        raise ValueError("Active job request_sha256 differs")
                audit.measurements.append({
                    "unit_identifier": label, "attempt_identifier": chosen,
                    "request_sha256": matches[0]["request_sha256"],
                    "serialized_request_sha256": record["serialized_request_sha256"],
                    "production_contract_sha256": contract_hash, "status": "request_compared",
                })
            except (OSError, ValueError, TypeError, KeyError) as exc:
                audit.errors.append(f"{label}.submission: {exc}")
    except (OSError, ValueError, TypeError, KeyError) as exc:
        audit.errors.append(f"submission: {exc}")
