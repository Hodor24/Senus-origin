from __future__ import annotations

import argparse
import json

from citizenship_search.app import attach_translation, build_discovery_report, seed_case


def main() -> None:
    parser = argparse.ArgumentParser(description="Family discovery helper for Polish citizenship research.")
    parser.add_argument("--query", default="Roman Senus Stryj 1957")
    parser.add_argument("--include-demo-translation", action="store_true")
    args = parser.parse_args()

    case_file = seed_case()
    if args.include_demo_translation:
        attach_translation(
            case_file=case_file,
            source_name="Example Ukrainian note",
            text="Narodzony w Stryju, ojciec: Mikolaj.",
            original_language="uk",
        )

    report = build_discovery_report(case_file, args.query)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
