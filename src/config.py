"""Application configuration persistence using QSettings.

Provides a centralized interface for saving and restoring user
preferences (window geometry, last-used directories, algorithm
choices, etc.) across application sessions.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from PyQt5.QtCore import QByteArray, QSettings

from src.constants import (
    APP_NAME,
    APP_ORG,
    DEFAULT_DILATE,
    DEFAULT_FEATHER_WIDTH,
    DEFAULT_OUTPUT_SUBDIR,
    DEFAULT_RADIUS,
)

logger = logging.getLogger(__name__)


class AppConfig:
    """Persistent application configuration backed by QSettings.

    Wraps QSettings to provide typed access to user preferences
    with sensible defaults. Settings are automatically persisted
    to the platform-appropriate location.

    Example:
        >>> config = AppConfig()
        >>> config.last_open_dir
        ''
        >>> config.last_open_dir = '/home/user/photos'
        >>> config.save()
    """

    def __init__(self) -> None:
        """Initialize configuration with platform-native storage."""
        self._settings = QSettings(APP_ORG, APP_NAME)
        logger.debug("Configuration loaded from %s", self._settings.fileName())

    # --- Window state ---

    @property
    def window_geometry(self) -> QByteArray:
        """Saved window geometry (position and size)."""
        return self._settings.value("window/geometry", QByteArray())

    @window_geometry.setter
    def window_geometry(self, value: QByteArray) -> None:
        self._settings.setValue("window/geometry", value)

    @property
    def window_state(self) -> QByteArray:
        """Saved window state (toolbars, docks)."""
        return self._settings.value("window/state", QByteArray())

    @window_state.setter
    def window_state(self, value: QByteArray) -> None:
        self._settings.setValue("window/state", value)

    @property
    def splitter_sizes(self) -> Optional[list[int]]:
        """Saved splitter widget sizes."""
        val = self._settings.value("window/splitter_sizes")
        if val:
            return [int(v) for v in val]
        return None

    @splitter_sizes.setter
    def splitter_sizes(self, value: list[int]) -> None:
        self._settings.setValue("window/splitter_sizes", value)

    # --- Directories ---

    @property
    def last_open_dir(self) -> str:
        """Last directory used for opening files."""
        return str(self._settings.value("dirs/last_open", ""))

    @last_open_dir.setter
    def last_open_dir(self, value: str) -> None:
        self._settings.setValue("dirs/last_open", value)

    @property
    def last_save_dir(self) -> str:
        """Last directory used for saving files."""
        return str(self._settings.value("dirs/last_save", ""))

    @last_save_dir.setter
    def last_save_dir(self, value: str) -> None:
        self._settings.setValue("dirs/last_save", value)

    @property
    def last_batch_dir(self) -> str:
        """Last directory used for batch processing."""
        return str(self._settings.value("dirs/last_batch", ""))

    @last_batch_dir.setter
    def last_batch_dir(self, value: str) -> None:
        self._settings.setValue("dirs/last_batch", value)

    # --- Algorithm settings ---

    @property
    def algorithm(self) -> str:
        """Last selected inpainting algorithm."""
        return str(self._settings.value("inpaint/algorithm", "Telea"))

    @algorithm.setter
    def algorithm(self, value: str) -> None:
        self._settings.setValue("inpaint/algorithm", value)

    @property
    def radius(self) -> int:
        """Last used search radius."""
        return int(self._settings.value("inpaint/radius", DEFAULT_RADIUS))

    @radius.setter
    def radius(self, value: int) -> None:
        self._settings.setValue("inpaint/radius", value)

    @property
    def dilate_mask(self) -> int:
        """Last used mask dilation."""
        return int(self._settings.value("inpaint/dilate", DEFAULT_DILATE))

    @dilate_mask.setter
    def dilate_mask(self, value: int) -> None:
        self._settings.setValue("inpaint/dilate", value)

    @property
    def feather_width(self) -> int:
        """Last used feather width."""
        return int(self._settings.value("inpaint/feather_width", DEFAULT_FEATHER_WIDTH))

    @feather_width.setter
    def feather_width(self, value: int) -> None:
        self._settings.setValue("inpaint/feather_width", value)

    @property
    def output_subdir(self) -> str:
        """Output subdirectory name for batch processing."""
        return str(self._settings.value("batch/output_subdir", DEFAULT_OUTPUT_SUBDIR))

    @output_subdir.setter
    def output_subdir(self, value: str) -> None:
        self._settings.setValue("batch/output_subdir", value)

    def save(self) -> None:
        """Flush all pending changes to persistent storage."""
        self._settings.sync()
        logger.debug("Configuration saved.")
