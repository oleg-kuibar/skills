#!/usr/bin/env python3
"""Create a Codex skill folder in this repository."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


ALLOWED_RESOURCES = {"assets", "references", "scripts"}
RESOURCE_ORDER = ["scripts", "references", "assets"]
SKILL_NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def default_skills_dir() -> Path:
    return repo_root() / "skills"


def is_valid_skill_name(name: str) -> bool:
    return 1 <= len(name) <= 64 and bool(SKILL_NAME_RE.fullmatch(name))


def display_name_from_skill_name(name: str) -> str:
    return " ".join(part.capitalize() for part in name.split("-"))


def yaml_string(value: str) -> str:
    return json.dumps(value)


def parse_resources(raw: str) -> list[str]:
    if not raw:
        return []

    resources = [item.strip() for item in raw.split(",") if item.strip()]
    invalid = sorted(set(resources) - ALLOWED_RESOURCES)
    if invalid:
        valid = ", ".join(sorted(ALLOWED_RESOURCES))
        raise argparse.ArgumentTypeError(
            f"unknown resource folder(s): {', '.join(invalid)}; valid values: {valid}"
        )

    requested = set(resources)
    return [resource for resource in RESOURCE_ORDER if resource in requested]


def skill_markdown(name: str, description: str, display_name: str, resources: list[str]) -> str:
    resource_section = ""
    if resources:
        resource_lines = {
            "assets": "- `assets/`: Store templates, images, fonts, or other reusable output files.",
            "references": "- `references/`: Store detailed context Codex should load only when needed.",
            "scripts": "- `scripts/`: Store deterministic helpers and test them before relying on them.",
        }
        joined_lines = "\n".join(resource_lines[item] for item in resources)
        resource_section = f"""
## Resources

{joined_lines}
"""

    return f"""---
name: {name}
description: {yaml_string(description)}
---

# {display_name}

## Workflow

TODO: Replace this template with concise, imperative instructions for Codex.
Explain the non-obvious process, files, tools, checks, and decision points needed
to perform this skill well.
{resource_section}"""


def openai_yaml(name: str, display_name: str, short_description: str, default_prompt: str) -> str:
    return f"""interface:
  display_name: {yaml_string(display_name)}
  short_description: {yaml_string(short_description)}
  default_prompt: {yaml_string(default_prompt)}

policy:
  allow_implicit_invocation: true
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("skill_name", help="Skill folder name, e.g. my-skill")
    parser.add_argument(
        "--path",
        type=Path,
        default=default_skills_dir(),
        help="Directory that will contain the skill folder. Defaults to ./skills.",
    )
    parser.add_argument(
        "--resources",
        type=parse_resources,
        default=[],
        help="Comma-separated optional folders: scripts,references,assets",
    )
    parser.add_argument(
        "--description",
        default="TODO: Describe what this skill does and the exact situations that should trigger it.",
        help="SKILL.md frontmatter description.",
    )
    parser.add_argument("--display-name", help="Human-facing display name for agents/openai.yaml.")
    parser.add_argument(
        "--short-description",
        default="TODO: Summarize this skill's job.",
        help="25-64 character UI summary for agents/openai.yaml.",
    )
    parser.add_argument(
        "--default-prompt",
        help="Default prompt snippet. Must mention the skill as $skill-name.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    name = args.skill_name

    if not is_valid_skill_name(name):
        print(
            "error: skill name must be 1-64 lowercase letters, digits, and single hyphens",
            file=sys.stderr,
        )
        return 2

    display_name = args.display_name or display_name_from_skill_name(name)
    default_prompt = args.default_prompt or f"Use ${name} to help with a concrete task."
    if f"${name}" not in default_prompt:
        print(f"error: --default-prompt must mention ${name}", file=sys.stderr)
        return 2

    output_root = args.path.expanduser().resolve()
    skill_dir = output_root / name
    if skill_dir.exists():
        print(f"error: {skill_dir} already exists", file=sys.stderr)
        return 1

    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        skill_markdown(name, args.description, display_name, args.resources),
        encoding="utf-8",
    )

    agents_dir = skill_dir / "agents"
    agents_dir.mkdir()
    (agents_dir / "openai.yaml").write_text(
        openai_yaml(name, display_name, args.short_description, default_prompt),
        encoding="utf-8",
    )

    for resource in args.resources:
        (skill_dir / resource).mkdir()

    print(f"created {skill_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
