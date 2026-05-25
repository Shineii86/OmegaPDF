"""OmegaPDF main orchestrator — ties fetching and PDF creation together."""

from __future__ import annotations

import os
from typing import Optional

from fetcher import get_series, get_chapter_images, download_image
from pdf_builder import images_to_pdf


def build_chapter_pdf(
    slug: str,
    chapter: str,
    output_dir: str = ".",
    output_name: Optional[str] = None,
) -> str:
    """Fetch a chapter's panels and assemble them into a PDF.

    Args:
        slug: Series slug (e.g. 'solo-leveling').
        chapter: Chapter identifier (e.g. 'chapter-1').
        output_dir: Directory to save the PDF.
        output_name: Custom filename (without extension). Defaults to
            '{series_title}_{chapter_name}.pdf'.

    Returns:
        Full path to the generated PDF file.
    """
    chapter_data = get_chapter_images(slug, chapter)
    if not chapter_data.get("success"):
        raise RuntimeError(chapter_data.get("error", "Failed to fetch chapter"))

    data = chapter_data["data"]
    image_urls: list[str] = data.get("images", [])
    if not image_urls:
        raise RuntimeError("No images found for this chapter")

    series_info = data.get("series", {})
    series_title = series_info.get("title", slug)
    chapter_name = data.get("name", chapter)

    if output_name is None:
        safe_title = series_title.replace(" ", "_").replace("/", "_")
        safe_chapter = chapter_name.replace(" ", "_").replace("/", "_")
        output_name = f"{safe_title}_{safe_chapter}"

    output_path = os.path.join(output_dir, f"{output_name}.pdf")

    print(f"Downloading {len(image_urls)} panels from '{series_title}' — {chapter_name}...")
    image_bytes_list = []
    for idx, url in enumerate(image_urls, 1):
        img_bytes = download_image(url)
        image_bytes_list.append(img_bytes)
        print(f"  [{idx}/{len(image_urls)}] Downloaded panel {idx}")

    print("Assembling PDF...")
    result_path = images_to_pdf(image_bytes_list, output_path, title=f"{series_title} — {chapter_name}")
    print(f"PDF saved to: {result_path}")
    return result_path
