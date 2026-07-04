from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .balance_sheet import BALANCE_ROW_PATTERNS, find_balance_sheet_page, parse_balance_rows
from .config import BALANCE_OUTPUT_ROWS
from .discovery import extract_pages, pdf_fiscal_period, sha256
from .models import PdfDocument, QuarterData, SourceRecord
from .periods import quarter_code, quarter_sort_key


SUPPLEMENTAL_BALANCE_DIR = "balance_sheet_supplemental"
SUPPLEMENTAL_BALANCE_MANIFEST = "manifest.json"
PARSER_FAMILY = "balance_sheet"

REQUIRED_SUPPLEMENTAL_BALANCE_QUARTERS = [
    "Q109",
    "Q209",
    "Q309",
    "Q111",
    "Q211",
    "Q311",
    "Q113",
    "Q213",
    "Q313",
    "Q115",
    "Q215",
    "Q315",
    "Q117",
    "Q217",
    "Q317",
    "Q119",
    "Q219",
    "Q319",
    "Q121",
    "Q221",
    "Q321",
    "Q123",
    "Q223",
    "Q323",
    "Q125",
    "Q225",
]

BALANCE_SECTION_HEADERS = {"Assets", "Liabilities"}
BALANCE_REPORT_ROWS = {
    row for row in BALANCE_OUTPUT_ROWS if row is not None and row not in BALANCE_SECTION_HEADERS
}


@dataclass(frozen=True)
class SupplementalBalanceDocument:
    quarter: str
    filename: str
    sha256: str
    source_url: str
    document: PdfDocument


def supplemental_manifest_path(input_dir: Path) -> Path:
    return input_dir / SUPPLEMENTAL_BALANCE_DIR / SUPPLEMENTAL_BALANCE_MANIFEST


def load_supplemental_balance_documents(
    input_dir: Path,
) -> tuple[list[SupplementalBalanceDocument], bool]:
    manifest_path = supplemental_manifest_path(input_dir)
    if not manifest_path.exists():
        return [], False

    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    entries = payload.get("sources")
    if not isinstance(entries, list):
        raise ValueError(f"{manifest_path} must contain a sources list.")

    documents: list[SupplementalBalanceDocument] = []
    for entry in entries:
        documents.append(_load_manifest_entry(input_dir, entry, manifest_path))
    return documents, True


def empty_supplemental_balance_coverage() -> dict[str, Any]:
    return {
        "required_quarters": REQUIRED_SUPPLEMENTAL_BALANCE_QUARTERS,
        "source_files_used": [],
        "filled_quarters": [],
        "filled_rows_by_quarter": {},
        "matched_rows_by_quarter": {},
        "missing_rows_by_quarter": {},
    }


def apply_supplemental_balance_documents(
    quarters: dict[str, QuarterData],
    documents: list[SupplementalBalanceDocument],
    *,
    manifest_found: bool,
) -> dict[str, Any]:
    coverage = empty_supplemental_balance_coverage()
    if manifest_found:
        _validate_required_manifest_coverage(documents)

    allowed_quarters = set(quarters)
    for source in documents:
        if source.quarter not in allowed_quarters:
            raise ValueError(
                f"Supplemental balance source {source.filename} maps to {source.quarter}, "
                "which is outside the current output columns."
            )
        if source.quarter not in REQUIRED_SUPPLEMENTAL_BALANCE_QUARTERS:
            raise ValueError(f"Unexpected supplemental balance quarter: {source.quarter}")

        page_number, text = find_balance_sheet_page(source.document.pages)
        parsed_rows = parse_balance_rows(text)
        filled_rows, matched_rows = _apply_parsed_balance_rows(source, quarters, parsed_rows, page_number)
        missing_rows = sorted(BALANCE_REPORT_ROWS - set(parsed_rows), key=_balance_row_sort_key)

        coverage["source_files_used"].append(
            {
                "quarter": source.quarter,
                "filename": source.filename,
                "sha256": source.sha256,
                "source_url": source.source_url,
            }
        )
        if filled_rows:
            coverage["filled_quarters"].append(source.quarter)
            coverage["filled_rows_by_quarter"][source.quarter] = filled_rows
        if matched_rows:
            coverage["matched_rows_by_quarter"][source.quarter] = matched_rows
        coverage["missing_rows_by_quarter"][source.quarter] = missing_rows

    coverage["filled_quarters"] = sorted(set(coverage["filled_quarters"]), key=quarter_sort_key)
    return coverage


