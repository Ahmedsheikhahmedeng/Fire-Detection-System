from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


def strip_json_line_comments(text: str) -> str:
    """Remove // comments while preserving // inside JSON strings."""
    result: list[str] = []
    in_string = False
    escaped = False
    index = 0

    while index < len(text):
        char = text[index]
        next_char = text[index + 1] if index + 1 < len(text) else ""

        if in_string:
            result.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            index += 1
            continue

        if char == '"':
            in_string = True
            result.append(char)
            index += 1
            continue

        if char == "/" and next_char == "/":
            index += 2
            while index < len(text) and text[index] not in "\r\n":
                index += 1
            continue

        result.append(char)
        index += 1

    return "".join(result)


def load_json_file(path: Path) -> Any:
    text = path.read_text(encoding="utf-8")
    stripped = strip_json_line_comments(text)
    stripped = re.sub(r",\s*([}\]])", r"\1", stripped)
    return json.loads(stripped)


def normalized_json_sha256_payload(path: Path) -> bytes:
    data = load_json_file(path)
    normalized = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return normalized.encode("utf-8")
