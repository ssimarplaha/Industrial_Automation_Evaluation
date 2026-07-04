import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from extract_siemens_financials import extract_all, int_tokens
from siemens_extractor.audit import write_audit
from siemens_extractor.config import OUTPUT_ROWS
from siemens_extractor.models import PdfDocument, QuarterData, SourceRecord
from siemens_extractor.supplemental_balance import (
    SupplementalBalanceDocument,
    apply_supplemental_balance_documents,
)
from siemens_extractor.verification import verify_outputs
from siemens_extractor.writer import format_cell, write_tsv


class SiemensExtractorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.quarters, cls.metadata = extract_all(Path("data"))

    def test_data_layout_is_used(self):
        self.assertEqual(len(self.metadata["processed_files"]), 34)
        self.assertEqual(len(self.quarters), 68)

    def test_token_parser_ignores_parenthesized_percentages(self):
        line = (
            "Industry Sector.................... 8,249 9,776 (16)% (14)% (2)% 0% "
            "8,070 9,288 (13)% (11)% (2)% 0% 911 934 (2)% 11.3% 10.1% 9-13%"
        )
        self.assertEqual(int_tokens(line), [8249, 9776, 8070, 9288, 911, 934])

    def test_duplicate_pdf_is_skipped(self):
        duplicates = self.metadata["duplicates"]
        self.assertEqual(len(duplicates), 1)
        self.assertEqual(duplicates[0]["duplicate_pdf"], "2010-q4-financial-statement-e.pdf")

    def test_q109_matches_income_statement_bridge(self):
        q109 = self.quarters["Q109"].values
        self.assertEqual(q109["Total Revenue"], 19634)
        self.assertEqual(q109["COGS"], 13994)
        self.assertEqual(q109["Gross Profit"], 5640)
        self.assertEqual(q109["Interest Income"], -308)
        self.assertEqual(q109["EBT"], 1735)
        self.assertEqual(q109["Net Income"], 1230)

    def test_q109_pdf_segment_source_is_retained(self):
        q109 = self.quarters["Q109"].values
        self.assertEqual(q109["Industry"], 9288)
        self.assertEqual(q109["Energy"], 6232)
        self.assertEqual(q109["Healthcare"], 2936)
        self.assertEqual(q109["Other"], 1178)

    def test_q410_uses_quarter_not_fiscal_year_columns(self):
        q410 = self.quarters["Q410"].values
        self.assertEqual(q410["Total Revenue"], 21229)
        self.assertEqual(q410["Industry"], 9780)
        self.assertEqual(q410["Energy"], 7260)
        self.assertEqual(q410["Healthcare"], 3413)

    def test_q416_uses_2016_reconstructed_mapping(self):
        q416 = self.quarters["Q416"]
        self.assertEqual(q416.values["Industry"], 8996)
        self.assertEqual(q416.values["Energy"], 9715)
        self.assertEqual(q416.values["Healthcare"], 3698)
        self.assertTrue(any("reconstructed" in warning for warning in q416.warnings))
        self.assertEqual(q416.sources["Industry"].source_type, "reconstructed")

    def test_q418_uses_2018_transition_mapping(self):
        q418 = self.quarters["Q418"]
        self.assertEqual(q418.values["Industry"], 10050)
        self.assertEqual(q418.values["Energy"], 9399)
        self.assertEqual(q418.values["Healthcare"], 3703)
        self.assertEqual(q418.values["Other"], -546)
        self.assertEqual(q418.sources["Energy"].source_type, "reconstructed")

    def test_q120_and_q420_use_modern_mapping(self):
        q120 = self.quarters["Q120"]
        q420 = self.quarters["Q420"]
        self.assertEqual(q120.values["Industry"], 10633)
        self.assertEqual(q120.values["Energy"], 6528)
        self.assertEqual(q120.values["Healthcare"], 3587)
        self.assertEqual(q420.values["Industry"], 11718)
        self.assertEqual(q420.values["Energy"], 0)
        self.assertEqual(q420.values["Healthcare"], 3876)

    def test_modern_native_sector_rows_are_retained(self):
        q226 = self.quarters["Q226"]
        expected = {
            "Digital Industries": 4626,
            "Smart Infrastructure": 5928,
            "Mobility": 3036,
            "Siemens Healthineers": 5681,
            "Industrial Business": 19271,
            "Siemens Financial Services (SFS)": 60,
            "Reconciliation to Consolidated Financial Statements": 425,
            "Siemens (continuing operations)": 19756,
        }
        for row, value in expected.items():
            with self.subTest(row=row):
                self.assertEqual(q226.values[row], value)
                self.assertEqual(q226.sources[row].source_type, "native")

    def test_early_2020_native_sector_aliases_are_normalized(self):
        q120 = self.quarters["Q120"]
        self.assertEqual(q120.values["Industrial Business"], 19586)
        self.assertEqual(q120.values["Siemens Financial Services (SFS)"], 188)
        self.assertEqual(q120.values["Reconciliation to Consolidated Financial Statements"], -618)
        self.assertEqual(q120.values["Siemens (continuing operations)"], 20317)

    def test_modern_parser_later_year_goldens(self):
        expected = {
            "Q422": {"Industry": 14478, "Energy": 0, "Healthcare": 6001, "Other": 94, "Total Revenue": 20573},
            "Q424": {"Industry": 13843, "Energy": 0, "Healthcare": 6328, "Other": 640, "Total Revenue": 20811},
            "Q226": {"Industry": 13590, "Energy": 0, "Healthcare": 5681, "Other": 485, "Total Revenue": 19756},
        }
        for code, rows in expected.items():
            with self.subTest(code=code):
                for row, value in rows.items():
                    self.assertEqual(self.quarters[code].values[row], value)

    def test_balance_sheet_goldens_across_layouts(self):
        expected = {
            "Q110": {
                "Cash & Cash Equivalets": 10446,
                "Total Current Assets (TCA)": 44300,
                "Total Liabilities": 67009,
                "S/E": 28071,
                "L+S/E": 95731,
            },
            "Q416": {
                "Cash & Cash Equivalets": 10604,
                "Total Current Assets (TCA)": 55329,
                "Total Liabilities": 90901,
                "L+S/E": 125717,
            },
            "Q418": {"Cash & Cash Equivalets": 11066, "Total Assets": 138915},
            "Q226": {
                "Cash & Cash Equivalets": 8664,
                "Total Current Assets (TCA)": 68954,
                "Long-Term Debt": 41523,
                "Total Liabilities": 97034,
                "L+S/E": 167971,
            },
        }
        for code, rows in expected.items():
            with self.subTest(code=code):
                for row, value in rows.items():
                    self.assertEqual(self.quarters[code].values[row], value)
                    self.assertEqual(self.quarters[code].sources[row].source_type, "native")

    def test_supplemental_balance_fills_missing_native_quarter(self):
        quarters = {"Q109": self._empty_quarter("Q109", 2009, 1)}
        coverage = apply_supplemental_balance_documents(
            quarters,
            [self._supplemental_balance_source()],
            manifest_found=False,
        )

        self.assertEqual(quarters["Q109"].values["Cash & Cash Equivalets"], 6071)
        self.assertEqual(quarters["Q109"].values["Total Assets"], 97422)
        self.assertEqual(quarters["Q109"].sources["Total Assets"].source_type, "native")
        self.assertEqual(
            quarters["Q109"].sources["Total Assets"].source_pdf,
            "balance_sheet_supplemental/2009-q1-financial-statement-e.pdf",
        )
        self.assertEqual(coverage["filled_quarters"], ["Q109"])

    def test_supplemental_balance_does_not_create_income_columns(self):
        quarters = {"Q109": self._empty_quarter("Q109", 2009, 1)}
        quarters["Q109"].values["Total Revenue"] = 19634
        text = "Revenue 1 2\n" + self._balance_sheet_text()

        apply_supplemental_balance_documents(
            quarters,
            [self._supplemental_balance_source(text=text)],
            manifest_found=False,
        )

        self.assertEqual(set(quarters), {"Q109"})
        self.assertNotIn("Q108", quarters)
        self.assertEqual(quarters["Q109"].values["Total Revenue"], 19634)

    def test_supplemental_balance_refuses_conflicting_native_value(self):
        quarters = {"Q109": self._empty_quarter("Q109", 2009, 1)}
        quarters["Q109"].values["Cash & Cash Equivalets"] = 999
        quarters["Q109"].sources["Cash & Cash Equivalets"] = SourceRecord(
            source_pdf="data.pdf",
            page=1,
            parser_family="balance_sheet",
            raw_line="Cash and cash equivalents 999",
            raw_values=[999],
            normalized_row="Cash & Cash Equivalets",
            normalized_value=999,
            source_type="native",
        )

        with self.assertRaisesRegex(ValueError, "Supplemental balance conflict"):
            apply_supplemental_balance_documents(
                quarters,
                [self._supplemental_balance_source()],
                manifest_found=False,
            )

    def test_supplemental_balance_reports_native_row_omissions(self):
        quarters = {"Q109": self._empty_quarter("Q109", 2009, 1)}
        coverage = apply_supplemental_balance_documents(
            quarters,
            [self._supplemental_balance_source()],
            manifest_found=False,
        )

        missing = coverage["missing_rows_by_quarter"]["Q109"]
        self.assertIn("Goodwill", missing)
        self.assertNotIn("Cash & Cash Equivalets", missing)
        self.assertNotIn("Goodwill", quarters["Q109"].values)

    def test_modern_balance_sheet_hidden_components_are_audited(self):
        q420 = self.quarters["Q420"]
        self.assertEqual(q420.values["Contract Assets"], 5545)
        self.assertEqual(q420.values["Contract Liabilities"], 7524)
        self.assertIn("balance_sheet", q420.raw_components)
        self.assertNotIn("Contract Assets", OUTPUT_ROWS)
        self.assertNotIn("Contract Liabilities", OUTPUT_ROWS)

    def test_metric_formulas_are_calculated_from_audited_rows(self):
        q226 = self.quarters["Q226"].values
        self.assertAlmostEqual(q226["Current Ratio"], q226["Total Current Assets (TCA)"] / q226["Total Current Liabilities"])
        self.assertAlmostEqual(q226["Debt Ratio"], q226["Total Liabilities"] / q226["Total Assets"])
        self.assertAlmostEqual(q226["Net Trading Cycles"], q226["DSO"] + q226["DIO"] - q226["DPO"])
        self.assertEqual(self.quarters["Q226"].sources["Current Ratio"].source_type, "calculated")

    def test_row_specific_formatting(self):
        self.assertEqual(format_cell(0.125, "SE Growth %"), "12.5%")
        self.assertEqual(format_cell(1.234, "Quick Ratio"), "1.23")
        self.assertEqual(format_cell(42.25, "DIO"), "42.2")

    def test_output_starts_q109_and_ends_q226(self):
        columns = self.metadata["columns"]
        self.assertEqual(columns[0], "Q109")
        self.assertEqual(columns[-1], "Q226")

    def test_tsv_row_order_matches_template(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "siemens_financials_wide.tsv"
            write_tsv(path, self.quarters)
            actual_rows = [line.split("\t")[0] for line in path.read_text().splitlines()[1:]]
        expected_rows = [row or "" for row in OUTPUT_ROWS]
        self.assertEqual(actual_rows, expected_rows)

    def test_tsv_has_no_trailing_whitespace(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "siemens_financials_wide.tsv"
            write_tsv(path, self.quarters)
            lines = path.read_text().splitlines()

        self.assertTrue(lines)
        self.assertTrue(all(not line.endswith((" ", "\t")) for line in lines))

    def test_verification_report_passes_for_generated_outputs(self):
        with TemporaryDirectory() as temp_dir:
            paths = self._write_temp_outputs(Path(temp_dir))
            report = verify_outputs(paths["tsv"], paths["audit"], Path("data"), paths["report"])

        self.assertTrue(report["metadata"]["passed"], report["issues"][:5])
        self.assertEqual(report["metadata"]["columns_checked"], 68)
        self.assertEqual(report["metadata"]["issue_counts"], {})

    def test_verification_catches_tsv_audit_mismatch(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            tsv_path, audit_path = self._write_minimal_verification_fixture(root)
            lines = tsv_path.read_text().splitlines()
            lines[1] = "Digital Industries\t999"
            tsv_path.write_text("\n".join(lines) + "\n")

            report = verify_outputs(tsv_path, audit_path, Path("data"))

        self.assertFalse(report["metadata"]["passed"])
        self.assertIn("tsv_audit_mismatch", report["metadata"]["issue_counts"])

    def test_verification_catches_missing_native_source_line(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            tsv_path, audit_path = self._write_minimal_verification_fixture(root)
            audit = json.loads(audit_path.read_text())
            audit["quarters"]["Q226"]["sources"]["Digital Industries"]["raw_line"] = "Not a Siemens PDF line"
            audit_path.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n")

            report = verify_outputs(tsv_path, audit_path, Path("data"))

        self.assertFalse(report["metadata"]["passed"])
        self.assertIn("missing_source_line", report["metadata"]["issue_counts"])

    def test_audit_flags_reconstructed_values(self):
        reconstructed = [
            source
            for quarter in self.quarters.values()
            for source in quarter.sources.values()
            if source.source_type == "reconstructed"
        ]
        self.assertTrue(reconstructed)
        self.assertTrue(any(source.parser_family == "division_2018" for source in reconstructed))
        self.assertTrue(any(source.parser_family == "modern_2020_2026" for source in reconstructed))

    def test_all_validations_pass(self):
        for code, quarter in self.quarters.items():
            with self.subTest(code=code):
                self.assertTrue(quarter.validations)
                self.assertTrue(all(item["passed"] for item in quarter.validations))

    def _write_temp_outputs(self, root: Path) -> dict[str, Path]:
        tsv_path = root / "siemens_financials_wide.tsv"
        audit_path = root / "siemens_financials_audit.json"
        report_path = root / "siemens_financials_verification_report.json"
        write_tsv(tsv_path, self.quarters)
        write_audit(
            audit_path,
            self.quarters,
            self.metadata["processed_files"],
            self.metadata["duplicates"],
            self.metadata["sample_warnings"],
            self.metadata["overrides_applied"],
        )
        return {"tsv": tsv_path, "audit": audit_path, "report": report_path}

    def _write_minimal_verification_fixture(self, root: Path) -> tuple[Path, Path]:
        tsv_path = root / "minimal.tsv"
        audit_path = root / "minimal_audit.json"
        source = self.quarters["Q226"].sources["Digital Industries"]
        payload = {
            "metadata": {"columns": ["Q226"]},
            "quarters": {
                "Q226": {
                    "values": {"Digital Industries": 4626},
                    "sources": {"Digital Industries": source.__dict__},
                    "validations": [],
                }
            },
        }
        tsv_path.write_text("Financial Years\tQ226\nDigital Industries\t4,626\n")
        audit_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        return tsv_path, audit_path

    def _empty_quarter(self, code: str, fiscal_year: int, quarter: int) -> QuarterData:
        return QuarterData(code=code, fiscal_year=fiscal_year, quarter=quarter, source_pdf="main.pdf")

    def _supplemental_balance_source(self, text: str | None = None) -> SupplementalBalanceDocument:
        document = PdfDocument(
            path=Path("balance_sheet_supplemental/2009-q1-financial-statement-e.pdf"),
            sha256="test-sha",
            fiscal_year=2009,
            quarter=1,
            code="Q109",
            pages=[text or self._balance_sheet_text()],
        )
        return SupplementalBalanceDocument(
            quarter="Q109",
            filename="2009-q1-financial-statement-e.pdf",
            sha256="test-sha",
            source_url="https://example.test/2009-q1-financial-statement-e.pdf",
            document=document,
        )

    def _balance_sheet_text(self) -> str:
        return "\n".join(
            [
                "12/31/08 9/30/08",
                "Cash and cash equivalents 6,071 6,893",
                "Trade and other receivables 16,145 15,785",
                "Other current financial assets 4,720 3,116",
                "Inventories 15,146 14,509",
                "Total current assets 44,602 43,242",
                "Total assets 97,422 94,463",
                "Total current liabilities 43,006 42,451",
                "Total liabilities 70,661 67,083",
                "Total equity attributable to shareholders of Siemens AG 26,147 26,774",
                "Total liabilities and equity 97,422 94,463",
            ]
        )


if __name__ == "__main__":
    unittest.main()
