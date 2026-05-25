## [1.2.0] - 2026-05-25
- Added "Download from URL" cell — paste an OmegaScans URL directly to get a PDF
- Parses `https://omegascans.org/series/{slug}/chapter-{num}` automatically

## [1.1.0] - 2026-05-25
- Modularized codebase into separate modules: config, fetcher, pdf_builder, main
- Created Google Colab notebook (OmegaPDF.ipynb) with interactive UI for browsing, searching, and downloading chapters as PDF
- Added proper project structure with requirements.txt
- Improved error handling and progress feedback during downloads

## [1.0.0] - 2026-05-25
- Initial release: single-script Colab notebook for fetching manhwa panels from OmegaAPI and generating PDFs
