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
    Quality preset controls JPEG compression (low=60, medium=80, high=95).
    """
    if not image_data_list:
        raise ValueError("No images provided for PDF generation")

    _, quality_label = QUALITY_PRESETS.get(quality, QUALITY_PRESETS[DEFAULT_QUALITY])
    jpeg_quality = {"low": 60, "medium": 80, "high": 95}.get(quality, 85)

    # Convert all images to JPEG bytes
    jpeg_list: list[bytes] = []
    for img_bytes in image_data_list:
        img = Image.open(io.BytesIO(img_bytes))
        if img.mode == "RGBA":
            img = img.convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=jpeg_quality)
        jpeg_list.append(buf.getvalue())
        img.close()

    # ── Build PDF manually ──
    pdf_objects: list[bytes] = []
    xref_offsets: list[int] = []
    obj_counter = 1

    def _add(raw: bytes) -> int:
        """Append a PDF object, record its byte offset, return its ID."""
        xref_offsets.append(len(b"%PDF-1.4\n") + sum(len(o) for o in pdf_objects))
        oid = obj_counter
        pdf_objects.append(raw)
        obj_counter += 1
        return oid

    # Obj 1: Pages placeholder (will be patched later)
    pages_id = _add(b"")

    # Obj 2: Catalog
    catalog_id = _add(
        b"1 0 obj\n<< /Type /Catalog /Pages " + str(pages_id).encode() + b" 0 R >>\nendobj\n"
    )

    # Build page objects
    page_ids: list[int] = []
    for jpeg_data in jpeg_list:
        img = Image.open(io.BytesIO(jpeg_data))
        w_px, h_px = img.size
        img.close()

        # Object: XObject (the JPEG image stream)
        img_header = (
            f"{obj_counter} 0 obj\n"
            f"<< /Type /XObject /Subtype /Image /Width {w_px} /Height {h_px} "
            f"/ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode "
            f"/Length {len(jpeg_data)} >>\n"
            f"stream\n"
        ).encode()
        img_oid = _add(img_header + jpeg_data + b"\nendstream\nendobj\n")

        # Object: Page — MediaBox = exact image pixel dimensions (1 px = 1 pt)
        page_raw = (
            f"{obj_counter} 0 obj\n"
            f"<< /Type /Page /Parent {pages_id} 0 R "
            f"/MediaBox [0 0 {w_px} {h_px}] "
            f"/Contents {img_oid} 0 R >>\n"
            f"endobj\n"
        ).encode()
        page_oid = _add(page_raw)
        page_ids.append(page_oid)

    # Patch Pages object with the actual Kids list
    kids_str = " ".join(f"{pid} 0 R" for pid in page_ids)
    pdf_objects[0] = (
        f"{pages_id} 0 obj\n"
        f"<< /Type /Pages /Kids [{kids_str}] /Count {len(page_ids)} >>\n"
        f"endobj\n"
    ).encode()

    # Optional: Info object for title/author metadata
    info_id = 0
    if title or author:
        info_parts = []
        if title:
            safe = title.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            info_parts.append(f"/Title ({safe})")
        if author:
            safe = author.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            info_parts.append(f"/Author ({safe})")
        if subject:
            safe = subject.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            info_parts.append(f"/Subject ({safe})")
        info_raw = (
            f"{obj_counter} 0 obj\n<< {' '.join(info_parts)} >>\nendobj\n"
        ).encode()
        info_id = _add(info_raw)

        # Patch Catalog to include /Info
        cat_parts = (
            f"{catalog_id} 0 obj\n"
            f"<< /Type /Catalog /Pages {pages_id} 0 R /Info {info_id} 0 R >>\n"
            f"endobj\n"
        ).encode()
        pdf_objects[catalog_id - 1] = cat_parts

    # ── Assemble the PDF file ──
    header = b"%PDF-1.4\n"
    body = b"".join(pdf_objects)
    xref_start = len(header) + len(body)

    # Cross-reference table
    xref_lines = [f"0 {obj_counter}\n".encode(), b"0000000000 65535 f \n"]
    for offset in xref_offsets:
        xref_lines.append(f"{offset:010d} 00000 n \n".encode())
    xref = b"xref\n" + b"".join(xref_lines)

    # Trailer
    trailer = (
        f"trailer\n<< /Size {obj_counter} /Root {catalog_id} 0 R >>\n"
        f"startxref\n{xref_start}\n%%EOF\n"
    ).encode()

    with open(output_path, "wb") as f:
        f.write(header + body + xref + trailer)

    return output_path


def merge_chapter_images(chapter_image_lists: list[list[bytes]]) -> list[bytes]:
    """Flatten multiple chapters' image lists into a single ordered list."""
    merged = []
    for chapter_images in chapter_image_lists:
        merged.extend(chapter_images)
    return merged
