"""Helpers for Siemens quarter code formatting and chronological sorting."""

from __future__ import annotations

import re


def quarter_code(quarter: int, fiscal_year: int) -> str:
    """Format a fiscal quarter and year as the TSV column code."""
    return f"Q{quarter}{fiscal_year % 100:02d}"


def quarter_sort_key(code: str) -> tuple[int, int]:
    """Parse a quarter code into a sortable fiscal year and quarter tuple."""
    match = re.fullmatch(r"Q([1-4])(\d{2})", code)
    if not match:
        raise ValueError(f"Invalid quarter code: {code}")
    quarter = int(match.group(1))
    year = 2000 + int(match.group(2))
    return year, quarter


def year_sort_key(code: str) -> int:
    """Parse an FY column code into a sortable fiscal year."""
    match = re.fullmatch(r"FY(\d{4})", code)
    if not match:
        raise ValueError(f"Invalid fiscal year code: {code}")
    return int(match.group(1))
