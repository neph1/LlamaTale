import json
import re

from tale import parse_utils

def find_balanced_json(text):
    stack = []
    in_string = False
    escape = False
    start_idx = None
    
    for i, char in enumerate(text):
        if char == '"' and not escape:
            in_string = not in_string
        elif char == '\\' and in_string:
            escape = not escape
        else:
            escape = False
        
        if not in_string:
            if char in '{[':
                if not stack:
                    start_idx = i
                stack.append(char)
            elif char in ']}':
                if stack:
                    stack.pop()
                    if not stack and start_idx is not None:
                        return text[start_idx:i+1]
    
    return None

def fix_invalid_escapes(s):
    # Handle invalid escape sequences (e.g., \', \x, etc.)
    pattern = r'(?:\\\\)(.)|(?:\\\\u)([0-9A-Fa-f]{4})'
    def replace(match):
        if match.group(2):  # Unicode escape
            try:
                chr(int(match.group(2), 16))
                return '\\' + match.group(1) + match.group(2)
            except:
                return match.group(2)
        else:
            esc_char = match.group(1)
            valid_escapes = ['"', '\\', 'n', 'r', 't', 'b', 'f']
            if esc_char in valid_escapes:
                return '\\' + esc_char
            else:
                return esc_char  # Return literal character for invalid escapes
    return re.sub(pattern, replace, s)

def robust_sanitize(json_str):
    # Remove markdown code blocks
    json_str = re.sub(r'^```[^\n]*\n|```\n$', '', json_str, flags=re.MULTILINE)
    
    # Extract first balanced JSON structure
    balanced = find_balanced_json(json_str)
    if not balanced:
        return None
    
    # Fix invalid escape sequences
    balanced = fix_invalid_escapes(balanced)
    
    # Additional fixes for common issues
    fixes = [
        # (r"'", '"'),                  # Convert single to double quotes
        (r'True|False|null',           # Normalize boolean/null values
         lambda m: m.group().lower()),
        (r',\s*([}\]])', r'\1'),      # Remove trailing commas
        (r'[\u201C\u201D]', '"'),      # Convert smart double quotes
        (r'[\u2018\u2019]', "'"),     # Convert smart single quotes
        (r'"{', '{'),                 # Fix misplaced quotes around braces
        (r'}"', '}'),
        (r'""', '"'),                 # Fix consecutive quotes
    ]
    
    for pattern, repl in fixes:
        balanced = re.sub(pattern, repl, balanced)
    
    return balanced

def safe_load(json_str):
    sanitized = parse_utils.sanitize_json(json_str)
    if not sanitized:
        return None
    
    try:
        return json.loads(sanitized)
    except json.JSONDecodeError as e:
        print(f"JSONDecodeError: {e} - Attempting partial recovery")
        # Attempt partial recovery
        for i in range(len(sanitized)-1, 0, -1):
            try:
                return json.loads(sanitized[:i])
            except:
                continue
        return None
    
