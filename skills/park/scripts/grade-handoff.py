#!/usr/bin/env python3
"""Score a written handoff against the session that produced it.

A handoff can only be wrong in ways a test cannot see: a next step nobody can act on,
a finding that was already in a commit, a fact that was in the session and got dropped.
So the check is a second model reading both the session and the handoff, with the same
SKILL.md the writer had. It runs locally through `claude -p`.

    grade-handoff.py                       # newest transcript here, newest handoff here
    grade-handoff.py --handoff F --session T
    grade-handoff.py --digest              # print what the judge would see, spend nothing

The judge runs with no settings loaded, so it grades against SKILL.md and nothing else.
A grade produced here means the same thing as a grade produced on another machine.

Scores append to this directory's own .claude/handoff/grades.jsonl, whatever --handoff
points at, so a series of grades stays in one comparable file. Already gitignored.
"""

import argparse
import json
import os
import pathlib
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from importlib import import_module

hook = import_module("handoff-pickup")

# The judge reads text and tool names, never tool results. Tool results are file contents
# and command output, which is what makes a raw transcript 25x its own text. Names and
# arguments still show what the session did.
TOOL_ARG_CHARS = 120

# `--setting-sources ""` loads no user, project, or local settings. That is what makes a
# grade mean the same thing on every machine: without it the judge also gets the grader's
# own CLAUDE.md and SessionStart hooks, which are a second rubric it was told not to use.
# It is also why nothing here has to dodge the pickup hook. No settings, no hooks, so the
# hook cannot fire and consume the handoff under grade.
# `--disallowedTools "*"`: the judge grades what it was given. Reading the repo would let
# it credit the handoff for facts that were never in it.
JUDGE_ARGS = ["claude", "-p", "--setting-sources", "", "--output-format", "json",
              "--disallowedTools", "*"]

SKILL = pathlib.Path(__file__).resolve().parent.parent / "SKILL.md"

RUBRIC = """You are grading a handoff file written by an AI coding session to hand its
live state to the next session. You have the session it was written from, and the skill
that told it what to write.

Grade only against the skill's own rules. Do not invent criteria.

Score each 1-5, where 3 is acceptable and 5 is nothing to improve:

- actionable: could someone with no memory of the session take the next step from this
  file alone? Deduct for a next step that names no file, command, or decision.
- durable_only: does it hold only what dies with the context window? Deduct for anything
  already recoverable from a commit, diff, ticket, plan file, or CLAUDE.md that is
  restated instead of referenced by path or URL.
- findings: are the expensive findings there? A ruled-out approach, a measured number, a
  user decision and its reason, a failure and why. Deduct for each one that was in the
  session and is missing from the handoff. This is the category with no other home.
- density: is every line carrying weight? Deduct for transcript-style narration, for
  restating the obvious, and for length beyond what the content needs.
- safety: any secret, key, token, password, or personal data that should have been
  redacted?

Then list:
- dropped: facts that were in the session, would die with the context, and are not in the
  handoff. Quote or closely paraphrase each. This is the most useful part of the grade.
- wasted: lines that could be cut or replaced with a path, quoted.
- skill_fix: a change to the skill that would have prevented the worst problem, or null
  if the handoff is the skill working as intended.

Return ONLY a JSON object, no prose around it:
{"scores": {"actionable": n, "durable_only": n, "findings": n, "density": n, "safety": n},
 "dropped": ["..."], "wasted": ["..."], "skill_fix": "..." or null,
 "verdict": "one sentence"}
"""


def newest(paths):
    paths = [p for p in paths if p.is_file()]
    return max(paths, key=lambda p: p.stat().st_mtime) if paths else None


def find_handoff(cwd):
    """The handoff for this directory, parked or already picked up."""
    live = hook.handoff_path(cwd)
    if live.is_file():
        return live
    # Usually it has already been consumed: park, next session picks it up, then grade.
    # glob on a directory that does not exist returns nothing, so this needs no guard.
    return newest(live.parent.glob(f"*{hook.PICKED_SUFFIX}"))


def find_session(cwd):
    """Claude Code's transcript for this directory. It flattens the path into one name."""
    slug = str(pathlib.Path(cwd).resolve()).replace("/", "-")
    d = pathlib.Path.home() / ".claude" / "projects" / slug
    return newest(d.glob("*.jsonl")) if d.is_dir() else None


