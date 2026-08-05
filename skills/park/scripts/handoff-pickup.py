#!/usr/bin/env python3
"""SessionStart hook: give a new session the handoff left by the previous one.

Reads <root>/.claude/handoff/<branch>.md and injects it as SessionStart context, then
renames it so it is picked up exactly once. Silent when there is nothing to hand over.

The handoff lives beside the work, not under $HOME, so it survives a checkout on a
different machine or user. `--path` prints the resolved path and is how /park finds
where to write: one implementation of the rule, no prose copy to drift from.

Run `--install` once to register the hook. Run `--selftest` to check this file.
Git is read by parsing .git rather than by subprocess, for speed and to avoid a
version-manager shim in the way.
"""

import datetime
import json
import os
import pathlib
import re
import shutil
import sys

# resume already carries the old context. compact does not: the docs list what survives
# it, and a conversation-only fact is not on the list, so a parked handoff is exactly
# what compaction drops. https://code.claude.com/docs/en/context-window
PICKUP_ON = ("startup", "clear", "compact")

PREAMBLE = (
    "Handoff written earlier in this directory, before the context was cleared or "
    "compacted. It is context for continuing that work, not a request to start "
    "acting. Read it, then wait for the user.\n\n"
)

# How old a handoff can be before the preamble says so. Claude Code stamps its own auto
# memory with a `modified` field for the same reason: the age of a fact tells the reader
# how much to trust it. https://code.claude.com/docs/en/memory
STALE_AFTER_DAYS = 3

# Kept for recovery from a premature /clear, then aged out. Without this they are one
# per branch forever, holding work state nobody reads.
PICKED_SUFFIX = ".md.picked"
DISCARD_PICKED_AFTER_DAYS = 30

# Handoffs are transient notes, never committed. A .gitignore inside the directory
# ignoring itself keeps every repo clean without editing any repo's .gitignore.
SELF_IGNORE = "*\n"

NO_BRANCH = "_"

# Stable path the skill refers to, so an install location does not leak into prose.
HOOK_LINK = "hooks/handoff-pickup.py"


def git_root_and_branch(start):
    """Nearest directory containing .git, and its checked-out branch. (None, None) if
    outside a repo. A worktree resolves to the worktree itself, on its own branch."""
    for d in (start, *start.parents):
        dotgit = d / ".git"
        if not dotgit.exists():
            continue
        gitdir = dotgit
        if dotgit.is_file():
            # Linked worktree: ".git" is a file holding "gitdir: <path>".
            pointer = dotgit.read_text(encoding="utf-8").partition("gitdir:")[2].strip()
            if not pointer:
                return d, None
            gitdir = pathlib.Path(pointer)
        head = gitdir / "HEAD"
        if not head.is_file():
            return d, None
        ref = head.read_text(encoding="utf-8").strip()
        # Detached HEAD holds a bare sha, which is not a branch.
        branch = ref.partition("refs/heads/")[2] if ref.startswith("ref:") else None
        return d, (branch or None)
    return None, None


def handoff_path(cwd):
    """Where this directory's handoff lives. Repo root when there is one, else cwd."""
    cwd = pathlib.Path(cwd).resolve()
    root, branch = git_root_and_branch(cwd)
    # Branch names reach the filesystem here, so allow only safe characters.
    slug = re.sub(r"[^A-Za-z0-9._-]", "-", branch) if branch else NO_BRANCH
    slug = slug.lstrip(".") or NO_BRANCH  # no dotfiles, no "..", no empty name
    return (root or cwd) / ".claude" / "handoff" / f"{slug}.md"


def prepare(path):
    """Make the directory writable by /park and invisible to git."""
    path.parent.mkdir(parents=True, exist_ok=True)
    ignore = path.parent / ".gitignore"
    if not ignore.is_file():
        ignore.write_text(SELF_IGNORE, encoding="utf-8")
    return path


