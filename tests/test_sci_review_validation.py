import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "skills" / "sci-review" / "scripts" / "validate_review_output.py"


def load_module():
    spec = importlib.util.spec_from_file_location("validate_review_output", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class SciReviewValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def test_literature_review_structure_passes(self):
        text = """
        # Introduction
        # Methodology
        # Challenges
        # Conclusion
        """
        result = self.module.validate_text(text, "literature-review")

        self.assertTrue(result["passed"])

    def test_rebuttal_bans_adversarial_tone(self):
        text = """
        Reviewer concern: baseline comparison.
        Response: the reviewer misunderstood the method.
        Revision plan: we will update Section 4.
        """
        result = self.module.validate_text(text, "rebuttal")

        self.assertFalse(result["passed"])
        self.assertIn("reviewer misunderstood", result["banned_phrases"])

    def test_cli_validation(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output = Path(tmp_dir) / "review.md"
            output.write_text("# Introduction\n# Methodology\n# Challenges\n# Conclusion\n", encoding="utf-8")

            exit_code = self.module.main(["--case", "literature-review", "--output", str(output)])

        self.assertEqual(exit_code, 0)


if __name__ == "__main__":
    unittest.main()
