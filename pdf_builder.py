"""PDF assembly from downloaded manhwa panel images with metadata and quality presets."""

from __future__ import annotations

import io
from typing import Optional

from PIL import Image

from config import PDF_QUALITY, QUALITY_PRESETS, DEFAULT_QUALITY


def images_to_pdf(
    image_data_list: list[bytes],
    output_path: str,
    title: Optional[str] = None,
    author: Optional[str] = None,
    subject: Optional[str] = None,
    quality: str = DEFAULT_QUALITY,
) -> str:
    """Convert a list of image byte arrays into a single PDF file.

    Each page is exactly the image size — zero margins, zero gaps.
    """
    if not image_data_list:
        raise ValueError("No images provided for PDF generation")

    # Convert all images to JPEG bytes (consistent format for PDF)
    jpeg_list: list[bytes] = []
    for img_bytes in image_data_list:
        img = Image.open(io.BytesIO(img_bytes))
        if img.mode == "RGBA":
            img = img.convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=PDF_QUALITY)
        jpeg_list.append(buf.getvalue())
        img.close()

    # Build PDF manually — each page = exact image size, no margins
    from struct import pack

    objects: list[bytes] = []
    offsets: list[int] = []
    obj_id = 1

    def add_obj(data: bytes) -> int:
        nonlocal obj_id
        offsets.append(sum(len(o) for o in objects) + sum(8 for _ in objects))
        objects.append(data)
        current = obj_id
        obj_id += 1
        return current

    # Catalog
    pages_id = add_obj(b"")  # placeholder for Pages
    catalog_id = add_obj(
        f"1 0 obj\n<< /Type /Catalog /Pages {pages_id} 0 R >>\nendobj\n".encode()
    )

    # Build page objects
    page_ids: list[int] = []
    for jpeg_data in jpeg_list:
        img = Image.open(io.BytesIO(jpeg_data))
        w_px, h_px = img.size
        img.close()

        # Page size in points (72 DPI) — exact pixel-to-point mapping
        w_pt = w_px
        h_pt = h_px

        img_obj_id = add_obj(
            f"{obj_id} 0 obj\n<< /Type /XObject /Subtype /Image /Width {w_px} /Height {h_px} "
            f"/ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length {len(jpeg_data)} >>\n"
            f"stream\n".encode()
            + jpeg_data
            + b"\nendstream\nendobj\n"
        )

        page_id = add_obj(
            f"2 0 obj\n<< /Type /Page /Parent {pages_id} 0 R "
            f"/MediaBox [0 0 {w_pt} {h_pt}] "
            f"/Contents {img_obj_id} 0 R >>\nendobj\n".encode()
        )
        page_ids.append(page_id)

    # Fix Pages object
    kids = " ".join(f"{pid} 0 R" for pid in page_ids)
    objects[0] = (
        f"{pages_id} 0 obj\n<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>\nendobj\n".encode()
    )

    # Title metadata in Catalog
    if title:
        # Escape PDF string special chars
        safe_title = title.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        objects[catalog_id - 1] = (
            f"{catalog_id} 0 obj\n<< /Type /Catalog /Pages {pages_id} 0 R "
            f"/Info {add_obj(f'1 0 obj\n<< /Title ({safe_title}) >>\nendobj\n'.encode())} 0 R >>\nendobj\n".encode()
        )

    # Assemble PDF
    header = b"%PDF-1.4\n"
    body = b"".join(objects)
    xref_offset = len(header) + len(body)

    xref = b"xref\n"
    xref += f"0 {obj_id}\n".encode()
    xref += b"0000000000 65535 f \n"
    for off in offsets:
        xref += f"{off:010d} 00000 n \n".encode()

    trailer = f"trailer\n<< /Size {obj_id} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode()

    with open(output_path, "wb") as f:
        f.write(header + body + xref + trailer)

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
