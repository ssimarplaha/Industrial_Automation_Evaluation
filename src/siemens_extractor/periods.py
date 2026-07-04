from __future__ import annotations

import re


def quarter_code(quarter: int, fiscal_year: int) -> str:
    return f"Q{quarter}{fiscal_year % 100:02d}"


def quarter_sort_key(code: str) -> tuple[int, int]:
    match = re.fullmatch(r"Q([1-4])(\d{2})", code)
    if not match:
        raise ValueError(f"Invalid quarter code: {code}")
    quarter = int(match.group(1))
    year = 2000 + int(match.group(2))
    return year, quarter
