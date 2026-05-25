"""PDF assembly from downloaded manhwa panel images."""

from __future__ import annotations

import io
from typing import Optional

from PIL import Image

from config import PDF_DPI, PDF_FORMAT, PDF_QUALITY


def images_to_pdf(
    image_data_list: list[bytes],
    output_path: str,
    title: Optional[str] = None,
) -> str:
    """Convert a list of image byte arrays into a single PDF file.

    Args:
        image_data_list: Ordered list of raw image bytes (one per page).
        output_path: File path for the output PDF.
        title: Optional PDF document title metadata.

    Returns:
        The output_path string on success.
    """
    if not image_data_list:
        raise ValueError("No images provided for PDF generation")

    pages: list[Image.Image] = []
    for idx, img_bytes in enumerate(image_data_list):
        img = Image.open(io.BytesIO(img_bytes))
        if img.mode == "RGBA":
            img = img.convert("RGB")
        pages.append(img)

    first_page = pages[0]
    rest_pages = pages[1:] if len(pages) > 1 else []

    first_page.save(
        output_path,
        format="PDF",
        save_all=True,
        append_images=rest_pages,
        resolution=PDF_DPI,
        quality=PDF_QUALITY,
    )

    for img in pages:
        img.close()

    return output_path
