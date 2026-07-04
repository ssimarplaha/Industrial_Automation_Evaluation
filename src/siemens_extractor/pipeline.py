from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from .audit import write_audit
from .balance_sheet import extract_balance_sheet
from .discovery import load_documents
from .income import extract_income_statement
from .metrics import calculate_metrics
from .models import QuarterData
from .periods import quarter_sort_key
from .segments import segment_parser_for
from .supplemental_balance import (
    apply_supplemental_balance_documents,
    load_supplemental_balance_documents,
)
from .validation import (
    add_other_segment_values,
    add_sample_reconciliation_warnings,
    apply_overrides,
    apply_yoy,
    validate_quarter,
)
from .verification import verify_outputs
from .writer import write_tsv


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract Siemens quarterly financials to TSV.")
    parser.add_argument("--input-dir", type=Path, default=Path("data"), help="Directory containing PDFs.")
    parser.add_argument("--output-dir", type=Path, default=Path("output"), help="Directory for TSV/audit output.")
    parser.add_argument(
        "--overrides",
        type=Path,
        default=None,
        help='Optional JSON file of manual overrides: {"Q109": {"Industry": 9351}}.',
    )
    return parser.parse_args()


def extract_all(input_dir: Path, overrides_path: Path | None = None) -> tuple[dict[str, QuarterData], dict[str, Any]]:
    documents, duplicates = load_documents(input_dir)
    if not documents:
        raise ValueError(f"No PDFs found in {input_dir}")
    supplemental_documents, supplemental_manifest_found = load_supplemental_balance_documents(input_dir)

    all_quarters: dict[str, QuarterData] = {}
    for document in documents:
        quarters = extract_income_statement(document)
        segment_parser_for(document.fiscal_year).extract(document, quarters)
        extract_balance_sheet(document, quarters)
        add_other_segment_values(quarters)
        for code, quarter_data in quarters.items():
            if code in all_quarters:
                raise ValueError(f"Duplicate quarter extracted from unique PDFs: {code}")
            all_quarters[code] = quarter_data

    balance_sheet_coverage = apply_supplemental_balance_documents(
        all_quarters,
        supplemental_documents,
        manifest_found=supplemental_manifest_found,
    )
    overrides_applied = apply_overrides(all_quarters, overrides_path)
    apply_yoy(all_quarters)
    calculate_metrics(all_quarters)
    for quarter_data in all_quarters.values():
        validate_quarter(quarter_data)
    sample_warnings = add_sample_reconciliation_warnings(all_quarters)
    metadata = {
        "processed_files": [document.path for document in documents],
        "duplicates": duplicates,
        "sample_warnings": sample_warnings,
        "overrides_applied": overrides_applied,
        "balance_sheet_coverage": balance_sheet_coverage,
        "columns": sorted(all_quarters, key=quarter_sort_key),
    }
    return all_quarters, metadata


def main() -> int:
    args = parse_args()
    input_dir = args.input_dir.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    quarters, metadata = extract_all(input_dir, args.overrides)
    tsv_path = output_dir / "siemens_financials_wide.tsv"
    audit_path = output_dir / "siemens_financials_audit.json"
    report_path = output_dir / "siemens_financials_verification_report.json"
    write_tsv(tsv_path, quarters)
    write_audit(
        audit_path,
        quarters,
        metadata["processed_files"],
        metadata["duplicates"],
        metadata["sample_warnings"],
        metadata["overrides_applied"],
        metadata["balance_sheet_coverage"],
    )
    report = verify_outputs(tsv_path, audit_path, input_dir, report_path)

    print(f"Wrote {tsv_path}")
    print(f"Wrote {audit_path}")
    print(f"Wrote {report_path}")
    if metadata["duplicates"]:
        print(f"Skipped {len(metadata['duplicates'])} duplicate PDF(s)")
    if metadata["sample_warnings"]:
        print(f"Recorded {len(metadata['sample_warnings'])} sample reconciliation warning(s)")
    if not report["metadata"]["passed"]:
        print(f"Verification failed with {len(report['issues'])} issue(s)")
        return 1
    return 0
