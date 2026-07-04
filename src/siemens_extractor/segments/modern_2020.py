"""Map modern 2020-2026 Siemens segments into the fixed TSV template."""

from __future__ import annotations

from ..config import MODERN_TO_BUCKET
from ..models import PdfDocument, QuarterData
from ..numbers import int_tokens
from ..periods import quarter_code
from .base import SegmentParser, assign_bucket_totals, first_revenue_after_heading, source_record


MODERN_ROW_ALIASES = [
    ("Siemens Financial Services (SFS)", "Siemens Financial Services (SFS)"),
    ("Financial Services (SFS)", "Siemens Financial Services (SFS)"),
    ("Siemens (continuing operations)", "Siemens (continuing operations)"),
    ("Industrial Businesses (IB)", "Industrial Business"),
    ("Industrial Business", "Industrial Business"),
    ("Siemens Healthineers", "Siemens Healthineers"),
    ("Smart Infrastructure", "Smart Infrastructure"),
    ("Digital Industries", "Digital Industries"),
    ("Mobility", "Mobility"),
]

MODERN_REQUIRED_ROWS = {
    "Digital Industries",
    "Smart Infrastructure",
    "Mobility",
    "Siemens Healthineers",
    "Industrial Business",
    "Siemens Financial Services (SFS)",
    "Reconciliation to Consolidated Financial Statements",
    "Siemens (continuing operations)",
}


class ModernSegmentParser(SegmentParser):
    """Parser for modern Siemens segment tables and native modern rows."""

    parser_family = "modern_2020_2026"

    def extract(self, document: PdfDocument, quarters: dict[str, QuarterData]) -> None:
        """Populate reconstructed old buckets plus native modern segment rows."""
        bucket_values, bucket_sources, found = first_revenue_after_heading(
            document,
            MODERN_TO_BUCKET,
            self.parser_family,
            "Modern segment revenue mapped into fixed old-bucket template.",
        )

        required = {"Digital Industries", "Smart Infrastructure", "Mobility", "Siemens Healthineers"}
        missing = sorted(required - found)
        if missing:
            raise ValueError(f"{document.path.name}: missing modern segment revenue rows: {missing}")

        rows = ["Industry", "Energy", "Healthcare"]
        assign_bucket_totals(
            document,
            quarters,
            bucket_values,
            bucket_sources,
            self.parser_family,
            rows,
            "Modern reported segments mapped into fixed old-bucket template.",
        )
        self._extract_native_rows(document, quarters)

    def _extract_native_rows(self, document: PdfDocument, quarters: dict[str, QuarterData]) -> None:
        """Extract modern rows that are exported directly under their own labels."""
        current_code = quarter_code(document.quarter, document.fiscal_year)
        prior_code = quarter_code(document.quarter, document.fiscal_year - 1)
        found: set[str] = set()

        for page_number, text in enumerate(document.pages, start=1):
            if "Digital Industries" not in text or "Siemens (continuing operations)" not in text:
                continue
            pending_reconciliation = False
            for raw_line in text.splitlines():
                line = raw_line.strip()
                if line == "Reconciliation to":
                    pending_reconciliation = True
                    continue
                if pending_reconciliation:
                    if line.startswith("Consolidated Financial Statements"):
                        self._store_native_row(
                            document,
                            quarters,
                            page_number,
                            "Reconciliation to Consolidated Financial Statements",
                            line,
                            current_code,
                            prior_code,
                            found,
                        )
                    pending_reconciliation = False
                elif line.startswith("Consolidated Financial Statements"):
                    self._store_native_row(
                        document,
                        quarters,
                        page_number,
                        "Reconciliation to Consolidated Financial Statements",
                        line,
                        current_code,
                        prior_code,
                        found,
                    )

                for prefix, row in MODERN_ROW_ALIASES:
                    if line.startswith(prefix):
                        self._store_native_row(
                            document,
                            quarters,
                            page_number,
                            row,
                            line,
                            current_code,
                            prior_code,
                            found,
                        )
                        break

        missing = sorted(MODERN_REQUIRED_ROWS - found)
        if missing:
            raise ValueError(f"{document.path.name}: missing native modern segment rows: {missing}")

    def _store_native_row(
        self,
        document: PdfDocument,
        quarters: dict[str, QuarterData],
        page_number: int,
        row: str,
        line: str,
        current_code: str,
        prior_code: str,
        found: set[str],
    ) -> None:
        """Store one native modern segment row for current and prior-year quarters."""
        if row in found:
            return
        values = int_tokens(line)
        if len(values) < 4:
            return
        found.add(row)
        note = "Revenue from Financial Results segment table."
        for code, value in [(current_code, values[2]), (prior_code, values[3])]:
            quarters[code].values[row] = value
            quarters[code].sources[row] = source_record(
                document,
                page_number,
                self.parser_family,
                line,
                values,
                row,
                value,
                note,
                source_type="native",
            )
