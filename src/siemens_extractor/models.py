from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal


Value = int | float | str | None
SourceType = Literal["native", "calculated", "reconstructed", "override"]


@dataclass(frozen=True)
class PdfDocument:
    path: Path
    sha256: str
    fiscal_year: int
    quarter: int
    code: str
    pages: list[str]


@dataclass
class SourceRecord:
    source_pdf: str
    page: int
    parser_family: str
    raw_line: str
    raw_values: list[int]
    normalized_row: str
    normalized_value: Value
    source_type: SourceType
    note: str = ""


@dataclass
class QuarterData:
    code: str
    fiscal_year: int
    quarter: int
    source_pdf: str
    values: dict[str, Value] = field(default_factory=dict)
    sources: dict[str, SourceRecord] = field(default_factory=dict)
    validations: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    raw_components: dict[str, dict[str, int]] = field(default_factory=dict)
