"""LaTeX formula rendering with local and network fallbacks."""

from __future__ import annotations

import hashlib
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

import requests


def _default_cache_dir() -> str:
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    return str(Path(base) / "Aut_Sci_Write" / "sci-ppt" / "formulas")


class FormulaRenderer:
    def __init__(self, dpi: int = 300, output_dir: Optional[str] = None):
        self.dpi = dpi
        self.output_dir = output_dir or _default_cache_dir()
        self.latex_available = self._check_latex()
        os.makedirs(self.output_dir, exist_ok=True)

    @staticmethod
    def _check_latex() -> bool:
        try:
            result = subprocess.run(["pdflatex", "--version"], capture_output=True, timeout=5)
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def render_formula(
        self,
        latex_code: str,
        color: str = "000000",
        background: str = "FFFFFF",
    ) -> Optional[str]:
        formula_hash = hashlib.md5(f"{latex_code}_{color}_{background}".encode("utf-8")).hexdigest()[:12]
        output_path = os.path.join(self.output_dir, f"formula_{formula_hash}.png")
        if os.path.exists(output_path):
            return output_path

        if self.latex_available:
            rendered = self._render_local(latex_code, output_path, color, background)
            if rendered:
                return rendered
        return self._render_fallback(latex_code, output_path, color, background)

    def _render_local(self, latex_code: str, output_path: str, color: str, background: str) -> Optional[str]:
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                tex_file = os.path.join(tmpdir, "formula.tex")
                self._create_tex_file(tex_file, latex_code, color, background)
                subprocess.run(
                    [
                        "pdflatex",
                        "-interaction=nonstopmode",
                        "-no-shell-escape",
                        "-output-directory",
                        tmpdir,
                        tex_file,
                    ],
                    capture_output=True,
                    timeout=20,
                    check=False,
                )
                pdf_file = os.path.join(tmpdir, "formula.pdf")
                if os.path.exists(pdf_file):
                    target_prefix = output_path[:-4] if output_path.endswith(".png") else output_path
                    result = subprocess.run(
                        ["pdftoppm", "-png", "-r", str(self.dpi), "-singlefile", pdf_file, target_prefix],
                        capture_output=True,
                        timeout=20,
                        check=False,
                    )
                    if result.returncode == 0 and os.path.exists(output_path):
                        return output_path
        except Exception:
            return None
        return None

    @staticmethod
    def _create_tex_file(tex_file: str, latex_code: str, color: str, background: str) -> None:
        tex_content = f"""\\documentclass[12pt]{{article}}
\\usepackage{{amsmath,amssymb,xcolor}}
\\usepackage[margin=0.1in]{{geometry}}
\\pagecolor[HTML]{{{background}}}
\\color[HTML]{{{color}}}
\\begin{{document}}
\\thispagestyle{{empty}}
\\[ {latex_code} \\]
\\end{{document}}"""
        with open(tex_file, "w", encoding="utf-8") as handle:
            handle.write(tex_content)

    def _render_fallback(self, latex_code: str, output_path: str, color: str, background: str) -> Optional[str]:
        try:
            import matplotlib

            matplotlib.use("Agg")
            import matplotlib.pyplot as plt

            fig = plt.figure(figsize=(0.1, 0.1), dpi=self.dpi)
            fig.text(0.5, 0.5, f"${latex_code}$", ha="center", va="center", fontsize=18, color=f"#{color}")
            fig.savefig(output_path, bbox_inches="tight", pad_inches=0.05, facecolor=f"#{background}", transparent=True)
            plt.close(fig)
            if os.path.exists(output_path):
                return output_path
        except Exception:
            pass

        try:
            encoded = requests.utils.quote(latex_code)
            # Honor the dpi/color args; use a transparent background (codecogs
            # \bg{transparent}) instead of a hardcoded white background.
            url = (
                f"https://latex.codecogs.com/png.image?"
                f"\\dpi{{{self.dpi}}}\\bg{{transparent}}\\fg{{{color}}}\\inline {encoded}"
            )
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                with open(output_path, "wb") as handle:
                    handle.write(response.content)
                return output_path
        except Exception:
            pass
        return None
