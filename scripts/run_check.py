#!/usr/bin/env python3
"""Capture one real check, with its complete output and original return code."""
import argparse
import datetime
import json
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import time


def stamp():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record", required=True, type=Path)
    parser.add_argument("--bind", action="append", type=Path, default=[], help="source/test input actually checked; repeat for each file")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        parser.error("a command is required after --")
    record = args.record.resolve()
    if not record.parent.is_dir():
        parser.error("the result directory must already exist")
    stdout = record.with_name(record.name + ".stdout.log")
    stderr = record.with_name(record.name + ".stderr.log")
    if any(path.exists() for path in (record, stdout, stderr)):
        parser.error("use a new record filename; existing evidence is preserved")
    bound = list(dict.fromkeys(path.resolve() for path in args.bind))
    if any(not path.is_file() for path in bound):
        parser.error("every bound input must be an existing file")
    snapshots = [{"path": str(path), "content_sha256": sha(path)} for path in bound]
    data = {
        "kind": "command_run",
        "command": command,
        "cwd": os.getcwd(),
        "started_at": stamp(),
        "stdout_reference": stdout.name,
        "stderr_reference": stderr.name,
        "input_snapshots": snapshots,
    }
    start = time.monotonic()
    with stdout.open("xb") as out, stderr.open("xb") as err:
        try:
            result = subprocess.run(command, stdout=out, stderr=err, check=False)
            data["exit_code"] = result.returncode
            data["execution_status"] = "completed"
        except OSError as error:
            data["exit_code"] = 127
            data["execution_status"] = "launch_failed"
            err.write((str(error) + "\n").encode())
    data["finished_at"] = stamp()
    data["elapsed_seconds"] = round(time.monotonic() - start, 6)
    data["stdout_sha256"] = sha(stdout)
    data["stderr_sha256"] = sha(stderr)
    data["inputs_unchanged"] = all(path.is_file() and sha(path) == item["content_sha256"] for path, item in zip(bound, snapshots))
    with record.open("x", encoding="utf-8") as output:
        output.write(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(data, ensure_ascii=False), flush=True)
    code = data["exit_code"]
    return (code if code >= 0 else 128 - code) if not (code == 0 and not data["inputs_unchanged"]) else 1


if __name__ == "__main__":
    sys.exit(main())
