from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from .discovery import extract_pages, pdf_fiscal_period
from .numbers import int_tokens
from .periods import quarter_sort_key
from .verification_rules import UNKNOWN, calculated_values_equal, expected_calculated_value
from .writer import format_cell


VALID_SOURCE_TYPES = {"native", "calculated", "reconstructed", "override"}


def verify_outputs(
    tsv_path: Path,
    audit_path: Path,
    input_dir: Path,
    report_path: Path | None = None,
) -> dict[str, Any]:
    audit = json.loads(audit_path.read_text())
    columns, rows, tsv_issues = _read_tsv(tsv_path)
    quarters = audit.get("quarters", {})
    issues: list[dict[str, Any]] = list(tsv_issues)
    checked_values: list[dict[str, Any]] = []
    page_cache: dict[str, list[str]] = {}
    source_type_counts: Counter[str] = Counter()

    metadata_columns = audit.get("metadata", {}).get("columns", [])
    if columns != metadata_columns:
        _add_issue(
            issues,
            "column_mismatch",
            "TSV columns do not match audit metadata columns.",
            tsv_columns=columns,
            audit_columns=metadata_columns,
        )

    _verify_tsv_cells(rows, columns, quarters, checked_values, issues)
    _verify_audit_values(quarters, input_dir, page_cache, checked_values, issues, source_type_counts)

    failed_validations = [
        {"quarter": code, "validation": validation}
        for code, quarter in quarters.items()
        for validation in quarter.get("validations", [])
        if not validation.get("passed")
    ]
    for item in failed_validations:
        _add_issue(
            issues,
            "failed_validation",
            f"{item['quarter']}: audit validation failed.",
            quarter=item["quarter"],
            validation=item["validation"],
        )

    issue_counts = Counter(issue["type"] for issue in issues)
    report = {
        "metadata": {
            "passed": not issues,
            "tsv_path": str(tsv_path),
            "audit_path": str(audit_path),
            "input_dir": str(input_dir),
            "columns_checked": len(columns),
            "quarters_checked": len(quarters),
            "exported_cells_checked": sum(len(row) for row in rows.values()),
            "exported_non_empty_cells_checked": sum(
                1 for row in rows.values() for cell in row.values() if cell
            ),
            "audit_values_checked": sum(
                1
                for quarter in quarters.values()
                for value in quarter.get("values", {}).values()
                if value is not None
            ),
            "source_lines_checked": sum(
                1 for item in checked_values if item.get("source_type") == "native"
            ),
            "source_type_counts": dict(sorted(source_type_counts.items())),
            "issue_counts": dict(sorted(issue_counts.items())),
        },
        "checked_values": checked_values,
        "issues": issues,
    }
    if report_path:
        report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return report


def _read_tsv(path: Path) -> tuple[list[str], dict[str, dict[str, str]], list[dict[str, Any]]]:
    issues: list[dict[str, Any]] = []
    lines = path.read_text().splitlines()
    if not lines:
        _add_issue(issues, "empty_tsv", "TSV file is empty.")
        return [], {}, issues

    header = lines[0].split("\t")
    if not header or header[0] != "Financial Years":
        _add_issue(issues, "invalid_tsv_header", "TSV header must start with Financial Years.")
    columns = header[1:]
    rows: dict[str, dict[str, str]] = {}

    for line_number, line in enumerate(lines[1:], start=2):
        cells = line.split("\t")
        cells += [""] * max(0, len(columns) + 1 - len(cells))
        row = cells[0]
        values = cells[1 : len(columns) + 1]
        if not row:
            if any(values):
                _add_issue(
                    issues,
                    "nonblank_separator_row",
                    "Blank separator row contains values.",
                    line_number=line_number,
                )
            continue
        if row in rows:
            _add_issue(issues, "duplicate_tsv_row", f"Duplicate TSV row: {row}.", row=row)
        rows[row] = dict(zip(columns, values))
    return columns, rows, issues


def _verify_tsv_cells(
    rows: dict[str, dict[str, str]],
    columns: list[str],
    quarters: dict[str, Any],
    checked_values: list[dict[str, Any]],
    issues: list[dict[str, Any]],
) -> None:
    for row, by_column in rows.items():
        for column in columns:
            actual = by_column.get(column, "")
            quarter = quarters.get(column)
            if quarter is None:
                _add_issue(issues, "missing_audit_quarter", f"Audit is missing {column}.", quarter=column)
                continue
            audit_value = quarter.get("values", {}).get(row)
            expected = format_cell(audit_value, row)
            checked_values.append(
                {
                    "check": "tsv_cell",
                    "quarter": column,
                    "row": row,
                    "tsv_value": actual,
                    "audit_value": audit_value,
                    "passed": actual == expected,
                }
            )
            if actual != expected:
                _add_issue(
                    issues,
                    "tsv_audit_mismatch",
                    f"{column} {row}: TSV value does not match audit value.",
                    quarter=column,
                    row=row,
                    tsv_value=actual,
                    audit_value=audit_value,
                    expected_tsv_value=expected,
                )
            if actual and row not in quarter.get("sources", {}):
                _add_issue(
                    issues,
                    "missing_exported_source",
                    f"{column} {row}: non-empty TSV value has no audit source.",
                    quarter=column,
                    row=row,
                    tsv_value=actual,
                )


