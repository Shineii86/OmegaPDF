"""OmegaPDF main orchestrator — ties fetching and PDF creation together.

Calls OmegaScans upstream API directly (no external API dependency).
"""

from __future__ import annotations

import os
from typing import Optional

from fetcher import get_chapter_images, download_image, download_images_concurrent
from pdf_builder import images_to_pdf, merge_chapter_images


def build_chapter_pdf(
    slug: str,
    chapter: str,
    output_dir: str = ".",
    output_name: Optional[str] = None,
    quality: str = "medium",
    page_range: Optional[tuple[int, int]] = None,
    title: Optional[str] = None,
    author: Optional[str] = None,
    use_concurrent: bool = True,
    progress_callback=None,
) -> str:
    """Fetch a chapter's panels and assemble them into a PDF.

    Args:
        slug: Series slug (e.g. 'solo-leveling').
        chapter: Chapter identifier (e.g. 'chapter-1').
        output_dir: Directory to save the PDF.
        output_name: Custom filename (without extension).
        quality: Quality preset ('low', 'medium', 'high').
        page_range: Optional (start, end) 1-indexed inclusive page range.
        title: PDF title metadata (auto-generated if None).
        author: PDF author metadata.
        use_concurrent: Use parallel downloads (default True).
        progress_callback: Optional callable(completed, total) for progress updates.

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

    # Apply page range filter (1-indexed inclusive)
    if page_range:
        start, end = page_range
        start = max(1, start) - 1  # convert to 0-indexed
        end = min(end, len(image_urls))
        image_urls = image_urls[start:end]

    if output_name is None:
        safe_title = series_title.replace(" ", "_").replace("/", "_")
        safe_chapter = chapter_name.replace(" ", "_").replace("/", "_")
        output_name = f"{safe_title}_{safe_chapter}"

    output_path = os.path.join(output_dir, f"{output_name}.pdf")

    pdf_title = title or f"{series_title} — {chapter_name}"

    if use_concurrent:
        image_bytes_list = download_images_concurrent(image_urls, progress_callback)
    else:
        image_bytes_list = []
        for idx, url in enumerate(image_urls, 1):
            img_bytes = download_image(url)
            image_bytes_list.append(img_bytes)
            if progress_callback:
                progress_callback(idx, len(image_urls))

    images_to_pdf(
        image_bytes_list,
        output_path,
        title=pdf_title,
        author=author,
        subject=f"{series_title}",
        quality=quality,
    )
    return output_path


def build_merged_pdf(
    slug: str,
    chapters: list[str],
    output_dir: str = ".",
    output_name: Optional[str] = None,
    quality: str = "medium",
    author: Optional[str] = None,
    use_concurrent: bool = True,
    progress_callback=None,
) -> str:
    """Download multiple chapters and merge them into a single PDF.

    Args:
        slug: Series slug.
        chapters: List of chapter identifiers in order.
        output_dir: Directory to save the PDF.
        output_name: Custom filename (without extension).
        quality: Quality preset ('low', 'medium', 'high').
        author: PDF author metadata.
        use_concurrent: Use parallel downloads.
        progress_callback: Optional callable(completed, total, chapter_name).

    Returns:
        Full path to the generated PDF file.
    """
    all_chapter_images: list[list[bytes]] = []
    series_title = slug

    for ch in chapters:
        ch_data = get_chapter_images(slug, ch)
        if not ch_data.get("success"):
            raise RuntimeError(f"Failed to fetch {ch}: {ch_data.get('error', 'Unknown')}")

        data = ch_data["data"]
        image_urls = data.get("images", [])
        series_title = data.get("series", {}).get("title", slug)
        chapter_name = data.get("name", ch)

        if use_concurrent:
            ch_bytes = download_images_concurrent(image_urls)
        else:
            ch_bytes = [download_image(u) for u in image_urls]

        all_chapter_images.append(ch_bytes)

        if progress_callback:
            progress_callback(ch, chapter_name)

    merged_bytes = merge_chapter_images(all_chapter_images)

    if output_name is None:
        safe_title = series_title.replace(" ", "_").replace("/", "_")
        first_ch = chapters[0].replace("chapter-", "ch")
        last_ch = chapters[-1].replace("chapter-", "ch")
        output_name = f"{safe_title}_{first_ch}-{last_ch}"

    output_path = os.path.join(output_dir, f"{output_name}.pdf")

    images_to_pdf(
        merged_bytes,
        output_path,
        title=f"{series_title} — {chapters[0]} to {chapters[-1]}",
        author=author,
        subject=series_title,
        quality=quality,
    )
    return output_path
