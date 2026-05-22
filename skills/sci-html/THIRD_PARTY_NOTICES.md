# Third-Party Reference Notes

This implementation was designed after reviewing local copies of these open-source projects: reveal.js, Marp, Slidev, Quarto CLI, impress.js, and Presenton.

No full runtime framework is bundled in this prototype. The code is a clean-room lightweight implementation that borrows architectural ideas: slide navigation, hash routing, print CSS, Markdown slide syntax, and layout naming.

If future versions copy substantial source code from those projects, preserve their license and attribution notices. For Presenton, also review NOTICE requirements.

## Bundled Aut_Sci_Write Components

This skill bundles a local copy of one Aut_Sci_Write skill and depends on another at runtime:

- `sci-extract`, copied under `src/sci_html/integrations/extract/`, for structured PDF insight extraction.
- `sci-figure`, installed as a runtime dependency (not bundled), for PDF figure detection and image export.

Keep their original copyright and license obligations when redistributing. The `sci-figure` package declares AGPL-3.0-or-later in its setup metadata, so distribution may impose AGPL obligations on the combined package.
