from __future__ import annotations

from ..config import DIVISION_TO_BUCKET_2016
from ..models import PdfDocument, QuarterData
from .base import SegmentParser, assign_bucket_totals, first_revenue_after_heading


class Division2016Parser(SegmentParser):
    parser_family = "division_2016"

    def extract(self, document: PdfDocument, quarters: dict[str, QuarterData]) -> None:
        bucket_values, bucket_sources, found = first_revenue_after_heading(
            document,
            DIVISION_TO_BUCKET_2016,
            self.parser_family,
            "2016 reconstructed bucket from division revenue.",
            page_numbers={3, 4, 5},
        )

        required = set(DIVISION_TO_BUCKET_2016)
        missing_healthcare = set() if {"Healthcare", "Healthineers"} & found else {"Healthcare/Healthineers"}
        required_non_healthcare = required - {"Healthcare", "Healthineers"}
        missing = sorted(required_non_healthcare - found) + sorted(missing_healthcare)
        if missing:
            raise ValueError(f"{document.path.name}: missing 2016 division revenue rows: {missing}")

        assign_bucket_totals(
            document,
            quarters,
            bucket_values,
            bucket_sources,
            self.parser_family,
            ["Industry", "Energy", "Healthcare"],
            "2016 reconstructed old-bucket mapping; not a native reported sector.",
        )
