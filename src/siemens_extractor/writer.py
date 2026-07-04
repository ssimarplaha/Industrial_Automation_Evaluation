from __future__ import annotations

from pathlib import Path

from .config import DAYS_ROWS, OUTPUT_ROWS, PERCENT_ROWS, RATIO_ROWS
from .models import QuarterData
from .periods import quarter_sort_key


def format_cell(value: int | float | str | None, row: str | None = None) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        if row in RATIO_ROWS:
            return f"{value:.2f}"
        if row in DAYS_ROWS:
            return f"{value:.1f}"
        if row in PERCENT_ROWS or row is None:
            return f"{value:.1%}"
        return f"{value:.1f}"
    if isinstance(value, int):
        return f"{value:,}"
    return str(value)


def write_tsv(path: Path, quarters: dict[str, QuarterData]) -> None:
    columns = sorted(quarters, key=quarter_sort_key)
    lines = ["Financial Years\t" + "\t".join(columns)]
    for row in OUTPUT_ROWS:
        if row is None:
            lines.append("\t".join([""] * (len(columns) + 1)))
            continue
        cells = [row] + [format_cell(quarters[column].values.get(row), row) for column in columns]
        lines.append("\t".join(cells))
    path.write_text("\n".join(lines) + "\n")
