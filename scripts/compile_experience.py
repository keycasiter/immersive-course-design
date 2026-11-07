#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
from experience_contract import compile_design, compile_index, validate_plan

def main():
    parser = argparse.ArgumentParser(description='Derive a readable experience manuscript and runtime index without acceptance claims.')
    parser.add_argument('plan', type=Path); parser.add_argument('--out', required=True, type=Path); args = parser.parse_args()
    try:
        plan = json.loads(args.plan.read_text()); errors = validate_plan(plan)
        if errors: print('INVALID:\n' + '\n'.join(errors)); return 1
        args.out.mkdir(parents=True, exist_ok=True)
        (args.out / 'experience.md').write_text(compile_design(plan))
        (args.out / 'scene-index.json').write_text(json.dumps(compile_index(plan), ensure_ascii=False, indent=2) + '\n')
    except (OSError, ValueError) as exc: print('INVALID: ' + str(exc)); return 1
    print('Derived experience.md and scene-index.json; no approvals or checks created.'); return 0
if __name__ == '__main__': raise SystemExit(main())
