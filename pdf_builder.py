"""PDF assembly from downloaded manhwa panel images with metadata and quality presets."""

from __future__ import annotations

import io
from typing import Optional

from PIL import Image

from config import PDF_FORMAT, PDF_QUALITY, QUALITY_PRESETS, DEFAULT_QUALITY

# Standard PDF page width in points (72 DPI) — A4-ish width for manhwa panels
_PDF_PAGE_WIDTH_PT = 595  # ~210mm (A4 width)


def _fit_image_to_page(img: Image.Image, target_width: int) -> Image.Image:
    """Resize image so it fills exactly target_width pixels with no extra space.

    For manhwa/manga panels, each image should stretch to full page width
    with zero margins or gaps between panels.
    """
    orig_w, orig_h = img.size
    if orig_w == target_width:
        return img

    scale = target_width / orig_w
    target_height = int(orig_h * scale)
    return img.resize((target_width, target_height), Image.LANCZOS)


def images_to_pdf(
    image_data_list: list[bytes],
    output_path: str,
    title: Optional[str] = None,
    author: Optional[str] = None,
    subject: Optional[str] = None,
    quality: str = DEFAULT_QUALITY,
) -> str:
    """Convert a list of image byte arrays into a single PDF file.

    Each image fills the full page width — zero gaps between panels.
    """
    if not image_data_list:
        raise ValueError("No images provided for PDF generation")

    dpi, _ = QUALITY_PRESETS.get(quality, QUALITY_PRESETS[DEFAULT_QUALITY])

    # Use a consistent pixel width so all pages align perfectly
    # Higher DPI = more pixels = sharper output but larger file
    pixel_width = int(_PDF_PAGE_WIDTH_PT * dpi / 72)

    pages: list[Image.Image] = []
    for img_bytes in image_data_list:
        img = Image.open(io.BytesIO(img_bytes))
        if img.mode == "RGBA":
            img = img.convert("RGB")
        img = _fit_image_to_page(img, pixel_width)
        pages.append(img)

    first_page = pages[0]
    rest_pages = pages[1:] if len(pages) > 1 else []

    pdf_info = {}
    if title:
        pdf_info["Title"] = title
    if author:
        pdf_info["Author"] = author
    if subject:
        pdf_info["Subject"] = subject

    # resolution=72 because we already sized pixels to fill the page exactly
    first_page.save(
        output_path,
        format="PDF",
        save_all=True,
        append_images=rest_pages,
        resolution=72,
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
