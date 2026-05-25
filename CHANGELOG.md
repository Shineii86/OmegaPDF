## [2.1.0] - 2026-05-25
- Telegram Bot integration: send PDFs directly to Telegram instead of downloading locally
- Bot token + chat ID configuration in Setup cell with test connection button
- "Send to Telegram" checkbox on every download cell (URL, slug, merge, batch)
- Dedicated "Send local PDF to Telegram" cell for uploading existing files
- New `telegram.py` module for standalone Python usage
- Batch Telegram send with 1s delay between messages to avoid rate limits

## [2.0.0] - 2026-05-25
- Concurrent panel downloads using ThreadPoolExecutor (up to 8x faster)
- Auto-retry with exponential backoff on failed image downloads
- Quality presets: Low (72 DPI), Medium (150 DPI), High (300 DPI / print quality)
- Custom page range support (e.g. download only pages 5-15)
- Merge multiple chapters into a single PDF
- Save PDFs directly to Google Drive
- Progress bars with tqdm for all downloads
- Thumbnail preview before full chapter download
- Browse trending/popular series cell
- PDF metadata embedding (title, author, subject)
- Batch download with optional ZIP packaging
- Modularized Python backend: config, fetcher, pdf_builder, main

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
