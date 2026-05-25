# OmegaPDF

Download manhwa panels from [OmegaScans](https://omegascans.org) and generate PDFs using the [OmegaAPI](https://omegaapi.vercel.app).

## Features

- Search and browse manhwa series
- List chapters for any series
- Download chapter panels and assemble into a single PDF
- Batch download multiple chapters at once
- Works in Google Colab with zero setup

## Quick Start

### Google Colab (Recommended)

1. Open `OmegaPDF.ipynb` in [Google Colab](https://colab.research.google.com/)
2. Run the setup cell
3. Search for a series, pick a chapter, generate a PDF

### Local Usage

```bash
pip install -r requirements.txt
```

```python
from main import build_chapter_pdf

# Download Chapter 1 of Solo Leveling as PDF
build_chapter_pdf("solo-leveling", "chapter-1")
```

## Project Structure

```
OmegaPDF/
├── OmegaPDF.ipynb    # Google Colab notebook
├── config.py         # API endpoints and settings
├── fetcher.py        # API client for OmegaAPI
├── pdf_builder.py    # Image-to-PDF assembly
├── main.py           # Orchestrator
├── requirements.txt  # Python dependencies
├── CHANGELOG.md      # Version history
└── README.md
```

## API Reference

This project uses the [OmegaAPI](https://github.com/Shineii86/OmegaAPI) — a free, public API for OmegaScans content.

| Endpoint | Description |
|----------|-------------|
| `/api/v1/series` | Browse all series |
| `/api/v1/series/{slug}` | Series details + chapters |
| `/api/v1/chapter/{slug}/{chapter}` | Chapter images |
| `/api/v1/search?q={query}` | Search series |

## License

This project is for educational purposes only. All manhwa content belongs to their respective owners.
