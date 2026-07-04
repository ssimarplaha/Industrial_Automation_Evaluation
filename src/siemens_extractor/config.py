"""Static row order, parser patterns, and segment mappings for the TSV contract."""

from __future__ import annotations

import re


INCOME_OUTPUT_ROWS = [
    "Digital Industries",
    "Smart Infrastructure",
    "Mobility",
    "Siemens Healthineers",
    "Industrial Business",
    "Siemens Financial Services (SFS)",
    "Reconciliation to Consolidated Financial Statements",
    "Siemens (continuing operations)",
    None,
    "Digital Industries Y/Y%",
    "Smart Infrastructure Y/Y%",
    "Mobility Y/Y%",
    "Siemens Healthineers Y/Y%",
    "Industrial Business Y/Y%",
    "Siemens Financial Services (SFS) Y/Y%",
    "Reconciliation to Consolidated Financial Statements Y/Y%",
    "Revenue Y/Y%",
    None,
    "COGS",
    "Gross Profit",
    None,
    "R&D",
    "SG&D",
    "Other Income",
    "Operating Expenses",
    "Total Expenses",
    "EBIT",
    "Income from Investment",
    "Interest Income",
    "Interest Expense",
    "Other Financial Income",
    "EBT",
    None,
    "Taxes",
    "Income From Continuous Operations",
    "Income From Dis-continued operations",
    "Net Income",
]

BALANCE_OUTPUT_ROWS = [
    "Assets",
    "Cash & Cash Equivalets",
    "Available-for-sale financial assets",
    "Trade and OR",
    "Other Current Financial Assets",
    "Inventories",
    "Income Tax Receivables",
    "Other Current Assets",
    "Assetes classifies as held for disposal",
    "Total Current Assets (TCA)",
    "Goodwill",
    "Other intangible assets",
    "PP&E",
    "Investments accounted for using equity method",
    "Other Financial Assets",
    "Deferred Tax Assets",
    "Other Assets",
    "Total Assets",
    None,
    "Liabilities",
    "Short-Term Debt",
    "Trade Payables",
    "Other Current Financial Liabilities",
    "Current Provisions",
    "Income Tax Payable",
    "Other Current Liabilities",
    "Liabilities associated with assets classified as held",
    "Total Current Liabilities",
    "Long-Term Debt",
    "Pension Plans and similar commitments",
    "Deferred Tax Liabilities",
    "Provisions",
    "Other Financial Liabilities",
    "Other Liabilities",
    "Total Liabilities",
    None,
    "S/E",
    "L+S/E",
]

METRIC_OUTPUT_ROWS = [
    "Current Assets Growth %",
    "Assets Growth %",
    "Total Liabilities Growth Rate %",
    "Liabilites Growth %",
    "Lt Debt as of Revenue %",
    "Quick Ratio",
    "Current Ratio",
    "DSO",
    "DIO",
    "DPO",
    "Net Trading Cycles",
    "Debt Ratio",
    "SE Growth %",
]

OUTPUT_ROWS = INCOME_OUTPUT_ROWS + [None] + BALANCE_OUTPUT_ROWS + [None] + METRIC_OUTPUT_ROWS

SEGMENT_ROWS = ["Industry", "Energy", "Healthcare", "Other", "Total Revenue"]

YY_ROWS = {
    "Digital Industries Y/Y%": "Digital Industries",
    "Smart Infrastructure Y/Y%": "Smart Infrastructure",
    "Mobility Y/Y%": "Mobility",
    "Siemens Healthineers Y/Y%": "Siemens Healthineers",
    "Industrial Business Y/Y%": "Industrial Business",
    "Siemens Financial Services (SFS) Y/Y%": "Siemens Financial Services (SFS)",
    "Reconciliation to Consolidated Financial Statements Y/Y%": (
        "Reconciliation to Consolidated Financial Statements"
    ),
    "Revenue Y/Y%": "Siemens (continuing operations)",
}

PERCENT_ROWS = set(YY_ROWS) | {
    "Current Assets Growth %",
    "Assets Growth %",
    "Total Liabilities Growth Rate %",
    "Liabilites Growth %",
    "Lt Debt as of Revenue %",
    "SE Growth %",
}

