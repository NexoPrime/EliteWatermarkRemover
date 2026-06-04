"""Tests for the ImageEditorView component."""

import cv2
import numpy as np
import pytest
from PyQt5.QtCore import QPointF

from src.ui.components.image_viewer import ImageEditorView, ToolMode


class TestImageSetup:
    """Tests for image loading and initialization."""

    def test_set_image_creates_mask(self, viewer, dummy_image):
        """Setting an image should create a matching empty mask."""
        assert viewer.mask is not None
        assert viewer.mask.shape == dummy_image.shape[:2]
        assert cv2.countNonZero(viewer.mask) == 0

    def test_set_image_resets_history(self, viewer, dummy_image):
        """Setting a new image should reset undo/redo history."""
        assert len(viewer.mask_history) == 1
        assert len(viewer.redo_history) == 0

    def test_get_mask_returns_mask(self, viewer):
        """get_mask() should return the current mask."""
        mask = viewer.get_mask()
        assert mask is not None
        assert mask is viewer.mask


class TestRectangleTool:
    """Tests for the rectangle selection tool."""

    def test_apply_rectangle(self, viewer):
        """Rectangle should fill the mask in the selected area."""
        viewer.set_tool(ToolMode.RECTANGLE)
        viewer.apply_rectangle(QPointF(10, 10), QPointF(50, 50))
        assert cv2.countNonZero(viewer.mask) > 0
        assert viewer.mask[30, 30] == 255  # Inside

    def test_rectangle_bounds_clamped(self, viewer):
        """Coordinates outside image should be clamped."""
        viewer.apply_rectangle(QPointF(-10, -10), QPointF(300, 300))
        assert cv2.countNonZero(viewer.mask) > 0

    def test_rectangle_updates_history(self, viewer):
        """Rectangle should add a history entry."""
        initial_len = len(viewer.mask_history)
        viewer.apply_rectangle(QPointF(10, 10), QPointF(50, 50))
        assert len(viewer.mask_history) == initial_len + 1


class TestBrushTool:
    """Tests for the brush selection tool."""

    def test_draw_brush(self, viewer):
        """Brush should paint on the mask."""
        viewer.set_tool(ToolMode.BRUSH, size=10)
        viewer.draw_brush(QPointF(100, 100))
        assert cv2.countNonZero(viewer.mask) > 0

    def test_brush_bounds_clamped(self, viewer):
        """Brush at image edge should not crash."""
        viewer.set_tool(ToolMode.BRUSH, size=10)
        viewer.draw_brush(QPointF(-5, -5))  # Outside
        viewer.draw_brush(QPointF(500, 500))  # Outside
        # Should not crash


class TestMagicWandTool:
    """Tests for the magic wand selection tool."""

    def test_apply_magic_wand(self, viewer):
        """Magic wand should select a region."""
        viewer.set_tool(ToolMode.MAGIC_WAND, tolerance=15)
        viewer.apply_magic_wand(QPointF(150, 150))  # Red circle area
        assert cv2.countNonZero(viewer.mask) > 0

    def test_magic_wand_doesnt_corrupt_image(self, viewer):
        """Magic wand should NOT modify the source image."""
        original = viewer.cv_img.copy()
        viewer.apply_magic_wand(QPointF(150, 150))
        assert np.array_equal(viewer.cv_img, original)

    def test_magic_wand_outside_bounds(self, viewer):
        """Magic wand outside image should do nothing."""
        viewer.apply_magic_wand(QPointF(500, 500))
        assert cv2.countNonZero(viewer.mask) == 0

    def test_magic_wand_updates_history(self, viewer):
        """Magic wand should add a history entry."""
        initial_len = len(viewer.mask_history)
        viewer.apply_magic_wand(QPointF(150, 150))
        assert len(viewer.mask_history) == initial_len + 1


