"""Enhanced PPT agent adapted for the packaged aut_sci_ppt layout.

This module uses academic parsing and optional formula rendering, then standard
PPT generation.
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from .academic_parser import AcademicParser, ContentType
from .agent import PPTAgent
from .generator.formula_renderer import FormulaRenderer


class EnhancedPPTAgent(PPTAgent):
    def __init__(self, config=None, scene: str = "academic", enable_enhancements: bool = True):
        super().__init__(config=config, scene=scene)
        self.enable_enhancements = enable_enhancements
        self.academic_parser = AcademicParser() if enable_enhancements else None
        self.formula_renderer = FormulaRenderer(dpi=300) if enable_enhancements else None

    def generate_from_pdf(
        self,
        pdf_path: str,
        output_path: str = "output.pptx",
        enable_formula_rendering: bool = True,
    ) -> Optional[str]:
        if not os.path.exists(pdf_path):
            self.logger.error("PDF not found: %s", pdf_path)
            return None

        try:
            pdf_text = self._extract_pdf_text(pdf_path)
            if not self.enable_enhancements or not self.academic_parser:
                return self.generate(pdf_text, output_path)

            self.academic_parser.parse_text(pdf_text)
            rendered_formulas = {}
            if enable_formula_rendering and self.formula_renderer:
                rendered_formulas = self._render_formulas()

            ppt_input = self._prepare_ppt_input(rendered_formulas)
            result = self.generate(ppt_input, output_path)
            self._record_run("success", pdf_path, output_path)
            return result
        except Exception as exc:
            self._record_run("failure", pdf_path, str(exc))
            self.logger.error("Enhanced PDF workflow failed: %s", exc)
            raise

    @staticmethod
    def _extract_pdf_text(pdf_path: str) -> str:
        import fitz

        text_parts = []
        with fitz.open(pdf_path) as doc:
            for page in doc:
                text_parts.append(page.get_text())
        return "\n\n".join(text_parts)

    def _render_formulas(self) -> Dict[str, str]:
        rendered = {}
        if not self.academic_parser or not self.formula_renderer:
            return rendered
        for block in self.academic_parser.get_blocks_by_type(ContentType.FORMULA):
            for formula in block.formulas:
                path = self.formula_renderer.render_formula(formula)
                if path:
                    rendered[formula] = path
        return rendered

    def _prepare_ppt_input(self, rendered_formulas: Dict[str, str]) -> str:
        if not self.academic_parser:
            return ""
        lines = [self.academic_parser.generate_ppt_outline()]
        if rendered_formulas:
            lines.append("")
            lines.append("1. Rendered formulas")
            for formula, image_path in rendered_formulas.items():
                # Emit the figure-comment format that TextParser.FIG_RE parses so
                # the rendered PNG is embedded. Pipes would break the regex groups,
                # so sanitise the label only.
                label = formula.replace("|", "/").strip()
                lines.append(
                    f"<!-- fig: {label} | path={image_path} | position=full -->"
                )
        return "\n".join(lines).strip()

    def _record_run(self, status: str, pdf_path: str, detail: str) -> None:
        log_dir = Path.home() / ".aut_sci_write" / "sci-ppt"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / "enhanced_runs.log"
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(f"{datetime.now().isoformat()}\t{status}\t{pdf_path}\t{detail}\n")

    def get_enhancement_status(self) -> Dict:
        return {
            "enhancements_enabled": self.enable_enhancements,
            "academic_parser": self.academic_parser is not None,
            "formula_renderer": self.formula_renderer is not None,
            "human_review": "not included",
        }


def create_enhanced_ppt(user_input: str, output_path: str = "output.pptx") -> str:
    return EnhancedPPTAgent().generate(user_input, output_path)


def create_enhanced_ppt_from_pdf(
    pdf_path: str,
    output_path: str = "output.pptx",
    enable_formula_rendering: bool = True,
) -> Optional[str]:
    return EnhancedPPTAgent().generate_from_pdf(
        pdf_path,
        output_path,
        enable_formula_rendering=enable_formula_rendering,
    )
