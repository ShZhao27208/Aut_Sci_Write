import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "skills" / "sci-search" / "sci_search.py"


def load_module():
    spec = importlib.util.spec_from_file_location("sci_search", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class SciSearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def test_load_journal_db_normalizes_external_schema(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "journal_db.json"
            db_path.write_text(
                json.dumps(
                    {
                        "Custom Journal": {
                            "JCR": "Q2",
                            "IF": 5.5,
                            "Partition": "材料科学2区",
                            "Publisher": "Test Publisher",
                        }
                    }
                ),
                encoding="utf-8",
            )

            journal_db = self.module.load_journal_db(db_path)

        self.assertIn("Custom Journal", journal_db)
        self.assertEqual(journal_db["Custom Journal"]["jcr_partition"], "Q2")
        self.assertEqual(journal_db["Custom Journal"]["impact_factor"], "5.5")
        self.assertEqual(journal_db["Custom Journal"]["publisher"], "Test Publisher")

    def test_paper_library_deduplicates_and_updates_entries(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            library_path = Path(tmp_dir) / "library.json"
            library = self.module.PaperLibrary(str(library_path))
            first = {
                "source": "pubmed",
                "title": "A Useful Paper",
                "authors": ["A. Author"],
                "year": "2025",
                "journal": "Nature",
                "url": "https://pubmed.ncbi.nlm.nih.gov/1/",
                "doi": "10.1000/example",
                "abstract": "old abstract",
            }
            updated = dict(first, abstract="new abstract")

            library.add_paper(first)
            library.add_paper(updated)

            saved = json.loads(library_path.read_text(encoding="utf-8"))

        self.assertEqual(len(library.papers), 1)
        self.assertEqual(library.papers[0]["abstract"], "new abstract")
        self.assertEqual(saved["papers"][0]["abstract"], "new abstract")

    def test_dedupe_results_preserves_first_seen_order(self):
        first = {
            "source": "arxiv",
            "title": "Paper A",
            "url": "https://arxiv.org/abs/1",
            "doi": "",
        }
        duplicate = dict(first, journal="Nature")
        second = {
            "source": "pubmed",
            "title": "Paper B",
            "url": "https://pubmed.ncbi.nlm.nih.gov/2/",
            "doi": "10.1000/b",
        }

        deduped = self.module.dedupe_results([first, duplicate, second])

        self.assertEqual([paper["title"] for paper in deduped], ["Paper A", "Paper B"])

    def test_dedupe_results_uses_normalized_doi_across_sources(self):
        wos = {
            "source": "wos",
            "title": "GNSS NLOS Mitigation",
            "url": "https://example.test/wos",
            "doi": "10.1000/GNSS.1",
        }
        scopus = {
            "source": "scopus",
            "title": "A different provider title",
            "url": "https://example.test/scopus",
            "doi": "https://doi.org/10.1000/gnss.1",
        }

        self.assertEqual(self.module.dedupe_results([wos, scopus]), [wos])

    def test_dedupe_results_falls_back_to_title_when_either_doi_is_missing(self):
        without_doi = {
            "source": "springer_meta",
            "title": "GNSS-NLOS: Mitigation!",
            "url": "https://example.test/meta",
            "doi": "",
        }
        with_doi = {
            "source": "scopus",
            "title": "gnss nlos mitigation",
            "url": "https://example.test/scopus",
            "doi": "10.1000/gnss.2",
        }

        self.assertEqual(
            self.module.dedupe_results([without_doi, with_doi]),
            [without_doi],
        )

    def test_dedupe_results_keeps_same_title_with_two_different_dois(self):
        first = {"source": "wos", "title": "Shared", "url": "a", "doi": "10.1/a"}
        second = {"source": "scopus", "title": "Shared", "url": "b", "doi": "10.1/b"}

        self.assertEqual(self.module.dedupe_results([first, second]), [first, second])

    def test_normalize_title_preserves_unicode_words(self):
        self.assertEqual(self.module.normalize_title("卫星-导航！"), "卫星 导航")

    def test_paper_library_updates_cross_source_duplicate_by_doi(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            library = self.module.PaperLibrary(str(Path(tmp_dir) / "library.json"))
            library.add_paper({
                "source": "wos", "title": "Paper", "authors": [], "year": "2025",
                "url": "a", "doi": "10.1000/PAPER",
            })
            library.add_paper({
                "source": "scopus", "title": "Paper from Scopus", "authors": [],
                "year": "2025", "url": "b",
                "doi": "https://doi.org/10.1000/paper",
            })

        self.assertEqual(len(library.papers), 1)
        self.assertEqual(library.papers[0]["source"], "scopus")


if __name__ == "__main__":
    unittest.main()
