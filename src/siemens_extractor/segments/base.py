"""Shared segment-parser abstractions and reconstruction helpers."""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import PdfDocument, QuarterData, SourceRecord, SourceType
from ..numbers import clean_label, int_tokens
from ..periods import quarter_code


class SegmentParser(ABC):
    """Interface for parser families that populate segment revenue rows."""

    parser_family: str

    @abstractmethod
    def extract(self, document: PdfDocument, quarters: dict[str, QuarterData]) -> None:
        """Populate segment rows for the document's current and prior-year quarters."""
        raise NotImplementedError


def blank_bucket_values(document: PdfDocument) -> dict[str, dict[str, int]]:
    """Create zeroed Industry/Energy/Healthcare buckets for both quarter columns."""
    current_code = quarter_code(document.quarter, document.fiscal_year)
    prior_code = quarter_code(document.quarter, document.fiscal_year - 1)
    return {
        current_code: {"Industry": 0, "Energy": 0, "Healthcare": 0},
        prior_code: {"Industry": 0, "Energy": 0, "Healthcare": 0},
    }


def blank_bucket_sources() -> dict[str, list[SourceRecord]]:
    """Create empty source buckets for reconstructed segment evidence."""
    return {"Industry": [], "Energy": [], "Healthcare": []}


def source_record(
    document: PdfDocument,
    page: int,
    parser_family: str,
    raw_line: str,
    values: list[int],
    row: str,
    value: int,
    note: str,
    source_type: SourceType = "reconstructed",
) -> SourceRecord:
    """Build a segment source record with parser-family provenance."""
    return SourceRecord(
        source_pdf=document.path.name,
        page=page,
        parser_family=parser_family,
        raw_line=raw_line.strip(),
        raw_values=values,
        normalized_row=row,
        normalized_value=value,
        source_type=source_type,
        note=note,
    )


def first_revenue_after_heading(
    document: PdfDocument,
    heading_to_bucket: dict[str, str],
    parser_family: str,
    note: str,
    page_numbers: set[int] | None = None,
) -> tuple[dict[str, dict[str, int]], dict[str, dict[str, list[SourceRecord]]], set[str]]:
    """Collect the first Revenue row after each known segment heading."""
    current_code = quarter_code(document.quarter, document.fiscal_year)
    prior_code = quarter_code(document.quarter, document.fiscal_year - 1)
    bucket_values = blank_bucket_values(document)
    bucket_sources = {
        current_code: blank_bucket_sources(),
        prior_code: blank_bucket_sources(),
    }

    headings = set(heading_to_bucket)
    found_headings: set[str] = set()
    current_heading: str | None = None
    for page_number, text in enumerate(document.pages, start=1):
        if page_numbers is not None and page_number not in page_numbers:
            continue
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if line in headings:
                current_heading = line
                continue
            if not current_heading or not line.startswith("Revenue "):
                continue
            values = int_tokens(line)
            if len(values) < 2:
                continue
            bucket = heading_to_bucket[current_heading]
            current_value, prior_value = values[:2]
            for code, value in [(current_code, current_value), (prior_code, prior_value)]:
                bucket_values[code][bucket] += value
                bucket_sources[code][bucket].append(
                    source_record(
                        document,
                        page_number,
                        parser_family,
                        f"{current_heading}: {clean_label(line)}",
                        values,
                        bucket,
                        value,
                        note,
                    )
                )
            found_headings.add(current_heading)
            current_heading = None

    return bucket_values, bucket_sources, found_headings


def assign_bucket_totals(
    document: PdfDocument,
    quarters: dict[str, QuarterData],
    bucket_values: dict[str, dict[str, int]],
    bucket_sources: dict[str, dict[str, list[SourceRecord]]],
    parser_family: str,
    rows: list[str],
    note: str,
) -> None:
    """Assign reconstructed bucket totals and component evidence to quarters."""
    for code in [quarter_code(document.quarter, document.fiscal_year), quarter_code(document.quarter, document.fiscal_year - 1)]:
        for row in rows:
            value = bucket_values[code][row]
            sources = bucket_sources[code][row]
            quarters[code].values[row] = value
            quarters[code].sources[row] = SourceRecord(
                source_pdf=document.path.name,
                page=sources[0].page if sources else 0,
                parser_family=parser_family,
                raw_line=" + ".join(source.raw_line for source in sources) if sources else "Calculated: no explicit segment reported",
                raw_values=[int(source.normalized_value or 0) for source in sources],
                normalized_row=row,
                normalized_value=value,
                source_type="reconstructed" if sources else "calculated",
                note=note if sources else f"No explicit {row} segment was reported for this parser family.",
            )
            if sources:
                quarters[code].warnings.append(note)
