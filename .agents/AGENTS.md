# Siemens Extractor Agent Guide

This file is the source of truth for Siemens extractor work. Reusable
engineering standards in this folder are subordinate when they conflict with
this repo's TSV, audit, PDF, verification, or runtime-command contracts.

This repo extracts Siemens financial data from local PDFs into an
Excel-pasteable TSV, detailed audit JSON, and verification report. Preserve
extraction behavior unless the user explicitly asks for a data or mapping
change.

## Hard Rules

- Keep public imports stable from `src/extract_siemens_financials.py`: `extract_all`, `int_tokens`, and `main`.
- Do not replace TSV with XLSX. `output/siemens_financials_wide.tsv` is the source of truth for v1.
- Do not edit PDFs under `data/`.
- Do not hand-edit generated files under `output/`; change them only by regenerating through the extractor.
- `output/siemens_financials_audit.json` must explain every exported non-empty TSV value.
- `output/siemens_financials_verification_report.json` must report a pass after regenerated outputs.
- Balance-sheet blanks are valid when the source PDF does not contain that quarter's native value.
- Reconstructed values must stay explicitly flagged in audit evidence.
- Keep maintained source, tests, scripts, and agent docs at or below 650 lines. The emergency ceiling is 675 lines and should not be used for normal work.
- Generated output and PDF files are excluded from the line-count policy.

## Working Style

- Prefer small parser-specific changes over broad rewrites.
- When a PDF format changes, inspect extracted text first and add focused parser coverage.
- Every extracted or calculated number should remain explainable through the audit JSON.
- Treat local PDFs plus documented parser rules as the correctness boundary unless the user asks for external source comparison.

## Verification

Use the bundled Python runtime if local Python does not have `pdfplumber`:

```bash
/Users/simarsingh/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m unittest discover -s src
```

Regenerate outputs with:

```bash
/Users/simarsingh/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 src/extract_siemens_financials.py
```
