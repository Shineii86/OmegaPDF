"""Panel and chapter data fetching from OmegaScans upstream API with inbuilt normalization.

Ported from OmegaAPI (src/lib/omega.ts) — calls OmegaScans directly,
normalizes responses, and provides concurrent downloads with retries.
"""

from __future__ import annotations

import re
import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

from config import (
    OMEGA_BASE_URL,
    MEDIA_CDN,
    UPSTREAM_SERIES_LIST,
    UPSTREAM_SERIES_SEARCH,
    UPSTREAM_SERIES_DETAIL,
    UPSTREAM_CHAPTERS_LIST,
    UPSTREAM_CHAPTER_CONTENT,
    REQUEST_TIMEOUT,
    MAX_WORKERS,
    MAX_RETRIES,
    RETRY_BACKOFF,
)

HEADERS = {
    "User-Agent": "OmegaPDF/3.0",
    "Accept": "application/json",
}


# ==================== NORMALIZATION HELPERS ====================
# Ported from omega.ts normalizeImageUrl / stripHtml

def _normalize_image_url(url: str) -> str:
    """Convert relative image paths to full CDN URLs.

    OmegaScans returns relative paths like 'uploads/series/slug/chapter/001.jpg'.
    This prepends the media CDN base URL.
    """
    if not url:
        return ""
    if url.startswith("http://") or url.startswith("https://"):
        return url
    return f"{MEDIA_CDN}/{url.lstrip('/')}"


def _strip_html(raw: str) -> str:
    """Strip HTML tags and decode common entities."""
    if not raw:
        return ""
    text = re.sub(r"<[^>]*>", "", raw)
    text = (
        text.replace("&ldquo;", "\u201c")
        .replace("&rdquo;", "\u201d")
        .replace("&mdash;", "\u2014")
        .replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&nbsp;", " ")
    )
    return re.sub(r"\s+", " ", text).strip()


# ==================== UPSTREAM FETCHER ====================

def _fetch_upstream(path: str, retries: int = 1) -> dict:
    """Generic GET request to the upstream OmegaScans API with retry on 5xx."""
    url = f"{OMEGA_BASE_URL}{path}"
    last_error = None

    for attempt in range(retries + 1):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            if resp.ok:
                return resp.json()
            if resp.status_code >= 500 and attempt < retries:
                time.sleep(1)
                continue
            resp.raise_for_status()
        except (requests.HTTPError, requests.ConnectionError, requests.Timeout) as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(1)
                continue

    raise last_error or RuntimeError(f"OmegaScans API error: {url}")


# ==================== NORMALIZERS ====================

def _normalize_series_list_item(raw: dict) -> dict:
    """Normalize a series from the list/search endpoint (fewer fields)."""
    schedule = raw.get("release_schedule") or {}
    days = [day.capitalize() for day, active in schedule.items() if active]

    free_chapters = raw.get("free_chapters") or []
    return {
        "id": raw["id"],
        "title": raw["title"],
        "slug": raw["series_slug"],
        "description": _strip_html(raw.get("description", "")),
        "thumbnail": _normalize_image_url(raw.get("thumbnail", "")),
        "cover": _normalize_image_url(raw.get("thumbnail", "")),
        "status": raw.get("status", ""),
        "type": raw.get("series_type", ""),
        "rating": round(raw.get("rating", 0), 2),
        "totalViews": raw.get("total_views", 0),
        "alternativeNames": raw.get("alternative_names", ""),
        "author": "",
        "studio": "",
        "releaseYear": "",
        "releaseSchedule": days,
        "tags": [],
        "chaptersCount": len(free_chapters),
        "bookmarksCount": 0,
        "isComingSoon": raw.get("is_coming_soon", False),
        "badge": raw.get("badge"),
        "createdAt": raw.get("created_at", ""),
        "updatedAt": raw.get("updated_at", ""),
        "chapters": [
            {
                "id": ch["id"],
                "name": ch["chapter_name"],
                "title": None,
                "slug": ch["chapter_slug"],
                "thumbnail": "",
                "price": 0,
                "isFree": True,
                "createdAt": ch.get("created_at", ""),
                "index": ch.get("meta", {}).get("index", ""),
                "url": f"/chapter/{raw['series_slug']}/{ch['chapter_slug']}",
            }
            for ch in free_chapters
        ],
        "url": f"/series/{raw['series_slug']}",
    }


