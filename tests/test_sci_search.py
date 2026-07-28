import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from urllib.parse import parse_qs, urlsplit


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "skills" / "sci-search" / "sci_search.py"


def load_module():
    spec = importlib.util.spec_from_file_location("sci_search", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class FakeResponse:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def read(self):
        return self.payload


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

    def test_parse_args_rejects_invalid_year_bounds(self):
        invalid_commands = [
            ["query", "--year-from", "22"],
            ["query", "--year-to", "year"],
            ["query", "--year-from", "2026", "--year-to", "2022"],
        ]
        for argv in invalid_commands:
            with self.subTest(argv=argv), self.assertRaises(SystemExit):
                self.module.parse_args(argv)

    def test_parse_args_defaults_to_recent_sort(self):
        args = self.module.parse_args(["query"])

        self.assertEqual(args.sort, "recent")
        self.assertIsNone(args.year_from)
        self.assertIsNone(args.year_to)

    def test_post_process_filters_inclusive_years_and_sorts_recent(self):
        papers = [
            {"source": "wos", "title": "2023 first", "doi": "1", "year": "2023"},
            {"source": "wos", "title": "unknown", "doi": "2", "year": ""},
            {"source": "wos", "title": "2025", "doi": "3", "year": "2025"},
            {"source": "wos", "title": "2023 second", "doi": "4", "year": "2023"},
            {"source": "wos", "title": "2021", "doi": "5", "year": "2021"},
        ]

        results = self.module.post_process_results(papers, 2022, 2025, "recent")

        self.assertEqual(
            [paper["title"] for paper in results],
            ["2025", "2023 first", "2023 second"],
        )

    def test_post_process_preserves_provider_order_for_relevance(self):
        papers = [
            {"source": "wos", "title": "Older", "doi": "1", "year": "2022"},
            {"source": "wos", "title": "Newer", "doi": "2", "year": "2026"},
        ]

        results = self.module.post_process_results(papers, None, None, "relevance")

        self.assertEqual(results, papers)

    def test_main_default_source_order_uses_only_four_enabled_sources(self):
        calls = []

        class KeyedFetcher:
            def __init__(self, name):
                self.name = name

            def is_available(self):
                return True

            def search(self, query, limit, **kwargs):
                calls.append(self.name)
                return []

        with mock.patch.object(self.module, "WoSFetcher", lambda: KeyedFetcher("wos")), \
                mock.patch.object(
                    self.module, "SpringerMetaFetcher", lambda: KeyedFetcher("springer_meta")
                ), \
                mock.patch.object(
                    self.module, "SpringerOpenAccessFetcher", lambda: KeyedFetcher("springer_oa")
                ), \
                mock.patch.object(self.module, "ScopusFetcher", lambda: KeyedFetcher("scopus")), \
                mock.patch.object(self.module.ArxivFetcher, "search") as arxiv, \
                mock.patch.object(self.module.PubmedFetcher, "search") as pubmed, \
                mock.patch.object(self.module.SemanticScholarFetcher, "search") as semantic, \
                mock.patch.object(self.module.OpenAlexFetcher, "search") as openalex, \
                mock.patch.object(self.module.time, "sleep"):
            self.module.main(["GNSS NLOS", "--no-cache"])

        self.assertEqual(calls, ["wos", "springer_meta", "springer_oa", "scopus"])
        arxiv.assert_not_called()
        pubmed.assert_not_called()
        semantic.assert_not_called()
        openalex.assert_not_called()

    def test_main_keeps_non_default_sources_explicitly_accessible(self):
        cases = [
            ("arxiv", "ArxivFetcher"),
            ("pubmed", "PubmedFetcher"),
            ("semantic_scholar", "SemanticScholarFetcher"),
            ("openalex", "OpenAlexFetcher"),
        ]
        for source, class_name in cases:
            fetcher = mock.Mock()
            fetcher.search.return_value = []
            with self.subTest(source=source), \
                    mock.patch.object(self.module, class_name, return_value=fetcher), \
                    mock.patch.object(self.module.time, "sleep"):
                self.module.main(["query", "--source", source, "--no-cache"])
            fetcher.search.assert_called_once_with("query", 5)

    def test_main_springer_source_runs_metadata_then_open_access(self):
        calls = []

        class SpringerFetcher:
            def __init__(self, name):
                self.name = name

            def is_available(self):
                return True

            def search(self, query, limit, **kwargs):
                calls.append(self.name)
                return []

        with mock.patch.object(
                self.module,
                "SpringerMetaFetcher",
                lambda: SpringerFetcher("springer_meta"),
            ), mock.patch.object(
                self.module,
                "SpringerOpenAccessFetcher",
                lambda: SpringerFetcher("springer_oa"),
            ), mock.patch.object(self.module.time, "sleep"):
            self.module.main(["query", "--source", "springer", "--no-cache"])

        self.assertEqual(calls, ["springer_meta", "springer_oa"])

    def test_wos_builds_bounded_recent_query_and_parses_citations(self):
        payload = {
            "hits": [{
                "uid": "WOS:1", "title": "GNSS NLOS", "names": {"authors": []},
                "source": {"sourceTitle": "Journal", "publishYear": 2025},
                "identifiers": {"doi": "10.1000/test"},
                "citations": [{"db": "WOS", "count": 12}],
            }]
        }
        with mock.patch.object(self.module, "get_config_value", return_value="test-key"), \
                mock.patch.object(
                    self.module.urllib.request,
                    "urlopen",
                    return_value=FakeResponse(payload),
                ) as urlopen:
            papers = self.module.WoSFetcher().search(
                "GNSS NLOS", 5, year_from=2022, year_to=2026, sort_mode="recent"
            )

        query = parse_qs(urlsplit(urlopen.call_args.args[0].full_url).query)
        self.assertEqual(query["q"], ["TS=(GNSS NLOS) AND PY=(2022-2026)"])
        self.assertEqual(query["sortField"], ["PY+D"])
        self.assertEqual(papers[0]["times_cited"], 12)

    def test_wos_relevance_query_has_no_sort_field(self):
        with mock.patch.object(self.module, "get_config_value", return_value="test-key"), \
                mock.patch.object(
                    self.module.urllib.request,
                    "urlopen",
                    return_value=FakeResponse({"hits": []}),
                ) as urlopen:
            self.module.WoSFetcher().search("GNSS", sort_mode="relevance")

        query = parse_qs(urlsplit(urlopen.call_args.args[0].full_url).query)
        self.assertNotIn("sortField", query)

    def test_springer_fetchers_use_unquoted_keywords_and_date_bounds(self):
        for fetcher_class in (
            self.module.SpringerMetaFetcher,
            self.module.SpringerOpenAccessFetcher,
        ):
            with self.subTest(fetcher=fetcher_class.__name__), \
                    mock.patch.object(self.module, "get_config_value", return_value="test-key"), \
                    mock.patch.object(
                        self.module.urllib.request,
                        "urlopen",
                        return_value=FakeResponse({"records": []}),
                    ) as urlopen:
                fetcher_class().search("GNSS NLOS", year_from=2022, year_to=2026)

            query = parse_qs(urlsplit(urlopen.call_args.args[0].full_url).query)
            self.assertEqual(
                query["q"],
                ["keyword:GNSS NLOS datefrom:2022-01-01 dateto:2026-12-31"],
            )

    def test_scopus_uses_non_phrase_year_query_and_recent_sort(self):
        payload = {"search-results": {"entry": []}}
        with mock.patch.object(self.module, "get_config_value", return_value="test-key"), \
                mock.patch.object(
                    self.module.urllib.request,
                    "urlopen",
                    return_value=FakeResponse(payload),
                ) as urlopen:
            self.module.ScopusFetcher().search(
                "GNSS NLOS", year_from=2022, year_to=2026, sort_mode="recent"
            )

        query = parse_qs(urlsplit(urlopen.call_args.args[0].full_url).query)
        self.assertEqual(
            query["query"],
            ["TITLE-ABS-KEY(GNSS NLOS) AND PUBYEAR > 2021 AND PUBYEAR < 2027"],
        )
        self.assertEqual(query["sort"], ["-coverDate"])


if __name__ == "__main__":
    unittest.main()
