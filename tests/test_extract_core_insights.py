import csv
import contextlib
import importlib.util
import io
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "extract_core_insights.py"


def load_module():
    spec = importlib.util.spec_from_file_location("extract_core_insights", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ExtractCoreInsightsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def sample_result(self):
        return {
            "metadata": {
                "title": "A Test Paper",
                "authors": ["Ada Lovelace", "Grace Hopper"],
                "journal": "Nature",
                "year": 2025,
                "doi": "10.1000/test",
            },
            "core_insights": {
                "research_problem": "Improve scientific extraction quality.",
                "methodology": "A heuristic extraction pipeline.",
                "key_results": ["Accuracy improved by 12.3%."],
                "innovation": ["Lazy dependency loading for CLI UX."],
                "application": "CLI workflows and batch review.",
                "limitations": ["OCR-heavy PDFs remain difficult."],
            },
            "confidence_scores": {
                "research_problem": 0.90,
                "methodology": 0.70,
                "key_results": 0.80,
                "innovation": 0.60,
                "application": 0.50,
                "limitations": 0.40,
            },
            "extraction_time": 3,
            "status": "success",
        }

    def test_help_runs_without_pdf_dependencies(self):
        result = subprocess.run(
            [sys.executable, str(MODULE_PATH), "--help"],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0)
        self.assertIn("--format", result.stdout)
        self.assertIn("--workers", result.stdout)

    def test_write_result_file_csv_uses_real_confidence_keys(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "paper.csv"
            self.module.write_result_file(
                self.sample_result(),
                output_path,
                "csv",
            )

            with output_path.open("r", encoding="utf-8", newline="") as f:
                rows = list(csv.DictReader(f))

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["Problem_Conf"], "0.90")
        self.assertEqual(rows[0]["Results_Conf"], "0.80")

    def test_batch_process_writes_requested_summary_format(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            pdf_dir = Path(tmp_dir) / "pdfs"
            output_dir = Path(tmp_dir) / "out"
            pdf_dir.mkdir()
            (pdf_dir / "paper1.pdf").write_bytes(b"%PDF-1.4")

            extractor = self.module.CoreInsightsExtractor()
            extractor.extract_from_pdf = lambda _path: self.sample_result()
            with contextlib.redirect_stdout(io.StringIO()):
                results = extractor.batch_process(
                    pdf_dir,
                    output_dir=output_dir,
                    workers=1,
                    summary_format="markdown",
                )

            summary_path = output_dir / "summary.md"
            summary_text = summary_path.read_text(encoding="utf-8")

        self.assertEqual(len(results), 1)
        self.assertIn("Batch Core Insights Summary", summary_text)


if __name__ == "__main__":
    unittest.main()
