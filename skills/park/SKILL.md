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
`SessionStart` hook in `~/.claude/settings.json` for `startup`, `clear`, and `compact`,
keeping every other setting and hook. Re-running it is safe. Restart Claude Code once
after installing.

Without the hook, nothing reads what /park writes, so the file branch below is a dead
end. Check with `ls ~/.claude/hooks/handoff-pickup.py`.

## What goes in

Only what dies with the context window. **Durable** means recorded in a commit, a diff,
a ticket, a plan file, or `CLAUDE.md`: it survives on its own, so a path or URL to it is
enough. Everything else dies with the context, so its content goes in this file. Check
every path you write against that, because a path to something not durable looks like a
reference and is not one.

That leaves six things. The last three are the ones with no other home:

- **Task.** What is being done, and how far it got.
- **Next step.** One concrete action, naming a file, a command, or a decision that is
  waiting on the user. "Nothing pending" is not a next step. If the work is finished,
  write what the reader should pick up instead, however small.
  Make it runnable from a fresh shell: every file gets a path that resolves, every
  command gets its arguments. A path that is not durable (a temp directory, a job dir, a
  clipboard) cannot be run later: copy the content in, or move the file somewhere that
  survives and write that path.
- **Live paths.** Files mid-edit, the branch, a worktree that is not the obvious
  one, a running background job. Paths and line ranges, not their contents. Include
  state the machine is still in: a restart not done, a commit not pushed, a process
  left running. For an uncommitted edit, write why it was made, not that it exists.
  `git status` and `git diff` return the state and the content. The reason does not
  survive anywhere.
- **Findings that cost something to learn.** A measured number with its units, a
  decision the user made and the reason, an approach that failed and why. A benchmark
  result, a score, a byte count, a cost: anything that took a command, a build, or a
  model call to learn goes in as the value, never as a path to where it sits. Losing it
  means paying for it twice, and it is the most common way a handoff loses its best
  content.
  A number also carries what it was measured on: the command or tool, and anything about
  the input or the machine the next measurement would have to match. Two numbers compare
  only if their conditions do. Without them a saved number reads like evidence and cannot
  be repeated, which is worse than not saving it.
- **The option you rejected, and what rejected it.** Its own question, because it is
  the one a list of numbers hides. Name the alternative you considered and the evidence
  that killed it. Without this the next session re-opens a road already closed.
- **Open threads.** A question the user never answered, a concern raised and left
  unresolved, something you tried to verify and could not. Nothing in a repo records
  a question, so these die without a trace.

Redact secrets: keys, tokens, passwords, personal data.

If the user named a focus, write toward that and cut the rest.

Around 30 lines is normal, measured across handoffs written by this skill. A long session
with many findings runs longer, and 80 lines has scored well. Length is not the test. Per
line is: every line either carries a fact that dies with the context, or it goes. A parked
task points at work rather than recording it, and whoever picks it up pays for every line.

Cut anything a shell command recovers. A branch name, whether a test passes, what is
staged, what an uncommitted diff contains: the next session can ask. Narration of the
last exchange goes too.

Before you write anything, scan the whole conversation once for the last three kinds:
findings, rejected options, open threads. They are what the earlier turns hold and what
recency pulls you away from. A handoff that covers only the last few turns is the common
failure.

## Where it goes

### To the next session here (default)

Ask for the path, do not derive it:

```
/usr/bin/python3 ~/.claude/hooks/handoff-pickup.py --path
```

It creates the directory and prints the file to write as its last line. Overwrite that file.

If it also warns that a handoff is already parked there, read that file before you write.
There is one per branch, so writing destroys it. Fold anything still true into what you
write, drop what your session has already finished, then overwrite. The warning carries the
age: minutes old is almost always this same session parking twice, and overwriting is right.
Hours or days old is another session, and its state is not yours to throw away.

The path is `<repo-root>/.claude/handoff/<branch>.md`, falling back to the current
directory when there is no repo, and it is gitignored.

If that command is missing, the pickup hook is not installed, so nothing will read what
you write. Say so, point at Setup above, then write
`<repo-root>/.claude/handoff/<branch>.md` by hand with slashes in the branch name turned
to dashes.

A `SessionStart` hook injects that file into the next session on this branch and consumes
it. Nothing else to run.

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

Someone with no memory of this conversation could take the next step from what you
wrote alone.

Task, next step, and live paths are always written. A finding, a rejected option, or an
open thread may genuinely not exist, but say which you looked for.

Then one line: the file path and that `/clear` is safe now, or the agent name and
that it is already running.
