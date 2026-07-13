"""Configuration constants for OmegaPDF — calls OmegaScans upstream API directly."""

# Upstream OmegaScans API (no external OmegaAPI dependency)
OMEGA_BASE_URL = "https://api.omegascans.org"
MEDIA_CDN = "https://media.omegascans.org"

# Upstream endpoint templates (raw OmegaScans format)
UPSTREAM_SERIES_LIST = "/query?type=series&page={page}"
UPSTREAM_SERIES_SEARCH = "/query?q={query}&type=series&page={page}"
UPSTREAM_SERIES_DETAIL = "/series/{slug}"
UPSTREAM_CHAPTERS_LIST = "/chapter/query?page={page}&perPage={per_page}&series_id={series_id}"
UPSTREAM_CHAPTER_CONTENT = "/chapter/{slug}/{chapter}"

# Defaults
DEFAULT_PAGE = 1
DEFAULT_PER_PAGE = 20
MAX_PER_PAGE = 100

# PDF settings
PDF_FORMAT = "JPEG"
PDF_QUALITY = 90

# Quality presets: (dpi, label)
QUALITY_PRESETS = {
    "low": (72, "Low (72 DPI — fast, small files)"),
    "medium": (150, "Medium (150 DPI — balanced)"),
    "high": (300, "High (300 DPI — print quality)"),
}
DEFAULT_QUALITY = "medium"

# HTTP
REQUEST_TIMEOUT = 30
MAX_WORKERS = 8  # concurrent download threads
MAX_RETRIES = 3
RETRY_BACKOFF = 1.0  # base seconds, doubles each retry
