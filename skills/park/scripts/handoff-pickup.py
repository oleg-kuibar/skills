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

import json
import os
import pathlib
import re
import shutil
import sys

# resume already carries the old context; compact just rewrote it. Injecting on
# either duplicates what is in the window.
PICKUP_ON = ("startup", "clear")

PREAMBLE = (
    "Handoff written by the previous session in this directory, before it was "
    "cleared. It is context for continuing that work, not a request to start "
    "acting. Read it, then wait for the user.\n\n"
)

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


def pickup(payload, env=None):
    """Return context text to inject, or None. Consumes the file when it returns text."""
    env = os.environ if env is None else env
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
    # Keep the last one picked up per branch, for recovery from a premature /clear.
    path.replace(path.with_suffix(".md.picked"))
    return PREAMBLE + text


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
    kept.append({
        "matcher": "startup|clear",
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
    print("Registered on SessionStart for startup and clear. Restart Claude Code once.")


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
        assert not path.is_file(), "picked up handoff must be consumed"
        assert path.with_suffix(".md.picked").is_file(), "kept for recovery"

        assert pickup({"source": "clear", "cwd": cwd}) is None, "picked up only once"

        # A second park+pickup replaces the old .picked rather than piling up.
        path.write_text("second", encoding="utf-8")
        pickup({"source": "clear", "cwd": cwd})
        assert len(list(path.parent.glob("*.picked"))) == 1, "one .picked per branch"

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
    print("selftest ok")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
        raise SystemExit(0)
    if "--install" in sys.argv:
        install()
        raise SystemExit(0)
    if "--path" in sys.argv:
        print(prepare(handoff_path(os.getcwd())))
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
