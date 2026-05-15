# sci-html

`sci-html` is the Aut_Sci_Write browser-presentation skill. It generates academic HTML slide deck directories from paper PDFs, Markdown, structured outlines, JSON deck data, or paper summaries.

Use it when the desired artifact is an interactive `index.html` report or clickable browser deck. Use `sci-ppt` instead when the desired artifact is a real `.pptx`.

## Quick Start

```bash
python scripts/generate_html_deck.py examples/sample_outline.md -o out/sample-deck
```

From the Aut_Sci_Write repository root:

```bash
python skills/sci-html/scripts/generate_html_deck.py generate skills/sci-html/examples/sample_outline.md -o skills/sci-html/out/sample-deck
```

Open `out/sample-deck/index.html` in a browser. Directory output is the only supported output mode because it keeps HTML, CSS, JavaScript, and copied figures cleanly separated.

## Paper To HTML

`sci-html` can also run as a paper-to-presentation skill. It bundles local extraction code derived from the suite's `sci-extract` and `sci-figure` skills so a PDF can become an HTML report in one step.

```bash
python scripts/generate_html_deck.py paper paper.pdf -o out/paper-report --author "Your Name"
```

From the Aut_Sci_Write repository root:

```bash
python skills/sci-html/scripts/generate_html_deck.py paper paper.pdf -o skills/sci-html/out/paper-report --author "Your Name"
```

Use `--paper-type auto|research|review` to override automatic routing. Research papers are organized around problem, method, results, innovation, applications, and limitations. Review literature is organized around scope, taxonomy, evidence base, consensus, controversy, evidence quality, gaps, and future directions.

This creates:

- `structured_insights.json`
- `figure_manifest.json`
- `figures/`
- `{paper-stem}-deck.md`
- `index.html`

Install the optional paper workflow dependencies first:

```bash
python -m pip install -r requirements.txt
```

When installed as part of Aut_Sci_Write, the repository root `requirements.txt` already includes the PDF and image-processing dependencies needed by `sci-html`.

## Controls

- Click: next slide
- Click left third of the screen: previous slide
- Right / Space / PageDown: next slide
- Left / PageUp: previous slide
- Home / End: first / last slide
- F: fullscreen
- On-screen `Prev` / `Next` buttons are included.

## Input Styles

Structured outline, Markdown slides with `---` separators, and JSON deck files are supported.

## Presentation Markup

- Use `layout: section` at the top of a slide block to create a chapter divider slide.
- Use `subtitle: 01` with a section slide to show chapter numbering.
- Wrap important phrases with `**important**` or `==important==` to render them as red highlights.
- Bullet slides render as numbered key points by default.
- Slides with only one or two content bullets render those items without visible numbers.
- Very long titles automatically receive smaller heading sizes so they fit inside the slide.
- Sparse slides automatically receive a subtle topic motif based on the title and bullets, such as mechanism, bio, application, hybrid, risk, or control.

## Notes

This skill uses a native lightweight runtime rather than depending on reveal.js, Slidev, or Marp. It intentionally does not generate single-file HTML; use the generated deck directory for distribution.

Generated outputs should normally go under `out/`; Aut_Sci_Write ignores those folders for git and package publishing.
