"""Reconstruct 2018 old-bucket segments from transition division rows."""

from __future__ import annotations

from ..config import DIVISION_TO_BUCKET_2018
from ..models import PdfDocument, QuarterData
from .base import SegmentParser, assign_bucket_totals, first_revenue_after_heading


class Division2018Parser(SegmentParser):
    """Parser for FY2018 transition layout with Healthineers naming variants."""

    parser_family = "division_2018"

    def extract(self, document: PdfDocument, quarters: dict[str, QuarterData]) -> None:
        """Map required 2018 divisions into fixed historical segment buckets."""
        bucket_values, bucket_sources, found = first_revenue_after_heading(
            document,
            DIVISION_TO_BUCKET_2018,
            self.parser_family,
            "2018 reconstructed bucket from transition division revenue.",
            page_numbers={3, 4, 5},
        )

        missing_healthcare = set() if {"Healthineers", "Siemens Healthineers"} & found else {"Healthineers"}
        required = set(DIVISION_TO_BUCKET_2018) - {"Healthineers", "Siemens Healthineers"}
        missing = sorted(required - found) + sorted(missing_healthcare)
        if missing:
            raise ValueError(f"{document.path.name}: missing 2018 division revenue rows: {missing}")

        assign_bucket_totals(
            document,
            quarters,
            bucket_values,
            bucket_sources,
            self.parser_family,
            ["Industry", "Energy", "Healthcare"],
            "2018 reconstructed old-bucket mapping; not a native reported sector.",
        )
