"""Calculate derived liquidity, growth, turnover, and leverage metrics."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from .config import METRIC_OUTPUT_ROWS
from .models import QuarterData, SourceRecord
from .periods import quarter_code, quarter_sort_key
from .writer import format_cell


PARSER_FAMILY = "metrics"


@dataclass(frozen=True)
class MetricCalculation:
    """A derived metric value plus the raw inputs needed for audit replay."""

    value: float
    raw_values: list[int]
    note: str


def calculate_metrics(quarters: dict[str, QuarterData]) -> None:
    """Populate metric rows and calculated source records for every quarter."""
    for code, quarter in quarters.items():
        for row in METRIC_OUTPUT_ROWS:
            calculation = metric_calculation(code, row, quarters)
            if calculation is None:
                quarter.values[row] = None
                continue
            quarter.values[row] = calculation.value
            quarter.sources[row] = SourceRecord(
                source_pdf=quarter.source_pdf,
                page=0,
                parser_family=PARSER_FAMILY,
                raw_line=f"Calculated metric: {row}",
                raw_values=calculation.raw_values,
                normalized_row=row,
                normalized_value=format_cell(calculation.value, row),
                source_type="calculated",
                note=calculation.note,
            )


def expected_metric_value(code: str, row: str, quarters: dict[str, Any]) -> float | None:
    """Recompute a metric value for verification without mutating quarters."""
    calculation = metric_calculation(code, row, quarters)
    return None if calculation is None else calculation.value


def metric_calculation(code: str, row: str, quarters: dict[str, Any]) -> MetricCalculation | None:
    """Dispatch one metric row to its calculation rule."""
    if row == "Current Assets Growth %":
        return growth_metric(code, quarters, "Total Current Assets (TCA)")
    if row == "Assets Growth %":
        return growth_metric(code, quarters, "Total Assets")
    if row in {"Total Liabilities Growth Rate %", "Liabilites Growth %"}:
        return growth_metric(code, quarters, "Total Liabilities")
    if row == "Lt Debt as of Revenue %":
        return long_term_debt_to_revenue(code, quarters)
    if row == "Quick Ratio":
        return quick_ratio(code, quarters)
    if row == "Current Ratio":
        return ratio_metric(
            code,
            quarters,
            "Total Current Assets (TCA)",
            "Total Current Liabilities",
            "Total current assets / total current liabilities.",
        )
    if row == "DSO":
        return turnover_days_metric(code, quarters, "Trade and OR", "Total Revenue", "quarterly revenue")
    if row == "DIO":
        return turnover_days_metric(code, quarters, "Inventories", "COGS", "quarterly COGS")
    if row == "DPO":
        return turnover_days_metric(code, quarters, "Trade Payables", "COGS", "quarterly COGS")
    if row == "Net Trading Cycles":
        return net_trading_cycles(code, quarters)
    if row == "Debt Ratio":
        return ratio_metric(code, quarters, "Total Liabilities", "Total Assets", "Total liabilities / total assets.")
    if row == "SE Growth %":
        return growth_metric(code, quarters, "S/E")
    return None


def growth_metric(code: str, quarters: dict[str, Any], source_row: str) -> MetricCalculation | None:
    """Calculate a year-over-year growth metric from one source row."""
    current = int_value(quarters.get(code), source_row)
    previous_code = previous_year_code(code)
    previous = int_value(quarters.get(previous_code), source_row)
    if current is None or previous in {None, 0}:
        return None
    value = current / previous - 1
    return MetricCalculation(
        value,
        [current, previous],
        f"{code} {source_row} / {previous_code} {source_row} - 1.",
    )


def long_term_debt_to_revenue(code: str, quarters: dict[str, Any]) -> MetricCalculation | None:
    """Calculate long-term debt as a share of trailing four-quarter revenue."""
    debt = int_value(quarters.get(code), "Long-Term Debt")
    revenue_codes = trailing_codes(code, 4)
    revenues = [int_value(quarters.get(revenue_code), "Total Revenue") for revenue_code in revenue_codes]
    if debt is None or any(value is None for value in revenues):
        return None
    total_revenue = sum(int(value) for value in revenues)
    if total_revenue == 0:
        return None
    return MetricCalculation(
        debt / total_revenue,
        [debt, *[int(value) for value in revenues]],
        f"Long-term debt / trailing four-quarter Total Revenue using {', '.join(revenue_codes)}.",
    )


def quick_ratio(code: str, quarters: dict[str, Any]) -> MetricCalculation | None:
    """Calculate quick assets divided by total current liabilities."""
    values = value_dict(quarters.get(code))
    required_rows = [
        "Cash & Cash Equivalets",
        "Trade and OR",
        "Other Current Financial Assets",
        "Total Current Liabilities",
    ]
    required = [int_or_none(values.get(row)) for row in required_rows]
    if any(value is None for value in required) or required[-1] == 0:
        return None
    optional_afs = int_or_none(values.get("Available-for-sale financial assets"))
    quick_assets = sum(int(value) for value in required[:-1]) + (optional_afs or 0)
    raw_values = [int(value) for value in required]
    if optional_afs is not None:
        raw_values.insert(1, optional_afs)
    return MetricCalculation(
        quick_assets / int(required[-1]),
        raw_values,
        "Quick assets / total current liabilities; AFS assets included only when reported.",
    )


def ratio_metric(
    code: str,
    quarters: dict[str, Any],
    numerator_row: str,
    denominator_row: str,
    note: str,
) -> MetricCalculation | None:
    """Calculate a simple ratio from two quarter-local rows."""
    numerator = int_value(quarters.get(code), numerator_row)
    denominator = int_value(quarters.get(code), denominator_row)
    if numerator is None or denominator in {None, 0}:
        return None
    return MetricCalculation(numerator / denominator, [numerator, denominator], note)


def turnover_days_metric(
    code: str,
    quarters: dict[str, Any],
    balance_row: str,
    flow_row: str,
    flow_label: str,
) -> MetricCalculation | None:
    """Calculate average balance divided by quarter flow, scaled by fiscal days."""
    current = int_value(quarters.get(code), balance_row)
    previous_code = previous_quarter_code(code)
    previous = int_value(quarters.get(previous_code), balance_row)
    flow = int_value(quarters.get(code), flow_row)
    days = fiscal_quarter_days(code)
    if current is None or previous is None or flow in {None, 0}:
        return None
    average_balance = (current + previous) / 2
    return MetricCalculation(
        average_balance / flow * days,
        [previous, current, flow, days],
        f"Average {balance_row} from {previous_code}/{code} divided by {flow_label} times fiscal days.",
    )


def net_trading_cycles(code: str, quarters: dict[str, Any]) -> MetricCalculation | None:
    """Calculate DSO plus DIO minus DPO using the same metric dispatcher."""
    dso = metric_calculation(code, "DSO", quarters)
    dio = metric_calculation(code, "DIO", quarters)
    dpo = metric_calculation(code, "DPO", quarters)
    if dso is None or dio is None or dpo is None:
        return None
    value = dso.value + dio.value - dpo.value
    return MetricCalculation(
        value,
        [round_tenth(dso.value), round_tenth(dio.value), round_tenth(dpo.value)],
        f"DSO {dso.value:.1f} + DIO {dio.value:.1f} - DPO {dpo.value:.1f}.",
    )


def int_value(quarter: Any, row: str) -> int | None:
    """Return an integer row value from a quarter-like object when present."""
    return int_or_none(value_dict(quarter).get(row))


def value_dict(quarter: Any) -> dict[str, Any]:
    """Normalize QuarterData or audit-dict inputs to a values dictionary."""
    if quarter is None:
        return {}
    if isinstance(quarter, QuarterData):
        return quarter.values
    return quarter.get("values", {})


def int_or_none(value: Any) -> int | None:
    """Accept integers only; blanks, floats, and strings are not metric inputs."""
    if isinstance(value, int):
        return value
    return None


def previous_year_code(code: str) -> str:
    """Return the same fiscal quarter in the prior fiscal year."""
    year, fiscal_quarter = quarter_sort_key(code)
    return quarter_code(fiscal_quarter, year - 1)


def previous_quarter_code(code: str) -> str:
    """Return the immediately preceding Siemens fiscal quarter code."""
    year, fiscal_quarter = quarter_sort_key(code)
    if fiscal_quarter == 1:
        return quarter_code(4, year - 1)
    return quarter_code(fiscal_quarter - 1, year)


def trailing_codes(code: str, count: int) -> list[str]:
    """Return a code followed by its prior fiscal quarters."""
    result = [code]
    while len(result) < count:
        result.append(previous_quarter_code(result[-1]))
    return result


def fiscal_quarter_days(code: str) -> int:
    """Return calendar-day count for the Siemens fiscal quarter represented by code."""
    year, fiscal_quarter = quarter_sort_key(code)
    if fiscal_quarter == 1:
        return (date(year - 1, 12, 31) - date(year - 1, 10, 1)).days + 1
    if fiscal_quarter == 2:
        return (date(year, 3, 31) - date(year, 1, 1)).days + 1
    if fiscal_quarter == 3:
        return (date(year, 6, 30) - date(year, 4, 1)).days + 1
    return (date(year, 9, 30) - date(year, 7, 1)).days + 1


def round_tenth(value: float) -> int:
    """Round a display value to one decimal place and store it as tenths."""
    return int(round(value * 10))
