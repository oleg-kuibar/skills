#!/usr/bin/env python3
"""SessionStart hook: give a new session the handoff left by the previous one.

Reads <root>/.claude/handoff/<branch-key>.md and injects it as SessionStart context, then
renames it so it is picked up exactly once. Silent when there is nothing to hand over.

The handoff lives beside the work, not under $HOME. `--path` prints the resolved path
and is how /park finds where to write: one implementation of the rule, no prose copy
to drift from.

Run `--install` once to register the hook. Run `--selftest` to check this file.
Git is read by parsing .git rather than by subprocess, for speed and to avoid a
version-manager shim in the way.
"""

import datetime
import json
import os
import pathlib
import shutil
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import handoff_lifecycle as lifecycle

# Stable path the skill refers to, so an install location does not leak into prose.
HOOK_LINK = "hooks/handoff-pickup.py"


def pickup(payload, env=None, now=None):
    """Translate SessionStart JSON into the Handoff lifecycle interface."""
    env = os.environ if env is None else env
    return lifecycle.consume_for_session(
        payload.get("cwd") or os.getcwd(),
        payload.get("source"),
        is_background=bool(env.get("CLAUDE_JOB_DIR")),
        now=now,
    )


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
    # Built from the lifecycle sources, so registration cannot drift from pickup behavior.
    kept.append({
        "matcher": "|".join(lifecycle.PICKUP_ON),
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
    print(f"Registered on SessionStart for {', '.join(lifecycle.PICKUP_ON)}. "
          "Restart Claude Code once.")


def selftest():
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        tmp = pathlib.Path(tmp).resolve()

        def write_path(cwd, now=None):
            return lifecycle.prepare_for_write(cwd, now)[0]

        plain = tmp / "notarepo" / "sub"
        plain.mkdir(parents=True)
        prepared, warning = lifecycle.prepare_for_write(plain)
        assert prepared == plain / ".claude/handoff/_.md" and warning == "", \
            "the lifecycle interface prepares a free path"
        prepared.write_text("public lifecycle", encoding="utf-8")
        consumed = lifecycle.consume_for_session(plain, "clear")
        assert consumed and consumed.endswith("public lifecycle") and not prepared.exists(), \
            "the lifecycle interface consumes a Handoff once"
        assert write_path(plain) == plain / ".claude/handoff/_.md", "no repo, keyed on cwd"

        repo = tmp / "repo"
        (repo / ".git").mkdir(parents=True)
        (repo / "deep" / "er").mkdir(parents=True)
        (repo / ".git" / "HEAD").write_text("ref: refs/heads/feat/token\n")
        want = repo / ".claude/handoff/feat%2Ftoken.md"
        assert write_path(repo) == want, write_path(repo)
        assert write_path(repo / "deep/er") == want, "a subdirectory maps to repo root"

        slash = write_path(repo)
        (repo / ".git" / "HEAD").write_text("ref: refs/heads/feat-token\n")
        dash = write_path(repo)
        assert slash != dash, "distinct branch names need distinct handoff files"

        (repo / ".git" / "HEAD").write_text("ref: refs/heads/../../escape\n")
        got = write_path(repo)
        assert got.parent == repo / ".claude/handoff", f"branch name escaped the dir: {got}"
        assert got.name.endswith("escape.md") and "/" not in got.name, got.name
        (repo / ".git" / "HEAD").write_text("ref: refs/heads/v1.2-hotfix\n")
        dotted = write_path(repo)
        assert dotted.name == "v1.2-hotfix.md", dotted.name
        assert dotted.with_suffix(lifecycle.PICKED_SUFFIX).name == "v1.2-hotfix.md.picked", \
            "a dot in a branch"
        (repo / ".git" / "HEAD").write_text("ref: refs/heads/...\n")
        assert write_path(repo).name == "_.md", "a name of only dots is not a filename"
        (repo / ".git" / "HEAD").write_text("9f1c0de0\n")
        assert write_path(repo).name == "_.md", "detached HEAD is not a branch"

        wt = tmp / "repo.worktrees" / "hotfix"
        wt.mkdir(parents=True)
        linked = repo / ".git" / "worktrees" / "hotfix"
        linked.mkdir(parents=True)
        (linked / "HEAD").write_text("ref: refs/heads/hotfix\n")
        (wt / ".git").write_text(f"gitdir: {linked}\n")
        assert write_path(wt) == wt / ".claude/handoff/hotfix.md", write_path(wt)

        (repo / ".git" / "HEAD").write_text("ref: refs/heads/main\n")
        path = write_path(repo)
        assert (path.parent / ".gitignore").read_text() == lifecycle.SELF_IGNORE, \
            "ignores itself"
        (path.parent / ".gitignore").write_text("grades.jsonl\n")
        write_path(repo)
        assert "*" in (path.parent / ".gitignore").read_text().splitlines(), \
            "an existing ignore file must still protect handoffs"
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
        assert path.with_suffix(lifecycle.PICKED_SUFFIX).is_file(), "kept for recovery"

        assert pickup({"source": "clear", "cwd": cwd}) is None, "picked up only once"

        # A second park+pickup replaces the old .picked rather than piling up.
        path.write_text("second", encoding="utf-8")
        assert pickup({"source": "compact", "cwd": cwd}), "compaction drops it too"
        assert len(list(path.parent.glob(f"*{lifecycle.PICKED_SUFFIX}"))) == 1, \
            "one .picked per branch"

        # Age is read from the mtime, so both checks move the clock instead of the file.
        def written_at(p):
            return datetime.datetime.fromtimestamp(p.stat().st_mtime, datetime.timezone.utc)

        path.write_text("old news", encoding="utf-8")
        later = written_at(path) + datetime.timedelta(days=lifecycle.STALE_AFTER_DAYS)
        got = pickup({"source": "clear", "cwd": cwd}, now=later)
        assert f"{lifecycle.STALE_AFTER_DAYS} days ago" in got, got

        # Overwriting an unread handoff is silent data loss, so --path warns about it.
        assert not path.is_file() and lifecycle.prepare_for_write(repo, later)[1] == "", \
            "free path, no warning"
        path.write_text("about to be flattened", encoding="utf-8")
        now = written_at(path)
        assert "0m ago" in lifecycle.prepare_for_write(repo, now)[1], \
            "a same-session re-park reads as minutes"
        assert "2h ago" in lifecycle.prepare_for_write(
            repo, now + datetime.timedelta(hours=2, minutes=5))[1]
        assert "3d ago" in lifecycle.prepare_for_write(
            repo, now + datetime.timedelta(days=3))[1]
        path.unlink()

        # A .picked for a branch nobody parks on again is what actually piles up.
        abandoned = path.parent / f"deleted-branch{lifecycle.PICKED_SUFFIX}"
        abandoned.write_text("from a merged branch", encoding="utf-8")
        path.write_text("newest", encoding="utf-8")
        gone = written_at(abandoned) + datetime.timedelta(
            days=lifecycle.DISCARD_PICKED_AFTER_DAYS, seconds=1)
        got = pickup({"source": "clear", "cwd": cwd}, now=gone)
        assert got.endswith("newest"), "the sweep must not eat the handoff being picked up"
        assert not abandoned.is_file(), "a .picked past its window is deleted"
        assert path.with_suffix(lifecycle.PICKED_SUFFIX).is_file(), "this branch keeps its own"

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
        # A source in the matcher but not in the lifecycle is a hook that runs and does nothing.
        assert set(ours[0]["matcher"].split("|")) == set(lifecycle.PICKUP_ON), \
            ours[0]["matcher"]
    print("selftest ok")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
        raise SystemExit(0)
    if "--install" in sys.argv:
        install()
        raise SystemExit(0)
    if "--path" in sys.argv:
        path, warning = lifecycle.prepare_for_write(os.getcwd())
        # Warning first and on stderr, path last, because the caller reads one interleaved
        # block and the contract is that the path is the last line.
        sys.stderr.write(warning)
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
