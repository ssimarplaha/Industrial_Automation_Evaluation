from __future__ import annotations

import re


def int_tokens(line: str) -> list[int]:
    """Extract integer-like values, ignoring percentages, decimals, and label footnotes."""
    tokens: list[int] = []
    pattern = re.compile(r"(?<![\w.(])(\(-?\d[\d,]*\)|-?\d[\d,]*|[—-])(?![\w.%-])")
    for match in pattern.finditer(line):
        token = match.group(1)
        if token in {"—", "-"}:
            tokens.append(0)
            continue
        negative = token.startswith("(") and token.endswith(")")
        cleaned = token.strip("()").replace(",", "")
        if cleaned.startswith("-"):
            negative = True
            cleaned = cleaned[1:]
        value = int(cleaned)
        tokens.append(-value if negative else value)
    return tokens


def clean_label(line: str) -> str:
    label = re.split(r"\.{2,}|\s{2,}(?=\(?-?\d|—|-)", line.strip(), maxsplit=1)[0]
    return re.sub(r"\s+", " ", label).strip()
