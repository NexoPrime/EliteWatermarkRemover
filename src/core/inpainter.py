"""Core inpainting engine for watermark removal.

Provides algorithms for image inpainting (watermark removal),
template matching, and geometric utilities. Supports multiple
OpenCV inpainting backends with automatic fallback detection.
"""

from __future__ import annotations

import logging
from typing import Optional

import cv2
import numpy as np

from src.constants import (
    GRAIN_MIN_RING_PIXELS,
    GRAIN_MIN_STD_DEV,
    GRAIN_NOISE_SCALE,
    GRAIN_RING_KERNEL_SIZE,
    TEMPLATE_MATCH_THRESHOLD,
)
from src.core.models import InpaintSettings

logger = logging.getLogger(__name__)

# Check for xphoto availability once at import time
_HAS_XPHOTO: bool = hasattr(cv2, "xphoto")
if not _HAS_XPHOTO:
    logger.warning(
        "cv2.xphoto not available. Shift-Map and FSR algorithms "
        "will fall back to Telea. Install opencv-contrib-python "
        "for full algorithm support."
    )


class Inpainter:
    """Static image inpainting engine.

    Provides methods for removing watermarks from images using
    various inpainting algorithms, with optional post-processing
    (grain restoration, edge feathering).

    All methods are stateless and can be called concurrently.
    """

    @staticmethod
    def inpaint_image(
        img: np.ndarray,
        mask: np.ndarray,
        settings: InpaintSettings,
    ) -> np.ndarray:
        """Remove a watermark from an image using the configured algorithm.

        Args:
            img: Source BGR image (H×W×3, uint8).
            mask: Binary mask where 255 = watermark region (H×W, uint8).
            settings: Inpainting configuration parameters.

        Returns:
            The inpainted image with the same shape and dtype as input.

        Raises:
            ValueError: If img and mask have incompatible dimensions.
        """
        if img.shape[:2] != mask.shape[:2]:
            raise ValueError(
                f"Image shape {img.shape[:2]} does not match "
                f"mask shape {mask.shape[:2]}"
            )

        logger.debug(
            "Inpainting with method=%s, radius=%d, dilate=%d, "
            "feather=%s (w=%d), grain=%s",
            settings.method,
            settings.radius,
            settings.dilate_mask,
            settings.use_feathering,
            settings.feather_width,
            settings.add_grain,
        )

        # Dilate mask to catch anti-aliased watermark edges
        if settings.dilate_mask > 0:
            kernel = np.ones((settings.dilate_mask, settings.dilate_mask), np.uint8)
            processing_mask = cv2.dilate(mask, kernel, iterations=1)
        else:
            processing_mask = mask.copy()

        # Perform inpainting
        inpainted = Inpainter._run_inpaint(
            img, processing_mask, settings.radius, settings.method
        )

        # Post-processing: grain restoration
        if settings.add_grain:
            inpainted = Inpainter._restore_grain(img, inpainted, processing_mask)

        # Post-processing: edge feathering
        if settings.use_feathering and settings.feather_width > 0:
            inpainted = Inpainter._feather_edges(
                img, inpainted, processing_mask, settings.feather_width
            )

        return inpainted

    @staticmethod
    def _run_inpaint(
        img: np.ndarray,
        mask: np.ndarray,
        radius: int,
        method_name: str,
    ) -> np.ndarray:
        """Execute the selected inpainting algorithm.

        Args:
            img: Source BGR image.
            mask: Binary processing mask.
            radius: Search radius for inpainting.
            method_name: Algorithm name.

        Returns:
            Inpainted image.
        """
        if method_name == "Telea":
            return cv2.inpaint(img, mask, radius, cv2.INPAINT_TELEA)

        if method_name == "Navier-Stokes":
            return cv2.inpaint(img, mask, radius, cv2.INPAINT_NS)

        if method_name == "Shift-Map (Content Aware)":
            if _HAS_XPHOTO:
                dst = np.zeros_like(img)
                inverted_mask = cv2.bitwise_not(mask)
                cv2.xphoto.inpaint(img, inverted_mask, dst, cv2.xphoto.INPAINT_SHIFTMAP)
                return dst
            logger.warning(
                "Shift-Map requested but cv2.xphoto unavailable. "
                "Falling back to Telea."
            )
            return cv2.inpaint(img, mask, radius, cv2.INPAINT_TELEA)

        if method_name == "FSR (Frequency Selective)":
            if _HAS_XPHOTO:
                dst = np.zeros_like(img)
                inverted_mask = cv2.bitwise_not(mask)
                cv2.xphoto.inpaint(img, inverted_mask, dst, cv2.xphoto.INPAINT_FSR_BEST)
                return dst
            logger.warning(
                "FSR requested but cv2.xphoto unavailable. " "Falling back to Telea."
            )
            return cv2.inpaint(img, mask, radius, cv2.INPAINT_TELEA)

        # Unknown method — default to Telea
        logger.warning("Unknown method '%s', defaulting to Telea.", method_name)
        return cv2.inpaint(img, mask, radius, cv2.INPAINT_TELEA)

    @staticmethod
    def _restore_grain(
        img: np.ndarray,
        inpainted: np.ndarray,
        mask: np.ndarray,
    ) -> np.ndarray:
        """Restore film grain / texture in the inpainted region.

        Samples noise characteristics from a ring around the mask
        boundary and injects matching noise into the inpainted area
        to prevent the 'plastic blur' look.

        Args:
            img: Original source image (for noise sampling).
            inpainted: Inpainted result to add grain to.
            mask: Binary processing mask.

        Returns:
            Inpainted image with grain restored in masked regions.
        """
        kernel = np.ones((GRAIN_RING_KERNEL_SIZE, GRAIN_RING_KERNEL_SIZE), np.uint8)
        dilated = cv2.dilate(mask, kernel, iterations=1)
        ring_mask = cv2.bitwise_xor(dilated, mask)

        if cv2.countNonZero(ring_mask) <= GRAIN_MIN_RING_PIXELS:
            return inpainted

        # Sample noise variance from the L channel (LAB color space)
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        l_channel = lab[:, :, 0]
        _, stddev = cv2.meanStdDev(l_channel, mask=ring_mask)
        std_val: float = float(stddev[0][0])

        if std_val <= GRAIN_MIN_STD_DEV:
            return inpainted

        # Generate and apply noise only inside the mask
        noise = np.random.normal(
            0, std_val * GRAIN_NOISE_SCALE, inpainted.shape
        ).astype(np.float32)
        noisy = np.clip(inpainted.astype(np.float32) + noise, 0, 255).astype(np.uint8)

        mask_norm = (mask.astype(np.float32) / 255.0)[:, :, np.newaxis]
        return (inpainted * (1 - mask_norm) + noisy * mask_norm).astype(np.uint8)

    @staticmethod
    def _feather_edges(
        img: np.ndarray,
        inpainted: np.ndarray,
        mask: np.ndarray,
        feather_width: int,
    ) -> np.ndarray:
        """Apply Gaussian feathering for seamless edge blending.

        Creates a smooth gradient at the mask boundary to blend the
        inpainted region with the original image, eliminating hard
        seams.

        Args:
            img: Original source image.
            inpainted: Inpainted result.
            mask: Binary processing mask.
            feather_width: Width of the feathering kernel in pixels.

        Returns:
            Blended image with feathered edges.
        """
        ksize = feather_width * 2 + 1
        sigma = feather_width / 2.0
        mask_blur = cv2.GaussianBlur(mask.astype(np.float32), (ksize, ksize), sigma)
        mask_blur = (mask_blur / 255.0)[:, :, np.newaxis]

        return (img * (1 - mask_blur) + inpainted * mask_blur).astype(np.uint8)

    @staticmethod
    def find_template(
        img: np.ndarray,
        template: np.ndarray,
        threshold: float = TEMPLATE_MATCH_THRESHOLD,
    ) -> Optional[tuple[int, int, int, int]]:
        """Find a template watermark in an image using cross-correlation.

        Uses normalized cross-correlation (TM_CCOEFF_NORMED) to locate
        the template within the image.

        Args:
            img: Source image to search in (BGR, uint8).
            template: Watermark template to find (BGR, uint8).
            threshold: Minimum correlation score to accept a match.

        Returns:
            Bounding box (x1, y1, x2, y2) if found, or None.
        """
        try:
            if template.shape[0] > img.shape[0] or template.shape[1] > img.shape[1]:
                logger.debug("Template larger than image, skipping match.")
                return None

            result = cv2.matchTemplate(img, template, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(result)

            if max_val > threshold:
                x, y = max_loc
                h, w = template.shape[:2]
                logger.debug(
                    "Template match found: score=%.3f, loc=(%d,%d)",
                    max_val,
                    x,
                    y,
                )
                return (x, y, x + w, y + h)

            logger.debug(
                "Template match below threshold: score=%.3f < %.3f",
                max_val,
                threshold,
            )
        except Exception:
            logger.exception("Template matching failed.")

        return None

    @staticmethod
    def scale_rect(
        rect: tuple[int, int, int, int],
        ref_w: int,
        ref_h: int,
        new_w: int,
        new_h: int,
    ) -> tuple[int, int, int, int]:
        """Proportionally scale a bounding rectangle.

        Args:
            rect: Original rectangle (x1, y1, x2, y2).
            ref_w: Reference image width.
            ref_h: Reference image height.
            new_w: Target image width.
            new_h: Target image height.

        Returns:
            Scaled rectangle (x1, y1, x2, y2).

        Raises:
            ValueError: If ref_w or ref_h is zero.
        """
        if ref_w == 0 or ref_h == 0:
            raise ValueError(
                f"Reference dimensions must be non-zero: "
                f"ref_w={ref_w}, ref_h={ref_h}"
            )
        x1, y1, x2, y2 = rect
        scale_x = new_w / ref_w
        scale_y = new_h / ref_h
        return (
            int(x1 * scale_x),
            int(y1 * scale_y),
            int(x2 * scale_x),
            int(y2 * scale_y),
        )
