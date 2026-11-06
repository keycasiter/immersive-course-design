#!/usr/bin/env python3
"""Read-only supplied-media and selected-video reuse checks; no provider calls."""

import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
import tempfile

from submission_contract import (
    expected_contract, inspect_attempt, local_path, object_rows, read_object,
)


IMAGE_FORMATS = {
    "png_pipe", "jpeg_pipe", "webp_pipe", "tiff_pipe", "bmp_pipe",
    "image2", "image2pipe", "gif", "apng",
}


def digest(path):
    checksum = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            checksum.update(block)
    return checksum.hexdigest()


def text(value):
    return isinstance(value, str) and bool(value.strip()) and "{{" not in value


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def verified_file(base, name, checksum):
    path = local_path(base, name).resolve()
    require(path.is_file(), "missing actual file")
    require(digest(path) == checksum, "file SHA256 changed or missing")
    return path


def run(command):
    try:
        result = subprocess.run(command, capture_output=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ValueError(f"media tool unavailable or timed out: {exc}") from exc
    require(result.returncode == 0,
            "media inspection failed: " + result.stderr.decode("utf-8", "replace")[-800:])
    return result.stdout


def inspect_media(path, kind):
    require(kind in ("image", "audio", "video"), "unsupported media kind")
    profile = json.loads(run([
        "ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path),
    ]))
    streams = profile.get("streams", [])
    wanted = "audio" if kind == "audio" else "video"
    selected = [row for row in streams if row.get("codec_type") == wanted]
    require(bool(selected), f"missing {wanted} stream")
    formats = set(profile.get("format", {}).get("format_name", "").split(","))
    if kind == "image":
        require(bool(formats & IMAGE_FORMATS), "image requires a raster image container")
    elif kind == "video":
        require(not formats & IMAGE_FORMATS, "video requires a video container")
    if wanted == "video":
        require(selected[0].get("width", 0) > 0 and selected[0].get("height", 0) > 0,
                "missing actual image dimensions")
    durations = []
    for row in selected + [profile.get("format", {})]:
        try:
            number = float(row.get("duration"))
            if math.isfinite(number) and number > 0:
                durations.append(number)
        except (TypeError, ValueError):
            pass
    duration = max(durations, default=None)
    if kind != "image":
        require(duration is not None, "missing actual media duration")
    command = ["ffmpeg", "-v", "error", "-xerror", "-nostdin", "-i", str(path)]
    command += ["-map", "0:a:0"] if kind == "audio" else ["-map", "0:v:0", "-map", "0:a?"]
    run(command + ["-f", "null", "-"])
    return {"kind": kind, "format": sorted(formats), "duration_seconds": duration}


def extract_frame(source, at_seconds, destination):
    """The evidence generator and validator use exactly the same extraction."""
    require(isinstance(at_seconds, (int, float)) and not isinstance(at_seconds, bool)
            and math.isfinite(at_seconds) and at_seconds >= 0, "invalid frame time")
    run([
        "ffmpeg", "-v", "error", "-xerror", "-nostdin", "-i", str(source),
        "-ss", format(at_seconds, ".9f"), "-map", "0:v:0", "-frames:v", "1",
        "-vf", "scale=w=min(640\\,iw):h=-2", "-threads", "1",
        "-f", "image2", "-c:v", "png", "-n", str(destination),
    ])
    require(Path(destination).is_file(), "frame extraction produced no image")


def inspect_review(review, checksum, base):
    require(isinstance(review, dict), "missing content review")
    require(review.get("status") == "passed", "content review is not passed")
    require(text(review.get("reviewer")), "missing actual reviewer")
    require(review.get("bound_sha256") == checksum, "content review binds an old file")
    evidence = verified_file(base, review.get("evidence_file"), review.get("evidence_sha256"))
    require(evidence.stat().st_size > 0, "empty content evidence")
    observations = review.get("observations")
    require(isinstance(observations, list) and bool(observations)
            and all(text(value) for value in observations), "missing actual content observations")


def unique_rows(value, field):
    rows = object_rows(value)
    identifiers = [row.get(field) for row in rows]
    require(all(text(value) for value in identifiers), f"missing {field}")
    require(len(set(identifiers)) == len(identifiers), f"duplicate {field}")
    return {row[field]: row for row in rows}


def validate_sources(record, base):
    errors, measurements = [], []
    try:
        require(record.get("schema_version") == "1.0", "source schema must be 1.0")
        sources = unique_rows(record.get("declared_sources"), "source_identifier")
        reviews = unique_rows(record.get("reviews"), "source_identifier")
        state = record.get("input_state")
        require(state in ("not_supplied", "supplied"), "invalid input_state")
        if state == "not_supplied":
            require(not sources and not reviews, "not_supplied cannot conceal declared inputs")
            return [], [{"input_state": "not_supplied"}]
        require(bool(sources), "supplied cannot have an empty inventory")
        require(set(sources) == set(reviews), "every supplied input requires exactly one review")
    except (ValueError, TypeError, KeyError) as exc:
        return [str(exc)], measurements
    sample_paths = set()
    for identifier, source in sources.items():
        try:
            review = reviews[identifier]
            require(text(source.get("purpose")), "missing source purpose")
            require(review.get("status") in ("passed", "failed"), "invalid source review status")
            if review.get("status") == "failed":
                require(text(review.get("failure_reason")), "failed input requires its reason")
                raise ValueError("input review failed: " + review["failure_reason"])
            media = verified_file(base, source.get("path"), source.get("content_sha256"))
            checksum = source["content_sha256"]
            require(review.get("source_sha256") == checksum, "source review binds an old file")
            profile = inspect_media(media, source.get("kind"))
            inspect_review(review.get("content_review"), checksum, base)
            samples = object_rows(review.get("frame_samples"))
            require(source["kind"] == "video" or not samples, "only video has frame_samples")
            if source["kind"] == "video":
                require(bool(samples), "video requires observed frame evidence")
            for sample in samples:
                require(sample.get("source_identifier") == identifier
                        and sample.get("source_sha256") == checksum,
                        "frame evidence belongs to another source")
                at = sample.get("at_seconds")
                require(isinstance(at, (float, int)) and not isinstance(at, bool)
                        and math.isfinite(at) and 0 <= at < profile["duration_seconds"],
                        "frame time outside actual video")
                saved = verified_file(base, sample.get("path"), sample.get("content_sha256"))
                require(saved not in sample_paths, "frame evidence path reused across samples")
                sample_paths.add(saved)
                with tempfile.TemporaryDirectory(prefix="source-admission-") as directory:
                    frame = Path(directory) / "frame.png"
                    extract_frame(media, at, frame)
                    require(digest(frame) == sample["content_sha256"],
                            "frame pixels do not match this source and time")
            require(digest(media) == checksum, "source changed during inspection")
            measurements.append({"source_identifier": identifier, "source_sha256": checksum, **profile})
        except (OSError, ValueError, TypeError, KeyError, OverflowError) as exc:
            errors.append(f"{identifier}: {exc}")
    return errors, measurements


def validate_reuse(record, base, materialized=False, record_path=None):
    try:
        require(record.get("schema_version") == "1.0", "reuse schema must be 1.0")
        require(record.get("operation") == "reuse_selected_asset", "unverified reuse operation")
        job_path = verified_file(base, record.get("source_job_file"), record.get("source_job_sha256"))
        job = read_object(job_path)
        require(job.get("schema_version") == "1.1", "reuse requires original Job 1.1 readback")
        require(job.get("terminal_phase") == "accepted" and job.get("phase") == "accepted",
                "original job is not accepted")
        attempts = unique_rows(job.get("attempts"), "attempt_identifier")
        chosen = record.get("source_attempt_identifier")
        require(chosen in attempts, "unknown original attempt")
        path_key = record.get("source_output_path")
        require(text(path_key) and path_key in job.get("output_paths", []), "undeclared original output")
        require(isinstance(job.get("output_attempt_identifiers"), dict)
                and job["output_attempt_identifiers"].get(path_key) == chosen, "wrong original output attempt")
        checksum = record.get("output_sha256")
        require(isinstance(job.get("output_sha256"), dict)
                and job["output_sha256"].get(path_key) == checksum, "original output SHA mismatch")
        output = verified_file(job_path.parent, path_key, checksum)
        normalized, readback = inspect_attempt(attempts[chosen], job_path.parent)
        plan_path = verified_file(base, record.get("current_plan_file"), record.get("current_plan_sha256"))
        plan = read_object(plan_path)
        require(plan.get("schema_version") == "1.2", "reuse requires current video plan 1.2")
        units = unique_rows(plan.get("generation_units"), "unit_identifier")
        unit = units.get(record.get("current_unit_identifier"))
        require(unit is not None, "unknown current unit")
        require(unit.get("output_attempt_identifier") == chosen, "current unit adopts another attempt")
        current_job = local_path(plan_path.parent, unit.get("job_file")).resolve()
        require(current_job == job_path, "current unit must retain original Job provenance")
        require(unit.get("output_sha256") == checksum, "current unit output SHA differs")
        destination = local_path(base, record.get("destination_path")).resolve()
        current_output = local_path(plan_path.parent, unit.get("output_file")).resolve()
        require(current_output in {output, destination},
                "current plan points outside the declared adopted output")
        if record_path is not None:
            require(local_path(plan_path.parent, unit.get("asset_reuse_file")).resolve()
                    == Path(record_path).resolve(), "current plan does not reference this reuse record")
        registry_path = verified_file(plan_path.parent, plan.get("utterance_registry_file"),
                                      plan.get("utterance_registry_sha256"))
        expected, speech, contract_hash = expected_contract(plan, unit, read_object(registry_path))
        require(expected == normalized, "current request differs from original accepted request")
        require(unit.get("requested_duration_seconds") == normalized["parameters"]["duration"],
                "current duration differs from original request")
        provider = readback.get("provider_identifier")
        require(text(provider) and provider == unit.get("provider_identifier") == job.get("provider"),
                "current provider differs from original readback")
        require(record.get("current_production_contract_sha256") == contract_hash,
                "current production contract identity changed")
        require(readback.get("production_contract_sha256") == contract_hash,
                "current authority or production contract differs from original")
        old_bindings = readback.get("utterance_bindings")
        require(isinstance(old_bindings, list), "missing original utterance bindings")
        keys = ("event_identifier", "utterance_identifier", "utterance_version", "text_sha256")
        require([{key: row.get(key) for key in keys} for row in object_rows(old_bindings)]
                == [{key: row.get(key) for key in keys} for row in speech],
                "current utterance authority differs from original")
        for line, binding in zip(speech, old_bindings):
            start, end = binding.get("prompt_start"), binding.get("prompt_end")
            if line["audio_source"] == "embedded_native":
                require(type(start) is int and type(end) is int
                        and 0 <= start < end <= len(normalized["prompt"])
                        and normalized["prompt"][start:end] == line["text"],
                        "original native dialogue binding differs from authority")
            else:
                require(start is None and end is None, "external voice was misreported as native")
        inspect_review(record.get("reuse_review"), checksum, base)
        profile = inspect_media(output, "video")
        require("mp4" in profile["format"], "current GenerateVideo output requires an actual MP4 container")
        require(destination.suffix.lower() == output.suffix.lower(), "destination changes output format suffix")
        if materialized:
            require(destination.is_file(), "destination has not been materialized")
        if destination.exists():
            require(destination.is_file() and digest(destination) == checksum,
                    "destination exists with different content; preserve it")
            if materialized:
                inspect_media(destination, "video")
        require(digest(output) == checksum, "original output changed during inspection")
        return [], [{"operation": "reuse_selected_asset", "source_attempt_identifier": chosen,
                     "output_sha256": checksum, "materialized": materialized, **profile}]
    except (OSError, ValueError, TypeError, KeyError, OverflowError) as exc:
        return [str(exc)], []


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("branch", choices=("source", "reuse"))
    parser.add_argument("record", type=Path)
    parser.add_argument("--materialized", action="store_true",
                        help="Reuse only: require and decode the actual destination")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    errors, measurements = [], []
    try:
        require(args.branch == "reuse" or not args.materialized, "--materialized is reuse only")
        record = read_object(args.record)
        if args.branch == "source":
            errors, measurements = validate_sources(record, args.record.resolve().parent)
        else:
            errors, measurements = validate_reuse(
                record, args.record.resolve().parent, args.materialized, args.record.resolve())
    except (OSError, ValueError, TypeError, KeyError) as exc:
        errors.append(str(exc))
    report = {
        "schema_version": "1.0", "branch": args.branch,
        "stage": "materialized" if args.materialized else "admission",
        "status": "failed" if errors else "passed", "errors": errors, "measurements": measurements,
        "limits": "Checks file identity, decoding and recorded observations; not truth, rights, full viewing, or runtime.",
    }
    payload = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    if args.report:
        require(args.report.parent.is_dir(), "report parent directory must exist")
        args.report.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
