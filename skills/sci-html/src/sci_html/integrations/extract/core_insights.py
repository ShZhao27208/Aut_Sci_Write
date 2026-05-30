"""Core Insights Extractor (trimmed vendored copy).

This is a focused subset of the sci-extract ``extract_core_insights`` module,
kept in-tree only to satisfy the sci-html paper pipeline, which uses
``CoreInsightsExtractor.extract_from_pdf``. The original CLI, batch processing,
and CSV/Markdown writers were intentionally removed to minimise duplication and
drift. For the full standalone tool, see the sci-extract skill.
"""

from __future__ import annotations

import re
from datetime import datetime


def ensure_pdf_dependencies():
    """Import heavy PDF dependencies lazily so the module stays importable."""
    try:
        import fitz  # PyMuPDF
        import pdfplumber
    except ImportError as exc:
        raise RuntimeError(
            "Required libraries not installed. Install with: "
            "pip install PyMuPDF pdfplumber"
        ) from exc
    return fitz, pdfplumber


class CoreInsightsExtractor:
    """Extract core insights from academic papers."""

    def __init__(self, verbose=False):
        self.verbose = verbose
        self.keywords = {
            'problem': ['research question', 'research objective', 'propose', 'aim', 'goal', 'problem', 'challenge'],
            'methodology': ['propose', 'method', 'algorithm', 'model', 'approach', 'develop', 'design', 'implement'],
            'results': ['result', 'finding', 'show', 'demonstrate', 'achieve', 'obtain', 'measure'],
            'innovation': ['novel', 'first', 'unlike', 'compared to', 'superior', 'advantage', 'new', 'innovative'],
            'application': ['application', 'potential', 'prospect', 'value', 'use', 'deployment', 'practical'],
            'limitations': ['limitation', 'challenge', 'future work', 'drawback', 'constraint', 'issue', 'problem']
        }
        self.review_keywords = {
            'scope': ['review', 'survey', 'scope', 'overview', 'field', 'literature', 'current status'],
            'taxonomy': ['taxonomy', 'classification', 'categorize', 'category', 'framework', 'types of', 'grouped into'],
            'selection': ['search strategy', 'database', 'inclusion criteria', 'exclusion criteria', 'eligible', 'screening', 'prisma', 'included studies'],
            'themes': ['theme', 'direction', 'approach', 'application', 'progress', 'trend', 'recent advances'],
            'consensus': ['consensus', 'consistent', 'agreement', 'generally', 'overall', 'evidence suggests', 'studies show'],
            'controversies': ['controversy', 'conflicting', 'inconsistent', 'heterogeneity', 'debate', 'disagreement', 'mixed results'],
            'evidence_quality': ['bias', 'quality', 'reproducibility', 'sample size', 'confounding', 'heterogeneity', 'limitation', 'risk of bias'],
            'gaps': ['gap', 'open question', 'future work', 'challenge', 'barrier', 'unresolved', 'needed'],
            'future': ['future direction', 'future perspective', 'outlook', 'next step', 'should be', 'need to'],
        }

    def extract_from_pdf(self, pdf_path, timeout=120, paper_type='auto'):
        """Extract insights from a single PDF."""
        start_time = datetime.now()

        try:
            text, metadata = self._extract_text_and_metadata(pdf_path)

            if not text:
                return self._error_result("no_text", "无法提取文本（可能是扫描版PDF，建议使用OCR工具如marker-pdf处理）", metadata, start_time)

            sections = self._identify_sections(text)
            resolved_type = self._detect_paper_type(text, metadata) if paper_type == 'auto' else paper_type
            if resolved_type == 'review':
                insights = self._extract_review_insights(sections)
            else:
                resolved_type = 'research'
                insights = {
                    'research_problem': self._extract_problem(sections),
                    'methodology': self._extract_methodology(sections),
                    'key_results': self._extract_results(sections),
                    'innovation': self._extract_innovation(sections),
                    'application': self._extract_application(sections),
                    'limitations': self._extract_limitations(sections),
                }
            confidence_scores = self._calculate_confidence_scores(insights, sections)
            elapsed = (datetime.now() - start_time).total_seconds()

            return {
                'metadata': metadata,
                'paper_type': resolved_type,
                'core_insights': insights,
                'confidence_scores': confidence_scores,
                'extraction_time': int(elapsed),
                'status': 'success',
            }

        except MemoryError:
            return self._error_result("pdf_too_large", "PDF文件过大，超出内存限制，建议分页处理", {}, start_time)
        except TimeoutError:
            return self._error_result("timeout", f"处理超时（>{timeout}s），文件可能过大或损坏", {}, start_time)
        except UnicodeDecodeError as e:
            return self._error_result("encoding", f"编码错误：{e}，建议用pdfplumber指定编码重试", {}, start_time)
        except Exception as e:
            # Classify by error message patterns before falling back to generic
            msg = str(e).lower()
            if "password" in msg or "encrypt" in msg:
                kind = "pdf_encrypted"
                detail = "PDF已加密，需要密码才能读取"
            elif "corrupt" in msg or "invalid" in msg or "eof" in msg:
                kind = "pdf_corrupt"
                detail = f"PDF文件损坏或格式无效：{e}"
            else:
                kind = "unknown"
                detail = str(e)
            return self._error_result(kind, detail, {}, start_time)

    def _extract_text_and_metadata(self, pdf_path):
        """Extract text and metadata from PDF"""
        doc = None
        try:
            fitz, pdfplumber = ensure_pdf_dependencies()
            # Use PyMuPDF for metadata
            doc = fitz.open(pdf_path)
            metadata = doc.metadata or {}

            # Extract text using pdfplumber
            text = ""
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() or ""

            # Parse metadata
            parsed_metadata = {
                'title': metadata.get('title', 'Unknown'),
                'authors': self._extract_authors(text),
                'journal': self._extract_journal(text),
                'year': self._extract_year(text),
                'doi': self._extract_doi(text),
                'pdf_path': str(pdf_path)
            }

            return text, parsed_metadata

        except RuntimeError:
            raise
        except Exception as e:
            if self.verbose:
                print(f"Error extracting text: {e}")
            raise
        finally:
            if doc is not None:
                doc.close()

    def _extract_authors(self, text):
        """Extract author names from text"""
        lines = text.split('\n')[:50]  # Check first 50 lines
        authors = []

        for line in lines:
            if any(keyword in line.lower() for keyword in ['author', 'by ', 'from ']):
                names = re.findall(r'[A-Z][a-z]+ [A-Z][a-z]+', line)
                authors.extend(names[:3])  # Limit to 3 authors
                break

        return authors[:5] if authors else []

    def _extract_journal(self, text):
        """Extract journal name from text"""
        patterns = [
            r'(?:Published in|Journal:|In )\s*([A-Z][^,\n]+)',
            r'([A-Z][a-zA-Z\s&]+)\s*(?:Volume|Vol\.|Issue|No\.)',
        ]

        for pattern in patterns:
            match = re.search(pattern, text[:1000])
            if match:
                return match.group(1).strip()

        return "Unknown"

    def _extract_year(self, text):
        """Extract publication year from text"""
        match = re.search(r'\b(20\d{2})\b', text[:1000])
        return int(match.group(1)) if match else None

    def _extract_doi(self, text):
        """Extract DOI from text"""
        match = re.search(r'(?:DOI|doi)[\s:]*([^\s\n]+)', text[:2000])
        return match.group(1) if match else ""

    def _identify_sections(self, text):
        """Identify major sections of the paper"""
        sections = {
            'full_text': text,
            'abstract': "",
            'introduction': "",
            'methodology': "",
            'results': "",
            'discussion': "",
            'conclusion': "",
            'taxonomy': "",
            'selection': "",
            'future': "",
            'limitations': "",
        }

        section_patterns = {
            'abstract': r'(?:^|\n)\s*(?:Abstract)',
            'introduction': r'(?:^|\n)\s*(?:1\.?\s+)?(?:Introduction|Background)',
            'methodology': r'(?:^|\n)\s*(?:2\.?\s+)?(?:Method|Methodology|Approach|Materials and Methods|Search Strategy|Data Sources)',
            'results': r'(?:^|\n)\s*(?:3\.?\s+)?(?:Result|Findings)',
            'discussion': r'(?:^|\n)\s*(?:4\.?\s+)?(?:Discussion)',
            'conclusion': r'(?:^|\n)\s*(?:5\.?\s+)?(?:Conclusion|Summary)',
            'taxonomy': r'(?:^|\n)\s*(?:\d+\.?\s+)?(?:Taxonomy|Classification|Framework|Categorization|Categories)',
            'selection': r'(?:^|\n)\s*(?:\d+\.?\s+)?(?:Search Strategy|Study Selection|Selection Criteria|Eligibility Criteria|Data Sources|Data Extraction|PRISMA)',
            'future': r'(?:^|\n)\s*(?:\d+\.?\s+)?(?:Future Directions|Future Perspectives|Outlook|Challenges and Future|Open Problems)',
            'limitations': r'(?:^|\n)\s*(?:\d+\.?\s+)?(?:Limitations|Evidence Quality|Risk of Bias)',
        }

        text_lower = text.lower()

        for section, pattern in section_patterns.items():
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                start = match.start()
                remaining = text_lower[start+100:]
                next_section = re.search(
                    r'(?:^|\n)\s*(?:\d+\.?\s+)?(?:Abstract|Introduction|Background|Method|Methodology|Approach|Search Strategy|Study Selection|Selection Criteria|Eligibility Criteria|Data Sources|Data Extraction|Taxonomy|Classification|Framework|Result|Findings|Discussion|Limitations|Future Directions|Future Perspectives|Outlook|Conclusion|Summary|References)',
                    remaining,
                    re.IGNORECASE,
                )

                if next_section:
                    end = start + 100 + next_section.start()
                else:
                    end = len(text)

                sections[section] = text[start:end]

        return sections

    def _detect_paper_type(self, text, metadata):
        """Detect whether the PDF is original research or review literature."""
        title = metadata.get('title') or ''
        front_matter = f"{title}\n{text[:8000]}".lower()
        review_patterns = [
            r'\breview\b',
            r'\bsurvey\b',
            r'\bsystematic review\b',
            r'\bmeta-analysis\b',
            r'\bmeta analysis\b',
            r'\bscoping review\b',
            r'\bbibliometric\b',
            r'\bliterature review\b',
            r'\bstate[- ]of[- ]the[- ]art\b',
            r'\brecent advances\b',
            r'\bfuture perspectives\b',
        ]
        review_hits = sum(1 for pattern in review_patterns if re.search(pattern, front_matter))
        research_signals = len(re.findall(r'\bwe (propose|develop|designed|conducted|evaluated|trained|synthesized)\b', front_matter))
        return 'review' if review_hits >= 1 and review_hits >= research_signals else 'research'

    def _extract_review_insights(self, sections):
        """Extract fields that matter for review, survey, and meta-analysis papers."""
        full_text = sections.get('full_text', '')
        intro_text = sections.get('abstract', '') + ' ' + sections.get('introduction', '')
        discussion_text = ' '.join([
            sections.get('discussion', ''),
            sections.get('limitations', ''),
            sections.get('future', ''),
            sections.get('conclusion', ''),
        ])

        return {
            'review_scope': self._extract_review_field(intro_text, self.review_keywords['scope'], limit=3),
            'review_type': self._extract_review_type(full_text),
            'taxonomy': self._extract_review_field(
                sections.get('taxonomy', '') + ' ' + full_text,
                self.review_keywords['taxonomy'],
                limit=5,
            ),
            'literature_selection': self._extract_review_field(
                sections.get('selection', '') + ' ' + sections.get('methodology', ''),
                self.review_keywords['selection'],
                limit=5,
            ),
            'major_themes': self._extract_review_field(
                intro_text + ' ' + sections.get('taxonomy', '') + ' ' + discussion_text,
                self.review_keywords['themes'],
                limit=5,
            ),
            'consensus_findings': self._extract_review_field(
                sections.get('results', '') + ' ' + discussion_text,
                self.review_keywords['consensus'],
                limit=4,
            ),
            'controversies': self._extract_review_field(
                discussion_text + ' ' + full_text,
                self.review_keywords['controversies'],
                limit=4,
            ),
            'evidence_quality': self._extract_review_field(
                sections.get('limitations', '') + ' ' + sections.get('selection', '') + ' ' + discussion_text,
                self.review_keywords['evidence_quality'],
                limit=4,
            ),
            'research_gaps': self._extract_review_field(
                discussion_text,
                self.review_keywords['gaps'],
                limit=5,
            ),
            'future_directions': self._extract_review_field(
                sections.get('future', '') + ' ' + sections.get('conclusion', ''),
                self.review_keywords['future'],
                limit=4,
            ),
            'key_tables_figures': self._extract_key_tables_figures(full_text),
        }

    def _extract_review_type(self, text):
        """Return a concise review subtype label."""
        text_lower = text[:12000].lower()
        if 'meta-analysis' in text_lower or 'meta analysis' in text_lower:
            return 'Meta-analysis'
        if 'systematic review' in text_lower or 'prisma' in text_lower:
            return 'Systematic review'
        if 'scoping review' in text_lower:
            return 'Scoping review'
        if 'bibliometric' in text_lower:
            return 'Bibliometric review'
        if 'survey' in text_lower:
            return 'Survey review'
        if 'review' in text_lower:
            return 'Narrative review'
        return 'Review type not explicit'

    def _extract_review_field(self, text, keywords, limit=4):
        """Extract review-relevant sentences, keeping output compact."""
        sentences = self._find_sentences_with_keywords(text, keywords)
        if not sentences:
            return ["Not found"]
        cleaned = []
        seen = set()
        for sentence in sentences:
            sentence = re.sub(r'\s+', ' ', sentence).strip()
            key = sentence.lower()[:120]
            if len(sentence) < 30 or key in seen:
                continue
            seen.add(key)
            cleaned.append(sentence)
            if len(cleaned) >= limit:
                break
        return cleaned if cleaned else ["Not found"]

    def _extract_key_tables_figures(self, text):
        """Extract captions for figures and tables that likely organize the review."""
        caption_pattern = r'\b(?:Figure|Fig\.|Table)\s*\d+[A-Za-z]?\s*[:.\-]?\s*([^\n]{20,220})'
        captions = []
        for match in re.finditer(caption_pattern, text):
            caption = re.sub(r'\s+', ' ', match.group(0)).strip()
            lowered = caption.lower()
            if any(term in lowered for term in [
                'taxonomy', 'classification', 'framework', 'overview', 'summary',
                'comparison', 'search', 'selection', 'prisma', 'forest', 'funnel',
                'evidence', 'workflow',
            ]):
                captions.append(caption)
            if len(captions) >= 6:
                break
        return captions if captions else ["Not found"]

    def _extract_problem(self, sections):
        """Extract research problem"""
        text = sections['introduction']
        sentences = self._find_sentences_with_keywords(text, self.keywords['problem'])
        if sentences:
            combined = ' '.join(sentences[-2:])  # Last 2 sentences usually have the problem
            return self._summarize_text(combined, max_length=2)
        return "Not found"

    def _extract_methodology(self, sections):
        """Extract research methodology"""
        text = sections['methodology']
        sentences = self._find_sentences_with_keywords(text, self.keywords['methodology'])
        if sentences:
            combined = ' '.join(sentences[:3])  # First 3 sentences usually describe method
            return self._summarize_text(combined, max_length=3)
        return "Not found"

    def _extract_results(self, sections):
        """Extract key results"""
        text = sections['results']
        sentences = self._find_sentences_with_keywords(text, self.keywords['results'])
        results = []
        for sentence in sentences[:5]:
            if any(char.isdigit() for char in sentence):
                results.append(sentence.strip())
        return results if results else ["Not found"]

    def _extract_innovation(self, sections):
        """Extract innovation points"""
        text = sections['discussion'] + ' ' + sections['conclusion']
        sentences = self._find_sentences_with_keywords(text, self.keywords['innovation'])
        innovations = []
        for sentence in sentences[:3]:
            innovations.append(sentence.strip())
        return innovations if innovations else ["Not found"]

    def _extract_application(self, sections):
        """Extract application value"""
        text = sections['conclusion'] + ' ' + sections['discussion']
        sentences = self._find_sentences_with_keywords(text, self.keywords['application'])
        if sentences:
            combined = ' '.join(sentences[:2])
            return self._summarize_text(combined, max_length=2)
        return "Not found"

    def _extract_limitations(self, sections):
        """Extract limitations"""
        text = sections['discussion'] + ' ' + sections['conclusion']
        sentences = self._find_sentences_with_keywords(text, self.keywords['limitations'])
        limitations = []
        for sentence in sentences[:2]:
            limitations.append(sentence.strip())
        return limitations if limitations else ["Not found"]

    def _find_sentences_with_keywords(self, text, keywords):
        """Find sentences containing keywords"""
        sentences = re.split(r'[.!?]\s+', text)
        matching = []
        for sentence in sentences:
            sentence_lower = sentence.lower()
            if any(keyword in sentence_lower for keyword in keywords):
                matching.append(sentence.strip())
        return matching

    def _summarize_text(self, text, max_length=2):
        """Simple text summarization"""
        sentences = re.split(r'[.!?]\s+', text)
        return '. '.join(sentences[:max_length]) + '.'

    def _calculate_confidence_scores(self, insights, sections):
        """Calculate confidence scores for each insight"""
        scores = {}

        for key, value in insights.items():
            if value == "Not found" or value == ["Not found"]:
                scores[key] = 0.0
            else:
                score = 0.5

                if isinstance(value, list):
                    if len(value) > 0 and value[0] != "Not found":
                        score += 0.2
                else:
                    if len(str(value)) > 50:
                        score += 0.2

                section_map = {
                    'research_problem': 'introduction',
                    'methodology': 'methodology',
                    'key_results': 'results',
                    'innovation': 'discussion',
                    'application': 'conclusion',
                    'limitations': 'discussion',
                    'review_scope': 'introduction',
                    'review_type': 'full_text',
                    'taxonomy': 'taxonomy',
                    'literature_selection': 'selection',
                    'major_themes': 'discussion',
                    'consensus_findings': 'results',
                    'controversies': 'discussion',
                    'evidence_quality': 'limitations',
                    'research_gaps': 'future',
                    'future_directions': 'future',
                    'key_tables_figures': 'full_text',
                }

                if section_map.get(key) in sections and sections[section_map[key]]:
                    score += 0.3

                scores[key] = min(score, 1.0)

        return scores

    def _error_result(self, error_kind, error_detail, metadata, start_time):
        """Generate a structured error result.

        error_kind is a machine-readable code:
          pdf_corrupt    — file is damaged / invalid format
          pdf_encrypted  — file is password-protected
          pdf_too_large  — out of memory
          timeout        — processing took too long
          encoding       — unicode / codec failure
          no_text        — text layer absent (scanned PDF, needs OCR)
          unknown        — uncategorised; see error_detail
        """
        elapsed = (datetime.now() - start_time).total_seconds()
        suggestions = {
            "no_text":       "使用 marker-pdf 或 tesseract-ocr skill 转换后重试",
            "pdf_corrupt":   "尝试用 pdfplumber 修复，或重新下载原始文件",
            "pdf_encrypted": "联系论文来源获取密码，或使用解密工具",
            "pdf_too_large": "使用 --pages 参数分批处理",
            "timeout":       "增加 timeout 参数，或分批处理",
            "encoding":      "以 latin-1 或 gbk 重试提取",
            "unknown":       "查看 error_detail 手动诊断",
        }
        return {
            'metadata': metadata,
            'core_insights': {k: 'Error' for k in
                              ['research_problem', 'methodology', 'key_results',
                               'innovation', 'application', 'limitations']},
            'confidence_scores': {k: 0.0 for k in
                                  ['research_problem', 'methodology', 'key_results',
                                   'innovation', 'application', 'limitations']},
            'extraction_time': int(elapsed),
            'status': 'error',
            'error_kind': error_kind,
            'error_detail': error_detail,
            'suggestion': suggestions.get(error_kind, suggestions['unknown']),
        }
