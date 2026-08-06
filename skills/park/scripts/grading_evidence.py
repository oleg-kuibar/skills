"""Build the complete evidence prompt used to Grade a parked Handoff."""

from dataclasses import dataclass
import json


TOOL_ARG_CHARS = 120
TOOL_RESULT_CHARS = 800


@dataclass(frozen=True)
class JudgeInput:
    prompt: str
    session: str
    stats: dict


def _digest_session(transcript):
    out, results, truncated = [], 0, 0
    for line in transcript.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            record = json.loads(line)
        except ValueError:
            continue
        if not isinstance(record, dict):
            continue
        role = record.get("type")
        if role not in ("user", "assistant"):
            continue
        content = record.get("message", {}).get("content")
        blocks = content if isinstance(content, list) else \
            [{"type": "text", "text": content}] if isinstance(content, str) else []
        for block in blocks:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "text":
                text = (block.get("text") or "").strip()
                if text and "<system-reminder>" not in text:
                    out.append(f"[{role}] {text}")
            elif block.get("type") == "tool_use":
                args = json.dumps(block.get("input", {}), default=str)[:TOOL_ARG_CHARS]
                out.append(f"[tool] {block.get('name')} {args}")
            elif block.get("type") == "tool_result":
                results += 1
                value = block.get("content", "")
                value = value if isinstance(value, str) else json.dumps(value, default=str)
                if len(value) > TOOL_RESULT_CHARS:
                    half = TOOL_RESULT_CHARS // 2
                    value = f"{value[:half]}\n...[truncated]...\n{value[-half:]}"
                    truncated += 1
                if value.strip():
                    out.append(f"[tool result] {value.strip()}")
    raw = transcript.stat().st_size
    text = "\n\n".join(out)
    size = len(text.encode("utf-8"))
    return text, {
        "raw_bytes": raw,
        "digest_bytes": size,
        "pct_of_raw": round(size / raw * 100, 1) if raw else 0,
        "tool_results_seen": results,
        "tool_results_truncated": truncated,
    }


def build_judge_input(transcript, handoff, skill, rubric):
    """Return the complete judge prompt, session digest, and evidence statistics."""
    session, stats = _digest_session(transcript)
    written = handoff.read_text(encoding="utf-8")
    stats = {
        **stats,
        "handoff_bytes": len(written.encode("utf-8")),
        "handoff_lines": written.count("\n") + 1,
    }
    prompt = "\n".join([
        rubric,
        "=== THE SKILL THE WRITER FOLLOWED ===",
        skill.read_text(encoding="utf-8"),
        "=== THE SESSION (text, tool calls, and bounded tool results) ===",
        session,
        "=== THE HANDOFF IT WROTE ===",
        written,
    ])
    return JudgeInput(prompt, session, stats)
