# Sh_Sci_Fig — Scientific Figure Extractor

Precisely extract figures and sub-figures from academic PDF papers.

## Features

- **Automatic figure detection** — Locates `Figure N` / `Fig. N` captions and determines image boundaries
- **Sub-figure splitting** — Splits composite figures into individual panels (a), (b), (c)... using white-space analysis + OCR
- **High-quality output** — Renders at configurable DPI (default 600) for publication-ready images
- **Robust fallback** — When OCR fails, falls back to caption-guided grid splitting

## Installation

### Prerequisites

- Python 3.9+
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract)
  - Windows: `winget install UB-Mannheim.TesseractOCR`
  - Linux: `apt install tesseract-ocr`
  - macOS: `brew install tesseract`

### Install

```bash
git clone https://github.com/xssjqx/Sh_Sci_Fig.git
cd Sh_Sci_Fig
pip install -r requirements.txt
```

## Usage

### Extract a specific figure

```bash
python scripts/extract_figure.py paper.pdf -f 3
```

### Extract a sub-figure

```bash
python scripts/extract_figure.py paper.pdf -f 2 -s c
```

### List all figures in a PDF

```bash
python scripts/extract_figure.py paper.pdf --list
```

### Extract all figures

```bash
python scripts/extract_figure.py paper.pdf --all -o ./output/
```

### Custom DPI and format

```bash
python scripts/extract_figure.py paper.pdf -f 2 -d 300 --format jpg -o ./output/
```

## CLI Options

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `<input>` | | PDF file path | Required |
| `--figure` | `-f` | Figure number to extract | Required* |
| `--subfigure` | `-s` | Sub-figure label (a, b, c...) | None |
| `--output` | `-o` | Output directory | `.` |
| `--dpi` | `-d` | Rendering resolution | 600 |
| `--list` | `-l` | List available figures | |
| `--all` | | Extract all figures | |
| `--format` | | `png` or `jpg` | `png` |
| `--quiet` | `-q` | Suppress info messages | |

*Required unless using `--list` or `--all`

## Output Naming

| Mode | Filename |
|------|----------|
| Whole figure | `figure_3.png` |
| Sub-figure | `figure_3c.png` |

## Architecture

```
src/
├── pdf_parser.py          # PDF rendering (PyMuPDF) + text extraction (pdfplumber)
├── figure_detector.py     # Caption detection + figure boundary computation
├── subfigure_splitter.py  # White-space grid splitting + OCR label assignment
├── image_processor.py     # Image saving + filename generation
├── exceptions.py          # Custom exception hierarchy
└── utils.py               # Logging, path validation, dependency checks
```

### How It Works

1. **Text extraction** — pdfplumber extracts all text with coordinates from each page
2. **Caption detection** — Regex matches `Fig. N` / `Figure N` at line start to find captions
3. **Boundary computation** — Analyzes text gaps above each caption to determine figure region
4. **Page rendering** — PyMuPDF renders the page at high DPI, then crops the figure region
5. **Sub-figure splitting** — White-space projection analysis finds grid structure; OCR + caption labels assign panel identifiers

## Dependencies

| Library | Role |
|---------|------|
| [pdfplumber](https://github.com/jsvine/pdfplumber) | Text + coordinate extraction |
| [PyMuPDF](https://pymupdf.readthedocs.io/) | PDF → image rendering |
| [opencv-python](https://opencv.org/) | Image processing |
| [Pillow](https://pillow.readthedocs.io/) | Image format conversion |
| [pytesseract](https://github.com/madmaze/pytesseract) | OCR for sub-figure labels |
| [NumPy](https://numpy.org/) | Array operations |

## Error Handling

| Scenario | Behavior |
|----------|----------|
| PDF not found | Clear error message with path |
| PDF encrypted | Error suggesting decrypted version |
| Figure not found | Error listing available figure numbers |
| OCR fails | Falls back to caption-guided grid splitting |
| Sub-figure not found | Returns entire figure with warning |

## License

AGPL-3.0-or-later — see [LICENSE](LICENSE).

**Note**: This project uses [PyMuPDF (fitz)](https://pymupdf.readthedocs.io/), which is licensed under AGPL v3. Therefore, this entire project is also licensed under AGPL v3 or later.
