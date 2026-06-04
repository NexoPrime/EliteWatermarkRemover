"""Image conversion utilities.

Provides helper functions for converting between OpenCV (numpy)
and Qt image formats, with proper memory safety.
"""

from __future__ import annotations

import logging

import cv2
import numpy as np
from PyQt5.QtGui import QImage, QPixmap

logger = logging.getLogger(__name__)


def cv_to_qpixmap(cv_img: np.ndarray) -> QPixmap:
    """Convert an OpenCV BGR image to a Qt QPixmap.

    Handles BGR (3-channel) and grayscale (1-channel) images.
    The returned QPixmap owns its own memory and is safe to use
    after the source numpy array is garbage-collected.

    Args:
        cv_img: Input image in OpenCV format (BGR or grayscale).

    Returns:
        A QPixmap containing the converted image.

    Raises:
        ValueError: If the image has an unsupported number of channels.
    """
    if cv_img.ndim == 2:
        # Grayscale
        h, w = cv_img.shape
        bytes_per_line = w
        q_img = QImage(cv_img.data, w, h, bytes_per_line, QImage.Format_Grayscale8)
    elif cv_img.ndim == 3 and cv_img.shape[2] == 3:
        # BGR → RGB
        rgb = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        bytes_per_line = ch * w
        q_img = QImage(rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
    elif cv_img.ndim == 3 and cv_img.shape[2] == 4:
        # BGRA → RGBA
        rgba = cv2.cvtColor(cv_img, cv2.COLOR_BGRA2RGBA)
        h, w, ch = rgba.shape
        bytes_per_line = ch * w
        q_img = QImage(rgba.data, w, h, bytes_per_line, QImage.Format_RGBA8888)
    else:
        raise ValueError(
            f"Unsupported image format: ndim={cv_img.ndim}, " f"shape={cv_img.shape}"
        )

    # CRITICAL: Copy the QImage so it owns its pixel data.
    # Without this, the numpy buffer can be garbage-collected
    # while Qt is still rendering, causing use-after-free crashes.
    return QPixmap.fromImage(q_img.copy())