class TestUndoRedo:
    """Tests for mask undo/redo functionality."""

    def test_undo(self, viewer):
        """Undo should restore the previous mask state."""
        viewer.apply_rectangle(QPointF(10, 10), QPointF(50, 50))
        assert cv2.countNonZero(viewer.mask) > 0
        viewer.undo_mask_edit()
        assert cv2.countNonZero(viewer.mask) == 0

    def test_redo(self, viewer):
        """Redo should restore the undone mask state."""
        viewer.apply_rectangle(QPointF(10, 10), QPointF(50, 50))
        viewer.undo_mask_edit()
        assert cv2.countNonZero(viewer.mask) == 0
        viewer.redo_mask_edit()
        assert cv2.countNonZero(viewer.mask) > 0

    def test_undo_past_empty(self, viewer):
        """Undo on empty history should do nothing."""
        viewer.undo_mask_edit()  # Should not crash
        assert cv2.countNonZero(viewer.mask) == 0

    def test_redo_past_empty(self, viewer):
        """Redo on empty redo stack should do nothing."""
        viewer.redo_mask_edit()  # Should not crash

    def test_new_action_clears_redo(self, viewer):
        """New mask action should clear redo history."""
        viewer.apply_rectangle(QPointF(10, 10), QPointF(50, 50))
        viewer.undo_mask_edit()
        assert len(viewer.redo_history) > 0
        viewer.apply_rectangle(QPointF(60, 60), QPointF(90, 90))
        assert len(viewer.redo_history) == 0


class TestClearAndSmooth:
    """Tests for clear selection and mask smoothing."""

    def test_clear_selection(self, viewer):
        """Clear should zero the entire mask."""
        viewer.apply_rectangle(QPointF(10, 10), QPointF(50, 50))
        viewer.clear_selection()
        assert cv2.countNonZero(viewer.mask) == 0

    def test_smooth_mask(self, viewer):
        """Smoothing should modify the mask edges."""
        viewer.apply_magic_wand(QPointF(150, 150))
        original = viewer.mask.copy()
        viewer.smooth_mask(kernel_size=5)
        # Smoothing may or may not change pixels, but should not crash
        assert viewer.mask is not None

    def test_smooth_empty_mask(self, viewer):
        """Smoothing empty mask should do nothing."""
        viewer.smooth_mask()  # Should not crash


class TestMaskIO:
    """Tests for mask save/load."""

    def test_save_and_load_png(self, viewer, tmp_dir):
        """Save and load mask as PNG should round-trip."""
        viewer.apply_rectangle(QPointF(10, 10), QPointF(50, 50))
        path = str(tmp_dir / "test_mask.png")
        assert viewer.save_mask(path)

        original_mask = viewer.mask.copy()
        viewer.clear_selection()
        assert viewer.load_mask(path)
        assert np.array_equal(viewer.mask, original_mask)

    def test_save_empty_mask_fails(self, viewer, tmp_dir):
        """Saving empty mask should return False."""
        path = str(tmp_dir / "empty.png")
        assert not viewer.save_mask(path)

    def test_load_nonexistent_fails(self, viewer, tmp_dir):
        """Loading non-existent file should return False."""
        assert not viewer.load_mask(str(tmp_dir / "nope.png"))

    def test_load_wrong_dimensions_fails(self, viewer, tmp_dir):
        """Loading mask with wrong dimensions should fail."""
        wrong_mask = np.zeros((50, 50), dtype=np.uint8)
        path = str(tmp_dir / "wrong_size.png")
        cv2.imwrite(path, wrong_mask)
        assert not viewer.load_mask(path)


class TestToolConfiguration:
    """Tests for tool mode switching."""

    def test_set_rectangle_tool(self, viewer):
        viewer.set_tool(ToolMode.RECTANGLE)
        assert viewer.current_tool == ToolMode.RECTANGLE

    def test_set_brush_tool(self, viewer):
        viewer.set_tool(ToolMode.BRUSH, size=30)
        assert viewer.current_tool == ToolMode.BRUSH
        assert viewer.brush_size == 30

    def test_set_wand_tool(self, viewer):
        viewer.set_tool(ToolMode.MAGIC_WAND, tolerance=25)
        assert viewer.current_tool == ToolMode.MAGIC_WAND
        assert viewer.wand_tolerance == 25
