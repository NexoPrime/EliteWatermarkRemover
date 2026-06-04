"""Tests for the core inpainting engine."""

import numpy as np
import pytest

from src.core.inpainter import Inpainter
from src.core.models import InpaintSettings


class TestInpaintImage:
    """Tests for Inpainter.inpaint_image()."""

    def test_telea_algorithm(self, dummy_image, simple_mask):
        """Telea algorithm should modify the masked region."""
        settings = InpaintSettings(method="Telea", radius=5)
        result = Inpainter.inpaint_image(dummy_image, simple_mask, settings)
        assert result.shape == dummy_image.shape
        assert result.dtype == np.uint8
        # Masked region should be different
        assert not np.array_equal(result[50:100, 50:100], dummy_image[50:100, 50:100])

    def test_navier_stokes_algorithm(self, dummy_image, simple_mask):
        """Navier-Stokes algorithm should produce valid output."""
        settings = InpaintSettings(method="Navier-Stokes", radius=5)
        result = Inpainter.inpaint_image(dummy_image, simple_mask, settings)
        assert result.shape == dummy_image.shape
        assert result.dtype == np.uint8

    def test_unknown_method_falls_back_to_telea(self, dummy_image, simple_mask):
        """Unknown method should fall back to Telea without crashing."""
        settings = InpaintSettings(method="NonExistentMethod", radius=5)
        result = Inpainter.inpaint_image(dummy_image, simple_mask, settings)
        assert result.shape == dummy_image.shape

    def test_dimension_mismatch_raises(self, dummy_image):
        """Mismatched image and mask dimensions should raise ValueError."""
        wrong_mask = np.zeros((100, 100), dtype=np.uint8)
        settings = InpaintSettings()
        with pytest.raises(ValueError, match="does not match"):
            Inpainter.inpaint_image(dummy_image, wrong_mask, settings)

    def test_zero_dilation(self, dummy_image, simple_mask):
        """Zero dilation should not crash."""
        settings = InpaintSettings(dilate_mask=0)
        result = Inpainter.inpaint_image(dummy_image, simple_mask, settings)
        assert result.shape == dummy_image.shape

    def test_with_grain_restoration(self, dummy_image, simple_mask):
        """Grain restoration should not crash."""
        settings = InpaintSettings(add_grain=True)
        result = Inpainter.inpaint_image(dummy_image, simple_mask, settings)
        assert result.shape == dummy_image.shape

    def test_without_grain_restoration(self, dummy_image, simple_mask):
        """Disabling grain should still produce valid output."""
        settings = InpaintSettings(add_grain=False)
        result = Inpainter.inpaint_image(dummy_image, simple_mask, settings)
        assert result.shape == dummy_image.shape

    def test_with_feathering(self, dummy_image, simple_mask):
        """Feathering should produce a blended result."""
        settings = InpaintSettings(use_feathering=True, feather_width=10)
        result = Inpainter.inpaint_image(dummy_image, simple_mask, settings)
        assert result.shape == dummy_image.shape

    def test_without_feathering(self, dummy_image, simple_mask):
        """Disabling feathering should still produce valid output."""
        settings = InpaintSettings(use_feathering=False)
        result = Inpainter.inpaint_image(dummy_image, simple_mask, settings)
        assert result.shape == dummy_image.shape

    def test_empty_mask(self, dummy_image):
        """Empty mask should return an image unchanged (or near-unchanged)."""
        empty_mask = np.zeros((200, 200), dtype=np.uint8)
        settings = InpaintSettings(use_feathering=False, add_grain=False, dilate_mask=0)
        result = Inpainter.inpaint_image(dummy_image, empty_mask, settings)
        assert result.shape == dummy_image.shape

    def test_full_mask(self, dummy_image):
        """Full mask (entire image selected) should not crash."""
        full_mask = np.full((200, 200), 255, dtype=np.uint8)
        settings = InpaintSettings()
        result = Inpainter.inpaint_image(dummy_image, full_mask, settings)
        assert result.shape == dummy_image.shape

    def test_single_pixel_mask(self, dummy_image):
        """Single pixel mask should not crash."""
        mask = np.zeros((200, 200), dtype=np.uint8)
        mask[100, 100] = 255
        settings = InpaintSettings()
        result = Inpainter.inpaint_image(dummy_image, mask, settings)
        assert result.shape == dummy_image.shape

    def test_large_dilation(self, dummy_image, simple_mask):
        """Large dilation should not crash."""
        settings = InpaintSettings(dilate_mask=50)
        result = Inpainter.inpaint_image(dummy_image, simple_mask, settings)
        assert result.shape == dummy_image.shape


class TestFindTemplate:
    """Tests for Inpainter.find_template()."""

    def test_exact_template_match(self, dummy_image):
        """Exact sub-image should be found."""
        template = dummy_image[50:100, 50:100].copy()
        result = Inpainter.find_template(dummy_image, template)
        assert result is not None
        x1, y1, x2, y2 = result
        assert x2 - x1 == 50
        assert y2 - y1 == 50

    def test_template_larger_than_image(self, dummy_image):
        """Template larger than image should return None."""
        big_template = np.zeros((300, 300, 3), dtype=np.uint8)
        result = Inpainter.find_template(dummy_image, big_template)
        assert result is None

    def test_no_match(self):
        """Completely different template should return None."""
        np.random.seed(42)
        img = np.random.randint(0, 255, (200, 200, 3), dtype=np.uint8)
        template = np.random.randint(0, 255, (50, 50, 3), dtype=np.uint8)
        result = Inpainter.find_template(img, template, threshold=0.99)
        assert result is None

    def test_custom_threshold(self, dummy_image):
        """Custom threshold should be respected."""
        template = dummy_image[50:100, 50:100].copy()
        # Very high threshold might still match exact copy
        result = Inpainter.find_template(dummy_image, template, threshold=0.99)
        assert result is not None


class TestScaleRect:
    """Tests for Inpainter.scale_rect()."""

    def test_identity_scale(self):
        """Same dimensions should return the same rect."""
        rect = (10, 20, 30, 40)
        result = Inpainter.scale_rect(rect, 100, 100, 100, 100)
        assert result == (10, 20, 30, 40)

    def test_double_scale(self):
        """Doubling dimensions should double coordinates."""
        rect = (10, 20, 30, 40)
        result = Inpainter.scale_rect(rect, 100, 100, 200, 200)
        assert result == (20, 40, 60, 80)

    def test_half_scale(self):
        """Halving dimensions should halve coordinates."""
        rect = (10, 20, 30, 40)
        result = Inpainter.scale_rect(rect, 100, 100, 50, 50)
        assert result == (5, 10, 15, 20)

    def test_zero_reference_raises(self):
        """Zero reference dimensions should raise ValueError."""
        with pytest.raises(ValueError, match="non-zero"):
            Inpainter.scale_rect((0, 0, 10, 10), 0, 100, 200, 200)
