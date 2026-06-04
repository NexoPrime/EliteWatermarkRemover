"""Main application window for the Elite Watermark Remover.

Provides the primary QMainWindow with all UI panels, menu bar,
status bar, keyboard shortcuts, and orchestration of the inpainting
workflow (single and batch processing).
"""

from __future__ import annotations

import logging
import os
import typing
from collections import deque
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from PyQt5.QtCore import Qt, QThread, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import (
    QAction,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMenuBar,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from src.config import AppConfig
from src.constants import (
    APP_NAME,
    APP_VERSION,
    DEFAULT_DILATE,
    DEFAULT_FEATHER_WIDTH,
    DEFAULT_OUTPUT_SUBDIR,
    DEFAULT_RADIUS,
    DEFAULT_WINDOW_HEIGHT,
    DEFAULT_WINDOW_WIDTH,
    IMAGE_FILTER,
    IMAGE_UNDO_MAX,
    LEFT_PANEL_MAX_WIDTH,
    LEFT_PANEL_MIN_WIDTH,
    MASK_FILTER,
    MIN_WINDOW_HEIGHT,
    MIN_WINDOW_WIDTH,
    SAVE_IMAGE_FILTER,
    SAVE_MASK_FILTER,
    SPLITTER_SIZES,
    SUPPORTED_IMAGE_EXTENSIONS,
)
from src.core.inpainter import Inpainter
from src.core.models import BatchSettings, InpaintSettings
from src.core.worker import BatchWorker
from src.ui.components.image_viewer import ImageEditorView, ToolMode

logger = logging.getLogger(__name__)


# ── Inpaint Worker Thread ─────────────────────────────────────


class _InpaintWorker(QThread):
    """Background thread for single-image inpainting.

    Prevents the UI from freezing during heavy inpaint operations.

    Signals:
        result_ready: Emitted with the inpainted image on success.
        error_occurred: Emitted with the error message on failure.
    """

    result_ready = pyqtSignal(np.ndarray)
    error_occurred = pyqtSignal(str)

    def __init__(
        self,
        img: np.ndarray,
        mask: np.ndarray,
        settings: InpaintSettings,
    ) -> None:
        super().__init__()
        self._img = img
        self._mask = mask
        self._settings = settings

    def run(self) -> None:
        """Execute inpainting in the background thread."""
        try:
            result = Inpainter.inpaint_image(self._img, self._mask, self._settings)
            self.result_ready.emit(result)
        except Exception as e:
            logger.exception("Inpainting failed.")
            self.error_occurred.emit(str(e))


# ── Main Window ───────────────────────────────────────────────


class EliteWatermarkRemover(QMainWindow):
    """Main application window for watermark removal.

    Provides a complete workflow for loading images, selecting
    watermark regions with interactive tools, removing watermarks
    using configurable inpainting algorithms, and batch processing
    entire folders.

    The window is divided into:
      - Left panel: Controls and settings (5 grouped sections)
      - Right panel: Interactive image viewer with mask overlay
      - Menu bar: File, Edit, Tools, Help menus
      - Status bar: Image info and processing status
    """

    def __init__(self) -> None:
        """Initialize the main window and restore saved state."""
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.setMinimumSize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)
        self.setAcceptDrops(True)

        # Configuration
        self.config = AppConfig()

        # Image state
        self.ref_image: Optional[np.ndarray] = None
        self.current_image: Optional[np.ndarray] = None
        self.undo_stack: deque[np.ndarray] = deque(maxlen=IMAGE_UNDO_MAX)

        # Template matching state
        self.ref_mask: Optional[np.ndarray] = None
        self.template_rect: Optional[tuple[int, int, int, int]] = None
        self.watermark_template: Optional[np.ndarray] = None

        # Batch state
        self.batch_folder: str = ""
        self.worker: Optional[BatchWorker] = None
        self._inpaint_worker: Optional[_InpaintWorker] = None

        # Build UI
        self._build_ui()
        self._build_menu_bar()
        self._build_status_bar()
        self._setup_shortcuts()
        self._restore_state()

        logger.info("Application window initialized.")

    # ══════════════════════════════════════════════════════════
    #  UI Construction
    # ══════════════════════════════════════════════════════════

    def _build_ui(self) -> None:
        """Build the main UI layout with splitter, panels, and viewer."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        self.splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(self.splitter)

        # Left panel
        left_panel = QWidget()
        left_panel.setMinimumWidth(LEFT_PANEL_MIN_WIDTH)
        left_panel.setMaximumWidth(LEFT_PANEL_MAX_WIDTH)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)

        # Tab Widget
        self.tabs = QTabWidget()
        left_layout.addWidget(self.tabs)

        # Tab 1: Editor
        tab_editor = QWidget()
        editor_layout = QVBoxLayout(tab_editor)
        self._build_file_section(editor_layout)
        self._build_tools_section(editor_layout)
        self._build_preview_section(editor_layout)
        editor_layout.addStretch()
        self.tabs.addTab(tab_editor, "Editor")

        # Tab 2: Engine
        tab_engine = QWidget()
        engine_layout = QVBoxLayout(tab_engine)
        self._build_settings_section(engine_layout)
        engine_layout.addStretch()
        self.tabs.addTab(tab_engine, "Engine")

        # Tab 3: Batch
        tab_batch = QWidget()
        batch_layout = QVBoxLayout(tab_batch)
        self._build_batch_section(batch_layout)
        batch_layout.addStretch()
        self.tabs.addTab(tab_batch, "Batch")

        # Viewer
        self.viewer = ImageEditorView()
        self.viewer.mask_changed.connect(self._on_mask_changed)
        self.viewer.undo_available.connect(self.btn_mask_undo.setEnabled)
        self.viewer.redo_available.connect(self.btn_mask_redo.setEnabled)
        self.viewer.heal_requested.connect(self._on_heal_requested)
        self.viewer.clone_requested.connect(self._on_clone_requested)
        self.btn_mask_undo.clicked.connect(self.viewer.undo_mask_edit)
        self.btn_mask_redo.clicked.connect(self.viewer.redo_mask_edit)
        self.btn_smooth_mask.clicked.connect(lambda: self.viewer.smooth_mask())

        self.splitter.addWidget(left_panel)
        self.splitter.addWidget(self.viewer)
        self.splitter.setSizes(SPLITTER_SIZES)

        self._select_tool(ToolMode.RECTANGLE)

    def _build_file_section(self, parent_layout: QVBoxLayout) -> None:
        """Build Section 1: Image & Mask Management."""
        group = QGroupBox("1. Image & Mask Management")
        layout = QVBoxLayout()

        btn_load = QPushButton("Load Image")
        btn_load.clicked.connect(self.load_image)
        layout.addWidget(btn_load)

        self.lbl_image_info = QLabel("No image loaded.")
        self.lbl_image_info.setWordWrap(True)
        layout.addWidget(self.lbl_image_info)

        mask_row = QHBoxLayout()
        btn_clear = QPushButton("Clear Mask")
        btn_clear.clicked.connect(self._clear_selection)
        mask_row.addWidget(btn_clear)

        btn_load_mask = QPushButton("Load Mask")
        btn_load_mask.clicked.connect(self.load_mask)
        mask_row.addWidget(btn_load_mask)

        btn_save_mask = QPushButton("Save Mask")
        btn_save_mask.clicked.connect(self._save_mask)
        mask_row.addWidget(btn_save_mask)
        layout.addLayout(mask_row)

        undo_redo_row = QHBoxLayout()
        self.btn_mask_undo = QPushButton("Undo Mask")
        self.btn_mask_undo.setEnabled(False)
        undo_redo_row.addWidget(self.btn_mask_undo)

        self.btn_mask_redo = QPushButton("Redo Mask")
        self.btn_mask_redo.setEnabled(False)
        undo_redo_row.addWidget(self.btn_mask_redo)
        layout.addLayout(undo_redo_row)

        self.btn_smooth_mask = QPushButton("Smooth Mask")
        self.btn_smooth_mask.setToolTip(
            "Applies morphological operations to refine mask edges."
        )
        layout.addWidget(self.btn_smooth_mask)

        group.setLayout(layout)
        parent_layout.addWidget(group)

    def _build_tools_section(self, parent_layout: QVBoxLayout) -> None:
        """Build Section 2: Advanced Selection Tools."""
        group = QGroupBox("2. Advanced Selection Tools")
        layout = QVBoxLayout()

        from PyQt5.QtWidgets import QSizePolicy

        self.btn_smart_obj = QToolButton()
        self.btn_smart_obj.setText("Smart Box")
        self.btn_smart_obj.setToolTip("Auto-detect object inside drawn rectangle")
        self.btn_smart_obj.setCheckable(True)
        self.btn_smart_obj.clicked.connect(
            lambda: self._select_tool(ToolMode.SMART_OBJECT)
        )
        self.btn_smart_obj.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.btn_smart_lasso = QToolButton()
        self.btn_smart_lasso.setText("Smart Lasso")
        self.btn_smart_lasso.setToolTip(
            "Draw a line loop around object for elite auto-snapping extraction"
        )
        self.btn_smart_lasso.setCheckable(True)
        self.btn_smart_lasso.clicked.connect(
            lambda: self._select_tool(ToolMode.SMART_LASSO)
        )
        self.btn_smart_lasso.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.btn_heal = QToolButton()
        self.btn_heal.setText("Heal Brush")
        self.btn_heal.setToolTip(
            "Instant AI texture repair. Brush over an artifact to fix it immediately."
        )
        self.btn_heal.setCheckable(True)
        self.btn_heal.clicked.connect(lambda: self._select_tool(ToolMode.HEAL))
        self.btn_heal.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.btn_clone = QToolButton()
        self.btn_clone.setText("Clone Stamp")
        self.btn_clone.setToolTip(
            "Alt-Click to set source, then brush to perfectly copy texture to new location."
        )
        self.btn_clone.setCheckable(True)
        self.btn_clone.clicked.connect(lambda: self._select_tool(ToolMode.CLONE_STAMP))
        self.btn_clone.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.btn_rect = QToolButton()
        self.btn_rect.setText("Rectangle")
        self.btn_rect.setCheckable(True)
        self.btn_rect.clicked.connect(lambda: self._select_tool(ToolMode.RECTANGLE))
        self.btn_rect.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.btn_brush = QToolButton()
        self.btn_brush.setText("Brush")
        self.btn_brush.setCheckable(True)
        self.btn_brush.clicked.connect(lambda: self._select_tool(ToolMode.BRUSH))
        self.btn_brush.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.btn_wand = QToolButton()
        self.btn_wand.setText("Magic Wand")
        self.btn_wand.setCheckable(True)
        self.btn_wand.clicked.connect(lambda: self._select_tool(ToolMode.MAGIC_WAND))
        self.btn_wand.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        layout.addWidget(self.btn_smart_lasso)
        layout.addWidget(self.btn_smart_obj)
        layout.addWidget(self.btn_heal)
        layout.addWidget(self.btn_clone)
        layout.addWidget(self.btn_brush)
        layout.addWidget(self.btn_rect)
        layout.addWidget(self.btn_wand)

        self.tool_buttons = [
            self.btn_smart_obj,
            self.btn_smart_lasso,
            self.btn_heal,
            self.btn_clone,
            self.btn_rect,
            self.btn_brush,
            self.btn_wand,
        ]
        layout.addLayout(tool_grid)

        param_row = QHBoxLayout()
        param_row.addWidget(QLabel("Brush Size / Wand Tolerance:"))
        self.spin_tool_param = QSpinBox()
        self.spin_tool_param.setRange(1, 200)
        self.spin_tool_param.setValue(20)
        self.spin_tool_param.valueChanged.connect(self._update_tool_params)
        param_row.addWidget(self.spin_tool_param)
        layout.addLayout(param_row)

        group.setLayout(layout)
        parent_layout.addWidget(group)

    def _build_settings_section(self, parent_layout: QVBoxLayout) -> None:
        """Build Section 3: Elite Removal Settings."""
        group = QGroupBox("3. Elite Removal Settings")
        layout = QVBoxLayout()

        meth_row = QHBoxLayout()
        meth_row.addWidget(QLabel("Algorithm:"))
        self.combo_method = QComboBox()
        self.combo_method.addItems(
            [
                "Shift-Map (Content Aware)",
                "FSR (Frequency Selective)",
                "Telea",
                "Navier-Stokes",
            ]
        )
        meth_row.addWidget(self.combo_method)
        layout.addLayout(meth_row)

        rad_row = QHBoxLayout()
        rad_row.addWidget(QLabel("Search Radius:"))
        self.spin_radius = QSpinBox()
        self.spin_radius.setRange(1, 200)
        self.spin_radius.setValue(DEFAULT_RADIUS)
        rad_row.addWidget(self.spin_radius)
        layout.addLayout(rad_row)

        dil_row = QHBoxLayout()
        dil_row.addWidget(QLabel("Mask Dilation (px):"))
        self.spin_dilate = QSpinBox()
        self.spin_dilate.setRange(0, 50)
        self.spin_dilate.setValue(DEFAULT_DILATE)
        self.spin_dilate.setToolTip(
            "Expands the mask to perfectly cover anti-aliased edge pixels."
        )
        dil_row.addWidget(self.spin_dilate)
        layout.addLayout(dil_row)

        self.chk_grain = QCheckBox("Auto-Restore Film Grain / Texture")
        self.chk_grain.setChecked(True)
        self.chk_grain.setToolTip(
            "Synthesizes local image noise to prevent the 'plastic' blur look."
        )
        layout.addWidget(self.chk_grain)

        self.chk_feather = QCheckBox("Feather Edges (Seamless Blend)")
        self.chk_feather.setChecked(True)
        layout.addWidget(self.chk_feather)

        feat_row = QHBoxLayout()
        feat_row.addWidget(QLabel("Feather Width:"))
        self.spin_feather = QSpinBox()
        self.spin_feather.setRange(1, 100)
        self.spin_feather.setValue(DEFAULT_FEATHER_WIDTH)
        feat_row.addWidget(self.spin_feather)
        layout.addLayout(feat_row)

        group.setLayout(layout)
        parent_layout.addWidget(group)

    def _build_preview_section(self, parent_layout: QVBoxLayout) -> None:
        """Build Section 4: Interactive Preview & Export."""
        group = QGroupBox("4. Interactive Preview & Export")
        layout = QVBoxLayout()

        btn_inpaint = QPushButton("Remove Watermark (Preview)")
        btn_inpaint.clicked.connect(self._inpaint_single)
        layout.addWidget(btn_inpaint)

        action_row = QHBoxLayout()

        self.btn_compare = QPushButton("Hold to Compare")
        self.btn_compare.pressed.connect(self._show_original)
        self.btn_compare.released.connect(self._show_current)
        action_row.addWidget(self.btn_compare)

        btn_undo = QPushButton("Undo Image")
        btn_undo.clicked.connect(self._undo_single)
        action_row.addWidget(btn_undo)

        btn_save = QPushButton("Save Result")
        btn_save.clicked.connect(self._save_single)
        action_row.addWidget(btn_save)

        layout.addLayout(action_row)
        group.setLayout(layout)
        parent_layout.addWidget(group)

    def _build_batch_section(self, parent_layout: QVBoxLayout) -> None:
        """Build Section 5: Automated Batch Processing."""
        group = QGroupBox("5. Automated Batch Processing")
        layout = QVBoxLayout()

        btn_folder = QPushButton("Select Target Folder")
        btn_folder.clicked.connect(self._select_folder)
        layout.addWidget(btn_folder)

        self.lbl_folder = QLabel("No folder selected.")
        self.lbl_folder.setWordWrap(True)
        layout.addWidget(self.lbl_folder)

        out_row = QHBoxLayout()
        out_row.addWidget(QLabel("Output Subdir:"))
        self.le_outdir = QLineEdit(DEFAULT_OUTPUT_SUBDIR)
        out_row.addWidget(self.le_outdir)
        layout.addLayout(out_row)

        self.chk_tm = QCheckBox("Smart Template Matching")
        self.chk_tm.setChecked(True)
        self.chk_tm.setToolTip(
            "Finds the exact watermark coordinates dynamically in each image."
        )
        layout.addWidget(self.chk_tm)

        self.btn_batch = QPushButton("Start Batch Process")
        self.btn_batch.clicked.connect(self._toggle_batch)
        layout.addWidget(self.btn_batch)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        self.lbl_status = QLabel("Ready.")
        layout.addWidget(self.lbl_status)

        group.setLayout(layout)
        parent_layout.addWidget(group)

    def _build_menu_bar(self) -> None:
        """Build the application menu bar with File, Edit, Tools, Help."""
        menu_bar = self.menuBar()

        # ─── File ───
        file_menu = menu_bar.addMenu("&File")

        act_open = QAction("&Open Image...", self)
        act_open.setShortcut(QKeySequence.Open)
        act_open.triggered.connect(self.load_image)
        file_menu.addAction(act_open)

        act_save = QAction("&Save Result...", self)
        act_save.setShortcut(QKeySequence.Save)
        act_save.triggered.connect(self._save_single)
        file_menu.addAction(act_save)

        file_menu.addSeparator()

        act_load_mask = QAction("Load &Mask...", self)
        act_load_mask.triggered.connect(self.load_mask)
        file_menu.addAction(act_load_mask)

        act_save_mask = QAction("Save Mas&k...", self)
        act_save_mask.triggered.connect(self._save_mask)
        file_menu.addAction(act_save_mask)

        file_menu.addSeparator()

        act_quit = QAction("&Quit", self)
        act_quit.setShortcut(QKeySequence.Quit)
        act_quit.triggered.connect(self.close)
        file_menu.addAction(act_quit)

        # ─── Edit ───
        edit_menu = menu_bar.addMenu("&Edit")

        act_undo_img = QAction("Undo &Image", self)
        act_undo_img.setShortcut(QKeySequence("Ctrl+Z"))
        act_undo_img.triggered.connect(self._undo_single)
        edit_menu.addAction(act_undo_img)

        act_undo_mask = QAction("Undo &Mask", self)
        act_undo_mask.setShortcut(QKeySequence("Ctrl+Shift+Z"))
        act_undo_mask.triggered.connect(
            self.viewer.undo_mask_edit if hasattr(self, "viewer") else lambda: None
        )
        edit_menu.addAction(act_undo_mask)

        act_redo_mask = QAction("&Redo Mask", self)
        act_redo_mask.setShortcut(QKeySequence("Ctrl+Y"))
        act_redo_mask.triggered.connect(
            self.viewer.redo_mask_edit if hasattr(self, "viewer") else lambda: None
        )
        edit_menu.addAction(act_redo_mask)

        edit_menu.addSeparator()

        act_clear = QAction("&Clear Selection", self)
        act_clear.setShortcut(QKeySequence("Escape"))
        act_clear.triggered.connect(self._clear_selection)
        edit_menu.addAction(act_clear)

        # ─── Tools ───
        tools_menu = menu_bar.addMenu("&Tools")

        act_rect = QAction("&Rectangle Tool", self)
        act_rect.setShortcut(QKeySequence("1"))
        act_rect.triggered.connect(lambda: self._select_tool(ToolMode.RECTANGLE))
        tools_menu.addAction(act_rect)

        act_brush = QAction("&Brush Tool", self)
        act_brush.setShortcut(QKeySequence("2"))
        act_brush.triggered.connect(lambda: self._select_tool(ToolMode.BRUSH))
        tools_menu.addAction(act_brush)

        act_wand = QAction("Magic &Wand Tool", self)
        act_wand.setShortcut(QKeySequence("3"))
        act_wand.triggered.connect(lambda: self._select_tool(ToolMode.MAGIC_WAND))
        tools_menu.addAction(act_wand)

        tools_menu.addSeparator()

        act_inpaint = QAction("&Remove Watermark", self)
        act_inpaint.setShortcut(QKeySequence("Ctrl+R"))
        act_inpaint.triggered.connect(self._inpaint_single)
        tools_menu.addAction(act_inpaint)

        # ─── Help ───
        help_menu = menu_bar.addMenu("&Help")

        act_shortcuts = QAction("&Keyboard Shortcuts", self)
        act_shortcuts.triggered.connect(self._show_shortcuts)
        help_menu.addAction(act_shortcuts)

        act_about = QAction("&About", self)
        act_about.triggered.connect(self._show_about)
        help_menu.addAction(act_about)

    def _build_status_bar(self) -> None:
        """Build the status bar with permanent info widgets."""
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Ready.")

        self.lbl_img_size = QLabel("")
        self.status_bar.addPermanentWidget(self.lbl_img_size)

    def _setup_shortcuts(self) -> None:
        """Set up additional keyboard shortcuts."""
        # Shortcuts are primarily set via QAction in menu bar.
        # This method is reserved for any non-menu shortcuts.
        pass

    def _restore_state(self) -> None:
        """Restore window geometry and settings from config."""
        geo = self.config.window_geometry
        if geo and not geo.isEmpty():
            self.restoreGeometry(geo)
        else:
            self.showMaximized()

        saved_algo = self.config.algorithm
        idx = self.combo_method.findText(saved_algo)
        if idx >= 0:
            self.combo_method.setCurrentIndex(idx)

        self.spin_radius.setValue(self.config.radius)
        self.spin_dilate.setValue(self.config.dilate_mask)
        self.spin_feather.setValue(self.config.feather_width)

        out_sub = self.config.output_subdir
        if out_sub:
            self.le_outdir.setText(out_sub)

    # ══════════════════════════════════════════════════════════
    #  Tool Selection
    # ══════════════════════════════════════════════════════════

    def _select_tool(self, tool: ToolMode) -> None:
        """Activate a selection tool and update button states.

        Args:
            tool: The tool mode to activate.
        """
        for btn in self.tool_buttons:
            btn.setChecked(False)

        if tool == ToolMode.RECTANGLE:
            self.btn_rect.setChecked(True)
        elif tool == ToolMode.BRUSH:
            self.btn_brush.setChecked(True)
        elif tool == ToolMode.MAGIC_WAND:
            self.btn_wand.setChecked(True)
        elif tool == ToolMode.CLONE_STAMP:
            self.btn_clone.setChecked(True)

        param = self.spin_tool_param.value()
        self.viewer.set_tool(tool, size=param, tolerance=param)

    def _update_tool_params(self, value: int) -> None:
        """Update tool parameters when the spin box changes.

        Args:
            value: New parameter value.
        """
        tool = ToolMode.RECTANGLE
        if self.btn_brush.isChecked():
            tool = ToolMode.BRUSH
        if self.btn_wand.isChecked():
            tool = ToolMode.MAGIC_WAND
        self.viewer.set_tool(tool, size=value, tolerance=value)

    # ══════════════════════════════════════════════════════════
    #  Image I/O
    # ══════════════════════════════════════════════════════════

    def load_image(self) -> None:
        """Open a file dialog and load a reference image."""
        start_dir = self.config.last_open_dir or ""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Reference Image", start_dir, IMAGE_FILTER
        )
        if not file_path:
            return

        img = cv2.imread(file_path)
        if img is None:
            QMessageBox.critical(self, "Error", "Failed to load image.")
            return

        self.config.last_open_dir = str(Path(file_path).parent)

        self.ref_image = img.copy()
        self.current_image = img.copy()
        self.undo_stack.clear()
        self.ref_mask = None
        self.template_rect = None
        self.watermark_template = None

        self.viewer.set_image(self.current_image)
        self.viewer.clear_selection()
        h, w = img.shape[:2]
        self.lbl_image_info.setText(f"Loaded: {Path(file_path).name}\nSize: {w}×{h}")
        self.lbl_img_size.setText(f"{w}×{h}")
        self._set_status("Image loaded. Use tools to select the watermark.")
        logger.info("Loaded image: %s (%dx%d)", file_path, w, h)

    def _save_single(self) -> None:
        """Save the current processed image."""
        if self.current_image is None:
            QMessageBox.warning(self, "Notice", "No image to save.")
            return

        start_dir = self.config.last_save_dir or ""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Result", start_dir, SAVE_IMAGE_FILTER
        )
        if not file_path:
            return

        self.config.last_save_dir = str(Path(file_path).parent)
        success = cv2.imwrite(file_path, self.current_image)
        if success:
            self._set_status(f"Saved: {Path(file_path).name}")
            logger.info("Saved result to %s", file_path)
        else:
            QMessageBox.critical(self, "Error", "Failed to save image.")
            logger.error("Failed to save image to %s", file_path)

    # ══════════════════════════════════════════════════════════
    #  Mask I/O
    # ══════════════════════════════════════════════════════════

    def _clear_selection(self) -> None:
        """Clear the current mask selection."""
        self.viewer.clear_selection()

    def load_mask(self, file_path: Optional[str] = None) -> None:
        """Load a mask from file (PNG or NPY format).

        Args:
            file_path: Path to mask file. If None, opens a dialog.
        """
        if self.ref_image is None:
            QMessageBox.warning(
                self, "Notice", "Load an image first before loading a mask."
            )
            return

        if not file_path:
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Load Mask", "", MASK_FILTER
            )

        if not file_path:
            return

        if file_path.lower().endswith(".npy"):
            try:
                # SECURITY: allow_pickle=False prevents arbitrary code execution
                loaded_mask = np.load(file_path, allow_pickle=False)
                if loaded_mask.shape[:2] != self.ref_image.shape[:2]:
                    QMessageBox.critical(
                        self,
                        "Error",
                        "Mask dimensions do not match current image dimensions.",
                    )
                    return
                self.viewer._add_mask_to_history(self.viewer.mask)
                self.viewer.mask = loaded_mask.astype(np.uint8)
                self.viewer.mask[self.viewer.mask > 0] = 255
                self.viewer.update_mask_overlay()
                self._on_mask_changed()
                self._set_status(f"Mask loaded from {Path(file_path).name}")
                logger.info("NPY mask loaded from %s", file_path)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load .npy mask: {e}")
                logger.exception("Failed to load NPY mask.")
        else:
            if self.viewer.load_mask(file_path):
                self._on_mask_changed()
                self._set_status(f"Mask loaded from {Path(file_path).name}")
            else:
                QMessageBox.critical(self, "Error", "Failed to load mask image.")

    def _save_mask(self) -> None:
        """Save the current mask to file (PNG or NPY format)."""
        if self.viewer.mask is None or cv2.countNonZero(self.viewer.mask) == 0:
            QMessageBox.warning(self, "Notice", "No mask to save.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Mask", "", SAVE_MASK_FILTER
        )
        if not file_path:
            return

        if file_path.lower().endswith(".npy"):
            try:
                np.save(file_path, self.viewer.mask)
                self._set_status(f"Mask saved to {Path(file_path).name}")
                logger.info("NPY mask saved to %s", file_path)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save .npy mask: {e}")
                logger.exception("Failed to save NPY mask.")
        else:
            if self.viewer.save_mask(file_path):
                self._set_status(f"Mask saved to {Path(file_path).name}")
            else:
                QMessageBox.critical(self, "Error", "Failed to save mask image.")

    # ══════════════════════════════════════════════════════════
    #  Mask Change Handler
    # ══════════════════════════════════════════════════════════

    def _on_mask_changed(self) -> None:
        """Handle mask changes — update reference data for batch."""
        if self.ref_image is None:
            return

        mask = self.viewer.get_mask()
        if mask is None or cv2.countNonZero(mask) == 0:
            self.ref_mask = None
            self.template_rect = None
            self.watermark_template = None
            self._set_status("Selection cleared.")
            return

        self.ref_mask = mask.copy()
        x, y, w, h = cv2.boundingRect(self.ref_mask)
        self.template_rect = (x, y, x + w, y + h)

        if w > 0 and h > 0:
            self.watermark_template = self.ref_image[y : y + h, x : x + w].copy()
        else:
            self.watermark_template = None

        self._set_status(f"Mask updated: Bounds {w}×{h} px")

    # ══════════════════════════════════════════════════════════
    #  Inpainting (Single Image)
    # ══════════════════════════════════════════════════════════

    def get_inpaint_settings(self) -> InpaintSettings:
        """Build an InpaintSettings from the current UI state.

        Returns:
            Typed inpainting settings.
        """
        return InpaintSettings(
            method=self.combo_method.currentText(),
            radius=self.spin_radius.value(),
            use_feathering=self.chk_feather.isChecked(),
            feather_width=self.spin_feather.value(),
            dilate_mask=self.spin_dilate.value(),
            add_grain=self.chk_grain.isChecked(),
        )

    def _inpaint_single(self) -> None:
        """Run watermark removal on the current image (off-thread)."""
        if self.current_image is None:
            QMessageBox.warning(self, "Notice", "Please load an image first.")
            return

        mask = self.viewer.get_mask()
        if mask is None or cv2.countNonZero(mask) == 0:
            QMessageBox.warning(
                self, "Notice", "Please select a region on the image using the tools."
            )
            return

        if self._inpaint_worker is not None and self._inpaint_worker.isRunning():
            self._set_status("Inpainting already in progress...")
            return

        self.undo_stack.append(self.current_image.copy())
        settings = self.get_inpaint_settings()

        self._set_status("Removing watermark...")
        self._inpaint_worker = _InpaintWorker(
            self.current_image.copy(), mask.copy(), settings
        )
        self._inpaint_worker.result_ready.connect(self._on_inpaint_done)
        self._inpaint_worker.error_occurred.connect(self._on_inpaint_error)
        self._inpaint_worker.start()

    def _on_heal_requested(self, temp_mask: np.ndarray) -> None:
        """Handle instant heal brush request."""
        if (
            self.current_image is None
            or self._inpaint_worker is not None
            and self._inpaint_worker.isRunning()
        ):
            return

        self.undo_stack.append(self.current_image.copy())
        settings = self.get_inpaint_settings()

        # Override radius for quick heal
        settings.radius = min(settings.radius, 15)

        self._set_status("Applying instant heal...")
        self._inpaint_worker = _InpaintWorker(
            self.current_image.copy(), temp_mask, settings
        )
        self._inpaint_worker.result_ready.connect(self._on_inpaint_done)
        self._inpaint_worker.error_occurred.connect(self._on_inpaint_error)
        self._inpaint_worker.start()

    @pyqtSlot(np.ndarray, int, int)
    def _on_clone_requested(self, mask: np.ndarray, dx: int, dy: int) -> None:
        """Handle instant clone stamp request.

        Copies texture from (x-dx, y-dy) to (x, y).
        """
        if self.current_image is None:
            return

        self.undo_stack.append(self.current_image.copy())

        h, w = self.current_image.shape[:2]

        # Matrix to shift mask to source position
        M_to_src = np.float32([[1, 0, -dx], [0, 1, -dy]])
        src_mask = cv2.warpAffine(mask, M_to_src, (w, h))

        # Extract pixels from source
        src_pixels = np.zeros_like(self.current_image)
        src_pixels[src_mask > 0] = self.current_image[src_mask > 0]

        # Matrix to shift pixels to target position
        M_to_dst = np.float32([[1, 0, dx], [0, 1, dy]])
        dst_pixels = cv2.warpAffine(src_pixels, M_to_dst, (w, h))

        # Soften mask for seamless blending
        blur_mask = cv2.GaussianBlur(mask, (7, 7), 0).astype(float) / 255.0
        if len(self.current_image.shape) == 3:
            blur_mask = np.expand_dims(blur_mask, axis=2)

        # Composite
        self.current_image = (
            dst_pixels * blur_mask + self.current_image * (1 - blur_mask)
        ).astype(np.uint8)
        self.viewer.update_image(self.current_image)
        self._set_status("Clone stamp applied.")

    def _show_original(self) -> None:
        if self.ref_image is not None:
            self.viewer.cv_img = self.ref_image
            self.viewer.set_image(self.ref_image)
            self.viewer.mask_item.hide()

    def _show_current(self) -> None:
        if self.current_image is not None:
            self.viewer.cv_img = self.current_image
            self.viewer.set_image(self.current_image)
            self.viewer.mask_item.show()

    @pyqtSlot(np.ndarray)
    def _on_inpaint_done(self, result: np.ndarray) -> None:
        """Handle successful inpainting result.

        Args:
            result: The inpainted image.
        """
        self.current_image = result
        self.viewer.update_image(self.current_image)
        self._set_status("Elite removal complete.")
        logger.info("Single inpainting completed successfully.")

    @pyqtSlot(str)
    def _on_inpaint_error(self, error_msg: str) -> None:
        """Handle inpainting failure.

        Args:
            error_msg: Description of what went wrong.
        """
        # Restore the pre-inpaint image from undo stack
        if self.undo_stack:
            self.current_image = self.undo_stack.pop()
        QMessageBox.critical(self, "Error", f"Inpainting failed: {error_msg}")
        self._set_status("Inpainting failed.")

    def _undo_single(self) -> None:
        """Undo the last inpainting operation."""
        if not self.undo_stack:
            self._set_status("Nothing to undo.")
            return

        self.current_image = self.undo_stack.pop()
        self.viewer.update_image(self.current_image)
        self._set_status("Undo successful.")

    # ══════════════════════════════════════════════════════════
    #  Batch Processing
    # ══════════════════════════════════════════════════════════

    def _select_folder(self) -> None:
        """Open a dialog to select a folder for batch processing."""
        start_dir = self.config.last_batch_dir or ""
        folder = QFileDialog.getExistingDirectory(
            self, "Select Folder with Images", start_dir
        )
        if folder:
            self.batch_folder = folder
            self.config.last_batch_dir = folder
            self.lbl_folder.setText(f"Folder: {Path(folder).name}")

    def _toggle_batch(self) -> None:
        """Start or cancel batch processing."""
        if self.worker is not None and self.worker.isRunning():
            self.worker.cancel()
            self.btn_batch.setText("Cancelling...")
            self.btn_batch.setEnabled(False)
            return

        if not self.batch_folder:
            QMessageBox.warning(self, "Notice", "Select a batch folder first.")
            return

        if self.ref_mask is None:
            QMessageBox.warning(
                self, "Notice", "Select the watermark area first using the tools."
            )
            return

        files = [
            f
            for f in os.listdir(self.batch_folder)
            if f.lower().endswith(SUPPORTED_IMAGE_EXTENSIONS)
        ]

        if not files:
            QMessageBox.warning(
                self, "Notice", "No supported images found in the selected folder."
            )
            return

        # Confirmation dialog
        reply = QMessageBox.question(
            self,
            "Confirm Batch Processing",
            f"Process {len(files)} images in:\n{self.batch_folder}\n\n" f"Continue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if reply != QMessageBox.Yes:
            return

        out_sub = self.le_outdir.text().strip() or DEFAULT_OUTPUT_SUBDIR
        out_dir = os.path.join(self.batch_folder, out_sub)
        os.makedirs(out_dir, exist_ok=True)

        self.config.output_subdir = out_sub

        batch_settings = BatchSettings(
            inpaint=self.get_inpaint_settings(),
            ref_shape=self.ref_image.shape,
            ref_mask=self.ref_mask,
            ref_rect=self.template_rect,
            template=self.watermark_template,
            use_template_matching=self.chk_tm.isChecked(),
        )

        self.worker = BatchWorker(self.batch_folder, files, out_dir, batch_settings)
        self.worker.progress_update.connect(self._on_batch_progress)
        self.worker.finished.connect(self._on_batch_finished)

        self.btn_batch.setText("Cancel Batch Process")
        self.btn_batch.setProperty("class", "danger")
        self.btn_batch.style().unpolish(self.btn_batch)
        self.btn_batch.style().polish(self.btn_batch)
        self.progress_bar.setValue(0)
        self.worker.start()
        logger.info("Batch processing started: %d images", len(files))

    @pyqtSlot(int, str)
    def _on_batch_progress(self, val: int, msg: str) -> None:
        """Handle batch progress updates.

        Args:
            val: Completion percentage (0-100).
            msg: Human-readable progress message.
        """
        self.progress_bar.setValue(val)
        self._set_status(msg)

    @pyqtSlot(bool, str)
    def _on_batch_finished(self, success: bool, msg: str) -> None:
        """Handle batch processing completion.

        Args:
            success: True if all images processed without errors.
            msg: Summary message.
        """
        self.btn_batch.setText("Start Batch Process")
        self.btn_batch.setProperty("class", "")
        self.btn_batch.style().unpolish(self.btn_batch)
        self.btn_batch.style().polish(self.btn_batch)
        self.btn_batch.setEnabled(True)

        if success:
            self.progress_bar.setValue(100)
            QMessageBox.information(self, "Complete", msg)
        else:
            QMessageBox.warning(self, "Batch Result", msg)

        self._set_status(msg)

    # ══════════════════════════════════════════════════════════
    #  Dialogs
    # ══════════════════════════════════════════════════════════

    def _show_shortcuts(self) -> None:
        """Display a dialog with keyboard shortcuts."""
        shortcuts = (
            "<h3>Keyboard Shortcuts</h3>"
            "<table cellpadding='4'>"
            "<tr><td><b>Ctrl+O</b></td><td>Open Image</td></tr>"
            "<tr><td><b>Ctrl+S</b></td><td>Save Result</td></tr>"
            "<tr><td><b>Ctrl+R</b></td><td>Remove Watermark</td></tr>"
            "<tr><td><b>Ctrl+Z</b></td><td>Undo Image</td></tr>"
            "<tr><td><b>Ctrl+Shift+Z</b></td><td>Undo Mask</td></tr>"
            "<tr><td><b>Ctrl+Y</b></td><td>Redo Mask</td></tr>"
            "<tr><td><b>Escape</b></td><td>Clear Selection</td></tr>"
            "<tr><td><b>1</b></td><td>Rectangle Tool</td></tr>"
            "<tr><td><b>2</b></td><td>Brush Tool</td></tr>"
            "<tr><td><b>3</b></td><td>Magic Wand Tool</td></tr>"
            "<tr><td><b>Scroll Wheel</b></td><td>Zoom In/Out</td></tr>"
            "<tr><td><b>Middle Click</b></td><td>Pan</td></tr>"
            "<tr><td><b>Shift+Click</b></td><td>Pan (alt)</td></tr>"
            "</table>"
        )
        QMessageBox.information(self, "Keyboard Shortcuts", shortcuts)

    def _show_about(self) -> None:
        """Display the About dialog."""
        QMessageBox.about(
            self,
            "About",
            f"<h3>{APP_NAME}</h3>"
            f"<p>Version {APP_VERSION}</p>"
            "<p>Professional-grade watermark removal tool with "
            "multiple inpainting algorithms, batch processing, "
            "and intelligent template matching.</p>"
            "<p>© 2024-2026 Elite Watermark Remover Contributors</p>",
        )

    # ══════════════════════════════════════════════════════════
    #  Drag & Drop
    # ══════════════════════════════════════════════════════════

    def dragEnterEvent(self, event: typing.Any) -> None:
        """Accept drag events for image files."""
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.toLocalFile().lower().endswith(SUPPORTED_IMAGE_EXTENSIONS):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event: typing.Any) -> None:
        """Handle dropped image files."""
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.lower().endswith(SUPPORTED_IMAGE_EXTENSIONS):
                img = cv2.imread(file_path)
                if img is not None:
                    self.ref_image = img.copy()
                    self.current_image = img.copy()
                    self.undo_stack.clear()
                    self.ref_mask = None
                    self.template_rect = None
                    self.watermark_template = None

                    self.viewer.set_image(self.current_image)
                    self.viewer.clear_selection()
                    h, w = img.shape[:2]
                    self.lbl_image_info.setText(
                        f"Loaded: {Path(file_path).name}\nSize: {w}×{h}"
                    )
                    self.lbl_img_size.setText(f"{w}×{h}")
                    self._set_status("Image loaded via drag & drop.")
                    logger.info("Image loaded via drop: %s", file_path)
                    return

    # ══════════════════════════════════════════════════════════
    #  Window Lifecycle
    # ══════════════════════════════════════════════════════════

    def closeEvent(self, event: typing.Any) -> None:
        """Save window state and confirm close if work is unsaved."""
        # Save preferences
        self.config.window_geometry = self.saveGeometry()
        self.config.algorithm = self.combo_method.currentText()
        self.config.radius = self.spin_radius.value()
        self.config.dilate_mask = self.spin_dilate.value()
        self.config.feather_width = self.spin_feather.value()
        self.config.save()

        # Cancel any running batch
        if self.worker is not None and self.worker.isRunning():
            reply = QMessageBox.question(
                self,
                "Confirm Exit",
                "Batch processing is still running. Quit anyway?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                event.ignore()
                return
            self.worker.cancel()
            self.worker.wait(3000)

        event.accept()
        logger.info("Application closed.")

    # ══════════════════════════════════════════════════════════
    #  Helpers
    # ══════════════════════════════════════════════════════════

    def _set_status(self, msg: str) -> None:
        """Update both the panel label and the status bar.

        Args:
            msg: Status message to display.
        """
        self.lbl_status.setText(msg)
        self.status_bar.showMessage(msg, 5000)

    # Backward-compatible public methods for tests
    def select_tool(self, tool: ToolMode) -> None:
        """Public alias for _select_tool (backward compatibility)."""
        self._select_tool(tool)

    def clear_selection(self) -> None:
        """Public alias for _clear_selection (backward compatibility)."""
        self._clear_selection()

    def inpaint_single(self) -> None:
        """Synchronous inpaint for backward compatibility with tests.

        Unlike _inpaint_single(), this runs synchronously on the
        calling thread so tests can assert results immediately.
        """
        if self.current_image is None:
            return
        mask = self.viewer.get_mask()
        if mask is None or cv2.countNonZero(mask) == 0:
            return

        self.undo_stack.append(self.current_image.copy())
        settings = self.get_inpaint_settings()
        self.current_image = Inpainter.inpaint_image(self.current_image, mask, settings)
        self.viewer.set_image(self.current_image)

    def on_mask_changed(self) -> None:
        """Public alias for _on_mask_changed (backward compatibility)."""
        self._on_mask_changed()

    def save_single(self) -> None:
        """Public alias for _save_single (backward compatibility)."""
        self._save_single()

    def undo_single(self) -> None:
        """Public alias for _undo_single (backward compatibility)."""
        self._undo_single()

    def toggle_batch(self) -> None:
        """Public alias for _toggle_batch (backward compatibility)."""
        self._toggle_batch()
