#!/usr/bin/env python3
"""Check Codex skill folder structure in this repository."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path


REPO_SKIP_DIRS = {".git", ".github", "docs", "tools", "__pycache__"}
SKILL_NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


@dataclass(frozen=True)
class Issue:
    level: str
    path: Path
    message: str


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def default_skills_dir() -> Path:
    return repo_root() / "skills"


def resolve_path(path: Path, root: Path) -> Path:
    if path.is_absolute():
        return path.resolve()
    return (root / path).resolve()


def relative(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def parse_scalar(raw: str) -> str:
    value = raw.strip()
    if not value:
        return ""
    if value.startswith('"'):
        return str(json.loads(value))
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1].replace("''", "'")
    return value


def parse_frontmatter(skill_file: Path) -> tuple[dict[str, str], str, list[Issue]]:
    text = skill_file.read_text(encoding="utf-8")
    lines = text.splitlines()
    issues: list[Issue] = []

    if not lines or lines[0].strip() != "---":
        return {}, "", [Issue("error", skill_file, "SKILL.md must start with YAML frontmatter")]

    closing_index = None
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            closing_index = index
            break

    if closing_index is None:
        return {}, "", [Issue("error", skill_file, "YAML frontmatter is missing a closing ---")]

    frontmatter: dict[str, str] = {}
    for line_number, line in enumerate(lines[1:closing_index], start=2):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if ":" not in stripped:
            issues.append(Issue("error", skill_file, f"line {line_number}: expected key: value"))
            continue
        key, raw_value = stripped.split(":", 1)
        key = key.strip()
        if key in frontmatter:
            issues.append(Issue("error", skill_file, f"line {line_number}: duplicate key {key}"))
            continue
        try:
            frontmatter[key] = parse_scalar(raw_value)
        except json.JSONDecodeError as exc:
            issues.append(Issue("error", skill_file, f"line {line_number}: invalid quoted string: {exc}"))

    body = "\n".join(lines[closing_index + 1 :]).strip()
    return frontmatter, body, issues


def extract_yaml_scalar(text: str, key: str) -> str | None:
    pattern = re.compile(rf"^\s+{re.escape(key)}:\s*(.+?)\s*$", re.MULTILINE)
    match = pattern.search(text)
    if not match:
        return None
    try:
        return parse_scalar(match.group(1))
    except json.JSONDecodeError:
        return None


def check_agent_metadata(skill_dir: Path, skill_name: str, strict: bool) -> list[Issue]:
    metadata_file = skill_dir / "agents" / "openai.yaml"
    if not metadata_file.exists():
        return [Issue("warning", metadata_file, "agents/openai.yaml is recommended")]

    text = metadata_file.read_text(encoding="utf-8")
    issues: list[Issue] = []
    if not re.search(r"^interface:\s*$", text, re.MULTILINE):
        issues.append(Issue("error", metadata_file, "missing top-level interface section"))

    default_prompt = extract_yaml_scalar(text, "default_prompt")
    if default_prompt is None:
        issues.append(Issue("error", metadata_file, "missing interface.default_prompt"))
    elif f"${skill_name}" not in default_prompt:
        issues.append(Issue("error", metadata_file, f"default_prompt must mention ${skill_name}"))

    short_description = extract_yaml_scalar(text, "short_description")
    if short_description is not None and not 25 <= len(short_description) <= 64:
        level = "error" if strict else "warning"
        issues.append(Issue(level, metadata_file, "short_description should be 25-64 characters"))

    display_name = extract_yaml_scalar(text, "display_name")
    if display_name is not None and not display_name.strip():
        issues.append(Issue("error", metadata_file, "display_name cannot be empty"))

    if "TODO" in text:
        level = "error" if strict else "warning"
        issues.append(Issue(level, metadata_file, "replace TODO placeholders before committing"))

    return issues


def check_skill(skill_dir: Path, strict: bool) -> list[Issue]:
    issues: list[Issue] = []
    skill_file = skill_dir / "SKILL.md"

    if not skill_file.is_file():
        return [Issue("error", skill_dir, "missing SKILL.md")]

    if not 1 <= len(skill_dir.name) <= 64 or not SKILL_NAME_RE.fullmatch(skill_dir.name):
        issues.append(
            Issue(
                "error",
                skill_dir,
                "folder name must be 1-64 lowercase letters, digits, and single hyphens",
            )
        )

    frontmatter, body, frontmatter_issues = parse_frontmatter(skill_file)
    issues.extend(frontmatter_issues)

    expected_keys = {"name", "description"}
    actual_keys = set(frontmatter)
    missing = sorted(expected_keys - actual_keys)
    extra = sorted(actual_keys - expected_keys)
    for key in missing:
        issues.append(Issue("error", skill_file, f"frontmatter is missing {key}"))
    for key in extra:
        issues.append(Issue("error", skill_file, f"frontmatter has unsupported key {key}"))

    name = frontmatter.get("name")
    if name and name != skill_dir.name:
        issues.append(Issue("error", skill_file, f"frontmatter name {name!r} must match folder name"))

    description = frontmatter.get("description", "")
    if not description.strip():
        issues.append(Issue("error", skill_file, "frontmatter description cannot be empty"))

    if not body:
        issues.append(Issue("error", skill_file, "body cannot be empty"))

    if "TODO" in skill_file.read_text(encoding="utf-8"):
        level = "error" if strict else "warning"
        issues.append(Issue(level, skill_file, "replace TODO placeholders before committing"))

    issues.extend(check_agent_metadata(skill_dir, skill_dir.name, strict))
    return issues


def find_skill_dirs(root: Path) -> list[Path]:
    skill_dirs: list[Path] = []
    for child in sorted(root.iterdir()):
        if not child.is_dir() or child.name.startswith(".") or child.name in REPO_SKIP_DIRS:
            continue
        if (child / "SKILL.md").exists():
            skill_dirs.append(child)
    return skill_dirs


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", type=Path, help="Skill folders. Defaults to all skills in ./skills.")
    parser.add_argument("--root", type=Path, default=repo_root(), help="Repository root.")
    parser.add_argument("--skills-dir", type=Path, help="Directory containing skill folders. Defaults to ./skills.")
    parser.add_argument("--strict", action="store_true", help="Treat placeholders and UI metadata issues as errors.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = args.root.expanduser().resolve()
    skills_dir = resolve_path(args.skills_dir, root) if args.skills_dir else root / "skills"
    if args.paths:
        skills = [resolve_path(path, root) for path in args.paths]
    elif skills_dir.exists():
        skills = find_skill_dirs(skills_dir)
    else:
        skills = []

    if not skills:
        print(f"No skill folders found under {skills_dir}; skill structure check is clean.")
        return 0

    all_issues: list[Issue] = []
    for skill_dir in skills:
        all_issues.extend(check_skill(skill_dir, args.strict))

    for issue in all_issues:
        print(f"{issue.level.upper()}: {relative(issue.path, root)}: {issue.message}")

    errors = [issue for issue in all_issues if issue.level == "error"]
    warnings = [issue for issue in all_issues if issue.level == "warning"]

    if errors:
        print(f"Skill structure check failed: {len(errors)} error(s), {len(warnings)} warning(s).", file=sys.stderr)
        return 1

    print(f"Checked {len(skills)} skill(s): {len(warnings)} warning(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
