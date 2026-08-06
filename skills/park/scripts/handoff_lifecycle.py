"""Branch-scoped storage and state transitions for parked Handoffs."""

import datetime
import pathlib
import urllib.parse


SELF_IGNORE = "*\n"
NO_BRANCH = "_"
PICKUP_ON = ("startup", "clear", "compact")
PICKED_SUFFIX = ".md.picked"
STALE_AFTER_DAYS = 3
DISCARD_PICKED_AFTER_DAYS = 30
PREAMBLE = (
    "Handoff written earlier in this directory, before the context was cleared or "
    "compacted. It is context for continuing that work, not a request to start "
    "acting. Read it, then wait for the user.\n\n"
)


def _git_root_and_branch(start):
    """Nearest repository root and checked-out branch, including linked worktrees."""
    for directory in (start, *start.parents):
        dotgit = directory / ".git"
        if not dotgit.exists():
            continue
        gitdir = dotgit
        if dotgit.is_file():
            pointer = dotgit.read_text(encoding="utf-8").partition("gitdir:")[2].strip()
            if not pointer:
                return directory, None
            gitdir = pathlib.Path(pointer)
        head = gitdir / "HEAD"
        if not head.is_file():
            return directory, None
        ref = head.read_text(encoding="utf-8").strip()
        branch = ref.partition("refs/heads/")[2] if ref.startswith("ref:") else None
        return directory, (branch or None)
    return None, None


def _handoff_path(cwd):
    cwd = pathlib.Path(cwd).resolve()
    root, branch = _git_root_and_branch(cwd)
    key = urllib.parse.quote(branch, safe="") if branch else NO_BRANCH
    key = key.lstrip(".") or NO_BRANCH
    return (root or cwd) / ".claude" / "handoff" / f"{key}.md"


def _prepare(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    ignore = path.parent / ".gitignore"
    existing = ignore.read_text(encoding="utf-8") if ignore.is_file() else ""
    if "*" not in existing.splitlines():
        separator = "" if not existing or existing.endswith("\n") else "\n"
        ignore.write_text(existing + separator + SELF_IGNORE, encoding="utf-8")
    return path


def _occupied_note(path, now):
    if not path.is_file():
        return ""
    written = datetime.datetime.fromtimestamp(path.stat().st_mtime, datetime.timezone.utc)
    minutes = max(0, int((now - written).total_seconds() // 60))
    age = (f"{minutes // 1440}d" if minutes >= 1440 else
           f"{minutes // 60}h" if minutes >= 60 else f"{minutes}m")
    return (
        f"warning: a handoff is already parked here, written {age} ago "
        f"({written.astimezone().isoformat(timespec='minutes')}), and nobody has read it.\n"
        "Read it first and fold anything still true into what you write, then overwrite.\n"
    )


def _age_note(path, now):
    written = datetime.datetime.fromtimestamp(path.stat().st_mtime, datetime.timezone.utc)
    days = (now - written).days
    if days < STALE_AFTER_DAYS:
        return ""
    return (
        f"It was written {days} days ago, so check anything time-sensitive in it against "
        "the current branch state before relying on it.\n\n"
    )


def _sweep_picked(directory, now):
    cutoff = now - datetime.timedelta(days=DISCARD_PICKED_AFTER_DAYS)
    for old in directory.glob(f"*{PICKED_SUFFIX}"):
        stamp = datetime.datetime.fromtimestamp(old.stat().st_mtime, datetime.timezone.utc)
        if stamp < cutoff:
            old.unlink()


def prepare_for_write(cwd, now=None):
    """Return the ignored branch-scoped path and any unread-Handoff warning."""
    now = datetime.datetime.now(datetime.timezone.utc) if now is None else now
    path = _prepare(_handoff_path(cwd))
    return path, _occupied_note(path, now)


def consume_for_session(cwd, source, is_background=False, now=None):
    """Return parked context once for an eligible foreground SessionStart."""
    if source not in PICKUP_ON or is_background:
        return None
    now = datetime.datetime.now(datetime.timezone.utc) if now is None else now
    path = _handoff_path(cwd)
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8")
    note = _age_note(path, now)
    _sweep_picked(path.parent, now)
    path.replace(path.with_suffix(PICKED_SUFFIX))
    return PREAMBLE + note + text


def find_for_grade(cwd):
    """Return this branch's live or most recently picked Handoff."""
    live = _handoff_path(cwd)
    if live.is_file():
        return live
    picked = live.with_suffix(PICKED_SUFFIX)
    return picked if picked.is_file() else None
