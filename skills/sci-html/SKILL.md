---
name: sci-html
description: Generate academic presentation-style HTML slide decks and browser reports from PDFs, structured text, Markdown, paper summaries, outlines, or research notes. Use whenever the user wants to convert a scientific paper PDF directly into an interactive HTML report, clickable web presentation, shareable browser deck, or PPT-like HTML output with figures, structured insights, section pages, and offline deck-directory output. In the Aut_Sci_Write suite, choose this skill when the user wants HTML/web output; choose sci-ppt when they explicitly need a .pptx file.
author: Shuo Zhao
license: MIT
copyright: Copyright (c) 2026 Shuo Zhao. All rights reserved.
triggers:
  - html slides
  - HTML report
  - paper to html
  - browser presentation
  - interactive paper report
  - web presentation
  - clickable slides
  - academic HTML
  - Markdown to HTML deck
  - PDF to HTML report
  - html academic report
  - web academic report
  - interactive literature report
  - paper html report
  - ppt-like html
  - offline html deck
---

# Sci HTML

Use this skill to create browser-based academic slide decks inside the Aut_Sci_Write suite. It can work from prepared Markdown/JSON, or run the full paper workflow from PDF to structured insights, extracted figures, and HTML deck.

Use `sci-html` for shareable browser output. Use `sci-ppt` when the user needs a real `.pptx`. Use `sci-extract` when the user only wants a text analysis without a presentation artifact.

## When To Use

Use this skill when the user asks for HTML slides, clickable presentation webpages, browser-based academic presentations, Markdown to slide deck, paper summary to web presentation, PDF paper to HTML report, or a PPT-like HTML file with left/right navigation.

## Output

Always create a deck directory containing `index.html`, `deck.json`, `assets/style.css`, `assets/deck.js`, and copied local figures under `assets/figures/`.

Do not create single-file HTML. Directory output is the standard mode because it keeps the presentation maintainable and avoids oversized embedded assets.

## Workflow

1. Parse the user's source content into a deck model.
2. Add cover, table of contents, section, summary, and ending slides when appropriate.
3. Validate image paths and slide structure.
4. Render HTML, CSS, and JS.
5. Tell the user the output path and navigation controls.

## PDF Paper Workflow

For a source PDF, use the integrated `paper` command rather than requiring separate `sci-extract` or `sci-figure` skills:

```bash
python scripts/generate_html_deck.py paper paper.pdf -o out/paper-report --author "Presenter"
```

When working from the Aut_Sci_Write repository root, run:

```bash
python skills/sci-html/scripts/generate_html_deck.py paper paper.pdf -o skills/sci-html/out/paper-report --author "Presenter"
```

This writes `structured_insights.json`, `figure_manifest.json`, extracted files under `figures/`, a generated `{paper-stem}-deck.md`, and the final `index.html`.

The PDF workflow uses bundled integrations copied from `sci-extract` and `sci-figure`. It requires `PyMuPDF`, `pdfplumber`, `numpy`, `opencv-python`, `Pillow`, and `pytesseract`; Tesseract OCR is optional and only affects subfigure OCR.

The integrated `sci-extract` logic detects original research versus review literature. Original research decks emphasize problem, method, results, innovation, applications, and limits. Review, survey, systematic review, scoping review, and meta-analysis decks emphasize scope, taxonomy, evidence base, consensus, controversies, evidence quality, research gaps, future directions, and important figures or tables. Use `--paper-type auto|research|review` when the user wants to override automatic routing.

## Presentation Markup

- Put `layout: section` at the top of a Markdown slide block to create a chapter divider.
- Put `subtitle: 01` below `layout: section` to show the chapter number.
- Use `**key phrase**` or `==key phrase==` for red emphasis.
- Keep bullets concise; generated bullet slides use numbered key-point cards by default.
- When a slide has only one or two content bullets, render it as plain statements without visible item numbers.
- Long slide and paper titles are automatically fitted by shrinking the heading and expanding its line width so the title stays on the page.
- Sparse slides automatically receive subtle topic motifs from title and bullet keywords, so visually empty areas are filled without requiring extra image assets.

## Navigation Controls

Generated decks support mouse click, left-third click for previous slide, explicit Prev/Next buttons, left/right arrow keys, space, Home/End, F fullscreen, and URL hash state such as `#/3`.

## Design Rules

Keep slides academic, readable, and presentation-oriented. Avoid long paragraphs. Prefer figures, concise numbered points, section breaks, and strong hierarchy. Use decorative but unobtrusive visual patterns to reduce empty space. Keep section and ending slides centered. Escape user-provided HTML by default. Do not write API keys or `.env` values into generated decks.

## Aut_Sci_Write Integration

- `sci-html` is one of the suite's output skills alongside `sci-ppt`.
- The paper workflow locally reuses Aut_Sci_Write extraction and figure-processing logic, so users do not need to manually chain `sci-extract` and `sci-figure` before generating a deck.
- Keep generated decks under `out/` or another user-selected output folder. These outputs are intentionally ignored by the repository/package rules.
- Do not create or require skill-local `.env` files for this skill; it runs offline except for optional dependencies installed by the user.