def _verify_audit_values(
    quarters: dict[str, Any],
    input_dir: Path,
    page_cache: dict[str, list[str]],
    checked_values: list[dict[str, Any]],
    issues: list[dict[str, Any]],
    source_type_counts: Counter[str],
) -> None:
    for code, quarter in quarters.items():
        values = quarter.get("values", {})
        sources = quarter.get("sources", {})
        for row, value in values.items():
            if value is None:
                continue
            source = sources.get(row)
            if source is None:
                _add_issue(issues, "missing_audit_source", f"{code} {row}: audit value has no source.")
                continue
            source_type = source.get("source_type")
            source_type_counts[str(source_type)] += 1
            checked_values.append(
                {
                    "check": "audit_source",
                    "quarter": code,
                    "row": row,
                    "audit_value": value,
                    "source_type": source_type,
                    "source_pdf": source.get("source_pdf"),
                    "page": source.get("page"),
                }
            )
            if source_type not in VALID_SOURCE_TYPES:
                _add_issue(
                    issues,
                    "invalid_source_type",
                    f"{code} {row}: invalid source type {source_type!r}.",
                    quarter=code,
                    row=row,
                    source_type=source_type,
                )
                continue
            if source.get("normalized_row") != row:
                _add_issue(
                    issues,
                    "normalized_row_mismatch",
                    f"{code} {row}: source normalized row does not match audit row.",
                    quarter=code,
                    row=row,
                    normalized_row=source.get("normalized_row"),
                )
            if not _source_value_matches(value, source.get("normalized_value"), row):
                _add_issue(
                    issues,
                    "normalized_value_mismatch",
                    f"{code} {row}: source normalized value does not match audit value.",
                    quarter=code,
                    row=row,
                    audit_value=value,
                    normalized_value=source.get("normalized_value"),
                )

            if source_type == "native":
                _verify_native_source(code, row, source, input_dir, page_cache, issues)
            elif source_type == "reconstructed":
                _verify_reconstructed_source(code, row, source, issues)
            elif source_type == "calculated":
                _verify_calculated_source(code, row, value, source, quarters, issues)


def _source_value_matches(value: Any, normalized_value: Any, row: str) -> bool:
    if value == normalized_value:
        return True
    if isinstance(normalized_value, str):
        return normalized_value == format_cell(value, row)
    return False


def _verify_native_source(
    code: str,
    row: str,
    source: dict[str, Any],
    input_dir: Path,
    page_cache: dict[str, list[str]],
    issues: list[dict[str, Any]],
) -> None:
    source_pdf = source.get("source_pdf")
    page_number = int(source.get("page") or 0)
    if not source_pdf or page_number <= 0:
        _add_issue(issues, "invalid_source_page", f"{code} {row}: native source has no PDF page.")
        return

    pages = _pages_for_source(input_dir, source_pdf, page_cache, issues)
    if not pages:
        return
    if page_number > len(pages):
        _add_issue(
            issues,
            "invalid_source_page",
            f"{code} {row}: source page is outside the PDF page range.",
            quarter=code,
            row=row,
            source_pdf=source_pdf,
            page=page_number,
            pages=len(pages),
        )
        return

    raw_line = str(source.get("raw_line") or "")
    candidates = _matching_page_lines(raw_line, pages[page_number - 1])
    if not candidates:
        _add_issue(
            issues,
            "missing_source_line",
            f"{code} {row}: raw source line was not found on the recorded PDF page.",
            quarter=code,
            row=row,
            source_pdf=source_pdf,
            page=page_number,
            raw_line=raw_line,
        )
        return

    raw_values = source.get("raw_values", [])
    if raw_values and not any(int_tokens(candidate) == raw_values for candidate in candidates):
        _add_issue(
            issues,
            "source_tokens_mismatch",
            f"{code} {row}: source line tokens do not match audit raw values.",
            quarter=code,
            row=row,
            source_pdf=source_pdf,
            page=page_number,
            raw_values=raw_values,
            source_line_tokens=[int_tokens(candidate) for candidate in candidates[:3]],
        )

    expected = _expected_native_value(code, row, source)
    if expected is None:
        _add_issue(
            issues,
            "native_rule_unknown",
            f"{code} {row}: no native parser selection rule for source.",
            quarter=code,
            row=row,
            parser_family=source.get("parser_family"),
        )
    elif expected != source.get("normalized_value"):
        _add_issue(
            issues,
            "native_rule_mismatch",
            f"{code} {row}: native value does not match parser selection rule.",
            quarter=code,
            row=row,
            expected=expected,
            normalized_value=source.get("normalized_value"),
            raw_values=raw_values,
        )


