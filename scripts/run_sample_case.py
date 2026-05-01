from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import argparse
import json

from backend.app.services.workflow_runner import get_runner


def main() -> None:
    parser = argparse.ArgumentParser(description='Run the seeded RemedAI sample case.')
    parser.add_argument('--sample', default='remediation_tender')
    parser.add_argument('--query', default='Should we bid on this tender?')
    args = parser.parse_args()

    result = get_runner().run_sample(sample_id=args.sample, query=args.query)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
