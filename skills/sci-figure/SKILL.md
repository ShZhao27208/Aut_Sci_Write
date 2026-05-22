---
name: sci-figure
description: Extracts figures and sub-figures from academic PDF papers. Supports Fig/Figure, Scheme, Chart, Supplementary Figure, Extended Data Figure (Nature), and Chinese equivalents (图/方案/示意图/附图/补充图). Sub-figure label recognition supports (a)/(A)/a)/(i)/(1)/a. formats. High-quality PNG output at configurable DPI. Use when user asks to "extract figure", "截取文献图片", "提取子图", "get figure from paper", "Scheme", "方案图", "补充图", "Supplementary Figure", or "Extended Data".
author: Shuo Zhao         
license: MIT
copyright: © 2026 Shuo Zhao. All rights reserved.
triggers:
  - 提取图片
  - 截取文献图片
  - 提取子图
  - 提取附图
  - 补充图
  - 方案图
  - 示意图
  - 图片提取
  - extract figure
  - extract subfigure
  - get figure from paper
  - Supplementary Figure
  - Extended Data
  - Scheme
  - figure extraction
---

# Sci-Figure — Scientific Figure Extractor

Precisely extract figures and sub-figures from academic PDF papers.

## Installation

Install the package from the skill directory before first use:

```bash
cd ${SKILL_DIR}
pip install -e .
```

This registers the `sh-sci-fig` CLI command. Requires Tesseract OCR:
- Windows: `winget install UB-Mannheim.TesseractOCR`
- Linux: `apt install tesseract-ocr`
- macOS: `brew install tesseract`

## Preferences (EXTEND.md)

Use Bash to check EXTEND.md existence (priority order):

```bash
# Check project-level first
test -f .baoyu-skills/sci-figure/EXTEND.md && echo "project"

# Then user-level (cross-platform: $HOME works on macOS/Linux/WSL)
test -f "$HOME/.baoyu-skills/sci-figure/EXTEND.md" && echo "user"
```

**EXTEND.md Supports**: Default DPI | Default output format | Tesseract path

## Usage

```bash
sh-sci-fig <input.pdf> [options]
```

## Options

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `<input>` | | PDF file path | Required |
| `--figure` | `-f` | Figure number (1, 2, 3...) | Required (except --list/--all) |
| `--subfigure` | `-s` | Sub-figure label (a, b, c...) | None (returns whole figure) |
| `--output` | `-o` | Output directory | Current directory |
| `--dpi` | `-d` | Output resolution | 600 |
| `--list` | `-l` | List all available figure numbers | false |
| `--all` | | Extract all figures | false |
| `--format` | | Output format (png/jpg) | png |
| `--strategy` | | Extraction strategy: hybrid/native/cv | hybrid |
| `--ocr` | | OCR engine: tesseract/easyocr/none | tesseract |
| `--render-page` | | Render full page with annotations | false |
| `--annotate` | | Draw bounding boxes on rendered page | false |
| `--bbox` | | Manual bbox override (x0,y0,x1,y1 in px) | None |
| `--no-trim` | | Disable whitespace trimming | false |
| `--debug` | | Enable debug logging | false |
| `--quiet` | `-q` | Suppress info messages | false |

## Examples

```bash
# Extract Figure 2, sub-figure c
sh-sci-fig paper.pdf -f 2 -s c

# Extract entire Figure 3
sh-sci-fig paper.pdf -f 3

# List all available figures in a PDF
sh-sci-fig paper.pdf --list

# Extract all figures
sh-sci-fig paper.pdf --all

# Custom output directory and DPI
sh-sci-fig paper.pdf -f 2 -s c -o ./output/ -d 300

# Use EasyOCR for sub-figure label detection
sh-sci-fig paper.pdf --all --ocr easyocr

# CV-only strategy (skip native extraction)
sh-sci-fig paper.pdf --all --strategy cv

# Render page with annotated bounding boxes (debugging)
sh-sci-fig paper.pdf -f 1 --render-page --annotate

# Manual bbox extraction (multimodal correction)
sh-sci-fig paper.pdf -f 1 --bbox 100,200,800,1200
```

**Output**:
```
Extracted: figure_2c.png (1920x1080, 600 DPI)
```

## Error Handling

| Scenario | Behavior |
|----------|----------|
| Figure number not found | Error + list all available figure numbers |
| OCR recognition failed | Return entire figure region |
| Sub-figure split failed | Return entire figure region |
| No sub-figure labels found | Return entire figure region |

## Tech Stack

| Library | Role |
|---------|------|
| pdfplumber | Text + coordinate extraction (caption detection) |
| PyMuPDF (fitz) | Native image extraction + high-quality page rendering |
| opencv-python | CV region detection, connected-component analysis, content validation |
| Pillow | Final cropping, format conversion |
| pytesseract | OCR for sub-figure label recognition (default) |
| easyocr | Alternative OCR engine (optional, `pip install sci-figure[ocr]`) |
| numpy | Image array operations |

## Extraction Engines (v2)

| Engine | Priority | Best For |
|--------|----------|----------|
| Native (PyMuPDF) | 1st | Raster images embedded in PDF |
| CV (connected-component) | 2nd | Vector graphics, colored plots |
| Caption-anchored | 3rd | Fallback when above engines fail |

The `hybrid` strategy (default) tries all three in order and validates results.

## Detected Figure Fields

| Field | Type | Description |
|-------|------|-------------|
| `number` | int | Figure number |
| `page` | int | Page index (0-based) |
| `bbox` | tuple | Crop region in pixels |
| `bbox_pdf` | tuple | Crop region in PDF points |
| `caption` | str | Caption text (truncated to 200 chars) |
| `caption_full` | str | Full caption text (no truncation) |
| `caption_bbox_pdf` | tuple | Caption bounding box in PDF points |
| `sublabels` | list[str] | Sub-figure labels, e.g. `["a","b","c"]` |
| `sublabel_details` | list[dict] | Labels with detected format, e.g. `{"label":"a","format":"(a)"}` |
| `figure_type` | str | One of: `figure`, `scheme`, `chart`, `supplementary`, `extended_data` |
| `is_supplementary` | bool | True for `supplementary` and `extended_data` types |
| `image` | ndarray | Cropped figure image (numpy array) |

## Extension Support

Custom configurations via EXTEND.md. See **Preferences** section for paths and supported options.





---

## © License & Copyright

**Aut_Sci_Write** — Autonomous Scientific Writer

- **Author**: Shuo Zhao
- **License**: MIT License
- **Copyright**: © 2026 Shuo Zhao. All rights reserved.
- **Original Work**: This is an original work created by the author. No reproduction, redistribution, or commercial use without explicit permission.
  **Permission is hereby granted**, free of charge, to any person obtaining a copy of this software... (**See the LICENSE file in the root directory for the full MIT terms.**)

---

*This skill is part of the Aut_Sci_Write suite. For full license terms, see the [LICENSE](../LICENSE) file in the project root.*
---

