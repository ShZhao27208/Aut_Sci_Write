import unittest

from sci_html.parser import parse_deck


class ParserTests(unittest.TestCase):
    def test_structured_outline_generates_sections(self):
        deck = parse_deck("""
Title: Test Deck
Author: Alice

1. Background
- Point A
- Point B

2. Results
- Point C
""")
        self.assertEqual(deck.title, "Test Deck")
        self.assertEqual(deck.slides[0].type, "cover")
        self.assertTrue(any(slide.type == "toc" for slide in deck.slides))
        self.assertEqual([s.title for s in deck.slides if s.type == "section"], ["Background", "Results"])

    def test_markdown_slide_breaks(self):
        deck = parse_deck("""
---
title: Markdown Deck
theme: journal-dark
---

# First

- A

---

# Second

- B
""")
        self.assertEqual(deck.title, "Markdown Deck")
        self.assertEqual(deck.theme, "journal-dark")
        self.assertGreaterEqual(len(deck.slides), 3)

    def test_markdown_slide_directive_section(self):
        deck = parse_deck("""
---
title: Directive Deck
---

layout: section
subtitle: 01

# Background
""")
        section = [slide for slide in deck.slides if slide.type == "section"][0]
        self.assertEqual(section.title, "Background")
        self.assertEqual(section.subtitle, "01")

    def test_chinese_metadata_and_long_bullets(self):
        deck = parse_deck("""
主题：中文标题
汇报人：张三
单位：材料学院
时间：2026-05-15

1、背景
- A
- B
- C
- D
- E
- F
""")
        self.assertEqual(deck.title, "中文标题")
        self.assertEqual(deck.author, "张三")
        self.assertEqual(deck.affiliation, "材料学院")
        self.assertEqual(deck.date, "2026-05-15")
        content_slides = [slide for slide in deck.slides if slide.type == "content"]
        self.assertEqual(len(content_slides), 2)
        self.assertLessEqual(max(len(slide.bullets) for slide in content_slides), 5)


if __name__ == "__main__":
    unittest.main()
