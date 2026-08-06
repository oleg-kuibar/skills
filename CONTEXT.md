# Agent Skills Library

This repository keeps reusable agent instructions and the machinery that preserves,
evaluates, and vendors them.

## Language

**Skill**:
A reusable instruction package that tells an agent when and how to perform a task.
_Avoid_: Prompt, command

**Handoff**:
Live conversational knowledge preserved because it is not durable anywhere else and a
later session will need it.
_Avoid_: Transcript, summary

**Pickup**:
The one-time act of making a parked Handoff available to the next eligible session.
_Avoid_: Resume, restore

**Grade**:
An evaluation of a Handoff against its source session and the Skill that governed it.
_Avoid_: Test, score

**Source Manifest**:
The canonical declaration of vendored sources and artifacts owned by this repository.
_Avoid_: Source list, vendor config
