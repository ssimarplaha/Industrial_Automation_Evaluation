# Extraction Workflow

Use this workflow for parser, validation, TSV, or audit changes.

## Run Tests

```bash
/Users/simarsingh/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m unittest discover -s src
```

The system Python may not include `pdfplumber`; the bundled runtime does.

## Regenerate Outputs

```bash
/Users/simarsingh/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 src/extract_siemens_financials.py
```

Expected output files:

- `output/siemens_financials_wide.tsv`
- `output/siemens_financials.xlsx`
- `output/siemens_financials_audit.json`
- `output/siemens_financials_verification_report.json`

## Spot Checks

- Audit metadata should report 34 processed unique PDFs and 1 skipped duplicate.
- Output columns should start at `Q109` and end at `Q226`.
- Workbook sheets should be exactly `Quarterly` and `Yearly`.
- Yearly columns should include only complete fiscal years.
- Reconstructed segment values should be flagged in audit JSON.
- Verification report metadata should report `"passed": true`.
