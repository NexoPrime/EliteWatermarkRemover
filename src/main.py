"""Application entry point for Elite Watermark Remover.

Sets up logging, creates the Qt application, applies the theme,
and launches the main window.
"""

from __future__ import annotations

import logging
import os
import sys


def get_resource_path(relative_path: str) -> str:
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    return os.path.join(base_path, relative_path)


from PyQt5.QtWidgets import QApplication

from src.constants import APP_NAME, APP_ORG, FONT_SIZE_PT
from src.ui.components.style import STYLE_SHEET
from src.ui.main_window import EliteWatermarkRemover
from src.utils.logging_config import setup_logging

logger = logging.getLogger(__name__)


def main() -> int:
    """Launch the application.

    Returns:
        Exit code (0 for success, non-zero for errors).
    """
    setup_logging(level=logging.INFO)
    logger.info("Starting %s...", APP_NAME)

    try:
        import multiprocessing

        import cv2
        from PyQt5.QtCore import Qt

        # Maximize CPU hardware thread allocation for Elite Performance
        cv2.setUseOptimized(True)
        cpu_count = multiprocessing.cpu_count()
        cv2.setNumThreads(cpu_count)
        logger.info(
            f"Initialized OpenCV hardware acceleration with {cpu_count} threads."
        )

        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

        app = QApplication(sys.argv)
        app.setApplicationName(APP_NAME)
        app.setOrganizationName(APP_ORG)
        app.setStyleSheet(STYLE_SHEET)

        # Set Professional Window Icon
        from PyQt5.QtGui import QIcon

        icon_path = get_resource_path(os.path.join("assets", "app_icon.png"))
        if os.path.exists(icon_path):
            app.setWindowIcon(QIcon(icon_path))

        window = EliteWatermarkRemover()
        window.show()

        logger.info("Application window displayed.")
        return app.exec_()

    except Exception:
        logger.exception("Fatal error during application startup.")
        return 1
