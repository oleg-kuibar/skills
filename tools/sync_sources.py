#!/usr/bin/env python3
"""Sync vendored skills and agents from pinned sources.json."""

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


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "sources.json"
COMMIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
REQUIRED = ("repo", "ref", "path", "target")


@dataclass(frozen=True)
class Source:
    repo: str
    ref: str
    path: Path
    target: Path
    include: tuple[str, ...]


def relative(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def error(path: Path, message: str) -> str:
    return f"ERROR: {relative(path)}: {message}"


def owned_targets() -> set[str]:
    """Targets authored in this repo, so they have no upstream to pin or diff."""
    try:
        data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return set()
    owned = data.get("owned") if isinstance(data, dict) else None
    return set(owned) if isinstance(owned, list) else set()


def load_sources() -> tuple[list[Source], list[str]]:
    try:
        data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [], [error(MANIFEST, f"invalid JSON: {exc}")]

    raw_sources = data.get("sources") if isinstance(data, dict) else None
    if not isinstance(raw_sources, list) or not raw_sources:
        return [], [error(MANIFEST, "sources must be a non-empty array")]

    sources: list[Source] = []
    errors: list[str] = []
    seen_targets: set[str] = set()
    for index, raw in enumerate(raw_sources, start=1):
        if not isinstance(raw, dict):
            errors.append(error(MANIFEST, f"sources[{index}] must be an object"))
            continue

        missing = [key for key in REQUIRED if key not in raw]
        if missing:
            errors.extend(error(MANIFEST, f"sources[{index}] missing {key}") for key in missing)
            continue

        values = {key: raw[key] for key in REQUIRED}
        bad = [key for key, value in values.items() if not isinstance(value, str) or not value.strip()]
        if bad:
            errors.extend(error(MANIFEST, f"sources[{index}].{key} must be a non-empty string") for key in bad)
            continue

        include = raw.get("include", ["**"])
        if not isinstance(include, list) or not all(isinstance(item, str) and item for item in include):
            errors.append(error(MANIFEST, f"sources[{index}].include must be a list of non-empty strings"))
            continue

        if not COMMIT_SHA_RE.fullmatch(values["ref"]):
            errors.append(error(MANIFEST, f"sources[{index}].ref must be a pinned 40-character commit SHA"))
            continue

        target = Path(values["target"])
        if target.is_absolute() or ".." in target.parts:
            errors.append(error(MANIFEST, f"sources[{index}].target must stay inside this repo"))
            continue
        if target.as_posix() in seen_targets:
            errors.append(error(MANIFEST, f"sources[{index}].target duplicates another source"))
            continue
        seen_targets.add(target.as_posix())

        sources.append(
            Source(
                repo=values["repo"],
                ref=values["ref"],
                path=Path(values["path"]),
                target=target,
                include=tuple(include),
            )
        )

    return sources, errors


def git(args: list[str], cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True)


def clone_repo(repo: str, ref: str, checkout_dir: Path) -> None:
    checkout_dir.mkdir(parents=True)
    git(["init", "--quiet"], checkout_dir)
    git(["remote", "add", "origin", repo], checkout_dir)
    try:
        git(["fetch", "--quiet", "--depth", "1", "origin", ref], checkout_dir)
    except subprocess.CalledProcessError:
        git(["fetch", "--quiet", "origin", ref], checkout_dir)
    git(["checkout", "--quiet", "--detach", "FETCH_HEAD"], checkout_dir)


def materialize_sources(sources: list[Source], cache_dir: Path) -> dict[tuple[str, str], Path]:
    clones: dict[tuple[str, str], Path] = {}
    for source in sources:
        key = (source.repo, source.ref)
        if key not in clones:
            checkout_dir = cache_dir / f"repo-{len(clones) + 1}"
            clone_repo(source.repo, source.ref, checkout_dir)
            clones[key] = checkout_dir
    return clones


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


def copy_source(source_root: Path, target: Path, files: dict[Path, Path]) -> None:
    if target.exists() or target.is_symlink():
        if target.is_dir() and not target.is_symlink():
            shutil.rmtree(target)
        else:
            target.unlink()

    if source_root.is_file():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_root, target)
        target.chmod(0o644)
        return

    for relative_path, source_file in files.items():
        destination = target / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_file, destination)
        destination.chmod(0o644)


def check_source_matches(source: Source, source_root: Path, files: dict[Path, Path]) -> list[str]:
    target = ROOT / source.target
    actual_files = target_files(target)
    expected_names = set(files)
    actual_names = set(actual_files)

    errors: list[str] = []
    for missing in sorted(expected_names - actual_names):
        errors.append(error(target / missing, "file is missing from vendored target"))
    for extra in sorted(actual_names - expected_names):
        errors.append(error(target / extra, "file is not present in upstream source selection"))
    for relative_path in sorted(expected_names & actual_names):
        if files[relative_path].read_bytes() != actual_files[relative_path].read_bytes():
            errors.append(error(target / relative_path, "file differs from upstream source"))
    return errors


def installable_targets() -> set[str]:
    skills = {
        path.relative_to(ROOT).as_posix()
        for path in (ROOT / "skills").iterdir()
        if path.is_dir() and (path / "SKILL.md").is_file()
    }
    agents_dir = ROOT / "agents"
    agents = {
        path.relative_to(ROOT).as_posix()
        for path in agents_dir.glob("*.md")
        if path.is_file()
    } if agents_dir.exists() else set()
    return skills | agents


def sync_or_check(sources: list[Source], check: bool) -> list[str]:
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="skills-sync-") as tmp:
        clones = materialize_sources(sources, Path(tmp))

        for source in sources:
            source_root = clones[(source.repo, source.ref)] / source.path
            if not source_root.exists():
                errors.append(error(source.target, "source path does not exist upstream"))
                continue

            files = included_files(source_root, source.include)
            if not files:
                errors.append(error(source.target, "source selection produced no files"))
                continue

            if check:
                errors.extend(check_source_matches(source, source_root, files))
            else:
                copy_source(source_root, ROOT / source.target, files)

    expected_targets = {source.target.as_posix() for source in sources} | owned_targets()
    for extra in sorted(installable_targets() - expected_targets):
        errors.append(error(ROOT / extra, "not declared in sources.json"))
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Fail if vendored files differ from pinned sources.")
    args = parser.parse_args(argv)

    sources, errors = load_sources()
    if not errors:
        try:
            errors.extend(sync_or_check(sources, args.check))
        except subprocess.CalledProcessError as exc:
            print(f"git command failed: {' '.join(exc.cmd)}", file=sys.stderr)
            return exc.returncode

    for message in errors:
        print(message)
    if errors:
        action = "check" if args.check else "sync"
        print(f"Source {action} failed: {len(errors)} error(s).", file=sys.stderr)
        return 1

    action = "Checked" if args.check else "Synced"
    print(f"{action} {len(sources)} source(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
