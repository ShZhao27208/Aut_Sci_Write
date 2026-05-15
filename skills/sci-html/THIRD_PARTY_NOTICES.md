# Third-Party Reference Notes

This implementation was designed after reviewing local copies of these open-source projects: reveal.js, Marp, Slidev, Quarto CLI, impress.js, and Presenton.

No full runtime framework is bundled in this prototype. The code is a clean-room lightweight implementation that borrows architectural ideas: slide navigation, hash routing, print CSS, Markdown slide syntax, and layout naming.

If future versions copy substantial source code from those projects, preserve their license and attribution notices. For Presenton, also review NOTICE requirements.

## Bundled Aut_Sci_Write Components

This skill now bundles local copies of two Aut_Sci_Write skills so `sci-html` can run as a standalone paper-to-HTML workflow:

- `sci-extract`, copied under `src/sci_html/integrations/extract/`, for structured PDF insight extraction.
- `sci-figure`, copied under `src/sci_html/integrations/figure/`, for PDF figure detection and image export.

Keep their original copyright and license obligations when redistributing this standalone skill. In particular, the source `sci-figure` package declares AGPL-3.0-or-later in its setup metadata, so distribution may impose AGPL obligations on the combined package.
