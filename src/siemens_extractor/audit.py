from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import QuarterData, SourceRecord
from .periods import quarter_sort_key


def source_to_dict(source: SourceRecord) -> dict[str, Any]:
    return {
        "source_pdf": source.source_pdf,
        "page": source.page,
        "parser_family": source.parser_family,
        "raw_line": source.raw_line,
        "raw_values": source.raw_values,
        "normalized_row": source.normalized_row,
        "normalized_value": source.normalized_value,
        "source_type": source.source_type,
        "note": source.note,
    }


def write_audit(
    path: Path,
    quarters: dict[str, QuarterData],
    processed_files: list[Path],
    duplicates: list[dict[str, str]],
    sample_warnings: list[str],
    overrides_applied: list[str],
) -> None:
    payload = {
        "metadata": {
            "processed_files": [path.name for path in processed_files],
            "duplicates_skipped": duplicates,
            "columns": sorted(quarters, key=quarter_sort_key),
            "sample_reconciliation_warnings": sample_warnings,
            "overrides_applied": overrides_applied,
        },
        "quarters": {
            code: {
                "source_pdf": quarter.source_pdf,
                "fiscal_year": quarter.fiscal_year,
                "quarter": quarter.quarter,
                "values": quarter.values,
                "sources": {row: source_to_dict(source) for row, source in sorted(quarter.sources.items())},
                "raw_components": quarter.raw_components,
                "validations": quarter.validations,
                "warnings": quarter.warnings,
            }
            for code, quarter in sorted(quarters.items(), key=lambda item: quarter_sort_key(item[0]))
        },
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
