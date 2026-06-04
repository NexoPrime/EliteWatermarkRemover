"""Application-wide constants and magic numbers.

Centralizes all hardcoded values used throughout the application
to make them discoverable, documentable, and configurable.
"""

from __future__ import annotations

# Application metadata
APP_NAME: str = "Elite Watermark Remover Pro"
APP_VERSION: str = "2.0.0"
APP_ORG: str = "EliteWatermarkRemover"

# Window defaults
DEFAULT_WINDOW_WIDTH: int = 1400
DEFAULT_WINDOW_HEIGHT: int = 1000
MIN_WINDOW_WIDTH: int = 900
MIN_WINDOW_HEIGHT: int = 600
LEFT_PANEL_MIN_WIDTH: int = 380
LEFT_PANEL_MAX_WIDTH: int = 700
SPLITTER_SIZES: list[int] = [450, 950]

# Zoom limits
ZOOM_IN_FACTOR: float = 1.15
ZOOM_OUT_FACTOR: float = 1.0 / 1.15
MIN_ZOOM: float = 0.05
MAX_ZOOM: float = 25.0

# Mask and history
MASK_HISTORY_MAX: int = 50
IMAGE_UNDO_MAX: int = 20
MASK_OVERLAY_COLOR: tuple[int, int, int, int] = (255, 0, 0, 100)  # RGBA

# Inpainting defaults
DEFAULT_RADIUS: int = 30
DEFAULT_DILATE: int = 3
DEFAULT_FEATHER_WIDTH: int = 15
DEFAULT_BRUSH_SIZE: int = 20
DEFAULT_WAND_TOLERANCE: int = 15

# Grain restoration constants
GRAIN_RING_KERNEL_SIZE: int = 15
GRAIN_MIN_RING_PIXELS: int = 10
GRAIN_MIN_STD_DEV: float = 1.0
GRAIN_NOISE_SCALE: float = 0.8

# Template matching
TEMPLATE_MATCH_THRESHOLD: float = 0.70

# Supported image formats
SUPPORTED_IMAGE_EXTENSIONS: tuple[str, ...] = (
    ".png",
    ".jpg",
    ".jpeg",
    ".bmp",
    ".tiff",
    ".tif",
    ".webp",
)
IMAGE_FILTER: str = (
    "Images (*.png *.jpg *.jpeg *.bmp *.tiff *.tif *.webp);;All Files (*.*)"
)
MASK_FILTER: str = "Mask Files (*.png *.npy);;All Files (*.*)"
SAVE_IMAGE_FILTER: str = "PNG Image (*.png);;JPEG Image (*.jpg);;All Files (*.*)"
SAVE_MASK_FILTER: str = "PNG Mask (*.png);;Numpy Mask (*.npy);;All Files (*.*)"

# Default output subdirectory for batch processing
DEFAULT_OUTPUT_SUBDIR: str = "_cleaned"

# Font configuration (cross-platform)
FONT_FAMILY: str = "'Inter', 'SF Pro Display', 'Segoe UI', 'Roboto', Arial, sans-serif"
FONT_SIZE_PT: int = 12
