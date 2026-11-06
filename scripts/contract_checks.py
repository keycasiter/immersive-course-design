"""Shared, field-aware checks for course contracts (standard library only)."""

import re

PLACEHOLDER = re.compile(r"\{\{[^{}\r\n]+\}\}|\bTBD\b", re.IGNORECASE)


def placeholder_paths(value, path="$"):
    """Original quotations are evidence, not template instructions."""
    found = []
    if isinstance(value, dict):
        for key, item in value.items():
            if key not in {"original_quote", "quoted_source_text"}:
                found.extend(placeholder_paths(item, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found.extend(placeholder_paths(item, f"{path}[{index}]"))
    elif isinstance(value, str) and PLACEHOLDER.search(value):
        found.append(path)
    return found