def digest(transcript):
    """Session text plus tool names, without tool results. Returns (text, stats)."""
    out, skipped = [], 0
    for line in transcript.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        if not isinstance(rec, dict):  # a bare string is valid JSON and not a record
            continue
        role = rec.get("type")
        if role not in ("user", "assistant"):
            continue
        content = rec.get("message", {}).get("content")
        blocks = content if isinstance(content, list) else \
            [{"type": "text", "text": content}] if isinstance(content, str) else []
        for b in blocks:
            if not isinstance(b, dict):
                continue
            if b.get("type") == "text":
                text = (b.get("text") or "").strip()
                # A system reminder is injected context, not something the session learned.
                if text and "<system-reminder>" not in text:
                    out.append(f"[{role}] {text}")
            elif b.get("type") == "tool_use":
                arg = json.dumps(b.get("input", {}), default=str)[:TOOL_ARG_CHARS]
                out.append(f"[tool] {b.get('name')} {arg}")
            elif b.get("type") == "tool_result":
                skipped += 1
    raw = transcript.stat().st_size
    text = "\n\n".join(out)
    # Bytes both sides. st_size is bytes, so len(str) would make pct_of_raw a ratio of
    # characters to bytes, and these numbers get quoted.
    size = len(text.encode("utf-8"))
    return text, {"raw_bytes": raw, "digest_bytes": size,
                  "pct_of_raw": round(size / raw * 100, 1) if raw else 0,
                  "tool_results_dropped": skipped}


def provider_env(settings=None):
    """The `env` block from user settings, which JUDGE_ARGS would otherwise drop along with
    everything else. On a Bedrock or Vertex setup that block is where the provider config
    lives, and without it the judge exits 401. It carries no grading criteria."""
    settings = settings or pathlib.Path.home() / ".claude" / "settings.json"
    if not settings.is_file():
        return {}
    try:
        block = json.loads(settings.read_text(encoding="utf-8")).get("env")
    except ValueError:
        return {}  # a settings file we cannot parse is not worth failing a grade over
    return {k: str(v) for k, v in block.items()} if isinstance(block, dict) else {}


def grade(handoff, transcript, model=None):
    session, stats = digest(transcript)
    # Read and measure before spawning the judge. The judge is a session, and a session
    # starting in this directory fires the pickup hook, which consumes the handoff.
    written = handoff.read_text(encoding="utf-8")
    stats["handoff_bytes"] = len(written.encode("utf-8"))
    stats["handoff_lines"] = written.count("\n") + 1
    prompt = "\n".join([
        RUBRIC,
        "=== THE SKILL THE WRITER FOLLOWED ===",
        SKILL.read_text(encoding="utf-8"),
        "=== THE SESSION (text and tool calls, no tool output) ===",
        session,
        "=== THE HANDOFF IT WROTE ===",
        written,
    ])
    run = subprocess.run(
        JUDGE_ARGS + (["--model", model] if model else []),
        input=prompt, capture_output=True, text=True,
        env={**os.environ, **provider_env()},
    )
    if run.returncode != 0:
        raise SystemExit(f"claude -p failed: {run.stderr.strip()[:400]}")
    envelope = json.loads(run.stdout)
    body = envelope.get("result", "")
    start, end = body.find("{"), body.rfind("}")
    if start < 0 or end < 0:
        raise SystemExit(f"judge returned no JSON:\n{body[:400]}")
    result = json.loads(body[start:end + 1])
    result["meta"] = {
        "handoff": str(handoff), "transcript": transcript.name,
        "cost_usd": envelope.get("total_cost_usd"), **stats,
    }
    return result


