import tempfile
import unittest
from pathlib import Path

import _path  # noqa: F401  # ensures src/ is importable without install

from sci_html.models import Deck, Slide
from sci_html.renderer import render_deck


class RendererTests(unittest.TestCase):
    def test_render_directory(self):
        deck = Deck(title="Render Test", slides=[Slide(type="cover", title="Render Test"), Slide(type="content", title="Content", bullets=["A <script>bad</script>"])])
        with tempfile.TemporaryDirectory() as tmp:
            output = render_deck(deck, Path(tmp) / "deck")
            self.assertTrue(output.exists())
            self.assertTrue((Path(tmp) / "deck" / "assets" / "deck.js").exists())
            html = output.read_text(encoding="utf-8")
            self.assertIn("Render Test", html)
            self.assertIn("motif-general", html)
            self.assertNotIn("<script>bad</script>", html)
            self.assertIn("&lt;script&gt;bad&lt;/script&gt;", html)
            self.assertIn('<ol class="bullet-list bullet-list-plain">', html)

    def test_highlight_markup_renders_safely(self):
        deck = Deck(title="Highlight", slides=[Slide(type="content", title="Content", bullets=["Use **key point** here"])])
        with tempfile.TemporaryDirectory() as tmp:
            output = render_deck(deck, Path(tmp) / "deck")
            html = output.read_text(encoding="utf-8")
            self.assertIn('<span class="text-highlight">key point</span>', html)

    def test_theme_motif_class_is_added(self):
        deck = Deck(title="Motif", slides=[Slide(type="content", title="Biomedical Imaging", bullets=["MRI probe"])])
        with tempfile.TemporaryDirectory() as tmp:
            output = render_deck(deck, Path(tmp) / "deck")
            html = output.read_text(encoding="utf-8")
            self.assertIn("motif-bio", html)

    def test_long_title_gets_fit_class(self):
        deck = Deck(title="Long", slides=[Slide(type="content", title="A Very Long Scientific Paper Title With Multiple Technical Clauses That Needs To Fit On One Slide", bullets=["A", "B", "C"])])
        with tempfile.TemporaryDirectory() as tmp:
            output = render_deck(deck, Path(tmp) / "deck")
            html = output.read_text(encoding="utf-8")
            self.assertIn("title-fit-long", html)
            self.assertIn('<ol class="bullet-list">', html)

    def test_single_file_flag_is_ignored_for_directory_only_output(self):
        deck = Deck(title="Single", slides=[Slide(type="cover", title="Single")])
        with tempfile.TemporaryDirectory() as tmp:
            output = render_deck(deck, Path(tmp) / "single.html", single_file=True)
            self.assertEqual(output, Path(tmp) / "single" / "index.html")
            self.assertTrue(output.exists())
            self.assertTrue((Path(tmp) / "single" / "assets" / "style.css").exists())

    def test_cover_metadata_and_controls_render(self):
        deck = Deck(
            title="Metadata",
            author="Alice",
            affiliation="Example Lab",
            date="2026-05-15",
            slides=[Slide(type="cover", title="Metadata")],
        )
        with tempfile.TemporaryDirectory() as tmp:
            output = render_deck(deck, Path(tmp) / "deck")
            html = output.read_text(encoding="utf-8")
            self.assertIn("Alice", html)
            self.assertIn("Example Lab", html)
            self.assertIn("2026-05-15", html)
            self.assertIn('id="deck-prev"', html)
            self.assertIn('id="deck-next"', html)


if __name__ == "__main__":
    unittest.main()
