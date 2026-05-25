"""Panel and chapter data fetching from OmegaAPI."""

from __future__ import annotations

import requests
from typing import Optional

from config import (
    BASE_URL,
    SERIES_ENDPOINT,
    SERIES_DETAIL_ENDPOINT,
    CHAPTERS_ENDPOINT,
    CHAPTER_DETAIL_ENDPOINT,
    SEARCH_ENDPOINT,
    REQUEST_TIMEOUT,
)


def _get(path: str, params: Optional[dict] = None) -> dict:
    """Make a GET request to the OmegaAPI and return the JSON response."""
    url = f"{BASE_URL}{path}"
    response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.json()


def search_series(query: str, page: int = 1, per_page: int = 20) -> dict:
    """Search for series by title.

    Returns:
        dict with 'success', 'data' (list of series), and optional 'pagination'.
    """
    return _get(SEARCH_ENDPOINT, params={"q": query})


def list_series(page: int = 1, per_page: int = 20) -> dict:
    """Browse available series with pagination.

    Returns:
        dict with 'success', 'data' (list of series), and 'pagination'.
    """
    return _get(SERIES_ENDPOINT, params={"page": page, "perPage": per_page})


def get_series(slug: str) -> dict:
    """Get full details for a single series including its chapters.

    Args:
        slug: URL-friendly series identifier (e.g. 'solo-leveling').

    Returns:
        dict with 'success' and 'data' (series object with chapters array).
    """
    return _get(SERIES_DETAIL_ENDPOINT.format(slug=slug))


def get_chapters(slug: str) -> dict:
    """Get the chapter list for a series.

    Args:
        slug: URL-friendly series identifier.

    Returns:
        dict with 'success' and 'data' (list of chapter objects).
    """
    return _get(CHAPTERS_ENDPOINT.format(slug=slug))


def get_chapter_images(slug: str, chapter: str) -> dict:
    """Get image URLs for a specific chapter.

    Args:
        slug: URL-friendly series identifier.
        chapter: Chapter identifier (e.g. 'chapter-1', 'chapter-155').

    Returns:
        dict with 'success' and 'data' containing:
            - images: list of image URL strings in page order
            - pageCount: total number of pages
            - series: parent series metadata
    """
    return _get(CHAPTER_DETAIL_ENDPOINT.format(slug=slug, chapter=chapter))


def download_image(url: str) -> bytes:
    """Download a single image and return its bytes.

    Args:
        url: Direct URL to the image file.

    Returns:
        Raw image bytes.

    Raises:
        requests.HTTPError: If the download fails.
    """
    response = requests.get(url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.content
