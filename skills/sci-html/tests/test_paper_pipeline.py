import tempfile
import unittest
from pathlib import Path

import _path  # noqa: F401  # ensures src/ is importable without install

from sci_html.paper_pipeline import build_paper_deck_markdown


class PaperPipelineTests(unittest.TestCase):
    def test_build_paper_deck_markdown_includes_figures_and_sections(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            figure = base / "figures" / "figure_1.png"
            figure.parent.mkdir()
            figure.write_bytes(b"placeholder")
            markdown = build_paper_deck_markdown(
                {
                    "metadata": {
                        "title": "Example Paper",
                        "authors": ["Alice A", "Bob B"],
                        "journal": "Example Journal",
                        "year": 2026,
                        "doi": "10.0000/example",
                    },
                    "core_insights": {
                        "research_problem": "A key problem is unclear.",
                        "methodology": ["The method combines extraction and rendering."],
                        "key_results": ["The result is a generated deck."],
                        "innovation": "A standalone workflow.",
                        "application": "Literature presentation.",
                        "limitations": "Manual review is still needed.",
                    },
                },
                [{"number": 1, "page": 2, "caption": "Main figure caption.", "image_path": str(figure)}],
                theme="academic-blue",
                author="Presenter",
                affiliation="Lab",
                report_date="2026-05-15",
                source_pdf=base / "paper.pdf",
                base_dir=base,
            )
            self.assertIn("title: Example Paper", markdown)
            self.assertIn("layout: section", markdown)
            self.assertIn("![Figure 1](figures/figure_1.png)", markdown)
            self.assertIn("**problem**", markdown.lower())

    def test_build_review_paper_deck_markdown_uses_review_structure(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            markdown = build_paper_deck_markdown(
                {
                    "paper_type": "review",
                    "metadata": {
                        "title": "Example Review",
                        "authors": ["Alice A"],
                        "journal": "Review Journal",
                        "year": 2026,
                    },
                    "core_insights": {
                        "review_type": "Systematic review",
                        "review_scope": "This review maps the field.",
                        "taxonomy": ["Methods are grouped into three families."],
                        "literature_selection": "The authors searched major databases.",
                        "consensus_findings": "Most studies agree on the main trend.",
                        "controversies": "Evidence remains mixed across datasets.",
                        "evidence_quality": "Small samples limit confidence.",
                        "research_gaps": "External validation is missing.",
                        "future_directions": "Future work should standardize benchmarks.",
                    },
                },
                [],
                theme="academic-blue",
                author="Presenter",
                affiliation="Lab",
                report_date="2026-05-15",
                source_pdf=base / "review.pdf",
                base_dir=base,
            )
            self.assertIn("# Review Map", markdown)
            self.assertIn("# Evidence and Debate", markdown)
            self.assertIn("Paper Type**: Systematic review", markdown)
            self.assertIn("standardize benchmarks", markdown)


if __name__ == "__main__":
    unittest.main()
