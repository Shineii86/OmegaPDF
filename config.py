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
PDF_DPI = 72
PDF_FORMAT = "JPEG"
PDF_QUALITY = 85

# HTTP
REQUEST_TIMEOUT = 30