def _pages_for_source(
    input_dir: Path,
    source_pdf: str,
    page_cache: dict[str, list[str]],
    issues: list[dict[str, Any]],
) -> list[str] | None:
    if source_pdf not in page_cache:
        path = input_dir / source_pdf
        if not path.exists():
            _add_issue(
                issues,
                "missing_source_pdf",
                f"Source PDF is missing: {source_pdf}.",
                source_pdf=source_pdf,
            )
            return None
        page_cache[source_pdf] = extract_pages(path)
    return page_cache[source_pdf]


def _matching_page_lines(raw_line: str, page_text: str) -> list[str]:
    raw_norm = _normalize_line(raw_line)
    if not raw_norm:
        return []
    matches = []
    for line in page_text.splitlines():
        line_norm = _normalize_line(line)
        if raw_norm in line_norm or line_norm in raw_norm:
            matches.append(line.strip())
    return matches


def _normalize_line(line: str) -> str:
    return " ".join(line.split())


def _expected_native_value(code: str, row: str, source: dict[str, Any]) -> Any:
    raw_values = source.get("raw_values", [])
    index = _native_value_index(code, source)
    if index is None or index >= len(raw_values):
        return None
    value = raw_values[index]
    return abs(value) if row == "COGS" else value


def _native_value_index(code: str, source: dict[str, Any]) -> int | None:
    source_pdf = source.get("source_pdf")
    if not source_pdf:
        return None
    source_year, source_quarter = pdf_fiscal_period(Path(source_pdf))
    code_year, code_quarter = quarter_sort_key(code)
    if code_quarter != source_quarter:
        return None
    if code_year == source_year:
        offset = 0
    elif code_year == source_year - 1:
        offset = 1
    else:
        return None

    parser_family = source.get("parser_family")
    if parser_family == "income_statement":
        return offset
    if parser_family == "balance_sheet":
        return offset
    if parser_family in {"legacy_sector_2010_2014", "modern_2020_2026"}:
        return 2 + offset
    return None


def _verify_reconstructed_source(
    code: str,
    row: str,
    source: dict[str, Any],
    issues: list[dict[str, Any]],
) -> None:
    raw_values = source.get("raw_values", [])
    expected = sum(int(value) for value in raw_values)
    if not raw_values:
        _add_issue(
            issues,
            "empty_reconstructed_source",
            f"{code} {row}: reconstructed value has no source components.",
            quarter=code,
            row=row,
        )
    if expected != source.get("normalized_value"):
        _add_issue(
            issues,
            "reconstructed_mismatch",
            f"{code} {row}: reconstructed value does not equal component sum.",
            quarter=code,
            row=row,
            expected=expected,
            normalized_value=source.get("normalized_value"),
            raw_values=raw_values,
        )


def _verify_calculated_source(
    code: str,
    row: str,
    value: Any,
    source: dict[str, Any],
    quarters: dict[str, Any],
    issues: list[dict[str, Any]],
) -> None:
    expected = expected_calculated_value(code, row, source, quarters)
    if expected is UNKNOWN:
        _add_issue(
            issues,
            "unknown_calculation_rule",
            f"{code} {row}: no calculation rule for audit source.",
            quarter=code,
            row=row,
            raw_line=source.get("raw_line"),
            parser_family=source.get("parser_family"),
        )
        return
    if not calculated_values_equal(expected, value):
        _add_issue(
            issues,
            "calculated_mismatch",
            f"{code} {row}: calculated audit value is incorrect.",
            quarter=code,
            row=row,
            expected=expected,
            audit_value=value,
            raw_values=source.get("raw_values", []),
        )
    if isinstance(expected, float) and source.get("normalized_value") != format_cell(expected, row):
        _add_issue(
            issues,
            "calculated_display_mismatch",
            f"{code} {row}: calculated source display value is incorrect.",
            quarter=code,
            row=row,
            expected=format_cell(expected, row),
            normalized_value=source.get("normalized_value"),
        )


def _add_issue(issues: list[dict[str, Any]], issue_type: str, message: str, **extra: Any) -> None:
    issue = {"type": issue_type, "message": message}
    issue.update(extra)
    issues.append(issue)
