"""Route Siemens fiscal years to the segment parser for that reporting era."""

from __future__ import annotations

from .base import SegmentParser
from .division_2016 import Division2016Parser
from .division_2018 import Division2018Parser
from .legacy_sector import LegacySectorParser
from .modern_2020 import ModernSegmentParser


def segment_parser_for(fiscal_year: int) -> SegmentParser:
    """Return the configured segment parser for a supported fiscal year."""
    if 2010 <= fiscal_year <= 2014:
        return LegacySectorParser()
    if fiscal_year == 2016:
        return Division2016Parser()
    if fiscal_year == 2018:
        return Division2018Parser()
    if 2020 <= fiscal_year <= 2026:
        return ModernSegmentParser()
    raise ValueError(f"No segment parser configured for FY {fiscal_year}")


__all__ = [
    "Division2016Parser",
    "Division2018Parser",
    "LegacySectorParser",
    "ModernSegmentParser",
    "SegmentParser",
    "segment_parser_for",
]
