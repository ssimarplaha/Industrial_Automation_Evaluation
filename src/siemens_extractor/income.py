from __future__ import annotations

from .config import INCOME_PATTERNS
from .models import PdfDocument, QuarterData, SourceRecord
from .numbers import clean_label, int_tokens
from .periods import quarter_code


PARSER_FAMILY = "income_statement"


def find_income_page(pages: list[str]) -> tuple[int, str]:
    fallback: tuple[int, str] | None = None
    for index, text in enumerate(pages, start=1):
        lines = [line.strip() for line in text.splitlines()]
        if any(_is_income_statement_heading(line) for line in lines):
            return index, text
        if "STATEMENTS OF INCOME" in text.upper() and "\nRevenue " in text and "\nNet income" in text:
            fallback = fallback or (index, text)
    if fallback:
        return fallback
    raise ValueError("Could not find consolidated statements of income page")


def _is_income_statement_heading(line: str) -> bool:
    upper = line.upper()
    return upper in {
        "CONSOLIDATED STATEMENTS OF INCOME",
        "CONDENSED CONSOLIDATED STATEMENTS OF INCOME",
    } or upper.startswith("CONSOLIDATED STATEMENTS OF INCOME (") or upper.startswith(
        "CONDENSED CONSOLIDATED STATEMENTS OF INCOME ("
    )


def select_first_two(values: list[int], label: str, source_pdf: str) -> list[int]:
    if len(values) < 2:
        raise ValueError(f"{source_pdf}: expected at least two values for {label!r}, got {values}")
    return values[:2]


def native_source(
    document: PdfDocument,
    page_number: int,
    raw_line: str,
    values: list[int],
    row: str,
    value: int,
) -> SourceRecord:
    return SourceRecord(
        source_pdf=document.path.name,
        page=page_number,
        parser_family=PARSER_FAMILY,
        raw_line=raw_line.strip(),
        raw_values=values,
        normalized_row=row,
        normalized_value=value,
        source_type="native",
    )


def calculated_source(
    document: PdfDocument,
    page_number: int,
    raw_line: str,
    values: list[int],
    row: str,
    value: int,
    note: str = "",
) -> SourceRecord:
    return SourceRecord(
        source_pdf=document.path.name,
        page=page_number,
        parser_family=PARSER_FAMILY,
        raw_line=raw_line,
        raw_values=values,
        normalized_row=row,
        normalized_value=value,
        source_type="calculated",
        note=note,
    )


