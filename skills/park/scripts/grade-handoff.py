#!/usr/bin/env python3
"""Score a written handoff against the session that produced it.

A handoff can only be wrong in ways a test cannot see: a next step nobody can act on,
a finding that was already in a commit, a fact that was in the session and got dropped.
So the check is a second model reading both the session and the handoff, with the same
SKILL.md the writer had. It runs locally through `claude -p`.

    grade-handoff.py                       # newest transcript and this branch's handoff
    grade-handoff.py --handoff F --session T
    grade-handoff.py --digest              # print reduced session evidence, spend nothing

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

import grading_evidence as evidence
import handoff_lifecycle as lifecycle

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
- density: is every line carrying weight? Deduct for transcript-style narration,
  restating the obvious, generated or disposable artifacts listed only because they are
  untracked, negative inventory such as "no process" or "no commit", quoted diff content,
  final green-test status, empty-section filler, and length beyond what the content needs.
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
    return lifecycle.find_for_grade(cwd)


def find_session(cwd):
    """Claude Code's transcript for this directory. It flattens the path into one name."""
    slug = str(pathlib.Path(cwd).resolve()).replace("/", "-")
    d = pathlib.Path.home() / ".claude" / "projects" / slug
    return newest(d.glob("*.jsonl")) if d.is_dir() else None


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


def grade(handoff, transcript, model=None, runner=subprocess.run, skill=SKILL):
    judge_input = evidence.build_judge_input(transcript, handoff, skill, RUBRIC)
    run = runner(
        JUDGE_ARGS + (["--model", model] if model else []),
        input=judge_input.prompt, capture_output=True, text=True,
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
        "cost_usd": envelope.get("total_cost_usd"), **judge_input.stats,
    }
    return result


def report(r):
    m, s = r["meta"], r["scores"]
    total = sum(s.values())
    print(f"handoff  {m['handoff_lines']} lines, {m['handoff_bytes']} bytes")
    print(f"session  {m['raw_bytes']:,} bytes raw, judged on {m['digest_bytes']:,} "
          f"({m['pct_of_raw']}%), {m['tool_results_seen']} tool results, "
          f"{m['tool_results_truncated']} truncated")
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
        handoff = pathlib.Path(tmp) / "handoff.md"
        skill = pathlib.Path(tmp) / "SKILL.md"
        handoff.write_text("next: rerun the benchmark")
        skill.write_text("keep expensive findings")
        t.write_text("\n".join(json.dumps(r) for r in [
            {"type": "user", "message": {"content": "fix the flaky test"}},
            {"type": "assistant", "message": {"content": [
                {"type": "text", "text": "looking"},
                {"type": "tool_use", "name": "Bash", "input": {"command": "yarn test"}}]}},
            {"type": "user", "message": {"content": [
                {"type": "tool_result", "content":
                 "command output\n" + "x" * 50000 + "\nbenchmark median 41 ms"}]}},
            {"type": "user", "message": {"content": "<system-reminder>ignore me</system-reminder>"}},
            {"type": "summary", "summary": "not a message"},
            "not json at all",
        ]), encoding="utf-8")
        judge_input = evidence.build_judge_input(t, handoff, skill, RUBRIC)
        text, stats = judge_input.session, judge_input.stats
        assert "fix the flaky test" in text and "yarn test" in text, text
        assert "benchmark median 41 ms" in text, "expensive command findings reach the judge"
        assert "ignore me" not in text, "system reminders are injected, not learned"
        assert stats["tool_results_truncated"] == 1, stats
        assert len(text) < 2000, "large tool results stay bounded"
        assert stats["digest_bytes"] < stats["raw_bytes"] / 10, stats

        assert "bounded tool results" in judge_input.prompt and \
            "benchmark median 41 ms" in judge_input.prompt, \
            "complete judge input owns both the evidence and its label"

        captured = {}

        def fake_runner(args, **kwargs):
            captured.update(args=args, **kwargs)
            body = {"scores": {"actionable": 5, "durable_only": 5, "findings": 5,
                               "density": 5, "safety": 5},
                    "dropped": [], "wasted": [], "skill_fix": None, "verdict": "ok"}
            return subprocess.CompletedProcess(args, 0, json.dumps({"result": json.dumps(body)}), "")

        graded = grade(handoff, t, runner=fake_runner, skill=skill)
        assert captured["input"] == judge_input.prompt and graded["meta"]["handoff_bytes"] > 0, \
            "the Claude adapter receives the complete judge input"

        # raw_bytes is st_size, so digest_bytes has to be bytes too or pct_of_raw is a
        # ratio of characters to bytes. Only a non-ASCII line can catch that.
        t.write_text(json.dumps(
            {"type": "user", "message": {"content": "jalapeño 3µs"}}), encoding="utf-8")
        non_ascii = evidence.build_judge_input(t, handoff, skill, RUBRIC)
        text, stats = non_ascii.session, non_ascii.stats
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

        repo = pathlib.Path(tmp) / "repo"
        (repo / ".git").mkdir(parents=True)
        (repo / ".git" / "HEAD").write_text("ref: refs/heads/main\n")
        live, _ = lifecycle.prepare_for_write(repo)
        current = live.with_suffix(lifecycle.PICKED_SUFFIX)
        other = live.parent / f"feature{lifecycle.PICKED_SUFFIX}"
        current.write_text("main")
        other.write_text("feature")
        os.utime(current, (1, 1))
        os.utime(other, (2, 2))
        assert lifecycle.find_for_grade(repo) == current, \
            "the lifecycle interface finds only this branch's Handoff"
        assert find_handoff(repo) == current, "automatic grading stays on the current branch"
    print("selftest ok")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--handoff"), ap.add_argument("--session"), ap.add_argument("--model")
    ap.add_argument("--log", help="where to append the score, to keep one series in one file")
    ap.add_argument("--digest", action="store_true", help="print reduced session evidence only")
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
        judge_input = evidence.build_judge_input(session, handoff, SKILL, RUBRIC)
        text = judge_input.session
        stats = {key: judge_input.stats[key] for key in (
            "raw_bytes", "digest_bytes", "pct_of_raw",
            "tool_results_seen", "tool_results_truncated")}
        print(json.dumps(stats, indent=2), file=sys.stderr)
        print(text)
        raise SystemExit(0)

    result = grade(handoff, session, a.model)
    report(result)
    # Keyed on this directory, not on where --handoff points. A grade is only worth having
    # next to the ones before it, and deriving the log from the input splits the series
    # across every temp dir a handoff was ever graded from.
    log = pathlib.Path(a.log) if a.log else \
        lifecycle.prepare_for_write(cwd)[0].parent / "grades.jsonl"
    with log.open("a", encoding="utf-8") as f:
        f.write(json.dumps(result) + "\n")
    print(f"\nappended to {log}")
