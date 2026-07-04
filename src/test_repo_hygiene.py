import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from siemens_extractor.loc_policy import line_count_violations, maintained_files


class RepoHygieneTests(unittest.TestCase):
    def test_current_repo_respects_line_count_policy(self):
        root = Path(__file__).resolve().parents[1]
        violations = line_count_violations(root)
        self.assertEqual([violation.message for violation in violations], [])

    def test_generated_output_is_ignored(self):
        root = Path(__file__).resolve().parents[1]
        scanned = {path.relative_to(root).as_posix() for path in maintained_files(root)}
        self.assertNotIn("output/siemens_financials_audit.json", scanned)
        self.assertNotIn("output/siemens_financials_verification_report.json", scanned)
        self.assertNotIn("output/siemens_financials_wide.tsv", scanned)

    def test_source_file_above_ceiling_fails(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source_dir = root / "src"
            source_dir.mkdir()
            oversized = source_dir / "oversized.py"
            oversized.write_text("\n".join(["pass"] * 676) + "\n", encoding="utf-8")

            violations = line_count_violations(root)

        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].severity, "hard")
        self.assertIn("above the hard ceiling", violations[0].message)


if __name__ == "__main__":
    unittest.main()
