import re
from typing import Optional

REASONING_TAG_NAMES = (
    "think",
    "thinking",
    "thought",
    "thoughts",
    "reasoning",
    "analysis",
    "scratchpad",
    "reflection",
    "inner_monologue",
    "chain_of_thought",
    "cot",
)


def _skip_quoted_segment(s: str, start: int) -> int:
    quote = s[start]
    i = start + 1
    escaped = False

    while i < len(s):
        ch = s[i]
        if escaped:
            escaped = False
        elif ch == "\\":
            escaped = True
        elif ch == quote:
            return i + 1
        i += 1

    return len(s)


def _find_reasoning_fence_end(s: str, start: int) -> Optional[int]:
    if not s.startswith("```", start):
        return None

    line_end = s.find("\n", start)
    if line_end == -1:
        line_end = len(s)

    fence_name = s[start + 3:line_end].strip().lower().replace("-", "_")
    if fence_name not in REASONING_TAG_NAMES:
        return None

    closing = s.find("```", line_end)
    return len(s) if closing == -1 else closing + 3


def _find_reasoning_tag_end(s: str, start: int) -> Optional[int]:
    remainder = s[start:]

    for tag in REASONING_TAG_NAMES:
        xml_open = re.match(rf"<\s*{re.escape(tag)}(?:\s+[^>]*)?>", remainder, flags=re.IGNORECASE)
        if xml_open:
            closing = re.search(rf"</\s*{re.escape(tag)}\s*>", remainder[xml_open.end():], flags=re.IGNORECASE)
            return len(s) if closing is None else start + xml_open.end() + closing.end()

        bracket_open = re.match(rf"\[\s*{re.escape(tag)}\s*\]", remainder, flags=re.IGNORECASE)
        if bracket_open:
            closing = re.search(rf"\[/\s*{re.escape(tag)}\s*\]", remainder[bracket_open.end():], flags=re.IGNORECASE)
            return len(s) if closing is None else start + bracket_open.end() + closing.end()

    return None


def strip_reasoning_sections(s: str) -> str:
    """Remove common reasoning sections emitted by LLMs while preserving JSON string values."""
    if not s:
        return ""

    cleaned = []
    i = 0
    while i < len(s):
        if s[i] in ('"', "'"):
            quoted_end = _skip_quoted_segment(s, i)
            cleaned.append(s[i:quoted_end])
            i = quoted_end
            continue

        reasoning_fence_end = _find_reasoning_fence_end(s, i)
        if reasoning_fence_end is not None:
            i = reasoning_fence_end
            continue

        reasoning_tag_end = _find_reasoning_tag_end(s, i)
        if reasoning_tag_end is not None:
            i = reasoning_tag_end
            continue

        cleaned.append(s[i])
        i += 1

    return re.sub(r"\n{3,}", "\n\n", "".join(cleaned)).strip()
