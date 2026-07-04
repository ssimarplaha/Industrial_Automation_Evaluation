"""Cross-row validation, calculated rows, overrides, and sample warnings."""

from __future__ import annotations

from pathlib import Path

from .config import SAMPLE_EXPECTATIONS, SEGMENT_ROWS, YY_ROWS
from .models import QuarterData, SourceRecord
from .periods import quarter_code, quarter_sort_key


def add_other_segment_values(quarters: dict[str, QuarterData]) -> None:
    """Calculate the residual Other segment from total and reported buckets."""
    for quarter in quarters.values():
        missing = [row for row in ["Industry", "Energy", "Healthcare", "Total Revenue"] if row not in quarter.values]
        if missing:
            raise ValueError(f"{quarter.source_pdf} {quarter.code}: missing segment inputs: {missing}")
        other = int(quarter.values["Total Revenue"]) - sum(
            int(quarter.values[row]) for row in ["Industry", "Energy", "Healthcare"]
        )
        quarter.values["Other"] = other
        quarter.sources["Other"] = SourceRecord(
            source_pdf=quarter.source_pdf,
            page=0,
            parser_family="calculated",
            raw_line="Calculated: Total Revenue - Industry - Energy - Healthcare",
            raw_values=[
                int(quarter.values["Total Revenue"]),
                int(quarter.values["Industry"]),
                int(quarter.values["Energy"]),
                int(quarter.values["Healthcare"]),
            ],
            normalized_row="Other",
            normalized_value=other,
            source_type="calculated",
        )


def validate_quarter(quarter: QuarterData) -> None:
    """Validate income-statement and balance-sheet bridges for one quarter."""
    def check(name: str, actual: int, expected: int, tolerance: int = 1) -> None:
        """Record one validation result and raise on material mismatch."""
        diff = actual - expected
        passed = abs(diff) <= tolerance
        quarter.validations.append(
            {
                "name": name,
                "actual": actual,
                "expected": expected,
                "difference": diff,
                "tolerance": tolerance,
                "passed": passed,
            }
        )
        if not passed:
            raise ValueError(
                f"{quarter.source_pdf} {quarter.code}: validation failed for {name}: "
                f"actual={actual}, expected={expected}, diff={diff}"
            )

    values = quarter.values
    check(
        "segments_tie_to_total_revenue",
        sum(int(values[row]) for row in SEGMENT_ROWS if row != "Total Revenue"),
        int(values["Total Revenue"]),
    )
    check("gross_profit_bridge", int(values["Total Revenue"]) - int(values["COGS"]), int(values["Gross Profit"]))
    check(
        "total_expenses_bridge",
        int(values["R&D"]) + int(values["SG&D"]) + int(values["Other Income"]) + int(values["Operating Expenses"]),
        int(values["Total Expenses"]),
    )
    check("ebit_bridge", int(values["Gross Profit"]) + int(values["Total Expenses"]), int(values["EBIT"]))
    check(
        "ebt_bridge",
        int(values["EBIT"]) + int(values["Income from Investment"]) + int(values["Interest Income"]),
        int(values["EBT"]),
        tolerance=2,
    )
    check(
        "net_income_bridge",
        int(values["Income From Continuous Operations"]) + int(values["Income From Dis-continued operations"]),
        int(values["Net Income"]),
    )
    validate_balance_sheet(quarter)


