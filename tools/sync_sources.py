#!/usr/bin/env python3
"""Sync vendored skills and agents from pinned sources.json."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import source_manifest


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "sources.json"
Source = source_manifest.Source


def relative(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def error(path: Path, message: str) -> str:
    return f"ERROR: {relative(path)}: {message}"


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


def materialize_sources(sources: tuple[Source, ...], cache_dir: Path) -> dict[tuple[str, str], Path]:
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


def sync_or_check(sources: tuple[Source, ...], owned: frozenset[str], check: bool) -> list[str]:
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

    expected_targets = {source.target.as_posix() for source in sources} | owned
    for extra in sorted(installable_targets() - expected_targets):
        errors.append(error(ROOT / extra, "not declared in sources.json"))
    return errors


def selftest() -> None:
    with tempfile.TemporaryDirectory(prefix="source-manifest-test-") as tmp:
        path = Path(tmp) / "sources.json"
        path.write_text(json.dumps({"version": 2, "sources": [], "owned": []}))
        _, errors = source_manifest.load_manifest(path)
        assert "version must be 1" in errors, "the Source Manifest owns version validation"

        path.write_text(json.dumps({
            "version": 1,
            "sources": [{"repo": "https://example.invalid/repo.git", "ref": "a" * 40,
                         "path": "skill", "target": "skills/vendored"}],
            "owned": ["skills/park"],
        }))
        manifest, errors = source_manifest.load_manifest(path)
        assert not errors and manifest.sources[0].target == Path("skills/vendored") and \
            manifest.owned == frozenset({"skills/park"}), \
            "one Source Manifest interface returns vendored and owned artifacts"

        path.write_text(json.dumps({
            "version": 1,
            "sources": [{"repo": "https://example.invalid/repo.git", "ref": "a" * 40,
                         "path": "skill", "target": "skills/vendored"}],
            "owned": ["skills/vendored"],
        }))
        _, errors = source_manifest.load_manifest(path)
        assert "owned[1] overlaps source target skills/vendored" in errors, \
            "vendored and owned artifacts cannot overlap"

        path.write_text(json.dumps({
            "version": 1,
            "sources": [{"repo": "https://example.invalid/repo.git", "ref": "a" * 40,
                         "path": "../escape", "target": "skills/vendored"}],
            "owned": [],
        }))
        _, errors = source_manifest.load_manifest(path)
        assert "sources[1].path must stay inside its checkout" in errors, \
            "a vendored source path cannot escape its checkout"
    print("selftest ok")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Fail if vendored files differ from pinned sources.")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args(argv)

    if args.selftest:
        selftest()
        return 0

    manifest, manifest_errors = source_manifest.load_manifest(MANIFEST)
    errors = [error(MANIFEST, message) for message in manifest_errors]
    if not errors:
        try:
            errors.extend(sync_or_check(manifest.sources, manifest.owned, args.check))
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
    print(f"{action} {len(manifest.sources)} source(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
