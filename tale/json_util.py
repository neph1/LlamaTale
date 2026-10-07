import json
import re
from typing import Any, Optional


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
    """Skip over a quoted string, preserving escaped quotes."""
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
    """Find the end of a fenced reasoning block such as ```thinking ... ```."""
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
    """Find the end of a tagged reasoning block such as <think>...</think>."""
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

def strip_markdown_fences(s: str) -> str:
    """Remove ```json fences or plain ``` fences."""
    return re.sub(r'^```(?:json)?|```$', '', s.strip(), flags=re.MULTILINE).strip()

def extract_json_block(s: str) -> str:
    """Extract the first balanced JSON object or array from a larger string."""
    start = None
    stack = []
    in_string = False
    escaped = False

    for i, ch in enumerate(s):
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue

        if ch == '"':
            in_string = True
            continue

        if start is None:
            if ch == "{":
                start = i
                stack.append("}")
            elif ch == "[":
                start = i
                stack.append("]")
            continue

        if ch in "[{":
            stack.append("}" if ch == "{" else "]")
        elif ch in "}]":
            if not stack or ch != stack[-1]:
                return s
            stack.pop()
            if not stack and start is not None:
                return s[start:i + 1]

    return s

def unwrap_double_encoded(s: str) -> str:
    """Unwrap when JSON is a quoted string containing JSON."""
    try:
        parsed = json.loads(s)
        if isinstance(parsed, str):
            return parsed
    except Exception:
        pass
    return s

def fix_trailing_commas(s: str) -> str:
    """Remove trailing commas before ] or }."""
    return re.sub(r',\s*([}\]])', r'\1', s)

def normalize_literals(s: str) -> str:
    """Normalize Python-style literals to JSON literals."""
    return (s.replace("None", "null")
             .replace("True", "true")
             .replace("False", "false"))

def sanitize_json(s: str) -> str:
    """Apply a pipeline of cleanup steps before parsing."""
    if not s:
        return ""
    s = strip_reasoning_sections(s)
    s = strip_markdown_fences(s)
    s = unwrap_double_encoded(s)
    s = strip_reasoning_sections(s)
    s = extract_json_block(s)
    s = fix_trailing_commas(s)
    s = normalize_literals(s)
    return s.strip()

def safe_load(s: str) -> Optional[Any]:
    """
    Try to parse JSON string from LLM output with progressive cleanup.
    Returns Python object or raises last error if unrecoverable.
    """
    cleaned = sanitize_json(s)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Try double-unwrapping in case of double-encoded JSON
        try:
            return json.loads(json.loads(cleaned))
        except Exception:
            raise
