#!/usr/bin/env python3
"""Check the skills bench repository structure."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from check_skills import Issue, check_skill, find_skill_dirs, relative


ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
CASE_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*/[a-z0-9]+(?:-[a-z0-9]+)*$")

REQUIRED_HARNESS_KEYS = {
    "id",
    "display_name",
    "kind",
    "adapter_status",
    "skill_projection",
    "notes",
}

REQUIRED_SUITE_KEYS = {
    "id",
    "title",
    "description",
    "cases",
}

REQUIRED_CASE_KEYS = {
    "id",
    "title",
    "suite",
    "objective",
    "work_type",
    "artifact_types",
    "prompt_profile",
    "harnesses",
    "skill_refs",
    "prompt",
    "rubric",
    "tags",
    "inputs",
    "expected_outputs",
    "evaluation",
}

PROMPT_TIERS = {
    "micro-edit",
    "normal-dev-chat",
    "artifact-backed",
    "long-context-agent",
}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_json(path: Path) -> tuple[dict[str, Any] | None, list[Issue]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [Issue("error", path, f"invalid JSON: {exc}")]

    if not isinstance(data, dict):
        return None, [Issue("error", path, "top-level JSON value must be an object")]

    return data, []


def check_required(path: Path, data: dict[str, Any], keys: set[str]) -> list[Issue]:
    return [Issue("error", path, f"missing required key {key}") for key in sorted(keys - set(data))]


def check_no_todo(path: Path, strict: bool) -> list[Issue]:
    if "TODO" not in path.read_text(encoding="utf-8"):
        return []
    level = "error" if strict else "warning"
    return [Issue(level, path, "replace TODO placeholders before committing")]


def as_string_list(path: Path, data: dict[str, Any], key: str) -> tuple[list[str], list[Issue]]:
    value = data.get(key)
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        return [], [Issue("error", path, f"{key} must be a list of non-empty strings")]
    return value, []


def check_prompt_profile(path: Path, data: dict[str, Any]) -> list[Issue]:
    profile = data.get("prompt_profile")
    if not isinstance(profile, dict):
        return [Issue("error", path, "prompt_profile must be an object")]

    issues: list[Issue] = []
    tier = profile.get("developer_prompt_tier")
    if tier not in PROMPT_TIERS:
        issues.append(
            Issue(
                "error",
                path,
                f"prompt_profile.developer_prompt_tier must be one of {', '.join(sorted(PROMPT_TIERS))}",
            )
        )

    for key in ["developer_prompt_chars", "developer_prompt_words"]:
        value = profile.get(key)
        if not isinstance(value, int) or value <= 0:
            issues.append(Issue("error", path, f"prompt_profile.{key} must be a positive integer"))

    token_range = profile.get("full_input_token_range")
    if not isinstance(token_range, dict):
        issues.append(Issue("error", path, "prompt_profile.full_input_token_range must be an object"))
    else:
        min_tokens = token_range.get("min")
        max_tokens = token_range.get("max")
        if not isinstance(min_tokens, int) or min_tokens <= 0:
            issues.append(Issue("error", path, "prompt_profile.full_input_token_range.min must be a positive integer"))
        if not isinstance(max_tokens, int) or max_tokens <= 0:
            issues.append(Issue("error", path, "prompt_profile.full_input_token_range.max must be a positive integer"))
        if isinstance(min_tokens, int) and isinstance(max_tokens, int) and min_tokens > max_tokens:
            issues.append(Issue("error", path, "prompt_profile.full_input_token_range.min cannot exceed max"))

    calibration = profile.get("calibration")
    if not isinstance(calibration, str) or not calibration.strip():
        issues.append(Issue("error", path, "prompt_profile.calibration must be a non-empty string"))

    chars = profile.get("developer_prompt_chars")
    words = profile.get("developer_prompt_words")
    token_range = profile.get("full_input_token_range")
    min_tokens = token_range.get("min") if isinstance(token_range, dict) else None
    max_tokens = token_range.get("max") if isinstance(token_range, dict) else None

    if tier == "micro-edit":
        if isinstance(chars, int) and chars > 120:
            issues.append(Issue("error", path, "micro-edit developer_prompt_chars should stay at or below 120"))
        if isinstance(words, int) and words > 15:
            issues.append(Issue("error", path, "micro-edit developer_prompt_words should stay at or below 15"))
    elif tier == "normal-dev-chat":
        if isinstance(words, int) and not 30 <= words <= 150:
            issues.append(Issue("error", path, "normal-dev-chat developer_prompt_words should be 30-150"))
        if isinstance(min_tokens, int) and min_tokens < 1000:
            issues.append(Issue("error", path, "normal-dev-chat full_input_token_range.min should be at least 1000"))
    elif tier == "artifact-backed":
        if isinstance(min_tokens, int) and min_tokens < 1000:
            issues.append(Issue("error", path, "artifact-backed full_input_token_range.min should be at least 1000"))
        if isinstance(max_tokens, int) and max_tokens < 1500:
            issues.append(Issue("error", path, "artifact-backed full_input_token_range.max should be at least 1500"))
    elif tier == "long-context-agent":
        if isinstance(min_tokens, int) and min_tokens < 20000:
            issues.append(Issue("error", path, "long-context-agent full_input_token_range.min should be at least 20000"))

    return issues


def check_harness(path: Path, strict: bool) -> tuple[str | None, list[Issue]]:
    data, issues = load_json(path)
    if data is None:
        return None, issues

    issues.extend(check_required(path, data, REQUIRED_HARNESS_KEYS))
    harness_id = data.get("id")
    if not isinstance(harness_id, str) or not ID_RE.fullmatch(harness_id):
        issues.append(Issue("error", path, "id must be lowercase letters, digits, and hyphens"))
        harness_id = None
    elif harness_id != path.stem:
        issues.append(Issue("error", path, "id must match the file name"))

    for key in ["display_name", "kind", "adapter_status", "skill_projection"]:
        if key in data and (not isinstance(data[key], str) or not data[key].strip()):
            issues.append(Issue("error", path, f"{key} must be a non-empty string"))

    if "notes" in data:
        _, list_issues = as_string_list(path, data, "notes")
        issues.extend(list_issues)

    issues.extend(check_no_todo(path, strict))
    return harness_id, issues


def check_suite(path: Path, case_ids: set[str], strict: bool) -> tuple[str | None, set[str], list[Issue]]:
    data, issues = load_json(path)
    if data is None:
        return None, set(), issues

    issues.extend(check_required(path, data, REQUIRED_SUITE_KEYS))
    suite_id = data.get("id")
    if not isinstance(suite_id, str) or not ID_RE.fullmatch(suite_id):
        issues.append(Issue("error", path, "id must be lowercase letters, digits, and hyphens"))
        suite_id = None
    elif suite_id != path.stem:
        issues.append(Issue("error", path, "id must match the file name"))

    for key in ["title", "description"]:
        if key in data and (not isinstance(data[key], str) or not data[key].strip()):
            issues.append(Issue("error", path, f"{key} must be a non-empty string"))

    cases, list_issues = as_string_list(path, data, "cases")
    issues.extend(list_issues)
    for case_id in cases:
        if not CASE_ID_RE.fullmatch(case_id):
            issues.append(Issue("error", path, f"case id {case_id!r} must look like suite/case"))
        elif suite_id and not case_id.startswith(f"{suite_id}/"):
            issues.append(Issue("error", path, f"case {case_id!r} does not belong to suite {suite_id!r}"))
        elif case_id not in case_ids:
            issues.append(Issue("error", path, f"case {case_id!r} does not exist"))

    issues.extend(check_no_todo(path, strict))
    return suite_id, set(cases), issues


def check_case(
    path: Path,
    harness_ids: set[str],
    skill_ids: set[str],
    suite_ids: set[str],
    strict: bool,
) -> tuple[str | None, list[Issue]]:
    data, issues = load_json(path)
    if data is None:
        return None, issues

    issues.extend(check_required(path, data, REQUIRED_CASE_KEYS))
    case_dir = path.parent
    expected_id = f"{case_dir.parent.name}/{case_dir.name}"

    case_id = data.get("id")
    if not isinstance(case_id, str) or not CASE_ID_RE.fullmatch(case_id):
        issues.append(Issue("error", path, "id must look like suite/case"))
        case_id = None
    elif case_id != expected_id:
        issues.append(Issue("error", path, f"id must match folder path {expected_id!r}"))

    suite = data.get("suite")
    if not isinstance(suite, str) or not ID_RE.fullmatch(suite):
        issues.append(Issue("error", path, "suite must be a lowercase id"))
    elif suite != case_dir.parent.name:
        issues.append(Issue("error", path, "suite must match the parent folder"))
    elif suite_ids and suite not in suite_ids:
        issues.append(Issue("error", path, f"suite {suite!r} is not declared in benches/suites"))

    for key in ["title", "objective", "work_type", "prompt", "rubric"]:
        if key in data and (not isinstance(data[key], str) or not data[key].strip()):
            issues.append(Issue("error", path, f"{key} must be a non-empty string"))

    for ref_key in ["prompt", "rubric"]:
        ref = data.get(ref_key)
        if isinstance(ref, str) and ref.strip() and not (case_dir / ref).is_file():
            issues.append(Issue("error", path, f"{ref_key} file {ref!r} does not exist"))

    harnesses, list_issues = as_string_list(path, data, "harnesses")
    issues.extend(list_issues)
    if "harnesses" in data and not harnesses:
        issues.append(Issue("error", path, "harnesses must list at least one harness"))
    for harness in harnesses:
        if harness not in harness_ids:
            issues.append(Issue("error", path, f"unknown harness {harness!r}"))

    skills, list_issues = as_string_list(path, data, "skill_refs")
    issues.extend(list_issues)
    if "skill_refs" in data and not skills:
        issues.append(Issue("error", path, "skill_refs must list at least one real skill"))
    for skill in skills:
        if skill not in skill_ids:
            issues.append(Issue("error", path, f"unknown skill_ref {skill!r}"))

    artifact_types, list_issues = as_string_list(path, data, "artifact_types")
    issues.extend(list_issues)
    if "artifact_types" in data and not artifact_types:
        issues.append(Issue("error", path, "artifact_types must list at least one developer artifact type"))

    issues.extend(check_prompt_profile(path, data))

    for key in ["tags", "expected_outputs"]:
        _, list_issues = as_string_list(path, data, key)
        issues.extend(list_issues)

    if "inputs" in data and not isinstance(data["inputs"], dict):
        issues.append(Issue("error", path, "inputs must be an object"))

    evaluation = data.get("evaluation")
    if not isinstance(evaluation, dict):
        issues.append(Issue("error", path, "evaluation must be an object"))
    else:
        if not isinstance(evaluation.get("mode"), str) or not evaluation.get("mode", "").strip():
            issues.append(Issue("error", path, "evaluation.mode must be a non-empty string"))
        max_score = evaluation.get("max_score")
        if not isinstance(max_score, int) or max_score <= 0:
            issues.append(Issue("error", path, "evaluation.max_score must be a positive integer"))

    files_to_scan = [path]
    for ref_key in ["prompt", "rubric"]:
        ref = data.get(ref_key)
        if isinstance(ref, str) and (case_dir / ref).is_file():
            files_to_scan.append(case_dir / ref)
    for scan_path in files_to_scan:
        issues.extend(check_no_todo(scan_path, strict))

    return case_id, issues


def find_json_files(path: Path) -> list[Path]:
    if not path.exists():
        return []
    return sorted(child for child in path.glob("*.json") if child.is_file())


def find_case_files(root: Path) -> list[Path]:
    cases_root = root / "benches" / "cases"
    if not cases_root.exists():
        return []
    return sorted(cases_root.glob("*/*/case.json"))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=repo_root(), help="Repository root.")
    parser.add_argument("--strict", action="store_true", help="Treat placeholders as errors.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = args.root.expanduser().resolve()
    issues: list[Issue] = []

    skills_dir = root / "skills"
    skill_dirs = find_skill_dirs(skills_dir) if skills_dir.exists() else []
    skill_ids = {path.name for path in skill_dirs}
    for skill_dir in skill_dirs:
        issues.extend(check_skill(skill_dir, args.strict))

    harness_ids: set[str] = set()
    for harness_file in find_json_files(root / "harnesses"):
        harness_id, harness_issues = check_harness(harness_file, args.strict)
        issues.extend(harness_issues)
        if harness_id:
            harness_ids.add(harness_id)

    case_files = find_case_files(root)
    case_file_by_id = {f"{path.parent.parent.name}/{path.parent.name}": path for path in case_files}
    case_ids = set(case_file_by_id)

    suite_ids: set[str] = set()
    declared_case_ids: set[str] = set()
    for suite_file in find_json_files(root / "benches" / "suites"):
        suite_id, suite_cases, suite_issues = check_suite(suite_file, case_ids, args.strict)
        issues.extend(suite_issues)
        declared_case_ids.update(suite_cases)
        if suite_id:
            suite_ids.add(suite_id)

    for case_id in sorted(case_ids - declared_case_ids):
        issues.append(Issue("error", case_file_by_id[case_id], "case is not listed in any suite"))

    for case_file in case_files:
        _, case_issues = check_case(case_file, harness_ids, skill_ids, suite_ids, args.strict)
        issues.extend(case_issues)

    if not skill_dirs:
        issues.append(Issue("warning", skills_dir, "no canonical skills found"))
    if not harness_ids:
        issues.append(Issue("warning", root / "harnesses", "no harness manifests found"))
    if not case_files:
        issues.append(Issue("warning", root / "benches" / "cases", "no bench cases found"))

    for issue in issues:
        print(f"{issue.level.upper()}: {relative(issue.path, root)}: {issue.message}")

    errors = [issue for issue in issues if issue.level == "error"]
    warnings = [issue for issue in issues if issue.level == "warning"]
    if errors:
        print(f"Structure check failed: {len(errors)} error(s), {len(warnings)} warning(s).", file=sys.stderr)
        return 1

    print(
        f"Checked {len(skill_dirs)} skill(s), {len(harness_ids)} harness(es), "
        f"{len(case_files)} bench case(s): {len(warnings)} warning(s)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
