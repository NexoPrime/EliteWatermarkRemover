"""Tests for the batch processing worker."""

import os

import cv2
import numpy as np
import pytest

from src.core.models import BatchSettings, InpaintSettings
from src.core.worker import BatchWorker


class TestBatchWorker:
    """Tests for BatchWorker."""

    def _create_test_images(self, folder, count=3):
        """Create test images in a folder."""
        files = []
        for i in range(count):
            name = f"test_{i}.png"
            img = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
            cv2.imwrite(str(folder / name), img)
            files.append(name)
        return files

    def test_batch_processing(self, qtbot, tmp_dir):
        """Batch processing should produce output files."""
        src_dir = tmp_dir / "input"
        src_dir.mkdir()
        out_dir = tmp_dir / "output"
        out_dir.mkdir()

        files = self._create_test_images(src_dir, count=2)
        mask = np.zeros((100, 100), dtype=np.uint8)
        mask[20:80, 20:80] = 255

        settings = BatchSettings(
            inpaint=InpaintSettings(
                method="Telea",
                radius=3,
                use_feathering=False,
                add_grain=False,
                dilate_mask=0,
            ),
            ref_shape=(100, 100, 3),
            ref_mask=mask,
            use_template_matching=False,
        )

        worker = BatchWorker(str(src_dir), files, str(out_dir), settings)

        results = []
        worker.finished.connect(lambda s, m: results.append((s, m)))

        with qtbot.waitSignal(worker.finished, timeout=10000):
            worker.start()

        worker.wait()

        assert len(results) == 1
        assert results[0][0] is True  # success
        for f in files:
            assert (out_dir / f).exists()

    def test_cancellation(self, qtbot, tmp_dir):
        """Cancellation should stop processing."""
        src_dir = tmp_dir / "input"
        src_dir.mkdir()
        out_dir = tmp_dir / "output"
        out_dir.mkdir()

        files = self._create_test_images(src_dir, count=10)
        mask = np.zeros((100, 100), dtype=np.uint8)
        mask[20:80, 20:80] = 255

        settings = BatchSettings(
            inpaint=InpaintSettings(
                method="Telea",
                radius=3,
                use_feathering=False,
                add_grain=False,
                dilate_mask=0,
            ),
            ref_shape=(100, 100, 3),
            ref_mask=mask,
            use_template_matching=False,
        )

        worker = BatchWorker(str(src_dir), files, str(out_dir), settings)

        with qtbot.waitSignal(worker.finished, timeout=10000):
            worker.start()
            worker.cancel()

        worker.wait()

        assert worker.is_cancelled

    def test_suspicious_filename_skipped(self, qtbot, tmp_dir):
        """Files with path traversal should be skipped."""
        src_dir = tmp_dir / "input"
        src_dir.mkdir()
        out_dir = tmp_dir / "output"
        out_dir.mkdir()

        mask = np.zeros((100, 100), dtype=np.uint8)
        mask[20:80, 20:80] = 255

        settings = BatchSettings(
            inpaint=InpaintSettings(
                method="Telea",
                radius=3,
                use_feathering=False,
                add_grain=False,
                dilate_mask=0,
            ),
            ref_shape=(100, 100, 3),
            ref_mask=mask,
            use_template_matching=False,
        )

        # Include a suspicious filename
        suspicious_files = ["../etc/passwd", "normal.png"]
        # Create the normal file
        img = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        cv2.imwrite(str(src_dir / "normal.png"), img)

        worker = BatchWorker(str(src_dir), suspicious_files, str(out_dir), settings)
        results = []
        worker.finished.connect(lambda s, m: results.append((s, m)))

        with qtbot.waitSignal(worker.finished, timeout=10000):
            worker.start()

        worker.wait()

    def test_corrupt_image_reported(self, qtbot, tmp_dir):
        """Corrupt image should trigger error signal, not crash."""
        src_dir = tmp_dir / "input"
        src_dir.mkdir()
        out_dir = tmp_dir / "output"
        out_dir.mkdir()

        # Create a corrupt "image" file
        corrupt_path = src_dir / "corrupt.png"
        corrupt_path.write_text("this is not an image")

        mask = np.zeros((100, 100), dtype=np.uint8)
        mask[20:80, 20:80] = 255

        settings = BatchSettings(
            inpaint=InpaintSettings(
                method="Telea",
                radius=3,
                use_feathering=False,
                add_grain=False,
                dilate_mask=0,
            ),
            ref_shape=(100, 100, 3),
            ref_mask=mask,
            use_template_matching=False,
        )

        errors = []
        worker = BatchWorker(str(src_dir), ["corrupt.png"], str(out_dir), settings)
        worker.error_occurred.connect(lambda f, e: errors.append((f, e)))

        with qtbot.waitSignal(worker.finished, timeout=10000):
            worker.start()

        worker.wait()

        assert len(errors) == 1
        assert errors[0][0] == "corrupt.png"
