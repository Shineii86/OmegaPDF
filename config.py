"""Configuration constants for OmegaPDF."""

BASE_URL = "https://omegaapi.vercel.app"
API_VERSION = "v1"

# Endpoint templates
SERIES_ENDPOINT = f"/api/{API_VERSION}/series"
SERIES_DETAIL_ENDPOINT = f"/api/{API_VERSION}/series/{{slug}}"
CHAPTERS_ENDPOINT = f"/api/{API_VERSION}/chapters/{{slug}}"
CHAPTER_DETAIL_ENDPOINT = f"/api/{API_VERSION}/chapter/{{slug}}/{{chapter}}"
SEARCH_ENDPOINT = f"/api/{API_VERSION}/search"

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
