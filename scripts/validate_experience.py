#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
from experience_contract import validate_plan

def main():
    parser = argparse.ArgumentParser(description='Check the current experience plan; no semantic or visual acceptance.')
    parser.add_argument('plan', type=Path); args = parser.parse_args()
    try: errors = validate_plan(json.loads(args.plan.read_text()))
    except (OSError, ValueError) as exc: errors = [str(exc)]
    if errors: print('INVALID:\n' + '\n'.join('- ' + e for e in errors)); return 1
    print('VALID: experience structure and references; actual quality/participation not established'); return 0
if __name__ == '__main__': raise SystemExit(main())