def _normalize_series_detail(raw: dict) -> dict:
    """Normalize a series from the detail endpoint (extra metadata)."""
    schedule = raw.get("release_schedule") or {}
    days = [day.capitalize() for day, active in schedule.items() if active]
    tags = raw.get("tags") or []
    meta = raw.get("meta") or {}

    return {
        "id": raw["id"],
        "title": raw["title"],
        "slug": raw["series_slug"],
        "description": _strip_html(raw.get("description", "")),
        "thumbnail": _normalize_image_url(raw.get("thumbnail", "")),
        "cover": _normalize_image_url(raw.get("thumbnail", "")),
        "status": raw.get("status", ""),
        "type": raw.get("series_type", ""),
        "rating": round(raw.get("rating", 0), 2),
        "totalViews": raw.get("total_views", 0),
        "alternativeNames": raw.get("alternative_names", ""),
        "author": raw.get("author", ""),
        "studio": raw.get("studio", ""),
        "releaseYear": raw.get("release_year", ""),
        "releaseSchedule": days,
        "tags": [t["name"] if isinstance(t, dict) else t for t in tags],
        "chaptersCount": int(meta.get("chapters_count", "0") or "0"),
        "bookmarksCount": int(meta.get("who_bookmarked_count", "0") or "0"),
        "isComingSoon": False,
        "badge": None,
        "createdAt": "",
        "updatedAt": "",
        "chapters": [],
        "url": f"/series/{raw['series_slug']}",
    }


def _normalize_chapter(raw: dict, series_slug: str) -> dict:
    """Normalize a chapter entry from the chapters list endpoint."""
    meta = raw.get("meta") or {}
    return {
        "id": raw["id"],
        "name": raw["chapter_name"],
        "title": raw.get("chapter_title"),
        "slug": raw["chapter_slug"],
        "thumbnail": _normalize_image_url(raw.get("chapter_thumbnail", "")),
        "price": raw.get("price", 0),
        "isFree": raw.get("price", 0) == 0,
        "createdAt": raw.get("created_at", ""),
        "index": meta.get("index", ""),
        "url": f"/chapter/{series_slug}/{raw['chapter_slug']}",
    }


def _normalize_chapter_content(raw_chapter: dict) -> dict:
    """Normalize chapter content (the reader payload with images)."""
    ch = raw_chapter.get("chapter", raw_chapter)
    ch_data = ch.get("chapter_data") or {}
    raw_images = ch_data.get("images") or []
    images = [_normalize_image_url(img) for img in raw_images]

    series = ch.get("series") or {}
    return {
        "id": ch["id"],
        "name": ch["chapter_name"],
        "title": ch.get("chapter_title"),
        "slug": ch["chapter_slug"],
        "index": ch.get("index", ""),
        "price": ch.get("price", 0),
        "isFree": ch.get("price", 0) == 0,
        "thumbnail": _normalize_image_url(ch.get("chapter_thumbnail", "")),
        "images": images,
        "pageCount": len(images),
        "createdAt": ch.get("created_at", ""),
        "series": {
            "id": series.get("id", 0),
            "title": series.get("title", ""),
            "slug": series.get("series_slug", ""),
            "thumbnail": _normalize_image_url(series.get("thumbnail", "")),
            "status": series.get("status", ""),
            "description": _strip_html(series.get("description", "")),
        },
        "url": f"/chapter/{series.get('series_slug', '')}/{ch['chapter_slug']}",
    }


# ==================== PUBLIC API ====================

