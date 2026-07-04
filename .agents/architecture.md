# Architecture

The extractor is a Python package under `src/siemens_extractor/` with a thin compatibility wrapper at `src/extract_siemens_financials.py`.

## Data Flow

1. `discovery.py` finds PDFs in `data/`, deduplicates by SHA-256, detects fiscal year and quarter, and extracts text once with `pdfplumber`.
2. `income.py` extracts consolidated income statement rows for the current and prior-year quarter.
3. `segments/` routes each fiscal year to the correct segment parser:
   - `legacy_sector.py` for 2010-2014.
   - `division_2016.py` for 2016.
   - `division_2018.py` for 2018.
   - `modern_2020.py` for 2020-2026.
4. `balance_sheet.py` extracts statement-of-financial-position rows and hidden bridge components.
5. `metrics.py` calculates audited growth, liquidity, working-capital, and leverage rows.
6. `validation.py` calculates residual rows, Y/Y rows, expenses, EBIT, overrides, and accounting bridge checks.
7. `yearly.py` derives complete fiscal-year columns from audited quarter columns.
8. `writer.py` writes the Excel-pasteable TSV and derived two-sheet workbook.
9. `audit.py` writes source and validation evidence for every quarter and year.

## Ownership Boundaries

- Parser code should stay inside `segments/` unless it is truly shared.
- Template row order and segment mappings belong in `config.py`.
- Quarter/source dataclasses belong in `models.py`.
- Public CLI behavior belongs in `pipeline.py`.
- Balance-sheet and metric logic belong in their dedicated modules, not in the segment parsers.
- Yearly aggregation belongs in `yearly.py`; it must derive from audited quarterly data, not new PDF parsing.

## Split Guidance

If a file approaches 650 lines, split by behavior:

- `income.py`: page detection, row parsing, normalization.
- `validation.py`: calculations, overrides, accounting checks.
- `config.py`: output template, income patterns, segment mappings.
