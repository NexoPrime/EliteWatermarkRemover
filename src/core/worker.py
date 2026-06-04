"""Background batch processing worker.

Provides a QThread-based worker that processes multiple images
in a folder, applying watermark removal with optional template
matching for dynamic watermark location.
"""

from __future__ import annotations

import logging
import multiprocessing
import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List

import cv2
import numpy as np
from PyQt5.QtCore import QThread, pyqtSignal

from src.constants import SUPPORTED_IMAGE_EXTENSIONS
from src.core.inpainter import Inpainter
from src.core.models import BatchProgress, BatchSettings, InpaintSettings

logger = logging.getLogger(__name__)


class BatchWorker(QThread):
    """Threaded batch processor for watermark removal.

    Processes all supported images in a folder, applying the
    configured inpainting settings to each. Supports cancellation
    and emits progress updates.

    Signals:
        progress_update: Emitted after each image with (percentage, message).
        finished: Emitted when processing completes with (success, message).
        error_occurred: Emitted when an individual image fails with (filename, error_msg).

    Example:
        >>> worker = BatchWorker(folder, files, out_dir, batch_settings)
        >>> worker.progress_update.connect(on_progress)
        >>> worker.finished.connect(on_done)
        >>> worker.start()
    """

    progress_update = pyqtSignal(int, str)
    finished = pyqtSignal(bool, str)
    error_occurred = pyqtSignal(str, str)

    def __init__(
        self,
        folder: str,
        files: List[str],
        out_dir: str,
        settings: BatchSettings,
    ) -> None:
        """Initialize the batch worker.

        Args:
            folder: Source folder containing images.
            files: List of filenames to process (relative to folder).
            out_dir: Output directory for processed images.
            settings: Batch processing configuration.
        """
        super().__init__()
        self.folder = folder
        self.files = sorted(files)  # Deterministic processing order
        self.out_dir = out_dir
        self.settings = settings
        self._cancel_event = threading.Event()

    def run(self) -> None:
        """Execute batch processing (runs in worker thread).

        Processes each image sequentially, applying template matching
        or mask scaling as configured. Emits progress after each image.
        """
        total = len(self.files)
        ref_h, ref_w = self.settings.ref_shape[:2]
        ref_mask = self.settings.ref_mask
        template = self.settings.template
        use_tm = self.settings.use_template_matching
        errors: list[str] = []

        logger.info(
            "Starting batch processing: %d images, method=%s, " "template_matching=%s",
            total,
            self.settings.inpaint.method,
            use_tm,
        )

        def _process_file(i: int, fname: str) -> None:
            if self._cancel_event.is_set():
                return

            safe_name = os.path.basename(fname)
            if safe_name != fname or ".." in fname:
                logger.warning("Skipping suspicious filename: %s", fname)
                return

            src_path = os.path.join(self.folder, safe_name)
            dst_path = os.path.join(self.out_dir, safe_name)

            try:
                self._process_single(
                    src_path, dst_path, ref_mask, ref_h, ref_w, template, use_tm
                )
            except Exception as e:
                error_msg = f"Error on {safe_name}: {e}"
                logger.error(error_msg, exc_info=True)
                errors.append(safe_name)
                self.error_occurred.emit(safe_name, str(e))

            progress = BatchProgress(
                current=i + 1,
                total=total,
                filename=safe_name,
                percentage=int(((i + 1) / total) * 100),
            )
            self.progress_update.emit(progress.percentage, progress.message)

        # Limit to half the CPU cores to prevent total OS lockup during heavy AI batching
        max_workers = max(1, multiprocessing.cpu_count() // 2)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(_process_file, i, fname)
                for i, fname in enumerate(self.files)
            ]
            for _ in as_completed(futures):
                if self._cancel_event.is_set():
                    executor.shutdown(wait=False, cancel_futures=True)
                    break

        if self._cancel_event.is_set():
            msg = "Batch cancelled by user."
            logger.info(msg)
            self.finished.emit(False, msg)
            return

        if errors:
            msg = (
                f"Batch completed with {len(errors)} error(s) "
                f"out of {total} images."
            )
            logger.warning(msg)
        else:
            msg = f"Batch processing completed successfully! ({total} images)"
            logger.info(msg)

        self.finished.emit(len(errors) == 0, msg)

    def _process_single(
        self,
        src_path: str,
        dst_path: str,
        ref_mask: np.ndarray,
        ref_h: int,
        ref_w: int,
        template: np.ndarray | None,
        use_tm: bool,
    ) -> None:
        """Process a single image file.

        Args:
            src_path: Full path to source image.
            dst_path: Full path for output image.
            ref_mask: Reference binary mask.
            ref_h: Reference image height.
            ref_w: Reference image width.
            template: Optional watermark template for matching.
            use_tm: Whether to use template matching.

        Raises:
            ValueError: If the image cannot be loaded.
            IOError: If the result cannot be saved.
        """
        img = cv2.imread(src_path)
        if img is None:
            raise ValueError(f"Failed to load image: {src_path}")

        h, w = img.shape[:2]
        mask: np.ndarray | None = None

        # Try template matching first
        if use_tm and template is not None:
            match = Inpainter.find_template(img, template)
            if match is not None:
                mask = np.zeros((h, w), dtype=np.uint8)
                x1, y1, x2, y2 = match
                x1, y1 = max(0, x1), max(0, y1)
                x2, y2 = min(w, x2), min(h, y2)
                mask[y1:y2, x1:x2] = 255

        # Fall back to proportional mask resize
        if mask is None:
            if w == ref_w and h == ref_h:
                mask = ref_mask.copy()
            else:
                mask = cv2.resize(
                    ref_mask,
                    (w, h),
                    interpolation=cv2.INTER_NEAREST,
                )

        cleaned = Inpainter.inpaint_image(img, mask, self.settings.inpaint)

        success = cv2.imwrite(dst_path, cleaned)
        if not success:
            raise IOError(f"Failed to save result: {dst_path}")

    def cancel(self) -> None:
        """Request cancellation of the batch processing.

        Thread-safe. The worker will stop after completing the
        current image.
        """
        logger.info("Batch cancellation requested.")
        self._cancel_event.set()

    @property
    def is_cancelled(self) -> bool:
        """Whether cancellation has been requested (thread-safe)."""
        return self._cancel_event.is_set()
