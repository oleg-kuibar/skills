---
name: park
description: Write the live state of this conversation somewhere it survives, so the session can be cleared. Hands to the next session in this directory, or to a background agent that continues now.
argument-hint: "(optional) focus for the next session, or 'bg' to hand to a background agent"
disable-model-invocation: true
---

Park the work: get what dies with the context window out of it, then the session is
safe to clear.

What to write is the same either way. Where it goes has two branches, and they are
exclusive. Pick one.

## Setup

One command, once per machine:

```
/usr/bin/python3 ~/.claude/skills/park/scripts/handoff-pickup.py --install
```

Claude Code only. The hook it registers is what reads the handoff back.

It symlinks the script to `~/.claude/hooks/handoff-pickup.py` and registers a
`SessionStart` hook in `~/.claude/settings.json`, keeping every other setting and hook.
Re-running it is safe. Restart Claude Code once after installing.

Without the hook, nothing reads what /park writes, so the file branch below is a dead
end. Check with `ls ~/.claude/hooks/handoff-pickup.py`.

## What goes in

Only what dies with the context window. A fact recorded in a commit, a diff, a
ticket, a plan file, or `CLAUDE.md` survives on its own, so reference it by path or
URL rather than restating it.

That leaves four things, and the fourth is worth the most:

- **Task.** What is being done, and how far it got.
- **Next step.** The single concrete action to take, specific enough to start on.
- **Live paths.** Files mid-edit, the branch, a worktree that is not the obvious
  one, a running background job. Paths and line ranges, not their contents.
- **Findings that cost something to learn.** A wrong turn already ruled out, a
  measured number, a decision the user made and the reason, an approach that failed
  and why. This is the part with no other home. Losing it means paying for it twice.

Redact secrets: keys, tokens, passwords, personal data.

If the user named a focus, write toward that and cut the rest.

Under ~15 lines is normal. A parked task points at work rather than recording it.
The failure is a file that reads like a transcript, because whoever picks it up pays
for every line.

## Where it goes

### To the next session here (default)

Ask for the path, do not derive it:

```
/usr/bin/python3 ~/.claude/hooks/handoff-pickup.py --path
```

It prints the file to write and creates the directory. Overwrite that file.

The path is `<repo-root>/.claude/handoff/<branch>.md`, falling back to the current
directory when there is no repo, and it is gitignored. Living beside the work means a
checkout on another machine or by another user finds the same handoff. Keying on the
branch means a worktree or a branch switch gets its own. The reading hook resolves it
the same way, which is why asking beats recomputing: one rule in one place.

If that command is missing, the pickup hook is not installed, so nothing will read what
you write. Say so, point at Setup above, then write
`<repo-root>/.claude/handoff/<branch>.md` by hand with slashes in the branch name turned
to dashes.

A `SessionStart` hook injects that file the next time a session starts on this branch,
then consumes it. Nothing else to run.

Open with a line saying this is parked context to read, not a task to start on. The
next session picks it up mid-turn and should wait for the user.

### To a background agent (`bg`)

Launch it seeded with the same content as its prompt:

```
claude --bg --name "<short task name>" "<parked content>"
```

It starts in the current directory and returns immediately. The user manages it with
`claude agents`.

Two differences from the file branch. The content becomes a live prompt, so the agent
acts on it straight away: write the next step as an instruction, not as a note.
Redaction is load-bearing here, because the prompt is the agent's own context.

Write no file on this branch. A file plus an agent means both fire, and the agent
picks up its own handoff on top of its prompt.

## Done when

Every one of the four kinds above is either written down or checked and found not to
apply, and someone with no memory of this conversation could take the next step from
what you wrote alone.

Then one line: the file path and that `/clear` is safe now, or the agent name and
that it is already running.
