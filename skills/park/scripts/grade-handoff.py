#!/usr/bin/env python3
"""Score a written handoff against the session that produced it.

A handoff can only be wrong in ways a test cannot see: a next step nobody can act on,
a finding that was already in a commit, a fact that was in the session and got dropped.
So the check is a second model reading both the session and the handoff, with the same
SKILL.md the writer had. It runs locally through `claude -p`.

    grade-handoff.py                       # newest transcript here, newest handoff here
    grade-handoff.py --handoff F --session T
    grade-handoff.py --digest              # print what the judge would see, spend nothing

Scores append to <handoff dir>/grades.jsonl, which the handoff .gitignore already covers.
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
    return live if live.is_file() else newest(live.parent.glob(f"*{hook.PICKED_SUFFIX}")) \
        if live.parent.is_dir() else None


def find_session(cwd):
    """Claude Code's transcript for this directory. It flattens the path into one name."""
    slug = str(pathlib.Path(cwd).resolve()).replace("/", "-")
    d = pathlib.Path.home() / ".claude" / "projects" / slug
    return newest(d.glob("*.jsonl")) if d.is_dir() else None


def digest(transcript):
    """Session text plus tool names, without tool results. Returns (text, stats)."""
    out, kept, skipped = [], 0, 0
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
                    kept += len(text)
            elif b.get("type") == "tool_use":
                arg = json.dumps(b.get("input", {}), default=str)[:TOOL_ARG_CHARS]
                out.append(f"[tool] {b.get('name')} {arg}")
                kept += len(arg)
            elif b.get("type") == "tool_result":
                skipped += 1
    raw = transcript.stat().st_size
    text = "\n\n".join(out)
    return text, {"raw_bytes": raw, "digest_bytes": len(text),
                  "pct_of_raw": round(len(text) / raw * 100, 1) if raw else 0,
                  "tool_results_dropped": skipped}


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
    # No tools: the judge grades what it was given. Reading the repo would let it credit
    # the handoff for facts that were never in it.
    # cwd outside the repo, so the pickup hook resolves somewhere else and this run does
    # not eat the handoff under grade. Belt and braces with the hook's own bg-agent guard.
    env = {**os.environ, "CLAUDE_JOB_DIR": tempfile.gettempdir()}
    run = subprocess.run(
        ["claude", "-p", "--output-format", "json", "--disallowedTools", "*"]
        + (["--model", model] if model else []),
        input=prompt, capture_output=True, text=True,
        cwd=tempfile.gettempdir(), env=env,
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
    print("selftest ok")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--handoff"), ap.add_argument("--session"), ap.add_argument("--model")
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
    log = handoff.parent / "grades.jsonl"
    with log.open("a", encoding="utf-8") as f:
        f.write(json.dumps(result) + "\n")
    print(f"\nappended to {log}")
