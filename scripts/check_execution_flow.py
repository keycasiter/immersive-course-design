#!/usr/bin/env python3
"""Exercise failure evidence, literal arguments, and preservation on rerun."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile


RUNNER = Path(__file__).with_name("run_check.py")


def main():
    with tempfile.TemporaryDirectory(prefix="course-command-evidence-") as folder:
        root = Path(folder)
        record = root / "failed.json"
        literal = "$(printf SHOULD_NOT_EXECUTE)`uname`; echo unsafe"
        command = [
            sys.executable, str(RUNNER), "--record", str(record), "--",
            sys.executable, "-c",
            "import sys; print(sys.argv[1]); print('failure detail', file=sys.stderr); sys.exit(7)",
            literal,
        ]
        result = subprocess.run(command, capture_output=True, text=True)
        assert result.returncode == 7, result
        data = json.loads(record.read_text())
        assert data["exit_code"] == 7 and data["execution_status"] == "completed"
        assert (root / data["stdout_reference"]).read_text() == literal + "\n"
        assert (root / data["stderr_reference"]).read_text() == "failure detail\n"
        before = {p.name: p.read_bytes() for p in root.iterdir()}
        repeat = subprocess.run(command, capture_output=True, text=True)
        assert repeat.returncode == 2
        assert before == {p.name: p.read_bytes() for p in root.iterdir()}
        missing = root / "missing.json"
        failure = subprocess.run(
            [sys.executable, str(RUNNER), "--record", str(missing), "--",
             str(root / "nonexistent-command")],
            capture_output=True, text=True,
        )
        assert failure.returncode == 127
        assert json.loads(missing.read_text())["execution_status"] == "launch_failed"
        success = root / "success.json"
        passed = subprocess.run(
            [sys.executable, str(RUNNER), "--record", str(success), "--",
             sys.executable, "-c", "print('record_contract_status=valid; coverage=false')"],
            capture_output=True, text=True,
        )
        assert passed.returncode == 0
        assert "acceptance_status" not in json.loads(success.read_text())
        long_record = root / "full-output.json"
        long_result = subprocess.run(
            [sys.executable, str(RUNNER), "--record", str(long_record), "--",
             sys.executable, "-c", "print('x'*100000); print('LAST'); raise SystemExit(3)"],
            capture_output=True, text=True,
        )
        assert long_result.returncode == 3
        log = root / json.loads(long_record.read_text())["stdout_reference"]
        assert log.stat().st_size > 100000 and log.read_text().endswith("LAST\n")
    print("5 command evidence scenarios passed")


if __name__ == "__main__":
    main()
