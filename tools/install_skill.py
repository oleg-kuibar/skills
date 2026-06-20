#!/usr/bin/env python3
"""Install a skill from this repository into Codex's personal skills directory."""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def source_skill_dir(skill_name: str) -> Path:
    canonical = repo_root() / "skills" / skill_name
    if canonical.exists():
        return canonical
    return repo_root() / skill_name


def default_target() -> Path:
    codex_home = os.environ.get("CODEX_HOME")
    base = Path(codex_home).expanduser() if codex_home else Path.home() / ".codex"
    return base / "skills"


def remove_existing(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("skill_name", help="Top-level skill folder to install.")
    parser.add_argument(
        "--target",
        type=Path,
        default=default_target(),
        help="Skills directory. Defaults to ${CODEX_HOME:-$HOME/.codex}/skills.",
    )
    parser.add_argument("--copy", action="store_true", help="Copy instead of creating a symlink.")
    parser.add_argument("--force", action="store_true", help="Replace an existing target path.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    source = source_skill_dir(args.skill_name)
    target_dir = args.target.expanduser().resolve()
    target = target_dir / args.skill_name

    if not (source / "SKILL.md").is_file():
        print(f"error: {source} is not a skill folder with SKILL.md", file=sys.stderr)
        return 1

    target_dir.mkdir(parents=True, exist_ok=True)

    if target.exists() or target.is_symlink():
        if target.is_symlink() and target.resolve() == source.resolve() and not args.copy:
            print(f"already installed: {target} -> {source}")
            return 0
        if not args.force:
            print(f"error: {target} already exists; use --force to replace it", file=sys.stderr)
            return 1
        remove_existing(target)

    if args.copy:
        shutil.copytree(source, target)
        print(f"copied {source} to {target}")
    else:
        target.symlink_to(source, target_is_directory=True)
        print(f"linked {target} -> {source}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
