"""Derive audited annual Siemens export columns from quarterly data."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from .config import BALANCE_OUTPUT_ROWS, INCOME_OUTPUT_ROWS, METRIC_OUTPUT_ROWS, OUTPUT_ROWS, YY_ROWS
from .models import QuarterData, SourceRecord, Value, YearData
from .periods import quarter_code, year_sort_key
from .writer import format_cell


PARSER_FAMILY = "yearly"
SECTION_ROWS = {"Assets", "Liabilities"}
HIDDEN_FLOW_ROWS = {"Total Revenue"}
FLOW_ROWS = {row for row in INCOME_OUTPUT_ROWS if row and row not in YY_ROWS} | HIDDEN_FLOW_ROWS
BALANCE_VALUE_ROWS = {row for row in BALANCE_OUTPUT_ROWS if row and row not in SECTION_ROWS}


@dataclass(frozen=True)
class AnnualCalculation:
    """An annual calculated value plus integer inputs for audit evidence."""

    value: int | float
    raw_values: list[int]
    note: str


def calculate_years(quarters: dict[str, Any]) -> dict[str, YearData]:
    """Create complete fiscal-year columns from audited quarterly columns."""
    years: dict[str, YearData] = {}
    for fiscal_year in complete_fiscal_years(quarters):
        source_quarters = [quarter_code(quarter, fiscal_year) for quarter in range(1, 5)]
        year = YearData(
            code=year_code(fiscal_year),
            fiscal_year=fiscal_year,
            source_quarters=source_quarters,
        )
        _add_base_rows(year, quarters)
        years[year.code] = year

    _add_yoy_rows(years)
    _add_metric_rows(years)
    _add_validations(years)
    return years


def complete_fiscal_years(quarters: dict[str, Any]) -> list[int]:
    """Return fiscal years where Q1 through Q4 are all extracted."""
    fiscal_years = sorted({_quarter_year(quarter) for quarter in quarters.values()})
    return [
        fiscal_year
        for fiscal_year in fiscal_years
        if all(quarter_code(quarter, fiscal_year) in quarters for quarter in range(1, 5))
    ]


def year_code(fiscal_year: int) -> str:
    """Format a fiscal year as the annual workbook/audit column code."""
    return f"FY{fiscal_year}"


def _add_base_rows(year: YearData, quarters: dict[str, Any]) -> None:
    """Populate annual flow sums and year-end balance rows."""
    q4_code = quarter_code(4, year.fiscal_year)
    q4_values = _values(quarters[q4_code])
    for row in [*OUTPUT_ROWS, *sorted(HIDDEN_FLOW_ROWS)]:
        if row is None or row in SECTION_ROWS or row in YY_ROWS or row in METRIC_OUTPUT_ROWS:
            continue
        calculation = None
        if row in FLOW_ROWS:
            calculation = _flow_sum(row, year.source_quarters, quarters)
        elif row in BALANCE_VALUE_ROWS:
            value = _int_or_none(q4_values.get(row))
            if value is not None:
                calculation = AnnualCalculation(
                    value,
                    [value],
                    f"Fiscal year-end value from {q4_code} {row}.",
                )
        if calculation is not None:
            _set_calculated(year, row, calculation)


def _flow_sum(row: str, source_quarters: list[str], quarters: dict[str, Any]) -> AnnualCalculation | None:
    """Sum a row across all four quarter columns when every quarter has it."""
    values = [_int_or_none(_values(quarters[code]).get(row)) for code in source_quarters]
    if any(value is None for value in values):
        return None
    raw_values = [int(value) for value in values]
    return AnnualCalculation(
        sum(raw_values),
        raw_values,
        f"Sum of {', '.join(source_quarters)} {row}.",
    )


def _add_yoy_rows(years: dict[str, YearData]) -> None:
    """Recompute annual year-over-year rows from annual source rows."""
    for code in sorted(years, key=year_sort_key):
        year = years[code]
        previous = years.get(year_code(year.fiscal_year - 1))
        for row, source_row in YY_ROWS.items():
            if previous is None:
                continue
            current_value = _int_or_none(year.values.get(source_row))
            previous_value = _int_or_none(previous.values.get(source_row))
            if current_value is None or previous_value in {None, 0}:
                continue
            calculation = AnnualCalculation(
                current_value / int(previous_value) - 1,
                [current_value, int(previous_value)],
                f"{code} {source_row} / {previous.code} {source_row} - 1.",
            )
            _set_calculated(year, row, calculation)


def _add_metric_rows(years: dict[str, YearData]) -> None:
    """Recompute annual ratios, leverage, turnover, and growth rows."""
    for code in sorted(years, key=year_sort_key):
        for row in METRIC_OUTPUT_ROWS:
            calculation = _metric_calculation(code, row, years)
            if calculation is not None:
                _set_calculated(years[code], row, calculation)


def _metric_calculation(code: str, row: str, years: dict[str, YearData]) -> AnnualCalculation | None:
    """Dispatch one annual metric row to its calculation rule."""
    if row == "Current Assets Growth %":
        return _growth_metric(code, years, "Total Current Assets (TCA)")
    if row == "Assets Growth %":
        return _growth_metric(code, years, "Total Assets")
    if row in {"Total Liabilities Growth Rate %", "Liabilites Growth %"}:
        return _growth_metric(code, years, "Total Liabilities")
    if row == "Lt Debt as of Revenue %":
        return _debt_to_annual_revenue(code, years)
    if row == "Quick Ratio":
        return _quick_ratio(code, years)
    if row == "Current Ratio":
        return _ratio_metric(
            code,
            years,
            "Total Current Assets (TCA)",
            "Total Current Liabilities",
            "Total current assets / total current liabilities.",
        )
    if row == "DSO":
        return _turnover_days_metric(code, years, "Trade and OR", "Total Revenue", "annual revenue")
    if row == "DIO":
        return _turnover_days_metric(code, years, "Inventories", "COGS", "annual COGS")
    if row == "DPO":
        return _turnover_days_metric(code, years, "Trade Payables", "COGS", "annual COGS")
    if row == "Net Trading Cycles":
        return _net_trading_cycles(code, years)
    if row == "Debt Ratio":
        return _ratio_metric(code, years, "Total Liabilities", "Total Assets", "Total liabilities / total assets.")
    if row == "SE Growth %":
        return _growth_metric(code, years, "S/E")
    return None


def _growth_metric(code: str, years: dict[str, YearData], source_row: str) -> AnnualCalculation | None:
    """Calculate annual year-over-year growth from one annual row."""
    current = _int_or_none(years[code].values.get(source_row))
    previous_code = year_code(year_sort_key(code) - 1)
    previous = years.get(previous_code)
    previous_value = None if previous is None else _int_or_none(previous.values.get(source_row))
    if current is None or previous_value in {None, 0}:
        return None
    return AnnualCalculation(
        current / int(previous_value) - 1,
        [current, int(previous_value)],
        f"{code} {source_row} / {previous_code} {source_row} - 1.",
    )


def _debt_to_annual_revenue(code: str, years: dict[str, YearData]) -> AnnualCalculation | None:
    """Calculate long-term debt as a share of annual revenue."""
    values = years[code].values
    debt = _int_or_none(values.get("Long-Term Debt"))
    revenue = _int_or_none(values.get("Total Revenue"))
    if debt is None or revenue in {None, 0}:
        return None
    return AnnualCalculation(debt / int(revenue), [debt, int(revenue)], "Long-term debt / annual Total Revenue.")


def _quick_ratio(code: str, years: dict[str, YearData]) -> AnnualCalculation | None:
    """Calculate year-end quick assets divided by current liabilities."""
    values = years[code].values
    required_rows = [
        "Cash & Cash Equivalets",
        "Trade and OR",
        "Other Current Financial Assets",
        "Total Current Liabilities",
    ]
    required = [_int_or_none(values.get(row)) for row in required_rows]
    if any(value is None for value in required) or required[-1] == 0:
        return None
    optional_afs = _int_or_none(values.get("Available-for-sale financial assets"))
    quick_assets = sum(int(value) for value in required[:-1]) + (optional_afs or 0)
    raw_values = [int(value) for value in required]
    if optional_afs is not None:
        raw_values.insert(1, optional_afs)
    return AnnualCalculation(
        quick_assets / int(required[-1]),
        raw_values,
        "Quick assets / total current liabilities; AFS assets included only when reported.",
    )


def _ratio_metric(
    code: str,
    years: dict[str, YearData],
    numerator_row: str,
    denominator_row: str,
    note: str,
) -> AnnualCalculation | None:
    """Calculate a simple year-end ratio from two annual rows."""
    values = years[code].values
    numerator = _int_or_none(values.get(numerator_row))
    denominator = _int_or_none(values.get(denominator_row))
    if numerator is None or denominator in {None, 0}:
        return None
    return AnnualCalculation(numerator / int(denominator), [numerator, int(denominator)], note)


def _turnover_days_metric(
    code: str,
    years: dict[str, YearData],
    balance_row: str,
    flow_row: str,
    flow_label: str,
) -> AnnualCalculation | None:
    """Calculate turnover using beginning/end balances and annual flow."""
    current = _int_or_none(years[code].values.get(balance_row))
    previous_code = year_code(year_sort_key(code) - 1)
    previous = years.get(previous_code)
    previous_value = None if previous is None else _int_or_none(previous.values.get(balance_row))
    flow = _int_or_none(years[code].values.get(flow_row))
    days = fiscal_year_days(year_sort_key(code))
    if current is None or previous_value is None or flow in {None, 0}:
        return None
    average_balance = (current + previous_value) / 2
    return AnnualCalculation(
        average_balance / int(flow) * days,
        [previous_value, current, int(flow), days],
        f"Average {balance_row} from {previous_code}/{code} divided by {flow_label} times fiscal days.",
    )


def _net_trading_cycles(code: str, years: dict[str, YearData]) -> AnnualCalculation | None:
    """Calculate annual DSO plus DIO minus DPO."""
    dso = _metric_calculation(code, "DSO", years)
    dio = _metric_calculation(code, "DIO", years)
    dpo = _metric_calculation(code, "DPO", years)
    if dso is None or dio is None or dpo is None:
        return None
    value = dso.value + dio.value - dpo.value
    return AnnualCalculation(
        value,
        [_round_tenth(float(dso.value)), _round_tenth(float(dio.value)), _round_tenth(float(dpo.value))],
        f"DSO {dso.value:.1f} + DIO {dio.value:.1f} - DPO {dpo.value:.1f}.",
    )


def fiscal_year_days(fiscal_year: int) -> int:
    """Return the calendar-day count in a Siemens fiscal year."""
    return (date(fiscal_year, 9, 30) - date(fiscal_year - 1, 10, 1)).days + 1


def _set_calculated(year: YearData, row: str, calculation: AnnualCalculation) -> None:
    """Store one calculated annual value and its audit source evidence."""
    year.values[row] = calculation.value
    year.sources[row] = SourceRecord(
        source_pdf=f"derived from {', '.join(year.source_quarters)}",
        page=0,
        parser_family=PARSER_FAMILY,
        raw_line=f"Calculated annual value: {row}",
        raw_values=calculation.raw_values,
        normalized_row=row,
        normalized_value=_normalized_value(calculation.value, row),
        source_type="calculated",
        note=calculation.note,
    )


def _normalized_value(value: Value, row: str) -> Value:
    """Store float displays the same way calculated quarterly sources do."""
    if isinstance(value, float):
        return format_cell(value, row)
    return value


def _add_validations(years: dict[str, YearData]) -> None:
    """Record lightweight validations for annual derived columns."""
    for year in years.values():
        exported_rows = [row for row in OUTPUT_ROWS if row and year.values.get(row) is not None]
        missing_sources = [row for row in exported_rows if row not in year.sources]
        year.validations.append(
            {
                "name": "annual_exported_values_have_sources",
                "passed": not missing_sources,
                "missing_sources": missing_sources,
            }
        )


def _quarter_year(quarter: Any) -> int:
    """Return fiscal year from QuarterData or audit-dict shaped input."""
    if isinstance(quarter, QuarterData):
        return quarter.fiscal_year
    fiscal_year = quarter.get("fiscal_year")
    if fiscal_year is not None:
        return int(fiscal_year)
    raise ValueError("Quarter is missing fiscal_year.")


def _values(item: Any) -> dict[str, Any]:
    """Return the values mapping from dataclass or audit-dict inputs."""
    if isinstance(item, (QuarterData, YearData)):
        return item.values
    return item.get("values", {})


def _int_or_none(value: Any) -> int | None:
    """Accept integer values only for annual arithmetic."""
    if isinstance(value, int):
        return value
    return None


def _round_tenth(value: float) -> int:
    """Round a display value to one decimal place and store it as tenths."""
    return int(round(value * 10))
