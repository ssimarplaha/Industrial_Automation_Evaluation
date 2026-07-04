from __future__ import annotations

import re

from .models import PdfDocument, QuarterData, SourceRecord
from .numbers import int_tokens
from .periods import quarter_code


PARSER_FAMILY = "balance_sheet"

CONTRACT_ASSETS = "Contract Assets"
CONTRACT_LIABILITIES = "Contract Liabilities"
NONCONTROLLING_INTERESTS = "Non-controlling interests"
TOTAL_EQUITY = "Total Equity"

BALANCE_ROW_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("Other Current Financial Assets", re.compile(r"^Other current financial assets\b", re.I)),
    ("Other Current Financial Liabilities", re.compile(r"^Other current financial liabilities\b", re.I)),
    ("L+S/E", re.compile(r"^Total liabilities and equity\b", re.I)),
    ("S/E", re.compile(r"^Total equity attributable to shareholders of Siemens AG\b", re.I)),
    ("Cash & Cash Equivalets", re.compile(r"^Cash and cash equivalents\b", re.I)),
    ("Available-for-sale financial assets", re.compile(r"^Available-for-sale financial assets\b", re.I)),
    ("Trade and OR", re.compile(r"^Trade and other receivables\b", re.I)),
    (CONTRACT_ASSETS, re.compile(r"^Contract assets\b", re.I)),
    ("Inventories", re.compile(r"^Inventories\b", re.I)),
    ("Income Tax Receivables", re.compile(r"^(Current income tax assets|Income tax receivables)\b", re.I)),
    ("Other Current Assets", re.compile(r"^Other current assets\b", re.I)),
    ("Assetes classifies as held for disposal", re.compile(r"^Assets classified as held for disposal\b", re.I)),
    ("Total Current Assets (TCA)", re.compile(r"^Total current assets\b", re.I)),
    ("Goodwill", re.compile(r"^Goodwill\b", re.I)),
    ("Other intangible assets", re.compile(r"^Other intangible assets\b", re.I)),
    ("PP&E", re.compile(r"^Property, plant and equipment\b", re.I)),
    (
        "Investments accounted for using equity method",
        re.compile(r"^Investments accounted for using the equity method\b", re.I),
    ),
    ("Other Financial Assets", re.compile(r"^Other financial assets\b", re.I)),
    ("Deferred Tax Assets", re.compile(r"^Deferred tax assets\b", re.I)),
    ("Other Assets", re.compile(r"^Other assets\b", re.I)),
    ("Total Assets", re.compile(r"^Total assets\b", re.I)),
    ("Short-Term Debt", re.compile(r"^Short-term debt and current maturities of long-term debt\b", re.I)),
    ("Trade Payables", re.compile(r"^Trade payables\b", re.I)),
    (CONTRACT_LIABILITIES, re.compile(r"^Contract liabilities\b", re.I)),
    ("Current Provisions", re.compile(r"^Current provisions\b", re.I)),
    ("Income Tax Payable", re.compile(r"^(Current income tax liabilities|Income tax payables)\b", re.I)),
    ("Other Current Liabilities", re.compile(r"^Other current liabilities\b", re.I)),
    (
        "Liabilities associated with assets classified as held",
        re.compile(r"^Liabilities associated with assets classified as held for disposal\b", re.I),
    ),
    ("Total Current Liabilities", re.compile(r"^Total current liabilities\b", re.I)),
    ("Long-Term Debt", re.compile(r"^Long-term debt\b", re.I)),
    (
        "Pension Plans and similar commitments",
        re.compile(
            r"^(Pension plans and similar commitments|Post-employment benefits|"
            r"Provisions for pensions and similar obligations)\b",
            re.I,
        ),
    ),
    ("Deferred Tax Liabilities", re.compile(r"^Deferred tax liabilities\b", re.I)),
    ("Provisions", re.compile(r"^Provisions\b", re.I)),
    ("Other Financial Liabilities", re.compile(r"^Other financial liabilities\b", re.I)),
    ("Other Liabilities", re.compile(r"^Other liabilities\b", re.I)),
    ("Total Liabilities", re.compile(r"^Total liabilities\b", re.I)),
    (NONCONTROLLING_INTERESTS, re.compile(r"^Non-controlling interests\b", re.I)),
    (TOTAL_EQUITY, re.compile(r"^Total equity\b", re.I)),
]


def extract_balance_sheet(document: PdfDocument, quarters: dict[str, QuarterData]) -> None:
    page_number, text = find_balance_sheet_page(document.pages)
    parsed_rows = parse_balance_rows(text)
    current_code = quarter_code(document.quarter, document.fiscal_year)
    assign_balance_values(document, quarters, parsed_rows, current_code, page_number, 0)
    if document.quarter == 4:
        prior_code = quarter_code(4, document.fiscal_year - 1)
        assign_balance_values(document, quarters, parsed_rows, prior_code, page_number, 1)


def find_balance_sheet_page(pages: list[str]) -> tuple[int, str]:
    for index, text in enumerate(pages, start=1):
        lower = text.lower()
        if (
            "cash and cash equivalents" in lower
            and "total assets" in lower
            and "total liabilities and equity" in lower
        ):
            return index, text
    raise ValueError("Could not find consolidated statements of financial position page")


def parse_balance_rows(text: str) -> dict[str, tuple[str, list[int]]]:
    rows: dict[str, tuple[str, list[int]]] = {}
    for raw_line in text.splitlines():
        line = " ".join(raw_line.strip().split())
        if not line:
            continue
        values = int_tokens(line)
        if not values:
            continue
        for row, pattern in BALANCE_ROW_PATTERNS:
            if pattern.search(line):
                rows.setdefault(row, (line, values))
                break
    return rows


def assign_balance_values(
    document: PdfDocument,
    quarters: dict[str, QuarterData],
    parsed_rows: dict[str, tuple[str, list[int]]],
    code: str,
    page_number: int,
    value_index: int,
) -> None:
    quarter = quarters.get(code)
    if quarter is None:
        return
    hidden_components: dict[str, int] = {}
    for row, (raw_line, values) in parsed_rows.items():
        if value_index >= len(values):
            continue
        value = values[value_index]
        quarter.values[row] = value
        quarter.sources[row] = SourceRecord(
            source_pdf=document.path.name,
            page=page_number,
            parser_family=PARSER_FAMILY,
            raw_line=raw_line,
            raw_values=values,
            normalized_row=row,
            normalized_value=value,
            source_type="native",
            note=f"Balance sheet column {value_index + 1} selected for {code}.",
        )
        if row in {CONTRACT_ASSETS, CONTRACT_LIABILITIES, NONCONTROLLING_INTERESTS, TOTAL_EQUITY}:
            hidden_components[row] = value
    if hidden_components:
        quarter.raw_components.setdefault("balance_sheet", {}).update(hidden_components)
