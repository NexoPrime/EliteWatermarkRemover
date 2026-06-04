"""Data models for the watermark remover application.

Contains typed dataclasses for settings, configuration,
and data transfer between components.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np


@dataclass(frozen=True)
class InpaintSettings:
    """Immutable settings for a single inpainting operation.

    Attributes:
        method: Algorithm name ('Telea', 'Navier-Stokes',
            'Shift-Map (Content Aware)', 'FSR (Frequency Selective)').
        radius: Search radius for inpainting algorithms (pixels).
        use_feathering: Whether to apply Gaussian edge feathering.
        feather_width: Width of the feathering kernel (pixels).
        dilate_mask: Number of pixels to dilate the mask by.
        add_grain: Whether to restore film grain/texture in inpainted area.
    """

    method: str = "Telea"
    radius: int = 7
    use_feathering: bool = True
    feather_width: int = 15
    dilate_mask: int = 3
    add_grain: bool = True


@dataclass
class BatchSettings:
    """Settings for batch processing a folder of images.

    Attributes:
        inpaint: The inpainting settings to apply to each image.
        ref_shape: Shape (H, W, C) of the reference image.
        ref_mask: Binary mask from the reference image.
        ref_rect: Bounding rectangle (x1, y1, x2, y2) of the mask.
        template: Cropped watermark image data for template matching.
        use_template_matching: Whether to use template matching to
            locate the watermark dynamically in each image.
    """

    inpaint: InpaintSettings
    ref_shape: tuple[int, ...]
    ref_mask: np.ndarray
    ref_rect: Optional[tuple[int, int, int, int]] = None
    template: Optional[np.ndarray] = None
    use_template_matching: bool = True


@dataclass
class BatchProgress:
    """Progress update from the batch worker.

    Attributes:
        current: Current image index (1-based).
        total: Total number of images.
        filename: Name of the file being processed.
        percentage: Completion percentage (0-100).
    """

    current: int
    total: int
    filename: str
    percentage: int

    @property
    def message(self) -> str:
        """Human-readable progress message."""
        return f"Processed {self.current}/{self.total}: {self.filename}"
