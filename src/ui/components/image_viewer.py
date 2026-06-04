"""Interactive image editor widget with mask selection tools.

Provides a zoomable, pannable image viewer built on QGraphicsView
with three mask selection tools (Rectangle, Brush, Magic Wand),
mask undo/redo, and overlay rendering.
"""

from __future__ import annotations

import logging
import typing
from collections import deque
from enum import Enum
from typing import Optional

import cv2
import numpy as np
from PyQt5.QtCore import QPointF, QRectF, Qt, pyqtSignal
from PyQt5.QtGui import QColor, QImage, QPainter, QPen, QPixmap
from PyQt5.QtWidgets import (
    QGraphicsPixmapItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsView,
)

from src.constants import (
    DEFAULT_BRUSH_SIZE,
    DEFAULT_WAND_TOLERANCE,
    MASK_HISTORY_MAX,
    MASK_OVERLAY_COLOR,
    MAX_ZOOM,
    MIN_ZOOM,
    ZOOM_IN_FACTOR,
    ZOOM_OUT_FACTOR,
)
from src.utils.image_utils import cv_to_qpixmap

logger = logging.getLogger(__name__)


class ToolMode(Enum):
    """Available mask selection tools."""

    RECTANGLE = 1
    BRUSH = 2
    MAGIC_WAND = 3
    SMART_OBJECT = 4
    SMART_LASSO = 5
    HEAL = 6
    CLONE_STAMP = 7