def search_series(query: str, page: int = 1, per_page: int = 20) -> dict:
    """Search for series by title. Returns normalized results."""
    path = UPSTREAM_SERIES_SEARCH.format(query=requests.utils.quote(query), page=page)
    raw = _fetch_upstream(path)
    return {
        "success": True,
        "data": [_normalize_series_list_item(s) for s in raw.get("data", [])],
        "pagination": _extract_pagination(raw.get("meta")),
    }


def list_series(page: int = 1, per_page: int = 20) -> dict:
    """Browse available series with pagination. Returns normalized results."""
    path = UPSTREAM_SERIES_LIST.format(page=page)
    raw = _fetch_upstream(path)
    return {
        "success": True,
        "data": [_normalize_series_list_item(s) for s in raw.get("data", [])],
        "pagination": _extract_pagination(raw.get("meta")),
    }


def get_series(slug: str) -> dict:
    """Get full details for a single series. Returns normalized result."""
    path = UPSTREAM_SERIES_DETAIL.format(slug=slug)
    raw = _fetch_upstream(path)
    return {
        "success": True,
        "data": _normalize_series_detail(raw),
    }


def get_chapters(slug: str) -> dict:
    """Get the chapter list for a series.

    First fetches the series detail to get the series ID, then queries chapters.
    """
    series_resp = get_series(slug)
    if not series_resp.get("success"):
        return {"success": False, "error": "Series not found"}
    series_data = series_resp["data"]
    series_id = series_data["id"]

    path = UPSTREAM_CHAPTERS_LIST.format(page=1, per_page=10000, series_id=series_id)
    raw = _fetch_upstream(path)
    return {
        "success": True,
        "data": [_normalize_chapter(ch, slug) for ch in raw.get("data", [])],
        "pagination": _extract_pagination(raw.get("meta")),
    }


def get_chapter_images(slug: str, chapter: str) -> dict:
    """Get image URLs for a specific chapter. Returns normalized result compatible with OmegaPDF."""
    path = UPSTREAM_CHAPTER_CONTENT.format(slug=slug, chapter=chapter)
    raw = _fetch_upstream(path)
    content = _normalize_chapter_content(raw)

    # Return in the format main.py expects: { success, data: { images, series, name } }
    return {
        "success": True,
        "data": {
            "images": content["images"],
            "name": content["name"],
            "series": content["series"],
            "pageCount": content["pageCount"],
        },
    }


def _extract_pagination(meta: Optional[dict]) -> dict:
    """Extract pagination metadata from upstream meta object."""
    if not meta:
        return {
            "total": 0, "perPage": 0, "currentPage": 1,
            "lastPage": 1, "hasNext": False, "hasPrevious": False,
        }
    return {
        "total": meta.get("total", 0),
        "perPage": meta.get("per_page", 0),
        "currentPage": meta.get("current_page", 1),
        "lastPage": meta.get("last_page", 1),
        "hasNext": bool(meta.get("next_page_url")),
        "hasPrevious": bool(meta.get("previous_page_url")),
    }


# ==================== IMAGE DOWNLOADS ====================

def download_image(url: str) -> bytes:
    """Download a single image with retry and exponential backoff.

    Raises:
        requests.HTTPError: If all retries are exhausted.
    """
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            return response.content
        except (requests.HTTPError, requests.ConnectionError, requests.Timeout):
            if attempt == MAX_RETRIES - 1:
                raise
            time.sleep(RETRY_BACKOFF * (2 ** attempt))
    raise RuntimeError("Unreachable")


def download_images_concurrent(
    urls: list[str],
    progress_callback=None,
) -> list[bytes]:
    """Download multiple images in parallel using a thread pool.

    Args:
        urls: List of image URLs to download.
        progress_callback: Optional callable(completed, total) called after each image.

    Returns:
        List of image bytes in the same order as urls.
    """
    results: dict[int, bytes] = {}
    total = len(urls)

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        future_to_idx = {
            pool.submit(download_image, url): idx
            for idx, url in enumerate(urls)
        }
        completed = 0
        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            results[idx] = future.result()
            completed += 1
            if progress_callback:
                progress_callback(completed, total)

    return [results[i] for i in range(total)]