def _load_manifest_entry(
    input_dir: Path,
    entry: Any,
    manifest_path: Path,
) -> SupplementalBalanceDocument:
    if not isinstance(entry, dict):
        raise ValueError(f"{manifest_path} entries must be objects.")
    quarter = _required_text(entry, "quarter", manifest_path)
    filename = _required_text(entry, "filename", manifest_path)
    expected_sha = _required_text(entry, "sha256", manifest_path)
    source_url = _required_text(entry, "source_url", manifest_path)

    path = input_dir / SUPPLEMENTAL_BALANCE_DIR / filename
    if not path.exists():
        raise ValueError(f"Supplemental balance PDF is missing: {path}")
    actual_sha = sha256(path)
    if actual_sha != expected_sha:
        raise ValueError(f"{filename} SHA-256 mismatch: expected {expected_sha}, got {actual_sha}.")

    fiscal_year, fiscal_quarter = pdf_fiscal_period(path)
    detected_quarter = quarter_code(fiscal_quarter, fiscal_year)
    if detected_quarter != quarter:
        raise ValueError(f"{filename} maps to {detected_quarter}, but manifest declares {quarter}.")

    document = PdfDocument(
        path=Path(SUPPLEMENTAL_BALANCE_DIR) / filename,
        sha256=actual_sha,
        fiscal_year=fiscal_year,
        quarter=fiscal_quarter,
        code=detected_quarter,
        pages=extract_pages(path),
    )
    return SupplementalBalanceDocument(quarter, filename, actual_sha, source_url, document)


def _apply_parsed_balance_rows(
    source: SupplementalBalanceDocument,
    quarters: dict[str, QuarterData],
    parsed_rows: dict[str, tuple[str, list[int]]],
    page_number: int,
) -> tuple[list[str], list[str]]:
    quarter = quarters[source.quarter]
    filled_rows: list[str] = []
    matched_rows: list[str] = []
    hidden_components: dict[str, int] = {}

    for row, (raw_line, values) in parsed_rows.items():
        if not values:
            continue
        value = values[0]
        existing = quarter.values.get(row)
        existing_source = quarter.sources.get(row)
        if existing is not None:
            if existing != value:
                raise ValueError(
                    f"Supplemental balance conflict for {source.quarter} {row}: "
                    f"existing {existing}, supplemental {value} from {source.filename}."
                )
            if existing_source is None or existing_source.source_type != "native":
                raise ValueError(f"{source.quarter} {row} already has a non-native value.")
            matched_rows.append(row)
            continue

        quarter.values[row] = value
        quarter.sources[row] = SourceRecord(
            source_pdf=source.document.path.as_posix(),
            page=page_number,
            parser_family=PARSER_FAMILY,
            raw_line=raw_line,
            raw_values=values,
            normalized_row=row,
            normalized_value=value,
            source_type="native",
            note=f"Supplemental balance sheet source selected for {source.quarter}.",
        )
        filled_rows.append(row)
        if row not in BALANCE_REPORT_ROWS:
            hidden_components[row] = value

    if hidden_components:
        quarter.raw_components.setdefault("balance_sheet", {}).update(hidden_components)
    return sorted(filled_rows, key=_balance_row_sort_key), sorted(matched_rows, key=_balance_row_sort_key)


def _validate_required_manifest_coverage(documents: list[SupplementalBalanceDocument]) -> None:
    declared = {document.quarter for document in documents}
    missing = sorted(set(REQUIRED_SUPPLEMENTAL_BALANCE_QUARTERS) - declared, key=quarter_sort_key)
    if missing:
        raise ValueError(f"Supplemental balance manifest is missing required quarters: {', '.join(missing)}")


def _required_text(entry: dict[str, Any], key: str, manifest_path: Path) -> str:
    value = entry.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{manifest_path} entry is missing text field {key!r}.")
    return value


def _balance_row_sort_key(row: str) -> tuple[int, str]:
    rows = [name for name, _pattern in BALANCE_ROW_PATTERNS]
    try:
        return rows.index(row), row
    except ValueError:
        return len(rows), row
