"""Panel and chapter data fetching from OmegaAPI with concurrent downloads and retries."""

from __future__ import annotations

import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

from config import (
    BASE_URL,
    SERIES_ENDPOINT,
    SERIES_DETAIL_ENDPOINT,
    CHAPTERS_ENDPOINT,
    CHAPTER_DETAIL_ENDPOINT,
    SEARCH_ENDPOINT,
    REQUEST_TIMEOUT,
    MAX_WORKERS,
    MAX_RETRIES,
    RETRY_BACKOFF,
)


def _get(path: str, params: Optional[dict] = None) -> dict:
    """Make a GET request to the OmegaAPI and return the JSON response."""
    url = f"{BASE_URL}{path}"
    response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.json()


def search_series(query: str, page: int = 1, per_page: int = 20) -> dict:
    """Search for series by title."""
    return _get(SEARCH_ENDPOINT, params={"q": query})


def list_series(page: int = 1, per_page: int = 20) -> dict:
    """Browse available series with pagination."""
    return _get(SERIES_ENDPOINT, params={"page": page, "perPage": per_page})


def get_series(slug: str) -> dict:
    """Get full details for a single series including its chapters."""
    return _get(SERIES_DETAIL_ENDPOINT.format(slug=slug))


def get_chapters(slug: str) -> dict:
    """Get the chapter list for a series."""
    return _get(CHAPTERS_ENDPOINT.format(slug=slug))


def get_chapter_images(slug: str, chapter: str) -> dict:
    """Get image URLs for a specific chapter."""
    return _get(CHAPTER_DETAIL_ENDPOINT.format(slug=slug, chapter=chapter))


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
