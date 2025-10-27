import json
import re
from typing import Any, Optional

def strip_markdown_fences(s: str) -> str:
    """Remove ```json fences or plain ``` fences."""
    return re.sub(r'^```(?:json)?|```$', '', s.strip(), flags=re.MULTILINE).strip()

def extract_json_block(s: str) -> str:
    """Extract the first {...} or [...] block if there is extra text around it."""
    match = re.search(r"(\{.*\}|\[.*\])", s, flags=re.DOTALL)
    return match.group(1) if match else s

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
    s = strip_markdown_fences(s)
    s = extract_json_block(s)
    s = unwrap_double_encoded(s)
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
