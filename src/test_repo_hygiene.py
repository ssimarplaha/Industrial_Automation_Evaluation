import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from siemens_extractor.loc_policy import line_count_violations, maintained_files


class RepoHygieneTests(unittest.TestCase):
    def agent_doc_paths(self, root):
        return [root / "AGENTS.md", *sorted((root / ".agents").rglob("*.md"))]

    def test_current_repo_respects_line_count_policy(self):
        root = Path(__file__).resolve().parents[1]
        violations = line_count_violations(root)
        self.assertEqual([violation.message for violation in violations], [])

    def test_all_agent_docs_are_covered_by_line_count_policy(self):
        root = Path(__file__).resolve().parents[1]
        scanned = {path.relative_to(root).as_posix() for path in maintained_files(root)}
        agent_docs = {path.relative_to(root).as_posix() for path in self.agent_doc_paths(root)}

        self.assertEqual(agent_docs - scanned, set())

    def test_root_agents_routes_to_siemens_agent_guide(self):
        root = Path(__file__).resolve().parents[1]
        text = (root / "AGENTS.md").read_text(encoding="utf-8")

        self.assertIn(".agents/AGENTS.md", text)
        self.assertIn("source of truth", text.lower())
        self.assertIn("Siemens-specific guidance overrides", text)

    def test_agent_docs_do_not_require_generic_python_gates(self):
        root = Path(__file__).resolve().parents[1]
        docs = self.agent_doc_paths(root)

        for path in docs:
            relative = path.relative_to(root).as_posix()
            for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                lower = line.lower()
                self.assertNotIn("make check", lower, f"{relative}:{line_number}")
                if "pytest" in lower:
                    self.assertTrue(
                        any(marker in lower for marker in ("future", "optional", "not current")),
                        f"{relative}:{line_number}",
                    )

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
