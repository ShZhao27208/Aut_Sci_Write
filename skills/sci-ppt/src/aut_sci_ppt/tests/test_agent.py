import os
import tempfile
import unittest
from pathlib import Path

from aut_sci_ppt.enhanced_agent import EnhancedPPTAgent
from aut_sci_ppt.models import (
    ContentListData,
    CoverData,
    ListItem,
    Page,
    ParsedData,
    PAGE_TYPE_CONTENT_LIST,
    PAGE_TYPE_SECTION,
)
from aut_sci_ppt.parser.text_parser import TextParser
from aut_sci_ppt.paginator.smart_paginator import SmartPaginator
from aut_sci_ppt.paper_workflow import _detect_paper_sections


class TestTextParser(unittest.TestCase):
    def test_parse_basic_meta(self):
        text = """
        Title: Test Presentation
        Author: Ada Lovelace
        Advisor: Grace Hopper
        Date: 2026-01-01
        """
        result = TextParser().parse(text)

        self.assertEqual(result.meta.title, "Test Presentation")
        self.assertEqual(result.meta.author, "Ada Lovelace")
        self.assertEqual(result.meta.advisor, "Grace Hopper")
        self.assertEqual(result.meta.date, "2026-01-01")

    def test_parser_generates_section_pages(self):
        text = """
        Title: Paper Talk
        Author: Ada Lovelace

        1. Background
        - Why the problem matters

        2. Method
        - The proposed approach
        """
        result = TextParser().parse(text)

        section_pages = [page for page in result.sections if page.page_type == PAGE_TYPE_SECTION]
        content_pages = [page for page in result.sections if page.page_type != PAGE_TYPE_SECTION]

        self.assertEqual([page.data.part_num for page in section_pages], ["1", "2"])
        self.assertEqual([page.data.part_title for page in section_pages], ["Background", "Method"])
        self.assertGreaterEqual(len(content_pages), 1)

    def test_validate_missing_fields(self):
        result = TextParser().parse("1. Only Section\n- content")
        warnings = TextParser().validate(result)

        self.assertIn("Missing title", warnings)
        self.assertIn("Missing author", warnings)


class TestSmartPaginator(unittest.TestCase):
    def test_paginator_does_not_create_section_pages(self):
        parsed = ParsedData()
        parsed.meta = CoverData(title="Test", author="Ada")
        parsed.sections.append(
            Page(
                page_type=PAGE_TYPE_CONTENT_LIST,
                data=ContentListData(title="Content", items=[ListItem(text="Item")]),
            )
        )

        pages = SmartPaginator().paginate(parsed)

        self.assertEqual([page.page_type for page in pages].count(PAGE_TYPE_SECTION), 0)

    def test_paginator_preserves_parser_section_pages(self):
        parsed = TextParser().parse(
            """
            Title: Test
            Author: Ada

            1. Background
            - Item
            """
        )
        pages = SmartPaginator().paginate(parsed)

        section_pages = [page for page in pages if page.page_type == PAGE_TYPE_SECTION]
        self.assertEqual(len(section_pages), 1)
        self.assertEqual(section_pages[0].data.part_num, "1")


class TestEnhancedPPTAgent(unittest.TestCase):
    def test_enhanced_agent_imports_and_reports_status(self):
        agent = EnhancedPPTAgent(enable_enhancements=True)
        status = agent.get_enhancement_status()

        self.assertTrue(status["enhancements_enabled"])
        self.assertEqual(status["human_review"], "not included")

    def test_missing_pdf_returns_none(self):
        result = EnhancedPPTAgent().generate_from_pdf(
            os.path.join(tempfile.gettempdir(), "missing-aut-sci-ppt.pdf"),
            str(Path(tempfile.gettempdir()) / "missing-output.pptx"),
            enable_formula_rendering=False,
        )

        self.assertIsNone(result)


class TestPaperWorkflowSectionDetection(unittest.TestCase):
    def test_raises_when_no_sections_detected(self):
        junk = "qwerty zzz lorem ipsum dolor sit amet random words only here."
        with self.assertRaises(ValueError) as ctx:
            _detect_paper_sections(junk, [junk])
        self.assertIn("could not extract paper structure", str(ctx.exception))

    def test_detects_real_sections(self):
        text = (
            "Abstract: this work. Introduction: background here. "
            "Methods: we do. Results: we found. Conclusion: done."
        )
        sections = _detect_paper_sections(text, [text])
        self.assertGreater(len(sections), 0)


if __name__ == "__main__":
    unittest.main()
