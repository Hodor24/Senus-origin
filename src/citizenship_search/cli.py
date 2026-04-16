from __future__ import annotations

import argparse
import json
from dataclasses import asdict

from citizenship_search.models import CaseFile
from citizenship_search.workflow import build_discovery_outputs


def main() -> None:
    parser = argparse.ArgumentParser(description="Discovery-first citizenship records search helper.")
    parser.add_argument("--query", default="Roman Senus Stryj 1957")
    args = parser.parse_args()

    case_file = CaseFile.for_roman_senus()
    outputs = build_discovery_outputs(case_file, args.query)
    serializable = {
        **outputs,
        "archive_requests": [asdict(r) for r in outputs["archive_requests"]],
        "translation_records": [asdict(t) for t in outputs["translation_records"]],
    }
    print(json.dumps(serializable, indent=2))


if __name__ == "__main__":
    main()
