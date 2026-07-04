"""Extract native 2010-2014 legacy Siemens sector revenue rows."""

from __future__ import annotations

import re

from ..config import OLD_SECTOR_PATTERNS
from ..models import PdfDocument, QuarterData, SourceRecord
from ..numbers import clean_label, int_tokens
from ..periods import quarter_code
from .base import SegmentParser


class LegacySectorParser(SegmentParser):
    """Parser for old-style Additional Information sector tables."""

    parser_family = "legacy_sector_2010_2014"

    def extract(self, document: PdfDocument, quarters: dict[str, QuarterData]) -> None:
        """Populate native Industry, Energy, and Healthcare sector rows."""
        page_number, text = self._find_segment_page(document.pages)
        current_code = quarter_code(document.quarter, document.fiscal_year)
        prior_code = quarter_code(document.quarter, document.fiscal_year - 1)
        found: dict[str, tuple[int, int, str, list[int]]] = {}

        for raw_line in text.splitlines():
            line = re.sub(r"(?<=[A-Za-z])\(\d+\)", "", raw_line.strip())
            for row, pattern in OLD_SECTOR_PATTERNS.items():
                if pattern.search(line):
                    values = int_tokens(line)
                    if len(values) < 4:
                        raise ValueError(f"{document.path.name}: could not parse segment revenue from {line!r}")
                    found[row] = (values[2], values[3], clean_label(line), values)

        missing = [row for row in OLD_SECTOR_PATTERNS if row not in found]
        if missing:
            raise ValueError(f"{document.path.name}: missing old-style segment rows: {missing}")

        for row, (current_value, prior_value, label, raw_values) in found.items():
            for code, value in [(current_code, current_value), (prior_code, prior_value)]:
                quarters[code].values[row] = value
                quarters[code].sources[row] = SourceRecord(
                    source_pdf=document.path.name,
                    page=page_number,
                    parser_family=self.parser_family,
                    raw_line=label,
                    raw_values=raw_values,
                    normalized_row=row,
                    normalized_value=value,
                    source_type="native",
                    note="Revenue from Additional Information (I) sector table.",
                )

    def _find_segment_page(self, pages: list[str]) -> tuple[int, str]:
        """Find the Additional Information page containing all legacy sectors."""
        for index, text in enumerate(pages, start=1):
            if "ADDITIONAL INFORMATION (I)" not in text:
                continue
            if all(pattern.search(text) for pattern in OLD_SECTOR_PATTERNS.values()):
                return index, text
        raise ValueError("Could not find old-style Additional Information (I) segment revenue page")