def extract_income_statement(document: PdfDocument) -> dict[str, QuarterData]:
    page_number, text = find_income_page(document.pages)
    current_code = quarter_code(document.quarter, document.fiscal_year)
    prior_code = quarter_code(document.quarter, document.fiscal_year - 1)
    quarters = {
        current_code: QuarterData(current_code, document.fiscal_year, document.quarter, document.path.name),
        prior_code: QuarterData(prior_code, document.fiscal_year - 1, document.quarter, document.path.name),
    }

    raw_by_code: dict[str, dict[str, int]] = {current_code: {}, prior_code: {}}
    source_by_code: dict[str, dict[str, SourceRecord]] = {current_code: {}, prior_code: {}}
    stop = False
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("Attributable to:") or line.startswith("Basic earnings per share"):
            stop = True
        if stop:
            continue
        label = clean_label(line)
        values = int_tokens(line)
        if len(values) < 2:
            continue
        for row, pattern in INCOME_PATTERNS:
            if not pattern.search(label):
                continue
            current_value, prior_value = select_first_two(values, label, document.path.name)
            for code, value in [(current_code, current_value), (prior_code, prior_value)]:
                raw_by_code[code][row] = value
                source_by_code[code][row] = native_source(document, page_number, line, values, row, value)
            break

    for code, quarter_data in quarters.items():
        raw = raw_by_code[code]
        sources = source_by_code[code]
        if "OTHER_OPERATING_NET" in raw:
            raw["Other Income"] = raw["OTHER_OPERATING_NET"]
            raw["Operating Expenses"] = 0
            source = sources["OTHER_OPERATING_NET"]
            sources["Other Income"] = SourceRecord(
                source_pdf=source.source_pdf,
                page=source.page,
                parser_family=PARSER_FAMILY,
                raw_line=source.raw_line,
                raw_values=source.raw_values,
                normalized_row="Other Income",
                normalized_value=raw["Other Income"],
                source_type="native",
                note="Combined other operating income/expenses net line mapped to Other Income.",
            )
            sources["Operating Expenses"] = SourceRecord(
                source_pdf=source.source_pdf,
                page=source.page,
                parser_family=PARSER_FAMILY,
                raw_line=source.raw_line,
                raw_values=source.raw_values,
                normalized_row="Operating Expenses",
                normalized_value=0,
                source_type="calculated",
                note="Combined other operating income/expenses net line; Operating Expenses set to 0.",
            )

        cogs_raw = raw.get("COGS_RAW")
        if cogs_raw is not None:
            quarter_data.values["COGS"] = abs(cogs_raw)
            source = sources["COGS_RAW"]
            quarter_data.sources["COGS"] = SourceRecord(
                source_pdf=source.source_pdf,
                page=source.page,
                parser_family=PARSER_FAMILY,
                raw_line=source.raw_line,
                raw_values=source.raw_values,
                normalized_row="COGS",
                normalized_value=abs(cogs_raw),
                source_type="native",
                note="Displayed as a positive cost number.",
            )

        interest_income = raw.get("INTEREST_INCOME_RAW", 0)
        interest_expense = raw.get("INTEREST_EXPENSE_RAW", 0)
        other_financial = raw.get("OTHER_FINANCIAL_RAW", 0)
        net_financial = interest_income + interest_expense + other_financial
        quarter_data.raw_components["financial_income_expense"] = {
            "interest_income": interest_income,
            "interest_expense": interest_expense,
            "other_financial_income_expense": other_financial,
            "net_financial_income_expense": net_financial,
        }
        quarter_data.values["Interest Income"] = net_financial
        quarter_data.values["Interest Expense"] = 0
        quarter_data.values["Other Financial Income"] = 0
        quarter_data.sources["Interest Income"] = calculated_source(
            document,
            page_number,
            "Interest income + Interest expense + Other financial income (expense), net",
            [interest_income, interest_expense, other_financial],
            "Interest Income",
            net_financial,
            "Template row holds net financial income/expense.",
        )
        quarter_data.sources["Interest Expense"] = calculated_source(
            document,
            page_number,
            "Interest expense",
            [interest_expense],
            "Interest Expense",
            0,
            "True component preserved in raw_components; output fixed at 0 per template bridge.",
        )
        quarter_data.sources["Other Financial Income"] = calculated_source(
            document,
            page_number,
            "Other financial income (expense), net",
            [other_financial],
            "Other Financial Income",
            0,
            "True component preserved in raw_components; output fixed at 0 per template bridge.",
        )

        passthrough_rows = [
            "Total Revenue",
            "Gross Profit",
            "R&D",
            "SG&D",
            "Other Income",
            "Operating Expenses",
            "Income from Investment",
            "EBT",
            "Taxes",
            "Income From Continuous Operations",
            "Income From Dis-continued operations",
            "Net Income",
        ]
        for row in passthrough_rows:
            if row in raw:
                quarter_data.values[row] = raw[row]
                source = sources[row]
                source.normalized_row = row
                source.normalized_value = raw[row]
                quarter_data.sources[row] = source

        if "Income From Dis-continued operations" not in quarter_data.values:
            continuous = quarter_data.values.get("Income From Continuous Operations")
            net_income = quarter_data.values.get("Net Income")
            if isinstance(continuous, int) and isinstance(net_income, int):
                discontinued = net_income - continuous
                quarter_data.values["Income From Dis-continued operations"] = discontinued
                quarter_data.sources["Income From Dis-continued operations"] = calculated_source(
                    document,
                    page_number,
                    "Calculated: Net Income - Income From Continuous Operations",
                    [net_income, continuous],
                    "Income From Dis-continued operations",
                    discontinued,
                    "Discontinued operations row was not separately reported.",
                )

        required = [
            "Total Revenue",
            "COGS",
            "Gross Profit",
            "R&D",
            "SG&D",
            "Other Income",
            "Operating Expenses",
            "Income from Investment",
            "EBT",
            "Taxes",
            "Income From Continuous Operations",
            "Income From Dis-continued operations",
            "Net Income",
        ]
        missing = [row for row in required if row not in quarter_data.values]
        if missing:
            raise ValueError(f"{document.path.name} {code}: missing income rows: {missing}")

        quarter_data.values["Total Expenses"] = (
            int(quarter_data.values["R&D"])
            + int(quarter_data.values["SG&D"])
            + int(quarter_data.values["Other Income"])
            + int(quarter_data.values["Operating Expenses"])
        )
        quarter_data.values["EBIT"] = int(quarter_data.values["Gross Profit"]) + int(
            quarter_data.values["Total Expenses"]
        )
        quarter_data.sources["Total Expenses"] = calculated_source(
            document,
            page_number,
            "Calculated: R&D + SG&D + Other Income + Operating Expenses",
            [
                int(quarter_data.values["R&D"]),
                int(quarter_data.values["SG&D"]),
                int(quarter_data.values["Other Income"]),
                int(quarter_data.values["Operating Expenses"]),
            ],
            "Total Expenses",
            int(quarter_data.values["Total Expenses"]),
        )
        quarter_data.sources["EBIT"] = calculated_source(
            document,
            page_number,
            "Calculated: Gross Profit + Total Expenses",
            [int(quarter_data.values["Gross Profit"]), int(quarter_data.values["Total Expenses"])],
            "EBIT",
            int(quarter_data.values["EBIT"]),
        )

    return quarters
