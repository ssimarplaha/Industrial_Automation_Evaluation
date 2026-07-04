# Siemens Extractor Agent Guide

This repo extracts Siemens financial data from local PDFs into an Excel-pasteable TSV and a detailed audit JSON. Preserve extraction behavior unless the user explicitly asks for a data or mapping change.

## Hard Rules

- Keep public imports stable from `src/extract_siemens_financials.py`: `extract_all`, `int_tokens`, and `main`.
- Do not replace TSV with XLSX. TSV is the source of truth for v1.
- Do not edit PDFs under `data/` or hand-edit generated files under `output/` unless regenerating outputs through the extractor.
- Keep maintained source, tests, scripts, and agent docs at or below 650 lines. The emergency ceiling is 675 lines and should not be used for normal work.
- Generated output and PDF files are excluded from the line-count policy.

## Working Style

- Prefer small parser-specific changes over broad rewrites.
- When a PDF format changes, inspect extracted text first and add focused parser coverage.
- Every extracted or calculated number should remain explainable through the audit JSON.
- Reconstructed segment values must stay flagged as `source_type="reconstructed"`.

## Verification

Use the bundled Python runtime if local Python does not have `pdfplumber`:

```bash
/Users/simarsingh/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m unittest discover -s src
```

Regenerate outputs with:

```bash
/Users/simarsingh/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 src/extract_siemens_financials.py
```