def occupied_note(path, now):
    """A warning for whoever is about to overwrite an unread handoff, or "" when the file
    is free. One file per branch, so a second /park destroys the first: Emacs solves the
    same collision the same way, by comparing mtimes and telling the writer rather than
    locking or merging. https://www.gnu.org/software/emacs/manual/html_node/emacs/Interlocking.html
    A fresh mtime is usually the same session re-parking, so the age is what makes the
    difference decidable and the caller is left to decide it."""
    if not path.is_file():
        return ""
    written = datetime.datetime.fromtimestamp(path.stat().st_mtime, datetime.timezone.utc)
    mins = max(0, int((now - written).total_seconds() // 60))
    age = f"{mins // 1440}d" if mins >= 1440 else f"{mins // 60}h" if mins >= 60 else f"{mins}m"
    return (
        f"warning: a handoff is already parked here, written {age} ago "
        f"({written.astimezone().isoformat(timespec='minutes')}), and nobody has read it.\n"
        "Read it first and fold anything still true into what you write, then overwrite.\n"
    )


def age_note(path, now):
    """A line about when this was written, or "" while it is still fresh. The mtime is
    already on disk, so dating a handoff costs nothing in the file itself."""
    written = datetime.datetime.fromtimestamp(path.stat().st_mtime, datetime.timezone.utc)
    days = (now - written).days
    if days < STALE_AFTER_DAYS:
        return ""
    return (
        f"It was written {days} days ago, so check anything time-sensitive in it against "
        "the current branch state before relying on it.\n\n"
    )


def sweep_picked(directory, now):
    """Delete already-picked handoffs past their recovery window."""
    cutoff = now - datetime.timedelta(days=DISCARD_PICKED_AFTER_DAYS)
    for old in directory.glob(f"*{PICKED_SUFFIX}"):
        stamp = datetime.datetime.fromtimestamp(old.stat().st_mtime, datetime.timezone.utc)
        if stamp < cutoff:
            old.unlink()


def pickup(payload, env=None, now=None):
    """Return context text to inject, or None. Consumes the file when it returns text."""
    env = os.environ if env is None else env
    now = datetime.datetime.now(datetime.timezone.utc) if now is None else now
    if payload.get("source") not in PICKUP_ON:
        return None
    # A background agent (`claude --bg`) already carries its handoff as its prompt, and
    # starts with source "startup" in the same cwd. Without this it eats a file parked
    # for the next interactive session. CLAUDE_JOB_DIR is set only in background jobs.
    if env.get("CLAUDE_JOB_DIR"):
        return None
    path = handoff_path(payload.get("cwd") or os.getcwd())
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8")
    note = age_note(path, now)
    sweep_picked(path.parent, now)  # before the rename, so this one is never a candidate
    # Keep the last one picked up per branch, for recovery from a premature /clear.
    # replace is atomic, so two sessions starting at once cannot both read this: one gets
    # the text, the other sees no file and stays silent, which is the intended once-only.
    path.replace(path.with_suffix(PICKED_SUFFIX))
    return PREAMBLE + note + text


def interpreter():
    """A python that will still be there at the next session start. Prefer the system
    one: a version-manager shim can exit non-zero in a directory that pins no version."""
    system = pathlib.Path("/usr/bin/python3")
    return str(system if system.is_file() else sys.executable)


def link_self(claude_dir):
    """Point <claude_dir>/hooks/handoff-pickup.py at this file. Returns the link path."""
    link = claude_dir / HOOK_LINK
    link.parent.mkdir(parents=True, exist_ok=True)
    target = pathlib.Path(__file__).resolve()
    if link.is_symlink() or link.exists():
        link.unlink()
    try:
        link.symlink_to(target)
    except (OSError, NotImplementedError):
        # No symlink support. A copy goes stale, so re-run --install after an update.
        shutil.copy2(target, link)
    return link


def register(settings, command):
    """Add the SessionStart hook to a settings.json file, replacing an older entry for
    this hook and leaving every other key and hook untouched."""
    data = {}
    if settings.is_file() and settings.read_text(encoding="utf-8").strip():
        data = json.loads(settings.read_text(encoding="utf-8"))  # broken JSON: raise, do not clobber
    starts = data.setdefault("hooks", {}).setdefault("SessionStart", [])
    kept = [h for h in starts if "handoff-pickup" not in json.dumps(h)]
    # Built from PICKUP_ON, so the registered matcher cannot drift from what pickup honours.
    kept.append({
        "matcher": "|".join(PICKUP_ON),
        "hooks": [{"type": "command", "command": command, "timeout": 5}],
    })
    data["hooks"]["SessionStart"] = kept
    settings.parent.mkdir(parents=True, exist_ok=True)
    tmp = settings.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    tmp.replace(settings)
    return settings


def install():
    claude_dir = pathlib.Path(os.path.expanduser("~")) / ".claude"
    link = link_self(claude_dir)
    settings = register(claude_dir / "settings.json", f'{interpreter()} "{link}"')
    print(f"hook  {link}")
    print(f"settings  {settings}")
    print(f"Registered on SessionStart for {', '.join(PICKUP_ON)}. Restart Claude Code once.")


def selftest():
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        tmp = pathlib.Path(tmp).resolve()

        plain = tmp / "notarepo" / "sub"
        plain.mkdir(parents=True)
        assert handoff_path(plain) == plain / ".claude/handoff/_.md", "no repo, keyed on cwd"

        repo = tmp / "repo"
        (repo / ".git").mkdir(parents=True)
        (repo / "deep" / "er").mkdir(parents=True)
        (repo / ".git" / "HEAD").write_text("ref: refs/heads/feat/token cache\n")
        want = repo / ".claude/handoff/feat-token-cache.md"
        assert handoff_path(repo) == want, handoff_path(repo)
        assert handoff_path(repo / "deep/er") == want, "a subdirectory maps to repo root"

        (repo / ".git" / "HEAD").write_text("ref: refs/heads/../../escape\n")
        got = handoff_path(repo)
        assert got.parent == repo / ".claude/handoff", f"branch name escaped the dir: {got}"
        assert got.name.endswith("escape.md") and "/" not in got.name, got.name
        (repo / ".git" / "HEAD").write_text("ref: refs/heads/v1.2-hotfix\n")
        dotted = handoff_path(repo)
        assert dotted.name == "v1.2-hotfix.md", dotted.name
        assert dotted.with_suffix(PICKED_SUFFIX).name == "v1.2-hotfix.md.picked", "a dot in a branch"
        (repo / ".git" / "HEAD").write_text("ref: refs/heads/...\n")
        assert handoff_path(repo).name == "_.md", "a name of only dots is not a filename"
        (repo / ".git" / "HEAD").write_text("9f1c0de0\n")
        assert handoff_path(repo).name == "_.md", "detached HEAD is not a branch"

        wt = tmp / "repo.worktrees" / "hotfix"
        wt.mkdir(parents=True)
        linked = repo / ".git" / "worktrees" / "hotfix"
        linked.mkdir(parents=True)
        (linked / "HEAD").write_text("ref: refs/heads/hotfix\n")
        (wt / ".git").write_text(f"gitdir: {linked}\n")
        assert handoff_path(wt) == wt / ".claude/handoff/hotfix.md", handoff_path(wt)

        (repo / ".git" / "HEAD").write_text("ref: refs/heads/main\n")
        path = prepare(handoff_path(repo))
        assert (path.parent / ".gitignore").read_text() == SELF_IGNORE, "ignores itself"
        cwd = str(repo)

        assert pickup({"source": "clear", "cwd": cwd}) is None, "no file, no context"

        path.write_text("state of play", encoding="utf-8")
        assert pickup({"source": "resume", "cwd": cwd}) is None, "resume must not pick up"
        assert path.is_file(), "a skipped source must leave the handoff in place"

        assert pickup({"source": "startup", "cwd": cwd}, {"CLAUDE_JOB_DIR": "/j"}) is None, \
            "a background agent must not consume a parked handoff"
        assert path.is_file(), "background agent must leave the handoff in place"

        got = pickup({"source": "clear", "cwd": cwd})
        assert got and got.endswith("state of play"), got
        assert "days ago" not in got, "a handoff written just now is not stale"
        assert not path.is_file(), "picked up handoff must be consumed"
        assert path.with_suffix(PICKED_SUFFIX).is_file(), "kept for recovery"

        assert pickup({"source": "clear", "cwd": cwd}) is None, "picked up only once"

        # A second park+pickup replaces the old .picked rather than piling up.
        path.write_text("second", encoding="utf-8")
        assert pickup({"source": "compact", "cwd": cwd}), "compaction drops it too"
        assert len(list(path.parent.glob(f"*{PICKED_SUFFIX}"))) == 1, "one .picked per branch"

        # Age is read from the mtime, so both checks move the clock instead of the file.
        def written_at(p):
            return datetime.datetime.fromtimestamp(p.stat().st_mtime, datetime.timezone.utc)

        path.write_text("old news", encoding="utf-8")
        later = written_at(path) + datetime.timedelta(days=STALE_AFTER_DAYS)
        got = pickup({"source": "clear", "cwd": cwd}, now=later)
        assert f"{STALE_AFTER_DAYS} days ago" in got, got

        # Overwriting an unread handoff is silent data loss, so --path warns about it.
        assert not path.is_file() and occupied_note(path, later) == "", "free path, no warning"
        path.write_text("about to be flattened", encoding="utf-8")
        now = written_at(path)
        assert "0m ago" in occupied_note(path, now), "a same-session re-park reads as minutes"
        assert "2h ago" in occupied_note(path, now + datetime.timedelta(hours=2, minutes=5))
        assert "3d ago" in occupied_note(path, now + datetime.timedelta(days=3))
        path.unlink()

        # A .picked for a branch nobody parks on again is what actually piles up.
        abandoned = path.parent / f"deleted-branch{PICKED_SUFFIX}"
        abandoned.write_text("from a merged branch", encoding="utf-8")
        path.write_text("newest", encoding="utf-8")
        gone = written_at(abandoned) + datetime.timedelta(days=DISCARD_PICKED_AFTER_DAYS, seconds=1)
        got = pickup({"source": "clear", "cwd": cwd}, now=gone)
        assert got.endswith("newest"), "the sweep must not eat the handoff being picked up"
        assert not abandoned.is_file(), "a .picked past its window is deleted"
        assert path.with_suffix(PICKED_SUFFIX).is_file(), "this branch keeps its own"

        # --install: writable link, and a settings merge that keeps what was there.
        home = tmp / "home" / ".claude"
        link = link_self(home)
        assert link.exists() and pathlib.Path(os.path.realpath(link)).name == \
            pathlib.Path(__file__).name, "link points at this file"
        link_self(home)  # twice in a row must not fail on the existing link
        settings = home / "settings.json"
        mine = {"matcher": "startup", "hooks": [{"type": "command", "command": "echo hi"}]}
        settings.write_text(json.dumps({"model": "opus", "hooks": {"SessionStart": [mine]}}))
        register(settings, "py /x/handoff-pickup.py")
        register(settings, "py /y/handoff-pickup.py")
        data = json.loads(settings.read_text())
        starts = data["hooks"]["SessionStart"]
        assert data["model"] == "opus", "unrelated settings survive"
        assert mine in starts, "unrelated SessionStart hook survives"
        ours = [h for h in starts if "handoff-pickup" in json.dumps(h)]
        assert len(ours) == 1, f"one entry after two installs, got {len(ours)}"
        assert ours[0]["hooks"][0]["command"] == "py /y/handoff-pickup.py", "latest path wins"
        # A source in the matcher but not in PICKUP_ON is a hook that runs and does nothing.
        assert set(ours[0]["matcher"].split("|")) == set(PICKUP_ON), ours[0]["matcher"]
    print("selftest ok")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
        raise SystemExit(0)
    if "--install" in sys.argv:
        install()
        raise SystemExit(0)
    if "--path" in sys.argv:
        path = prepare(handoff_path(os.getcwd()))
        # Warning first and on stderr, path last, because the caller reads one interleaved
        # block and the contract is that the path is the last line.
        sys.stderr.write(occupied_note(path, datetime.datetime.now(datetime.timezone.utc)))
        print(path)
        raise SystemExit(0)
    try:
        context = pickup(json.load(sys.stdin))
    except Exception:
        raise SystemExit(0)  # a broken handoff must never block a session opening
    if context:
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": context,
            }
        }))
