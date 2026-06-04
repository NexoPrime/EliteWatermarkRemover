"""Tests for the main window integration."""

import os

import cv2
import numpy as np
import pytest
from PyQt5.QtCore import QPointF

from src.core.models import InpaintSettings
from src.ui.components.image_viewer import ToolMode
from src.ui.main_window import EliteWatermarkRemover


class TestWindowCreation:
    """Tests for window initialization."""

    def test_window_instantiation(self, window):
        """Window should instantiate without errors."""
        assert window is not None
        assert window.windowTitle().startswith("Elite Watermark Remover")

    def test_viewer_has_image(self, window):
        """Viewer should have an image loaded."""
        assert window.viewer.cv_img is not None


class TestToolSelection:
    """Tests for tool selection."""

    def test_select_rectangle(self, window):
        window.select_tool(ToolMode.RECTANGLE)
        assert window.btn_rect.isChecked()
        assert not window.btn_brush.isChecked()
        assert not window.btn_wand.isChecked()

    def test_select_brush(self, window):
        window.select_tool(ToolMode.BRUSH)
        assert not window.btn_rect.isChecked()
        assert window.btn_brush.isChecked()

    def test_select_wand(self, window):
        window.select_tool(ToolMode.MAGIC_WAND)
        assert not window.btn_rect.isChecked()
        assert window.btn_wand.isChecked()


class TestInpaintSettings:
    """Tests for settings construction."""

    def test_get_inpaint_settings(self, window):
        """Settings should be an InpaintSettings instance."""
        settings = window.get_inpaint_settings()
        assert isinstance(settings, InpaintSettings)
        assert settings.method in [
            "Shift-Map (Content Aware)",
            "FSR (Frequency Selective)",
            "Telea",
            "Navier-Stokes",
        ]

    def test_settings_reflect_ui(self, window):
        """Settings should match UI widget values."""
        window.spin_radius.setValue(10)
        window.spin_dilate.setValue(5)
        window.chk_grain.setChecked(False)
        settings = window.get_inpaint_settings()
        assert settings.radius == 10
        assert settings.dilate_mask == 5
        assert settings.add_grain is False


class TestSingleInpaint:
    """Tests for single image inpainting."""

    def test_inpaint_modifies_image(self, window):
        """Inpainting should modify the current image."""
        window.viewer.apply_rectangle(QPointF(10, 10), QPointF(50, 50))
        window.on_mask_changed()
        original = window.current_image.copy()
        window.inpaint_single()
        assert not np.array_equal(window.current_image, original)

    def test_undo_restores_image(self, window):
        """Undo should restore the image before inpainting."""
        window.viewer.apply_rectangle(QPointF(10, 10), QPointF(50, 50))
        window.on_mask_changed()
        original = window.current_image.copy()
        window.inpaint_single()
        window.undo_single()
        assert np.array_equal(window.current_image, original)

    def test_undo_empty_stack(self, window):
        """Undo with empty stack should do nothing."""
        window.undo_single()  # Should not crash


class TestMaskManagement:
    """Tests for mask save/load via main window."""

    def test_on_mask_changed_updates_ref_mask(self, window):
        """Mask change should update ref_mask."""
        window.viewer.apply_rectangle(QPointF(10, 10), QPointF(50, 50))
        window.on_mask_changed()
        assert window.ref_mask is not None
        assert cv2.countNonZero(window.ref_mask) > 0

    def test_on_mask_changed_creates_template(self, window):
        """Mask change should create a watermark template."""
        window.viewer.apply_rectangle(QPointF(10, 10), QPointF(50, 50))
        window.on_mask_changed()
        assert window.watermark_template is not None
        assert window.template_rect is not None

    def test_clear_selection_resets(self, window):
        """Clearing selection should reset mask state."""
        window.viewer.apply_rectangle(QPointF(10, 10), QPointF(50, 50))
        window.on_mask_changed()
        window.clear_selection()
        window.on_mask_changed()
        assert window.ref_mask is None

    def test_load_npy_mask(self, window, tmp_dir):
        """Loading NPY mask should work."""
        mask = np.zeros((200, 200), dtype=np.uint8)
        mask[30:70, 30:70] = 255
        path = str(tmp_dir / "test_mask.npy")
        np.save(path, mask)

        window.load_mask(path)
        loaded = window.viewer.get_mask()
        assert np.array_equal(loaded, mask)
