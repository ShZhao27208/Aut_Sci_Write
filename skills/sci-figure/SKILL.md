---
name: sci-figure
description: Extracts figures and sub-figures from academic PDF papers. Supports Fig/Figure, Scheme, Chart, Supplementary Figure, Extended Data Figure (Nature), and Chinese equivalents (图/方案/示意图/附图/补充图). Sub-figure label recognition supports (a)/(A)/a)/(i)/(1)/a. formats. High-quality PNG output at configurable DPI. Use when user asks to "extract figure", "截取文献图片", "提取子图", "get figure from paper", "Scheme", "方案图", "补充图", "Supplementary Figure", or "Extended Data".
author: Shuo Zhao         
license: MIT
copyright: © 2026 Shuo Zhao. All rights reserved. 
original: This is an original work created by the author. No reproduction or redistribution without permission.  
---

# Sci-Figure — Scientific Figure Extractor

Precisely extract figures and sub-figures from academic PDF papers.

## Script Directory

Scripts in `scripts/` subdirectory. Replace `${SKILL_DIR}` with this SKILL.md's directory path.

| Script | Purpose |
|--------|---------|
| `scripts/extract_figure.py` | Main CLI for figure extraction |

## Preferences (EXTEND.md)

Use Bash to check EXTEND.md existence (priority order):

```bash
# Check project-level first
test -f .baoyu-skills/Sh_Sci_Fig/EXTEND.md && echo "project"

# Then user-level (cross-platform: $HOME works on macOS/Linux/WSL)
test -f "$HOME/.baoyu-skills/Sh_Sci_Fig/EXTEND.md" && echo "user"
```

**EXTEND.md Supports**: Default DPI | Default output format | Tesseract path

## Usage

```bash
python ${SKILL_DIR}/scripts/extract_figure.py <input.pdf> [options]
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
| `--format` | | Output format | png |

## Examples

```bash
# Extract Figure 2, sub-figure c
python ${SKILL_DIR}/scripts/extract_figure.py paper.pdf -f 2 -s c

# Extract entire Figure 3
python ${SKILL_DIR}/scripts/extract_figure.py paper.pdf -f 3

# List all available figures in a PDF
python ${SKILL_DIR}/scripts/extract_figure.py paper.pdf --list

# Extract all figures
python ${SKILL_DIR}/scripts/extract_figure.py paper.pdf --all

# Custom output directory and DPI
python ${SKILL_DIR}/scripts/extract_figure.py paper.pdf -f 2 -s c -o ./output/ -d 300
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
| pdfplumber | Text + coordinate extraction (locate "Figure X" labels) |
| PyMuPDF (fitz) | PDF → high-quality image rendering (600 DPI) |
| opencv-python | Boundary detection, contour analysis |
| Pillow | Final cropping, format conversion |
| pytesseract | OCR for sub-figure label recognition |

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

