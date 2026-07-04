# Siemens Extractor Agent Entrypoint

This repository extracts Siemens financial data from local PDFs into a
paste-ready TSV, derived workbook, audit JSON, and verification report. Use
this file as the root router only; `.agents/AGENTS.md` is the source of truth
for Siemens extractor rules.

Siemens-specific guidance overrides reusable engineering standards whenever
they conflict.

## Reading Order

Before important edits, read the affected contract in this order:

1. `.agents/AGENTS.md` for hard Siemens extractor rules.
2. `.agents/architecture.md` for package ownership and data flow.
3. `.agents/workflows/extraction.md` for current test and regeneration
   commands.
4. `.agents/checklists/refactor_checklist.md` before finishing refactors.
5. Existing tests and implementation files for the touched behavior.
6. Reusable standards under `.agents/` for general engineering discipline.

The broad standards are subordinate references. Do not follow generic commands
there when they differ from the Siemens workflow.

## Current Siemens Contracts

- PDFs under `data/` are local source material and must not be edited.
- Generated files under `output/` must change only by running the extractor.
- `output/siemens_financials_wide.tsv` is the source-of-truth export for v1.
- `output/siemens_financials.xlsx` is a derived workbook with `Quarterly` and
  `Yearly` sheets; it must not replace the TSV source-of-truth contract.
- `output/siemens_financials_audit.json` must explain every exported non-empty
  TSV and workbook value.
- `output/siemens_financials_verification_report.json` must pass after outputs
  are regenerated.
- Balance-sheet blanks are valid when the source PDF does not contain that
  quarter's native value.
- Reconstructed values must remain explicitly flagged in audit evidence.

## Current Gate

Run the repo test gate with the bundled runtime:

```bash
/Users/simarsingh/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m unittest discover -s src
```

Regenerate outputs with:

```bash
/Users/simarsingh/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 src/extract_siemens_financials.py
```

Future tooling improvements include Ruff, mypy, pytest, dependency audit,
packaging smoke checks, and a single project-wide quality command unless this
repo adds them deliberately.

## Reusable Standards

- `.agents/principal-engineering-standard.md`
- `.agents/python-backend-standard.md`
- `.agents/testing-quality-gate.md`
- `.agents/review-checklist.md`
- `.agents/docs-decisions.md`
- `.agents/security-secrets.md`
- `.agents/operations-reliability.md`
