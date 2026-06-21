#!/usr/bin/env python3
"""Sync vendored skills and agents from sources.json."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
COMMIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
SOURCE_KINDS = {"skill", "agent"}


@dataclass(frozen=True)
class Issue:
    level: str
    path: Path
    message: str


@dataclass(frozen=True)
class Source:
    name: str
    kind: str
    repo: str
    ref: str
    track: str | None
    path: Path
    target: Path
    include: tuple[str, ...]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def relative(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def load_json_object(path: Path) -> tuple[dict[str, Any] | None, list[Issue]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [Issue("error", path, f"invalid JSON: {exc}")]
    if not isinstance(data, dict):
        return None, [Issue("error", path, "top-level JSON value must be an object")]
    return data, []


def load_sources(path: Path) -> tuple[list[Source], list[Issue]]:
    data, issues = load_json_object(path)
    if data is None:
        return [], issues

    raw_sources = data.get("sources")
    if not isinstance(raw_sources, list) or not raw_sources:
        return [], [Issue("error", path, "sources must be a non-empty array")]

    sources: list[Source] = []
    seen_targets: set[str] = set()
    for index, raw in enumerate(raw_sources, start=1):
        if not isinstance(raw, dict):
            issues.append(Issue("error", path, f"sources[{index}] must be an object"))
            continue

        missing = [key for key in ["name", "kind", "repo", "ref", "path", "target"] if key not in raw]
        for key in missing:
            issues.append(Issue("error", path, f"sources[{index}] missing {key}"))
        if missing:
            continue

        name = raw["name"]
        kind = raw["kind"]
        repo = raw["repo"]
        ref = raw["ref"]
        track = raw.get("track")
        source_path = raw["path"]
        target = raw["target"]
        include = raw.get("include", ["**"])

        for key, value in [
            ("name", name),
            ("kind", kind),
            ("repo", repo),
            ("ref", ref),
            ("path", source_path),
            ("target", target),
        ]:
            if not isinstance(value, str) or not value.strip():
                issues.append(Issue("error", path, f"sources[{index}].{key} must be a non-empty string"))
        if not isinstance(include, list) or not all(isinstance(item, str) and item for item in include):
            issues.append(Issue("error", path, f"sources[{index}].include must be a list of non-empty strings"))
        if track is not None and (not isinstance(track, str) or not track.strip()):
            issues.append(Issue("error", path, f"sources[{index}].track must be a non-empty string when set"))

        if isinstance(name, str) and not NAME_RE.fullmatch(name):
            issues.append(Issue("error", path, f"sources[{index}].name must be lowercase letters, digits, and hyphens"))
        if isinstance(kind, str) and kind not in SOURCE_KINDS:
            issues.append(Issue("error", path, f"sources[{index}].kind must be one of {', '.join(sorted(SOURCE_KINDS))}"))
        if isinstance(ref, str) and not COMMIT_SHA_RE.fullmatch(ref):
            issues.append(Issue("error", path, f"sources[{index}].ref must be a pinned 40-character commit SHA"))

        if issues and any(issue.message.startswith(f"sources[{index}]") for issue in issues):
            continue

        target_path = Path(target)
        if target_path.is_absolute() or ".." in target_path.parts:
            issues.append(Issue("error", path, f"sources[{index}].target must be a relative path inside this repo"))
            continue
        target_key = target_path.as_posix()
        if target_key in seen_targets:
            issues.append(Issue("error", path, f"sources[{index}].target duplicates another source"))
            continue
        seen_targets.add(target_key)

        sources.append(
            Source(
                name=name,
                kind=kind,
                repo=repo,
                ref=ref,
                track=track,
                path=Path(source_path),
                target=target_path,
                include=tuple(include),
            )
        )

    return sources, issues


def run(cmd: list[str], cwd: Path | None = None) -> None:
    result = subprocess.run(cmd, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode == 0:
        return
    if result.stdout:
        print(result.stdout, file=sys.stderr, end="")
    if result.stderr:
        print(result.stderr, file=sys.stderr, end="")
    raise subprocess.CalledProcessError(result.returncode, cmd)


def capture(cmd: list[str], cwd: Path | None = None) -> str:
    result = subprocess.run(cmd, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode == 0:
        return result.stdout
    if result.stdout:
        print(result.stdout, file=sys.stderr, end="")
    if result.stderr:
        print(result.stderr, file=sys.stderr, end="")
    raise subprocess.CalledProcessError(result.returncode, cmd)


def clone_repo(repo: str, ref: str, checkout_dir: Path) -> None:
    checkout_dir.mkdir(parents=True)
    run(["git", "init", "--quiet"], cwd=checkout_dir)
    run(["git", "remote", "add", "origin", repo], cwd=checkout_dir)
    try:
        run(["git", "fetch", "--quiet", "--depth", "1", "origin", ref], cwd=checkout_dir)
    except subprocess.CalledProcessError:
        run(["git", "fetch", "--quiet", "origin", ref], cwd=checkout_dir)
    run(["git", "checkout", "--quiet", "--detach", "FETCH_HEAD"], cwd=checkout_dir)


def materialize_sources(sources: list[Source], cache_dir: Path) -> dict[tuple[str, str], Path]:
    clones: dict[tuple[str, str], Path] = {}
    for source in sources:
        key = (source.repo, source.ref)
        if key in clones:
            continue
        checkout_dir = cache_dir / f"repo-{len(clones) + 1}"
        clone_repo(source.repo, source.ref, checkout_dir)
        clones[key] = checkout_dir
    return clones


def resolve_track_ref(repo: str, track: str) -> str:
    if COMMIT_SHA_RE.fullmatch(track):
        return track

    candidates = [f"refs/heads/{track}", f"refs/tags/{track}^{{}}", f"refs/tags/{track}", track]
    for candidate in candidates:
        output = capture(["git", "ls-remote", repo, candidate]).strip()
        if not output:
            continue
        for line in output.splitlines():
            sha = line.split()[0]
            if COMMIT_SHA_RE.fullmatch(sha):
                return sha
    raise RuntimeError(f"could not resolve {track!r} in {repo}")


def included_files(source_root: Path, patterns: tuple[str, ...]) -> dict[Path, Path]:
    if source_root.is_file():
        return {Path(source_root.name): source_root}

    files: dict[Path, Path] = {}
    for pattern in patterns:
        for candidate in source_root.glob(pattern):
            if candidate.is_file():
                files[candidate.relative_to(source_root)] = candidate
    return dict(sorted(files.items(), key=lambda item: item[0].as_posix()))


def target_files(target: Path) -> dict[Path, Path]:
    if target.is_file():
        return {Path(target.name): target}
    if not target.exists():
        return {}
    return {
        path.relative_to(target): path
        for path in sorted(target.rglob("*"))
        if path.is_file()
    }


def remove_path(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)


def copy_source(source_root: Path, target: Path, files: dict[Path, Path]) -> None:
    if target.exists() or target.is_symlink():
        remove_path(target)

    if source_root.is_file():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_root, target)
        return

    target.mkdir(parents=True, exist_ok=True)
    for relative_path, source_file in files.items():
        destination = target / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_file, destination)


def check_source_matches(root: Path, source: Source, source_root: Path, files: dict[Path, Path]) -> list[Issue]:
    issues: list[Issue] = []
    target = root / source.target
    actual_files = target_files(target)

    if source_root.is_file():
        expected_bytes = source_root.read_bytes()
        if not target.is_file():
            return [Issue("error", target, "target file is missing")]
        if target.read_bytes() != expected_bytes:
            return [Issue("error", target, "target file differs from upstream source")]
        return []

    expected_names = set(files)
    actual_names = set(actual_files)
    for missing in sorted(expected_names - actual_names):
        issues.append(Issue("error", target / missing, "file is missing from vendored target"))
    for extra in sorted(actual_names - expected_names):
        issues.append(Issue("error", target / extra, "file is not present in upstream source selection"))
    for relative_path in sorted(expected_names & actual_names):
        if files[relative_path].read_bytes() != actual_files[relative_path].read_bytes():
            issues.append(Issue("error", target / relative_path, "file differs from upstream source"))
    return issues


def parse_scalar(raw: str) -> str:
    value = raw.strip()
    if not value:
        return ""
    if value.startswith('"'):
        return str(json.loads(value))
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1].replace("''", "'")
    return value


def parse_frontmatter(path: Path) -> tuple[dict[str, str], str, list[Issue]]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    issues: list[Issue] = []
    if not lines or lines[0].strip() != "---":
        return {}, "", [Issue("error", path, "file must start with YAML frontmatter")]

    closing_index = None
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            closing_index = index
            break
    if closing_index is None:
        return {}, "", [Issue("error", path, "YAML frontmatter is missing a closing ---")]

    frontmatter: dict[str, str] = {}
    frontmatter_lines = lines[1:closing_index]
    index = 0
    while index < len(frontmatter_lines):
        line = frontmatter_lines[index]
        line_number = index + 2
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            index += 1
            continue
        if line[:1].isspace():
            index += 1
            continue
        if ":" not in stripped:
            issues.append(Issue("error", path, f"line {line_number}: expected key: value"))
            index += 1
            continue
        key, raw_value = stripped.split(":", 1)
        key = key.strip()
        raw_value = raw_value.strip()
        if key in frontmatter:
            issues.append(Issue("error", path, f"line {line_number}: duplicate key {key}"))
            index += 1
            continue
        if not raw_value:
            continuation: list[str] = []
            lookahead = index + 1
            while lookahead < len(frontmatter_lines) and frontmatter_lines[lookahead][:1].isspace():
                continuation_line = frontmatter_lines[lookahead].strip()
                if continuation_line and not continuation_line.startswith("#"):
                    continuation.append(continuation_line)
                lookahead += 1
            frontmatter[key] = " ".join(continuation)
            index = lookahead
            continue
        try:
            frontmatter[key] = parse_scalar(raw_value)
        except json.JSONDecodeError as exc:
            issues.append(Issue("error", path, f"line {line_number}: invalid quoted string: {exc}"))
        index += 1

    body = "\n".join(lines[closing_index + 1 :]).strip()
    return frontmatter, body, issues


def validate_frontmatter(path: Path, expected_name: str, item_type: str) -> list[Issue]:
    frontmatter, body, issues = parse_frontmatter(path)
    for key in sorted({"name", "description"} - set(frontmatter)):
        issues.append(Issue("error", path, f"frontmatter is missing {key}"))

    name = frontmatter.get("name")
    if name and name != expected_name:
        target = "folder name" if item_type == "skill" else "file name"
        issues.append(Issue("error", path, f"frontmatter name {name!r} must match {target}"))

    if not frontmatter.get("description", "").strip():
        issues.append(Issue("error", path, "frontmatter description cannot be empty"))
    if not body:
        issues.append(Issue("error", path, "body cannot be empty"))
    if "TODO" in path.read_text(encoding="utf-8"):
        issues.append(Issue("error", path, "replace TODO placeholders before committing"))
    return issues


def find_skill_dirs(root: Path) -> list[Path]:
    skills_dir = root / "skills"
    if not skills_dir.exists():
        return []
    return sorted(path for path in skills_dir.iterdir() if path.is_dir() and (path / "SKILL.md").is_file())


def find_agent_files(root: Path) -> list[Path]:
    agents_dir = root / "agents"
    if not agents_dir.exists():
        return []
    return sorted(path for path in agents_dir.glob("*.md") if path.is_file())


def normalize_skill_slug(value: str) -> str:
    return re.sub(r"[-_\s]+", "-", value.strip().lower())


def validate_skills_sh_config(root: Path, skill_ids: set[str]) -> list[Issue]:
    config_file = root / "skills.sh.json"
    if not config_file.exists():
        return []

    data, issues = load_json_object(config_file)
    if data is None:
        return issues

    not_grouped = data.get("notGrouped")
    if not_grouped is not None and not_grouped not in {"top", "bottom"}:
        issues.append(Issue("error", config_file, "notGrouped must be either top or bottom"))

    groupings = data.get("groupings")
    if not isinstance(groupings, list) or not groupings:
        issues.append(Issue("error", config_file, "groupings must be a non-empty array"))
        return issues

    seen_skills: set[str] = set()
    for index, grouping in enumerate(groupings, start=1):
        if not isinstance(grouping, dict):
            issues.append(Issue("error", config_file, f"grouping {index} must be an object"))
            continue

        title = grouping.get("title")
        if not isinstance(title, str) or not title.strip():
            issues.append(Issue("error", config_file, f"grouping {index} title must be a non-empty string"))

        skills = grouping.get("skills")
        if not isinstance(skills, list) or not skills:
            issues.append(Issue("error", config_file, f"grouping {index} skills must be a non-empty array"))
            continue

        for raw_skill in skills:
            if not isinstance(raw_skill, str) or not raw_skill.strip():
                issues.append(Issue("error", config_file, f"grouping {index} skills must contain non-empty strings"))
                continue
            skill = normalize_skill_slug(raw_skill)
            if skill not in skill_ids:
                issues.append(Issue("error", config_file, f"grouping {index} references unknown skill {raw_skill!r}"))
            if skill in seen_skills:
                issues.append(Issue("error", config_file, f"skill {raw_skill!r} appears in more than one group"))
            seen_skills.add(skill)
    return issues


def validate_repo(root: Path, sources: list[Source]) -> list[Issue]:
    issues: list[Issue] = []
    source_targets = {source.target.as_posix() for source in sources}

    skills = find_skill_dirs(root)
    agents = find_agent_files(root)

    for skill_dir in skills:
        if not NAME_RE.fullmatch(skill_dir.name):
            issues.append(Issue("error", skill_dir, "folder name must be lowercase letters, digits, and hyphens"))
        if skill_dir.relative_to(root).as_posix() not in source_targets:
            issues.append(Issue("error", skill_dir, "skill is not declared in sources.json"))
        issues.extend(validate_frontmatter(skill_dir / "SKILL.md", skill_dir.name, "skill"))

    for agent_file in agents:
        if not NAME_RE.fullmatch(agent_file.stem):
            issues.append(Issue("error", agent_file, "file name must be lowercase letters, digits, and hyphens"))
        if agent_file.relative_to(root).as_posix() not in source_targets:
            issues.append(Issue("error", agent_file, "agent is not declared in sources.json"))
        issues.extend(validate_frontmatter(agent_file, agent_file.stem, "agent"))

    declared_skill_targets = {source.target.as_posix() for source in sources if source.kind == "skill"}
    actual_skill_targets = {skill.relative_to(root).as_posix() for skill in skills}
    for missing in sorted(declared_skill_targets - actual_skill_targets):
        issues.append(Issue("error", root / missing, "declared skill target is missing"))

    declared_agent_targets = {source.target.as_posix() for source in sources if source.kind == "agent"}
    actual_agent_targets = {agent.relative_to(root).as_posix() for agent in agents}
    for missing in sorted(declared_agent_targets - actual_agent_targets):
        issues.append(Issue("error", root / missing, "declared agent target is missing"))

    issues.extend(validate_skills_sh_config(root, {skill.name for skill in skills}))
    return issues


def sync_or_check(root: Path, sources: list[Source], check: bool) -> list[Issue]:
    issues: list[Issue] = []
    with tempfile.TemporaryDirectory(prefix="skills-sync-") as tmp:
        clones = materialize_sources(sources, Path(tmp))

        for source in sources:
            checkout = clones[(source.repo, source.ref)]
            source_root = checkout / source.path
            target = root / source.target

            if not source_root.exists():
                issues.append(Issue("error", source.target, "source path does not exist upstream"))
                continue

            files = included_files(source_root, source.include)
            if not files:
                issues.append(Issue("error", source.target, "source selection produced no files"))
                continue

            if check:
                issues.extend(check_source_matches(root, source, source_root, files))
            else:
                copy_source(source_root, target, files)

    issues.extend(validate_repo(root, sources))
    return issues


def update_manifest_refs(manifest: Path) -> tuple[list[dict[str, str]], list[Issue]]:
    data, issues = load_json_object(manifest)
    if data is None:
        return [], issues

    raw_sources = data.get("sources")
    if not isinstance(raw_sources, list):
        return [], [Issue("error", manifest, "sources must be an array")]

    resolved: dict[tuple[str, str], str] = {}
    changes: list[dict[str, str]] = []
    for index, raw in enumerate(raw_sources, start=1):
        if not isinstance(raw, dict):
            issues.append(Issue("error", manifest, f"sources[{index}] must be an object"))
            continue
        repo = raw.get("repo")
        ref = raw.get("ref")
        track = raw.get("track", "main")
        name = raw.get("name", f"sources[{index}]")
        target = raw.get("target", "")

        if not all(isinstance(value, str) and value.strip() for value in [repo, ref, track, name, target]):
            issues.append(Issue("error", manifest, f"sources[{index}] has invalid repo/ref/track/name/target"))
            continue

        key = (repo, track)
        raw["track"] = track
        if key not in resolved:
            try:
                resolved[key] = resolve_track_ref(repo, track)
            except (RuntimeError, subprocess.CalledProcessError) as exc:
                issues.append(Issue("error", manifest, f"sources[{index}] failed to resolve {repo}@{track}: {exc}"))
                continue

        new_ref = resolved[key]
        if ref != new_ref:
            raw["ref"] = new_ref
            changes.append(
                {
                    "name": name,
                    "repo": repo,
                    "track": track,
                    "target": target,
                    "old": ref,
                    "new": new_ref,
                }
            )

    if issues:
        return changes, issues

    manifest.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return changes, []


def short_sha(value: str) -> str:
    return value[:12] if COMMIT_SHA_RE.fullmatch(value) else value


def write_report(path: Path, changes: list[dict[str, str]]) -> None:
    lines = [
        "# Vendored Skill Source Update",
        "",
        "Generated by `python3 tools/sync_sources.py --update`.",
        "",
    ]

    if not changes:
        lines.append("No upstream updates found.")
    else:
        lines.extend(
            [
                "Updated pinned upstream refs:",
                "",
                "| Source | Repo | Track | Target | Old | New |",
                "| --- | --- | --- | --- | --- | --- |",
            ]
        )
        for change in changes:
            lines.append(
                "| {name} | {repo} | {track} | `{target}` | `{old}` | `{new}` |".format(
                    name=change["name"],
                    repo=change["repo"],
                    track=change["track"],
                    target=change["target"],
                    old=short_sha(change["old"]),
                    new=short_sha(change["new"]),
                )
            )

    lines.extend(
        [
            "",
            "Vendored files are generated from `sources.json`; edit the manifest or upstream source instead of hand-editing generated files.",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=repo_root(), help="Repository root.")
    parser.add_argument("--manifest", type=Path, default=Path("sources.json"), help="Source manifest path.")
    parser.add_argument("--check", action="store_true", help="Fail if vendored files differ from upstream.")
    parser.add_argument("--update", action="store_true", help="Update refs from tracked upstream branches before syncing.")
    parser.add_argument("--report", type=Path, help="Write a Markdown update report.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = args.root.expanduser().resolve()
    manifest = args.manifest if args.manifest.is_absolute() else root / args.manifest

    if args.check and args.update:
        print("error: --check and --update cannot be used together", file=sys.stderr)
        return 2
    if args.report and not args.update:
        print("error: --report requires --update", file=sys.stderr)
        return 2

    update_changes: list[dict[str, str]] = []
    if args.update:
        update_changes, update_issues = update_manifest_refs(manifest)
        if update_issues:
            for issue in update_issues:
                print(f"{issue.level.upper()}: {relative(issue.path, root)}: {issue.message}")
            print(f"Source update failed: {len(update_issues)} error(s).", file=sys.stderr)
            return 1

    sources, issues = load_sources(manifest)
    if not issues:
        issues.extend(sync_or_check(root, sources, args.check))

    if args.update and args.report and not issues:
        report = args.report if args.report.is_absolute() else root / args.report
        write_report(report, update_changes)

    for issue in issues:
        print(f"{issue.level.upper()}: {relative(issue.path, root)}: {issue.message}")

    errors = [issue for issue in issues if issue.level == "error"]
    if errors:
        action = "check" if args.check else "sync"
        print(f"Source {action} failed: {len(errors)} error(s).", file=sys.stderr)
        return 1

    action = "Updated" if args.update else "Checked" if args.check else "Synced"
    skill_count = sum(1 for source in sources if source.kind == "skill")
    agent_count = sum(1 for source in sources if source.kind == "agent")
    suffix = f", {len(update_changes)} upstream ref update(s)" if args.update else ""
    print(f"{action} {len(sources)} source(s): {skill_count} skill(s), {agent_count} agent(s){suffix}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
