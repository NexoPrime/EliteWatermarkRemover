"""Shared test fixtures for the watermark remover test suite."""

import os
import sys

import cv2
import numpy as np
import pytest

# Force headless mode for testing
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["XDG_RUNTIME_DIR"] = "/tmp"

from PyQt5.QtWidgets import QApplication

from src.core.models import BatchSettings, InpaintSettings
from src.ui.components.image_viewer import ImageEditorView, ToolMode
from src.ui.main_window import EliteWatermarkRemover


@pytest.fixture(scope="session")
def qapp():
    """Create a single QApplication for the entire test session."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


@pytest.fixture
def dummy_image():
    """Create a 200x200 test image with a watermark-like feature."""
    img = np.zeros((200, 200, 3), dtype=np.uint8)
    img[:] = (100, 150, 200)  # Blueish background
    cv2.putText(img, "WM", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.circle(img, (150, 150), 20, (50, 50, 250), -1)  # Red circle
    return img


@pytest.fixture
def large_image():
    """Create a larger 800x600 test image."""
    img = np.random.randint(0, 255, (600, 800, 3), dtype=np.uint8)
    return img


@pytest.fixture
def grayscale_image():
    """Create a grayscale test image."""
    return np.random.randint(0, 255, (100, 100), dtype=np.uint8)


@pytest.fixture
def simple_mask():
    """Create a simple 200x200 test mask with a filled rectangle."""
    mask = np.zeros((200, 200), dtype=np.uint8)
    mask[50:100, 50:100] = 255
    return mask


@pytest.fixture
def default_settings():
    """Create default InpaintSettings."""
    return InpaintSettings()


@pytest.fixture
def window(qapp, dummy_image):
    """Create an EliteWatermarkRemover window with a loaded image."""
    w = EliteWatermarkRemover()
    w.viewer.set_image(dummy_image)
    w.ref_image = dummy_image.copy()
    w.current_image = dummy_image.copy()
    yield w
    w.close()


@pytest.fixture
def viewer(qapp, dummy_image):
    """Create a standalone ImageEditorView with a loaded image."""
    v = ImageEditorView()
    v.set_image(dummy_image)
    return v


@pytest.fixture
def tmp_dir(tmp_path):
    """Provide a temporary directory for file I/O tests."""
    return tmp_path
