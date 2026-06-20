#!/usr/bin/env python3
"""Create a benchmark case folder."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


CASE_PART_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def parse_csv(raw: str) -> list[str]:
    return [item.strip() for item in raw.split(",") if item.strip()]


def parse_case_ref(raw: str) -> tuple[str, str]:
    parts = raw.split("/")
    if len(parts) != 2 or not all(CASE_PART_RE.fullmatch(part) for part in parts):
        raise argparse.ArgumentTypeError("case must look like suite-id/case-id")
    return parts[0], parts[1]


def build_case_json(
    case_ref: str,
    suite: str,
    harnesses: list[str],
    skills: list[str],
    work_type: str,
    artifact_types: list[str],
    prompt_tier: str,
    developer_prompt_chars: int,
    developer_prompt_words: int,
    full_input_min_tokens: int,
    full_input_max_tokens: int,
) -> str:
    data = {
        "id": case_ref,
        "title": "TODO: Short case title",
        "suite": suite,
        "objective": "TODO: Behavior this case is meant to measure.",
        "work_type": work_type,
        "artifact_types": artifact_types,
        "prompt_profile": {
            "developer_prompt_tier": prompt_tier,
            "developer_prompt_chars": developer_prompt_chars,
            "developer_prompt_words": developer_prompt_words,
            "full_input_token_range": {
                "min": full_input_min_tokens,
                "max": full_input_max_tokens,
            },
            "calibration": "TODO: Explain which empirical prompt-length tier this case targets.",
        },
        "harnesses": harnesses,
        "skill_refs": skills,
        "prompt": "prompt.md",
        "rubric": "rubric.md",
        "tags": [],
        "inputs": {
            "workspace": "none",
            "network": False,
            "requires_tools": False,
        },
        "expected_outputs": [],
        "evaluation": {
            "mode": "human-rubric",
            "max_score": 10,
        },
    }
    return json.dumps(data, indent=2) + "\n"


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def update_suite(root: Path, suite: str, case_ref: str) -> Path:
    suites_dir = root / "benches" / "suites"
    suites_dir.mkdir(parents=True, exist_ok=True)
    suite_file = suites_dir / f"{suite}.json"

    if suite_file.exists():
        data = json.loads(suite_file.read_text(encoding="utf-8"))
    else:
        data = {
            "id": suite,
            "title": "TODO: Suite title",
            "description": "TODO: Suite description.",
            "cases": [],
        }

    cases = data.get("cases")
    if not isinstance(cases, list):
        raise ValueError(f"{suite_file} has a non-list cases field")
    if case_ref not in cases:
        cases.append(case_ref)

    write_json(suite_file, data)
    return suite_file


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", type=parse_case_ref, help="Case id, e.g. dev-daily/my-case")
    parser.add_argument(
        "--harnesses",
        default="codex",
        help="Comma-separated harness ids. Defaults to codex.",
    )
    parser.add_argument(
        "--skills",
        default="",
        help="Comma-separated canonical skill ids referenced by the prompt.",
    )
    parser.add_argument(
        "--work-type",
        default="TODO: Real developer work type.",
        help="Real developer work type, e.g. code-review or ci-triage.",
    )
    parser.add_argument(
        "--artifact-types",
        default="",
        help="Comma-separated developer artifact types, e.g. ci-log,source-snippet.",
    )
    parser.add_argument(
        "--prompt-tier",
        default="normal-dev-chat",
        choices=["micro-edit", "normal-dev-chat", "artifact-backed", "long-context-agent"],
        help="Prompt-length tier this case targets.",
    )
    parser.add_argument("--developer-prompt-chars", type=int, default=240)
    parser.add_argument("--developer-prompt-words", type=int, default=40)
    parser.add_argument("--full-input-min-tokens", type=int, default=1500)
    parser.add_argument("--full-input-max-tokens", type=int, default=6000)
    parser.add_argument(
        "--no-suite-update",
        action="store_true",
        help="Do not add the new case to benches/suites/<suite>.json.",
    )
    parser.add_argument("--root", type=Path, default=repo_root(), help="Repository root.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    suite, case_id = args.case
    case_ref = f"{suite}/{case_id}"
    root = args.root.expanduser().resolve()
    case_dir = root / "benches" / "cases" / suite / case_id

    if case_dir.exists():
        print(f"error: {case_dir} already exists", file=sys.stderr)
        return 1

    case_dir.mkdir(parents=True)
    (case_dir / "case.json").write_text(
        build_case_json(
            case_ref,
            suite,
            parse_csv(args.harnesses),
            parse_csv(args.skills),
            args.work_type,
            parse_csv(args.artifact_types),
            args.prompt_tier,
            args.developer_prompt_chars,
            args.developer_prompt_words,
            args.full_input_min_tokens,
            args.full_input_max_tokens,
        ),
        encoding="utf-8",
    )
    (case_dir / "prompt.md").write_text(
        "TODO: Write the exact user-facing prompt for this case.\n",
        encoding="utf-8",
    )
    (case_dir / "rubric.md").write_text(
        "# Rubric\n\nTODO: Define scoring criteria that separate skill use, instruction following, correctness, harness awareness, and unsupported invention.\n",
        encoding="utf-8",
    )

    if args.no_suite_update:
        print(f"created {case_dir}")
    else:
        try:
            suite_file = update_suite(root, suite, case_ref)
        except (json.JSONDecodeError, ValueError) as exc:
            print(f"error: created {case_dir}, but could not update suite: {exc}", file=sys.stderr)
            return 1
        print(f"created {case_dir}")
        print(f"updated {suite_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