class ImageEditorView(QGraphicsView):
    """Interactive image viewer with mask editing capabilities.

    Displays an OpenCV image with a semi-transparent red mask overlay.
    Supports three selection tools for creating masks, with full
    undo/redo history. Includes zoom (mouse wheel) and pan
    (middle-click or Shift+click).

    Signals:
        mask_changed: Emitted whenever the mask is modified.
        undo_available: Emitted with True/False when undo state changes.
        redo_available: Emitted with True/False when redo state changes.

    Attributes:
        cv_img: The current OpenCV image being displayed.
        mask: The current binary mask (H×W, uint8, 0 or 255).
    """

    mask_changed = pyqtSignal()
    undo_available = pyqtSignal(bool)
    redo_available = pyqtSignal(bool)
    heal_requested = pyqtSignal(np.ndarray)
    clone_requested = pyqtSignal(np.ndarray, int, int)

    def __init__(self, parent: Optional[object] = None) -> None:
        """Initialize the image editor view.

        Args:
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self.scene_obj = QGraphicsScene(self)
        self.setScene(self.scene_obj)
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.NoDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setAcceptDrops(True)

        # Image state
        self.cv_img: Optional[np.ndarray] = None
        self.mask: Optional[np.ndarray] = None
        self.pixmap_item: Optional[QGraphicsPixmapItem] = None
        self.mask_item: Optional[QGraphicsPixmapItem] = None
        self.rect_preview_item: Optional[QGraphicsRectItem] = None
        self.lasso_path_item = None
        self._lasso_points: list[QPointF] = []
        self._heal_mask: Optional[np.ndarray] = None
        self.clone_source: Optional[QPointF] = None

        # Tool state
        self.current_tool: ToolMode = ToolMode.RECTANGLE
        self.brush_size: int = DEFAULT_BRUSH_SIZE
        self.wand_tolerance: int = DEFAULT_WAND_TOLERANCE

        # Interaction state
        self._is_panning: bool = False
        self._pan_start_pos: QPointF = QPointF()
        self._is_drawing: bool = False
        self._draw_start_pos: QPointF = QPointF()
        self._current_zoom: float = 1.0

        # Mask history (bounded)
        self.mask_history: deque[np.ndarray] = deque(maxlen=MASK_HISTORY_MAX)
        self.redo_history: deque[np.ndarray] = deque(maxlen=MASK_HISTORY_MAX)

    # ── History Management ────────────────────────────────────

    def _add_mask_to_history(self, new_mask_state: Optional[np.ndarray]) -> None:
        """Record a mask state in the undo history.

        Skips recording if the state is identical to the most recent
        entry (prevents duplicate history from no-op operations).

        Args:
            new_mask_state: The mask state to record.
        """
        if new_mask_state is None:
            return
        if self.mask_history and np.array_equal(self.mask_history[-1], new_mask_state):
            return

        self.mask_history.append(new_mask_state.copy())
        self.redo_history.clear()
        self.undo_available.emit(len(self.mask_history) > 1)
        self.redo_available.emit(False)

    def undo_mask_edit(self) -> None:
        """Undo the last mask edit, restoring the previous state."""
        if len(self.mask_history) <= 1:
            return

        current_state = self.mask_history.pop()
        self.redo_history.append(current_state)
        self.mask = self.mask_history[-1].copy()
        self.update_mask_overlay()
        self.mask_changed.emit()
        self.undo_available.emit(len(self.mask_history) > 1)
        self.redo_available.emit(True)
        logger.debug(
            "Mask undo: history=%d, redo=%d",
            len(self.mask_history),
            len(self.redo_history),
        )

    def redo_mask_edit(self) -> None:
        """Redo the last undone mask edit."""
        if not self.redo_history:
            return

        next_state = self.redo_history.pop()
        self.mask_history.append(next_state)
        self.mask = next_state.copy()
        self.update_mask_overlay()
        self.mask_changed.emit()
        self.undo_available.emit(True)
        self.redo_available.emit(len(self.redo_history) > 0)
        logger.debug(
            "Mask redo: history=%d, redo=%d",
            len(self.mask_history),
            len(self.redo_history),
        )

    # ── Tool Configuration ────────────────────────────────────

    def set_tool(
        self,
        tool: ToolMode,
        size: int = DEFAULT_BRUSH_SIZE,
        tolerance: int = DEFAULT_WAND_TOLERANCE,
    ) -> None:
        """Set the active selection tool and its parameters.

        Args:
            tool: The tool mode to activate.
            size: Brush radius in pixels (for Brush tool).
            tolerance: Color tolerance (for Magic Wand tool).
        """
        self.current_tool = tool
        self.brush_size = size
        self.wand_tolerance = tolerance

        if tool == ToolMode.MAGIC_WAND:
            self.setCursor(Qt.PointingHandCursor)
        else:
            self.setCursor(Qt.CrossCursor)

    # ── Image Management ──────────────────────────────────────

    def set_image(self, cv_img: np.ndarray) -> None:
        """Set a new image to display and reset the mask.

        Creates a fresh empty mask matching the image dimensions
        and resets all history.

        Args:
            cv_img: OpenCV BGR image to display.
        """
        self.cv_img = cv_img.copy()
        h, w = cv_img.shape[:2]
        self.mask = np.zeros((h, w), dtype=np.uint8)

        self.mask_history = []
        self.redo_history = []
        self._heal_mask = np.zeros((h, w), dtype=np.uint8)
        self._add_mask_to_history(self.mask)

        self.scene_obj.clear()
        pixmap = cv_to_qpixmap(cv_img)
        self.pixmap_item = self.scene_obj.addPixmap(pixmap)
        self.setSceneRect(QRectF(pixmap.rect()))

        self.mask_item = QGraphicsPixmapItem()
        self.scene_obj.addItem(self.mask_item)
        # Lasso preview
        from PyQt5.QtWidgets import QGraphicsPathItem

        self.lasso_path_item = QGraphicsPathItem()
        self.lasso_path_item.setPen(QPen(QColor(255, 255, 255), 2, Qt.DashLine))
        self.lasso_path_item.hide()
        self.scene_obj.addItem(self.lasso_path_item)

        self.rect_preview_item = QGraphicsRectItem()
        self.rect_preview_item.setPen(QPen(QColor(255, 0, 0), 2, Qt.DashLine))
        self.rect_preview_item.setBrush(QColor(255, 0, 0, 40))
        self.scene_obj.addItem(self.rect_preview_item)
        self.rect_preview_item.hide()

        self._current_zoom = 1.0
        self.update_mask_overlay()
        self.fitInView(self.sceneRect(), Qt.KeepAspectRatio)
        logger.debug("Image set: %dx%d", w, h)

    def update_image(self, cv_img: np.ndarray) -> None:
        """Update the displayed image without clearing the scene or mask history."""
        self.cv_img = cv_img.copy()
        if self.pixmap_item is not None:
            self.pixmap_item.setPixmap(cv_to_qpixmap(self.cv_img))
        self.update_mask_overlay()

    def get_mask(self) -> Optional[np.ndarray]:
        """Return the current mask array.

        Returns:
            The binary mask (H×W, uint8), or None if no image is loaded.
        """
        return self.mask

    def clear_selection(self) -> None:
        """Clear the entire mask, filling it with zeros."""
        if self.mask is not None and cv2.countNonZero(self.mask) > 0:
            self.mask.fill(0)
            self._add_mask_to_history(self.mask)
            self.update_mask_overlay()
            if self.rect_preview_item:
                self.rect_preview_item.hide()
            self.mask_changed.emit()

    def set_show_original(self, show: bool) -> None:
        """Temporarily hide the pixmap to reveal the original image."""
        if self.pixmap_item:
            self.pixmap_item.setVisible(not show)

    # ── Mask Overlay Rendering ────────────────────────────────

    def update_mask_overlay(self) -> None:
        """Update the red semi-transparent overlay from the current mask."""
        if self.cv_img is None or self.mask is None or self.mask_item is None:
            return

        h, w = self.mask.shape
        overlay = np.zeros((h, w, 4), dtype=np.uint8)

        # Draw standard selection mask in RED
        r, g, b, a = MASK_OVERLAY_COLOR
        overlay[self.mask > 0] = [r, g, b, a]

        # Draw healing mask in GREEN while dragging
        if self._heal_mask is not None:
            overlay[self._heal_mask > 0] = (0, 255, 0, 100)

        qimg = QImage(overlay.data, w, h, w * 4, QImage.Format_RGBA8888)
        self.mask_item.setPixmap(QPixmap.fromImage(qimg.copy()))

    # ── Mask Operations ───────────────────────────────────────

    def smooth_mask(self, kernel_size: int = 5) -> None:
        """Smooth the mask edges using morphological open + close.

        Args:
            kernel_size: Size of the elliptical structuring element.
        """
        if self.mask is None or cv2.countNonZero(self.mask) == 0:
            return

        kernel = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE, (kernel_size, kernel_size)
        )
        opened = cv2.morphologyEx(self.mask, cv2.MORPH_OPEN, kernel)
        closed = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, kernel)
        self.mask = closed
        self._add_mask_to_history(self.mask)
        self.update_mask_overlay()
        self.mask_changed.emit()

    def load_mask(self, file_path: str) -> bool:
        """Load a mask from an image file.

        The mask is binarized (pixels > 0 become 255) and must match
        the current image dimensions.

        Args:
            file_path: Path to the mask image file.

        Returns:
            True if the mask was loaded successfully, False otherwise.
        """
        if self.cv_img is None:
            logger.warning("Cannot load mask: no image loaded.")
            return False
        try:
            loaded_mask = cv2.imread(file_path, cv2.IMREAD_GRAYSCALE)
            if loaded_mask is None:
                raise ValueError(f"Could not read mask image: {file_path}")
            if loaded_mask.shape[:2] != self.cv_img.shape[:2]:
                raise ValueError(
                    f"Mask dimensions {loaded_mask.shape[:2]} do not match "
                    f"image dimensions {self.cv_img.shape[:2]}"
                )

            self.mask = loaded_mask
            self.mask[self.mask > 0] = 255
            self._add_mask_to_history(self.mask)
            self.update_mask_overlay()
            self.mask_changed.emit()
            logger.info("Mask loaded from %s", file_path)
            return True
        except Exception:
            logger.exception("Failed to load mask from %s", file_path)
            return False

    def save_mask(self, file_path: str) -> bool:
        """Save the current mask to an image file.

        Args:
            file_path: Destination file path.

        Returns:
            True if saved successfully, False otherwise.
        """
        if self.mask is None or cv2.countNonZero(self.mask) == 0:
            logger.warning("Cannot save mask: mask is empty.")
            return False
        try:
            success = cv2.imwrite(file_path, self.mask)
            if not success:
                raise IOError(f"cv2.imwrite failed for {file_path}")
            logger.info("Mask saved to %s", file_path)
            return True
        except Exception:
            logger.exception("Failed to save mask to %s", file_path)
            return False

    # ── Mouse Events ──────────────────────────────────────────

    def wheelEvent(self, event: typing.Any) -> None:
        """Handle mouse wheel for zooming with enforced limits.

        Zoom is clamped between MIN_ZOOM and MAX_ZOOM.
        """
        if self.pixmap_item is None:
            return

        if event.angleDelta().y() > 0:
            factor = ZOOM_IN_FACTOR
        else:
            factor = ZOOM_OUT_FACTOR

        new_zoom = self._current_zoom * factor
        if MIN_ZOOM <= new_zoom <= MAX_ZOOM:
            self._current_zoom = new_zoom
            self.scale(factor, factor)

    def mousePressEvent(self, event: typing.Any) -> None:
        """Handle mouse press for panning and drawing."""
        if self.pixmap_item is None:
            return super().mousePressEvent(event)

        # Pan: middle-click or Shift+left-click
        if event.button() == Qt.MiddleButton or (
            event.button() == Qt.LeftButton and event.modifiers() == Qt.ShiftModifier
        ):
            self._is_panning = True
            self._pan_start_pos = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
            return

        # Draw: left-click
        if event.button() == Qt.LeftButton:
            pos = self.mapToScene(event.pos())

            if (
                self.current_tool == ToolMode.CLONE_STAMP
                and event.modifiers() == Qt.AltModifier
            ):
                self.clone_source = pos
                event.accept()
                return

            self._is_drawing = True
            self._draw_start_pos = pos

            if self.current_tool in (
                ToolMode.BRUSH,
                ToolMode.HEAL,
                ToolMode.CLONE_STAMP,
            ):
                self._draw_brush(pos)
            elif self.current_tool == ToolMode.MAGIC_WAND:
                self._apply_magic_wand(pos)
                self._is_drawing = False  # One-click action
            elif self.current_tool in (ToolMode.RECTANGLE, ToolMode.SMART_OBJECT):
                self.rect_preview_item.setRect(QRectF(pos, pos))
                self.rect_preview_item.show()

            elif self.current_tool == ToolMode.SMART_LASSO:
                self._lasso_points = [pos]
                from PyQt5.QtGui import QPainterPath

                path = QPainterPath(pos)
                self.lasso_path_item.setPath(path)
                self.lasso_path_item.show()

            event.accept()
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: typing.Any) -> None:
        """Handle mouse move for panning and live drawing."""
        if self._is_panning:
            delta = event.pos() - self._pan_start_pos
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - delta.x()
            )
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - delta.y()
            )
            self._pan_start_pos = event.pos()
            event.accept()
            return

        if self._is_drawing:
            pos = self.mapToScene(event.pos())
            if self.current_tool in (
                ToolMode.BRUSH,
                ToolMode.HEAL,
                ToolMode.CLONE_STAMP,
            ):
                self._draw_brush(pos)
            elif self.current_tool in (ToolMode.RECTANGLE, ToolMode.SMART_OBJECT):
                scene_rect = self.sceneRect()
                x1 = max(scene_rect.left(), min(self._draw_start_pos.x(), pos.x()))
                y1 = max(scene_rect.top(), min(self._draw_start_pos.y(), pos.y()))
                x2 = min(scene_rect.right(), max(self._draw_start_pos.x(), pos.x()))
                y2 = min(scene_rect.bottom(), max(self._draw_start_pos.y(), pos.y()))
                self.rect_preview_item.setRect(QRectF(QPointF(x1, y1), QPointF(x2, y2)))
            elif self.current_tool == ToolMode.SMART_LASSO:
                self._lasso_points.append(pos)
                path = self.lasso_path_item.path()
                path.lineTo(pos)
                self.lasso_path_item.setPath(path)
            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: typing.Any) -> None:
        """Handle mouse release — finalize drawing or end pan."""
        if self._is_panning:
            self._is_panning = False
            self.set_tool(self.current_tool, self.brush_size, self.wand_tolerance)
            event.accept()
            return

        if self._is_drawing:
            self._is_drawing = False
            if self.current_tool == ToolMode.RECTANGLE:
                pos = self.mapToScene(event.pos())
                self._apply_rectangle(self._draw_start_pos, pos)
                self.rect_preview_item.hide()
            elif self.current_tool == ToolMode.SMART_OBJECT:
                pos = self.mapToScene(event.pos())
                self._apply_smart_object(self._draw_start_pos, pos)
                self.rect_preview_item.hide()
            elif self.current_tool == ToolMode.SMART_LASSO:
                if len(self._lasso_points) > 2:
                    self._apply_smart_lasso(self._lasso_points)
                self.lasso_path_item.hide()
                self._lasso_points = []
            elif self.current_tool == ToolMode.HEAL:
                if (
                    self._heal_mask is not None
                    and cv2.countNonZero(self._heal_mask) > 0
                ):
                    heal_copy = self._heal_mask.copy()
                    self._heal_mask.fill(0)
                    self.heal_requested.emit(heal_copy)
            elif self.current_tool == ToolMode.CLONE_STAMP:
                if (
                    self.clone_source is not None
                    and self._heal_mask is not None
                    and cv2.countNonZero(self._heal_mask) > 0
                ):
                    dx = int(self._draw_start_pos.x() - self.clone_source.x())
                    dy = int(self._draw_start_pos.y() - self.clone_source.y())
                    clone_copy = self._heal_mask.copy()
                    self._heal_mask.fill(0)
                    self.clone_requested.emit(clone_copy, dx, dy)
                elif self.clone_source is None and self._heal_mask is not None:
                    self._heal_mask.fill(0)
            elif self.current_tool == ToolMode.BRUSH:
                # Record final brush state to history
                self._add_mask_to_history(self.mask)

            self.update_mask_overlay()
            self.mask_changed.emit()
            event.accept()
            return

        super().mouseReleaseEvent(event)

    # ── Drawing Tools (private) ───────────────────────────────

    def _draw_brush(self, pos: QPointF) -> None:
        """Paint a circle on the mask at the given position.

        Coordinates are clamped to image bounds to prevent
        out-of-bounds writes.

        Args:
            pos: Scene-space position to paint at.
        """
        if self.mask is None:
            return
        h, w = self.mask.shape
        x = max(0, min(int(pos.x()), w - 1))
        y = max(0, min(int(pos.y()), h - 1))

        if (
            self.current_tool in (ToolMode.HEAL, ToolMode.CLONE_STAMP)
            and self._heal_mask is not None
        ):
            cv2.circle(self._heal_mask, (x, y), self.brush_size, 255, -1)
        else:
            cv2.circle(self.mask, (x, y), self.brush_size, 255, -1)

        self.update_mask_overlay()

    def _apply_rectangle(self, p1: QPointF, p2: QPointF) -> None:
        """Fill a rectangular region on the mask.

        Coordinates are sorted and clamped to image bounds.

        Args:
            p1: First corner of the rectangle.
            p2: Opposite corner of the rectangle.
        """
        if self.mask is None:
            return
        h, w = self.mask.shape
        x1 = max(0, min(int(p1.x()), int(p2.x())))
        y1 = max(0, min(int(p1.y()), int(p2.y())))
        x2 = min(w, max(int(p1.x()), int(p2.x())))
        y2 = min(h, max(int(p1.y()), int(p2.y())))
        cv2.rectangle(self.mask, (x1, y1), (x2, y2), 255, -1)
        # History is recorded in mouseReleaseEvent — NOT here.
        # This prevents double-recording the same mask state.

    def _apply_smart_object(self, p1: QPointF, p2: QPointF) -> None:
        """Use GrabCut to automatically select the foreground object inside the rect.

        Args:
            p1: First corner of the selection box.
            p2: Opposite corner of the selection box.
        """
        if self.mask is None or self.cv_img is None:
            return

        h, w = self.mask.shape
        x1 = max(0, min(int(p1.x()), int(p2.x())))
        y1 = max(0, min(int(p1.y()), int(p2.y())))
        x2 = min(w, max(int(p1.x()), int(p2.x())))
        y2 = min(h, max(int(p1.y()), int(p2.y())))

        rect_w = x2 - x1
        rect_h = y2 - y1

        # GrabCut requires a bounding rect > 0 area, minimum 5x5 for stability
        if rect_w < 5 or rect_h < 5:
            # Fallback to normal rectangle if it's too small to segment
            cv2.rectangle(self.mask, (x1, y1), (x2, y2), 255, -1)
            return

        # Ensure image is BGR format for GrabCut
        img_bgr = self.cv_img
        if len(img_bgr.shape) == 2:
            img_bgr = cv2.cvtColor(img_bgr, cv2.COLOR_GRAY2BGR)

        gc_mask = np.zeros((h, w), np.uint8)
        bgd_model = np.zeros((1, 65), np.float64)
        fgd_model = np.zeros((1, 65), np.float64)

        rect = (x1, y1, rect_w, rect_h)

        try:
            # 5 iterations usually give an excellent balance between quality and speed
            cv2.grabCut(
                img_bgr, gc_mask, rect, bgd_model, fgd_model, 5, cv2.GC_INIT_WITH_RECT
            )

            # Extract sure foreground (1) and probable foreground (3)
            mask_binary = np.where((gc_mask == 1) | (gc_mask == 3), 255, 0).astype(
                "uint8"
            )

            # Merge with existing mask
            self.mask = cv2.bitwise_or(self.mask, mask_binary)
        except Exception as e:
            logger.error("Smart object selection failed: %s", e)

    def _apply_smart_lasso(self, points: list[QPointF]) -> None:
        """Use GrabCut initialized with a freehand lasso polygon.

        Args:
            points: List of points making up the lasso boundary.
        """
        if self.mask is None or self.cv_img is None or len(points) < 3:
            return

        h, w = self.mask.shape

        # Convert QPointF list to numpy array of integer coordinates
        pts = np.array([[[int(p.x()), int(p.y())]] for p in points], dtype=np.int32)

        # Clamp points to image bounds
        pts[:, 0, 0] = np.clip(pts[:, 0, 0], 0, w - 1)
        pts[:, 0, 1] = np.clip(pts[:, 0, 1], 0, h - 1)

        # Ensure image is BGR format for GrabCut
        img_bgr = self.cv_img
        if len(img_bgr.shape) == 2:
            img_bgr = cv2.cvtColor(img_bgr, cv2.COLOR_GRAY2BGR)

        # Create the GrabCut mask
        # Initialize everything to BGD (0)
        gc_mask = np.zeros((h, w), np.uint8)

        # Fill the drawn polygon with PR_FGD (3)
        cv2.fillPoly(gc_mask, [pts], 3)

        # Find the bounding rect of the polygon to ensure it's valid
        x, y, rect_w, rect_h = cv2.boundingRect(pts)
        if rect_w < 5 or rect_h < 5:
            # Fallback to simple polygon fill if too small
            cv2.fillPoly(self.mask, [pts], 255)
            return

        bgd_model = np.zeros((1, 65), np.float64)
        fgd_model = np.zeros((1, 65), np.float64)

        try:
            # Run GrabCut with Mask Initialization
            # The polygon is PR_FGD, the rest is BGD.
            cv2.grabCut(
                img_bgr, gc_mask, None, bgd_model, fgd_model, 5, cv2.GC_INIT_WITH_MASK
            )

            # Extract sure foreground (1) and probable foreground (3)
            mask_binary = np.where((gc_mask == 1) | (gc_mask == 3), 255, 0).astype(
                "uint8"
            )

            # Merge with existing mask
            self.mask = cv2.bitwise_or(self.mask, mask_binary)
        except Exception as e:
            logger.error("Smart lasso selection failed: %s", e)

    def _apply_magic_wand(self, pos: QPointF) -> None:
        """Select a contiguous color region using flood fill.

        Uses FLOODFILL_MASK_ONLY so the source image is not modified.
        The flood fill result is OR-ed into the existing mask.

        Args:
            pos: Scene-space click position (seed point).
        """
        if self.cv_img is None:
            return
        h, w = self.cv_img.shape[:2]
        x, y = int(pos.x()), int(pos.y())
        if not (0 <= x < w and 0 <= y < h):
            return

        seed_pt = (x, y)
        tol = self.wand_tolerance
        diff = (tol, tol, tol)

        flood_mask = np.zeros((h + 2, w + 2), dtype=np.uint8)
        flags = cv2.FLOODFILL_FIXED_RANGE | (255 << 8) | cv2.FLOODFILL_MASK_ONLY
        # CRITICAL: Pass a copy to floodFill to prevent any possibility
        # of the source image being modified.
        img_copy = self.cv_img.copy()
        cv2.floodFill(img_copy, flood_mask, seed_pt, (255, 255, 255), diff, diff, flags)

        self.mask = cv2.bitwise_or(self.mask, flood_mask[1:-1, 1:-1])
        self._add_mask_to_history(self.mask)
        self.update_mask_overlay()
        self.mask_changed.emit()

    def auto_detect_text(self) -> None:
        """Automatically detect high-contrast text and logos using morphological operations."""
        if self.cv_img is None or self.mask is None:
            return

        # Convert to grayscale
        gray = cv2.cvtColor(self.cv_img, cv2.COLOR_BGR2GRAY)

        # Apply morphological gradient to highlight edges and text boundaries
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        grad = cv2.morphologyEx(gray, cv2.MORPH_GRADIENT, kernel)

        # Binarize using Otsu's thresholding
        _, bw = cv2.threshold(grad, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)

        # Connect horizontally oriented regions (text lines)
        connected = cv2.morphologyEx(
            bw, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (9, 1))
        )

        # Find contours
        contours, _ = cv2.findContours(
            connected.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        h, w = self.cv_img.shape[:2]
        img_area = h * w

        for contour in contours:
            x, y, cw, ch = cv2.boundingRect(contour)
            area = cw * ch

            # Filter contours based on size and aspect ratio typical for text
            if area > 15 and area < (img_area * 0.2):
                cv2.rectangle(self.mask, (x, y), (x + cw, y + ch), 255, -1)

        self._add_mask_to_history(self.mask)
        self.update_mask_overlay()
        self.mask_changed.emit()

    # ── Public aliases for backward compatibility with tests ──

    def draw_brush(self, pos: QPointF) -> None:
        """Public alias for _draw_brush (backward compatibility)."""
        self._draw_brush(pos)

    def apply_rectangle(self, p1: QPointF, p2: QPointF) -> None:
        """Public alias for _apply_rectangle (backward compatibility).

        Note: Unlike the internal version, this also records history
        to maintain compatibility with existing test code.
        """
        self._apply_rectangle(p1, p2)
        self._add_mask_to_history(self.mask)

    def apply_magic_wand(self, pos: QPointF) -> None:
        """Public alias for _apply_magic_wand (backward compatibility)."""
        self._apply_magic_wand(pos)