def validate_balance_sheet(quarter: QuarterData) -> None:
    """Validate balance-sheet subtotal and total bridges when data is present."""
    values = quarter.values
    if "Total Assets" not in values:
        return

    def check(name: str, actual: int, expected: int, tolerance: int = 2) -> None:
        """Record one balance-sheet validation and raise on mismatch."""
        diff = actual - expected
        passed = abs(diff) <= tolerance
        quarter.validations.append(
            {
                "name": name,
                "actual": actual,
                "expected": expected,
                "difference": diff,
                "tolerance": tolerance,
                "passed": passed,
            }
        )
        if not passed:
            raise ValueError(
                f"{quarter.source_pdf} {quarter.code}: validation failed for {name}: "
                f"actual={actual}, expected={expected}, diff={diff}"
            )

    def present_sum(rows: list[str]) -> int:
        """Sum only component rows reported for this quarter."""
        return sum(int(values[row]) for row in rows if row in values)

    current_asset_rows = [
        "Cash & Cash Equivalets",
        "Available-for-sale financial assets",
        "Trade and OR",
        "Other Current Financial Assets",
        "Contract Assets",
        "Inventories",
        "Income Tax Receivables",
        "Other Current Assets",
        "Assetes classifies as held for disposal",
    ]
    noncurrent_asset_rows = [
        "Goodwill",
        "Other intangible assets",
        "PP&E",
        "Investments accounted for using equity method",
        "Other Financial Assets",
        "Deferred Tax Assets",
        "Other Assets",
    ]
    current_liability_rows = [
        "Short-Term Debt",
        "Trade Payables",
        "Other Current Financial Liabilities",
        "Contract Liabilities",
        "Current Provisions",
        "Income Tax Payable",
        "Other Current Liabilities",
        "Liabilities associated with assets classified as held",
    ]
    noncurrent_liability_rows = [
        "Long-Term Debt",
        "Pension Plans and similar commitments",
        "Deferred Tax Liabilities",
        "Provisions",
        "Other Financial Liabilities",
        "Other Liabilities",
    ]

    check("total_current_assets_bridge", present_sum(current_asset_rows), int(values["Total Current Assets (TCA)"]))
    check(
        "total_assets_bridge",
        int(values["Total Current Assets (TCA)"]) + present_sum(noncurrent_asset_rows),
        int(values["Total Assets"]),
    )
    check(
        "total_current_liabilities_bridge",
        present_sum(current_liability_rows),
        int(values["Total Current Liabilities"]),
    )
    check(
        "total_liabilities_bridge",
        int(values["Total Current Liabilities"]) + present_sum(noncurrent_liability_rows),
        int(values["Total Liabilities"]),
    )
    if "Total Equity" in values and "Non-controlling interests" in values:
        check(
            "total_equity_bridge",
            int(values["S/E"]) + int(values["Non-controlling interests"]),
            int(values["Total Equity"]),
        )
        check(
            "total_liabilities_and_equity_bridge",
            int(values["Total Liabilities"]) + int(values["Total Equity"]),
            int(values["L+S/E"]),
        )


def apply_yoy(quarters: dict[str, QuarterData]) -> None:
    """Populate year-over-year percentage rows from prior-year quarter values."""
    for code, quarter in quarters.items():
        year, fiscal_quarter = quarter_sort_key(code)
        previous_code = quarter_code(fiscal_quarter, year - 1)
        previous = quarters.get(previous_code)
        for yy_row, source_row in YY_ROWS.items():
            if not previous:
                quarter.values[yy_row] = None
                continue
            if source_row not in quarter.values or source_row not in previous.values:
                quarter.values[yy_row] = None
                continue
            previous_value = int(previous.values[source_row])
            if previous_value == 0:
                quarter.values[yy_row] = None
                continue
            value = int(quarter.values[source_row]) / previous_value - 1
            quarter.values[yy_row] = value
            quarter.sources[yy_row] = SourceRecord(
                source_pdf=quarter.source_pdf,
                page=0,
                parser_family="calculated",
                raw_line=f"Calculated: {code} {source_row} / {previous_code} {source_row} - 1",
                raw_values=[int(quarter.values[source_row]), previous_value],
                normalized_row=yy_row,
                normalized_value=f"{value:.1%}",
                source_type="calculated",
            )


def apply_overrides(quarters: dict[str, QuarterData], overrides_path: Path | None) -> list[str]:
    """Apply explicit manual overrides and mark their audit source type."""
    if not overrides_path:
        return []
    if not overrides_path.exists():
        raise FileNotFoundError(f"Override file not found: {overrides_path}")
    import json

    overrides = json.loads(overrides_path.read_text())
    applied: list[str] = []
    for code, row_values in overrides.items():
        if code not in quarters:
            raise ValueError(f"Override references unknown quarter: {code}")
        for row, value in row_values.items():
            old_value = quarters[code].values.get(row)
            quarters[code].values[row] = value
            quarters[code].sources[row] = SourceRecord(
                source_pdf=str(overrides_path),
                page=0,
                parser_family="override",
                raw_line="Manual override",
                raw_values=[],
                normalized_row=row,
                normalized_value=value,
                source_type="override",
                note=f"Manual override replaced {old_value!r}.",
            )
            applied.append(f"{code} {row}: {old_value!r} -> {value!r}")
    return applied


def add_sample_reconciliation_warnings(quarters: dict[str, QuarterData]) -> list[str]:
    """Record known differences between legacy samples and PDF-derived values."""
    warnings: list[str] = []
    for code, expected_rows in SAMPLE_EXPECTATIONS.items():
        quarter = quarters.get(code)
        if not quarter:
            continue
        for row, expected in expected_rows.items():
            actual = quarter.values.get(row)
            if actual != expected:
                message = (
                    f"{code} {row}: PDF-derived value {actual!r} differs from original sample "
                    f"value {expected!r}; PDF value retained."
                )
                quarter.warnings.append(message)
                warnings.append(message)
    return warnings
