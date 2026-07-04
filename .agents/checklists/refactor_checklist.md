# Refactor Checklist

Use this before finishing codebase refactors.

- Public imports from `extract_siemens_financials` still work.
- No maintained source, test, script, or agent doc file exceeds 650 lines.
- Generated outputs and PDFs are not counted by the LOC policy.
- Parser changes have representative golden tests.
- Audit fields still explain native, calculated, reconstructed, and override values.
- TSV row order and blank separator rows still match `OUTPUT_ROWS`.
- Full test suite passes with the bundled Python runtime.
- Outputs are regenerated only when extraction behavior changes.