RATIO_ROWS = {"Quick Ratio", "Current Ratio", "Debt Ratio"}
DAYS_ROWS = {"DSO", "DIO", "DPO", "Net Trading Cycles"}

INCOME_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("Total Revenue", re.compile(r"^Revenue\b", re.I)),
    ("COGS_RAW", re.compile(r"^(Cost of goods sold and services rendered|Cost of sales)\b", re.I)),
    ("Gross Profit", re.compile(r"^Gross profit\b", re.I)),
    ("R&D", re.compile(r"^Research and development expenses\b", re.I)),
    (
        "SG&D",
        re.compile(
            r"^(Marketing, selling and general administrative expenses|Selling and general administrative expenses)\b",
            re.I,
        ),
    ),
    ("OTHER_OPERATING_NET", re.compile(r"^Other operating income \(expenses\), net\b", re.I)),
    ("Other Income", re.compile(r"^Other operating income\b", re.I)),
    ("Operating Expenses", re.compile(r"^Other operating expense(?:s)?\b", re.I)),
    (
        "Income from Investment",
        re.compile(
            r"^(Income \(loss\)|Income|Loss) from investments accounted for using the equity method, net\b",
            re.I,
        ),
    ),
    ("INTEREST_INCOME_RAW", re.compile(r"^Interest income\b", re.I)),
    ("INTEREST_EXPENSE_RAW", re.compile(r"^Interest expense(?:s)?\b", re.I)),
    ("OTHER_FINANCIAL_RAW", re.compile(r"^Other financial income \(expense(?:s)?\), net\b", re.I)),
    (
        "EBT",
        re.compile(r"^Income (?:\(loss\) )?from continuing operations before income taxes\b", re.I),
    ),
    ("Taxes", re.compile(r"^Income tax(?:es| expenses)\b", re.I)),
    (
        "Income From Continuous Operations",
        re.compile(r"^Income (?:\(loss\) )?from continuing operations\b", re.I),
    ),
    (
        "Income From Dis-continued operations",
        re.compile(r"^(Income \(loss\)|Income|Loss) from discontinued operations, net of income taxes\b", re.I),
    ),
    ("Net Income", re.compile(r"^Net income(?: \(loss\))?\b", re.I)),
]

OLD_SECTOR_PATTERNS = {
    "Industry": re.compile(r"\bIndustry Sector\b", re.I),
    "Energy": re.compile(r"\bEnergy Sector\b", re.I),
    "Healthcare": re.compile(r"\bHealthcare Sector\b", re.I),
}

DIVISION_TO_BUCKET_2016 = {
    "Power and Gas": "Energy",
    "Wind Power and Renewables": "Energy",
    "Energy Management": "Energy",
    "Building Technologies": "Industry",
    "Mobility": "Industry",
    "Digital Factory": "Industry",
    "Process Industries and Drives": "Industry",
    "Healthcare": "Healthcare",
    "Healthineers": "Healthcare",
}

DIVISION_TO_BUCKET_2018 = {
    "Power and Gas": "Energy",
    "Energy Management": "Energy",
    "Siemens Gamesa Renewable Energy": "Energy",
    "Building Technologies": "Industry",
    "Mobility": "Industry",
    "Digital Factory": "Industry",
    "Process Industries and Drives": "Industry",
    "Healthineers": "Healthcare",
    "Siemens Healthineers": "Healthcare",
}

MODERN_TO_BUCKET = {
    "Digital Industries": "Industry",
    "Smart Infrastructure": "Industry",
    "Mobility": "Industry",
    "Portfolio Companies": "Industry",
    "Gas and Power": "Energy",
    "Siemens Gamesa Renewable Energy": "Energy",
    "Siemens Healthineers": "Healthcare",
}

SAMPLE_EXPECTATIONS = {
    "Q109": {
        "Industry": 9351,
        "Energy": 6232,
        "Healthcare": 2936,
        "Other": 1115,
        "Total Revenue": 19634,
        "COGS": 13994,
        "Gross Profit": 5640,
        "EBT": 1735,
        "Net Income": 1230,
    }
}