def report(r):
    m, s = r["meta"], r["scores"]
    total = sum(s.values())
    print(f"handoff  {m['handoff_lines']} lines, {m['handoff_bytes']} bytes")
    print(f"session  {m['raw_bytes']:,} bytes raw, judged on {m['digest_bytes']:,} "
          f"({m['pct_of_raw']}%), {m['tool_results_dropped']} tool results dropped")
    print(f"cost     ${m['cost_usd']:.3f}" if m.get("cost_usd") else "")
    print(f"\nscore    {total}/25")
    for k, v in s.items():
        print(f"  {k:<13} {v}  {'#' * v}")
    for label, key in (("DROPPED (was in session, not in handoff)", "dropped"),
                       ("WASTED (cut or replace with a path)", "wasted")):
        items = r.get(key) or []
        print(f"\n{label}: {len(items)}")
        for i in items:
            print(f"  - {i}")
    if r.get("skill_fix"):
        print(f"\nSKILL FIX  {r['skill_fix']}")
    print(f"\n{r.get('verdict', '')}")


def selftest():
    with tempfile.TemporaryDirectory() as tmp:
        t = pathlib.Path(tmp) / "s.jsonl"
        t.write_text("\n".join(json.dumps(r) for r in [
            {"type": "user", "message": {"content": "fix the flaky test"}},
            {"type": "assistant", "message": {"content": [
                {"type": "text", "text": "looking"},
                {"type": "tool_use", "name": "Bash", "input": {"command": "yarn test"}}]}},
            {"type": "user", "message": {"content": [
                {"type": "tool_result", "content": "x" * 50000}]}},
            {"type": "user", "message": {"content": "<system-reminder>ignore me</system-reminder>"}},
            {"type": "summary", "summary": "not a message"},
            "not json at all",
        ]), encoding="utf-8")
        text, stats = digest(t)
        assert "fix the flaky test" in text and "yarn test" in text, text
        assert "x" * 100 not in text, "tool results must not reach the judge"
        assert "ignore me" not in text, "system reminders are injected, not learned"
        assert stats["tool_results_dropped"] == 1, stats
        assert stats["digest_bytes"] < stats["raw_bytes"] / 10, stats

        # raw_bytes is st_size, so digest_bytes has to be bytes too or pct_of_raw is a
        # ratio of characters to bytes. Only a non-ASCII line can catch that.
        t.write_text(json.dumps(
            {"type": "user", "message": {"content": "jalapeño 3µs"}}), encoding="utf-8")
        text, stats = digest(t)
        assert stats["digest_bytes"] == len(text.encode("utf-8")) > len(text), stats

        # The judge must load no settings, or it grades against the grader's CLAUDE.md too.
        assert JUDGE_ARGS[JUDGE_ARGS.index("--setting-sources") + 1] == "", JUDGE_ARGS

        # ...but the provider config in that settings file is what keeps it authenticated.
        s = pathlib.Path(tmp) / "settings.json"
        assert provider_env(s) == {}, "no settings file, nothing to pass through"
        s.write_text('{"env": {"CLAUDE_CODE_USE_BEDROCK": 1}, "model": "opus"}')
        assert provider_env(s) == {"CLAUDE_CODE_USE_BEDROCK": "1"}, provider_env(s)
        s.write_text("{ not json")
        assert provider_env(s) == {}, "a broken settings file must not fail the grade"
    print("selftest ok")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--handoff"), ap.add_argument("--session"), ap.add_argument("--model")
    ap.add_argument("--log", help="where to append the score, to keep one series in one file")
    ap.add_argument("--digest", action="store_true", help="print the judge's input only")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
        raise SystemExit(0)

    cwd = os.getcwd()
    handoff = pathlib.Path(a.handoff) if a.handoff else find_handoff(cwd)
    session = pathlib.Path(a.session) if a.session else find_session(cwd)
    if not handoff or not handoff.is_file():
        raise SystemExit("no handoff found. run /park first, or pass --handoff")
    if not session or not session.is_file():
        raise SystemExit("no transcript found for this directory. pass --session")

    if a.digest:
        text, stats = digest(session)
        print(json.dumps(stats, indent=2), file=sys.stderr)
        print(text)
        raise SystemExit(0)

    result = grade(handoff, session, a.model)
    report(result)
    # Keyed on this directory, not on where --handoff points. A grade is only worth having
    # next to the ones before it, and deriving the log from the input splits the series
    # across every temp dir a handoff was ever graded from.
    log = pathlib.Path(a.log) if a.log else \
        hook.prepare(hook.handoff_path(cwd)).parent / "grades.jsonl"
    with log.open("a", encoding="utf-8") as f:
        f.write(json.dumps(result) + "\n")
    print(f"\nappended to {log}")
