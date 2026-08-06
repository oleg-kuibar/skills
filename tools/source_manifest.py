"""Parse the canonical Source Manifest for vendored and owned artifacts."""

from dataclasses import dataclass
import json
from pathlib import Path
import re


COMMIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
REQUIRED = ("repo", "ref", "path", "target")


@dataclass(frozen=True)
class Source:
    repo: str
    ref: str
    path: Path
    target: Path
    include: tuple[str, ...]


@dataclass(frozen=True)
class Manifest:
    sources: tuple[Source, ...]
    owned: frozenset[str]


def load_manifest(path):
    """Return a parsed Source Manifest and validation messages."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return Manifest((), frozenset()), [f"invalid JSON: {exc}"]
    if not isinstance(data, dict):
        return Manifest((), frozenset()), ["manifest must be an object"]
    errors = []
    if data.get("version") != 1:
        errors.append("version must be 1")

    raw_sources = data.get("sources")
    if not isinstance(raw_sources, list) or not raw_sources:
        errors.append("sources must be a non-empty array")
        raw_sources = []

    sources = []
    seen_targets = set()
    for index, raw in enumerate(raw_sources, start=1):
        if not isinstance(raw, dict):
            errors.append(f"sources[{index}] must be an object")
            continue
        missing = [key for key in REQUIRED if key not in raw]
        if missing:
            errors.extend(f"sources[{index}] missing {key}" for key in missing)
            continue
        values = {key: raw[key] for key in REQUIRED}
        bad = [key for key, value in values.items()
               if not isinstance(value, str) or not value.strip()]
        if bad:
            errors.extend(f"sources[{index}].{key} must be a non-empty string" for key in bad)
            continue
        include = raw.get("include", ["**"])
        if not isinstance(include, list) or not all(
                isinstance(item, str) and item for item in include):
            errors.append(f"sources[{index}].include must be a list of non-empty strings")
            continue
        if not COMMIT_SHA_RE.fullmatch(values["ref"]):
            errors.append(f"sources[{index}].ref must be a pinned 40-character commit SHA")
            continue
        source_path = Path(values["path"])
        if source_path.is_absolute() or ".." in source_path.parts:
            errors.append(f"sources[{index}].path must stay inside its checkout")
            continue
        target = Path(values["target"])
        if target.is_absolute() or ".." in target.parts:
            errors.append(f"sources[{index}].target must stay inside this repo")
            continue
        if target.as_posix() in seen_targets:
            errors.append(f"sources[{index}].target duplicates another source")
            continue
        seen_targets.add(target.as_posix())
        sources.append(Source(
            repo=values["repo"],
            ref=values["ref"],
            path=source_path,
            target=target,
            include=tuple(include),
        ))

    raw_owned = data.get("owned", [])
    if not isinstance(raw_owned, list):
        errors.append("owned must be an array")
        raw_owned = []
    owned = set()
    for index, raw in enumerate(raw_owned, start=1):
        if not isinstance(raw, str) or not raw.strip():
            errors.append(f"owned[{index}] must be a non-empty string")
            continue
        target = Path(raw)
        if target.is_absolute() or ".." in target.parts:
            errors.append(f"owned[{index}] must stay inside this repo")
            continue
        key = target.as_posix()
        if key in owned:
            errors.append(f"owned[{index}] duplicates another owned target")
            continue
        overlap = next((source.target for source in sources
                        if target == source.target or target in source.target.parents
                        or source.target in target.parents), None)
        if overlap is not None:
            errors.append(f"owned[{index}] overlaps source target {overlap.as_posix()}")
            continue
        owned.add(key)
    return Manifest(tuple(sources), frozenset(owned)), errors
