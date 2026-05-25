"""PDF assembly from downloaded manhwa panel images with metadata and quality presets."""

from __future__ import annotations

import io
from typing import Optional

from PIL import Image

from config import PDF_FORMAT, PDF_QUALITY, QUALITY_PRESETS, DEFAULT_QUALITY


def images_to_pdf(
    image_data_list: list[bytes],
    output_path: str,
    title: Optional[str] = None,
    author: Optional[str] = None,
    subject: Optional[str] = None,
    quality: str = DEFAULT_QUALITY,
) -> str:
    """Convert a list of image byte arrays into a single PDF file.

    Args:
        image_data_list: Ordered list of raw image bytes (one per page).
        output_path: File path for the output PDF.
        title: PDF document title metadata.
        author: PDF document author metadata.
        subject: PDF document subject metadata.
        quality: Quality preset key ('low', 'medium', 'high').

    Returns:
        The output_path string on success.
    """
    if not image_data_list:
        raise ValueError("No images provided for PDF generation")

    dpi, _ = QUALITY_PRESETS.get(quality, QUALITY_PRESETS[DEFAULT_QUALITY])

    pages: list[Image.Image] = []
    for img_bytes in image_data_list:
        img = Image.open(io.BytesIO(img_bytes))
        if img.mode == "RGBA":
            img = img.convert("RGB")
        pages.append(img)

    first_page = pages[0]
    rest_pages = pages[1:] if len(pages) > 1 else []

    # Build PDF info dict for metadata
    pdf_info = {}
    if title:
        pdf_info["Title"] = title
    if author:
        pdf_info["Author"] = author
    if subject:
        pdf_info["Subject"] = subject

    first_page.save(
        output_path,
        format="PDF",
        save_all=True,
        append_images=rest_pages,
        resolution=dpi,
        quality=PDF_QUALITY,
        pdf_info=pdf_info or None,
    )

    for img in pages:
        img.close()

    return output_path


def merge_chapter_images(chapter_image_lists: list[list[bytes]]) -> list[bytes]:
    """Flatten multiple chapters' image lists into a single ordered list.

    Args:
        chapter_image_lists: List of image-byte-lists, one per chapter, in order.

    Returns:
        Combined flat list of all image bytes.
    """
    merged = []
    for chapter_images in chapter_image_lists:
        merged.extend(chapter_images)
    return merged
