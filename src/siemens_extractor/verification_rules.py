"""Pure rules used to replay calculated audit values during verification."""

from __future__ import annotations

from typing import Any

from .config import METRIC_OUTPUT_ROWS, YY_ROWS
from .metrics import expected_metric_value
from .periods import quarter_code, quarter_sort_key


class Unknown:
    """Sentinel for calculated rows that have no registered replay rule."""

    pass


UNKNOWN = Unknown()


def expected_calculated_value(code: str, row: str, source: dict[str, Any], quarters: dict[str, Any]) -> Any:
    """Return the expected value for one calculated audit source."""
    values = quarters[code]["values"]
    raw_values = source.get("raw_values", [])
    raw_line = str(source.get("raw_line") or "")

    if row in METRIC_OUTPUT_ROWS:
        return expected_metric_value(code, row, quarters)
    if row == "Other":
        return int(values["Total Revenue"]) - int(values["Industry"]) - int(values["Energy"]) - int(
            values["Healthcare"]
        )
    if row == "Total Expenses":
        return int(values["R&D"]) + int(values["SG&D"]) + int(values["Other Income"]) + int(
            values["Operating Expenses"]
        )
    if row == "EBIT":
        return int(values["Gross Profit"]) + int(values["Total Expenses"])
    if row == "Interest Income":
        return sum(int(value) for value in raw_values)
    if row in {"Interest Expense", "Other Financial Income"}:
        return 0
    if row == "Operating Expenses" and "Combined other operating income/expenses net line" in source.get("note", ""):
        return 0
    if row == "Income From Dis-continued operations":
        return int(values["Net Income"]) - int(values["Income From Continuous Operations"])
    if row.endswith("Y/Y%"):
        return expected_yoy_value(code, row, quarters)
    if raw_line == "Calculated: no explicit segment reported":
        return 0
    return UNKNOWN


def expected_yoy_value(code: str, row: str, quarters: dict[str, Any]) -> Any:
    """Recalculate a Y/Y row from the current and prior-year audit values."""
    source_row = YY_ROWS.get(row)
    if source_row is None:
        return UNKNOWN
    year, fiscal_quarter = quarter_sort_key(code)
    previous_code = quarter_code(fiscal_quarter, year - 1)
    previous = quarters.get(previous_code)
    if previous is None:
        return None
    current_values = quarters[code]["values"]
    previous_values = previous["values"]
    if source_row not in current_values or source_row not in previous_values:
        return None
    previous_value = int(previous_values[source_row])
    if previous_value == 0:
        return None
    return int(current_values[source_row]) / previous_value - 1


def calculated_values_equal(expected: Any, actual: Any) -> bool:
    """Compare calculated values using tight tolerance for floats."""
    if expected is None:
        return actual is None
    if isinstance(expected, float) or isinstance(actual, float):
        return abs(float(expected) - float(actual)) < 0.0000000001
    return expected == actual
