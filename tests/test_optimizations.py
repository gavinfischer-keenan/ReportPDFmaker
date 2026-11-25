"""
Tests for math optimizations, modularized helpers, and bug fixes across pdf_maker.
"""
import os
import pymupdf
import pytest
from PIL import Image

from pdf_maker.utils.color_utils import get_relative_luminance, _SRGB_LINEAR_LUT
from pdf_maker.converters.pdf_builder import (
    PageItem,
    build_pdf,
    get_source_image_dimensions,
    get_image_canvas_bounds,
)
from pdf_maker.converters.pdf_compressor import _get_image_dpi
from pdf_maker.converters.pdf_handler import split_pdf_to_pages
from pdf_maker.settings_manager import compute_settings_diff


class TestColorLutOptimization:
    def test_lut_length_and_endpoints(self):
        assert len(_SRGB_LINEAR_LUT) == 256
        assert _SRGB_LINEAR_LUT[0] == pytest.approx(0.0)
        assert _SRGB_LINEAR_LUT[255] == pytest.approx(1.0)

    def test_luminance_matches_exact_srgb_formula(self):
        for r, g, b in [(10, 20, 30), (128, 64, 255), (200, 150, 50)]:
            def exact(c):
                n = c / 255.0
                return n / 12.92 if n <= 0.04045 else ((n + 0.055) / 1.055) ** 2.4
            expected = 0.2126 * exact(r) + 0.7152 * exact(g) + 0.0722 * exact(b)
            assert get_relative_luminance(r, g, b) == pytest.approx(expected, rel=1e-9)

    def test_out_of_range_values_clamped(self):
        assert get_relative_luminance(-5, 300, 128) >= 0.0


class TestFastImageDimensionLookup:
    def test_normal_and_rotated_dimensions(self, dummy_png):
        # dummy_png is 100x80
        item = PageItem(id="d1", source_file=dummy_png, source_type="image", converted_pdf="")
        assert get_source_image_dimensions(item) == (100, 80)

        item.image_rotation = 90
        assert get_source_image_dimensions(item) == (80, 100)

        item.image_crop = (0.0, 0.0, 0.5, 0.5)
        assert get_source_image_dimensions(item, apply_crop=True) == (40, 50)

    def test_exif_orientation_swap_without_pixel_decode(self, tmp_path):
        p = tmp_path / "exif_rot.jpg"
        img = Image.new("RGB", (120, 60), (0, 128, 255))
        exif = img.getexif()
        exif[0x0112] = 6  # 90 CW EXIF orientation
        img.save(str(p), exif=exif)

        item = PageItem(id="d2", source_file=str(p), source_type="image", converted_pdf="")
        assert get_source_image_dimensions(item) == (60, 120)
        bounds = get_image_canvas_bounds(item, 800, 600, zoom=1.0)
        assert bounds is not None and bounds[2] > 0 and bounds[3] > 0


class TestPdfHelpersAndSkipCover:
    def test_split_pdf_to_pages(self, tmp_path):
        src = tmp_path / "multi.pdf"
        doc = pymupdf.open()
        for _ in range(3):
            doc.new_page(width=200, height=300)
        doc.save(str(src))
        doc.close()

        parts = split_pdf_to_pages(str(src), cleanup_source=True)
        assert len(parts) == 3
        assert not src.exists()
        for pt in parts:
            assert os.path.isfile(pt)
            os.unlink(pt)

    def test_build_pdf_skip_cover_page(self, tmp_path, dummy_png):
        p1 = PageItem(id="p1", source_file=dummy_png, source_type="image", converted_pdf="")
        p2 = PageItem(id="p2", source_file=dummy_png, source_type="image", converted_pdf="")
        out = tmp_path / "out.pdf"
        ok, err = build_pdf(
            [p1, p2],
            str(out),
            page_number_settings={
                "enabled": True,
                "skip_cover_page": True,
                "style": "page_x_of_y",
                "position": "bottom",
                "alignment": "center",
                "font": "Helvetica",
                "font_size": 10,
                "color": "#000000",
            },
            page_size="Letter",
        )
        assert ok, err
        doc = pymupdf.open(str(out))
        assert len(doc) == 2
        # Page size Letter: 612 x 792
        assert doc[0].rect.width == pytest.approx(612.0, abs=0.5)
        assert "Page 1" not in doc[0].get_text()
        assert "Page 2 of 2" in doc[1].get_text()
        doc.close()


class TestCompressorDpiAndSettingsDiff:
    def test_get_image_dpi_uses_both_axes(self):
        # Tall thin image where height DPI exceeds width DPI
        dpi = _get_image_dpi({"width": 500, "height": 3000}, 595.28, 841.89)
        assert dpi == pytest.approx((3000 / 841.89) * 72.0)

    def test_compute_settings_diff(self):
        old = {"page_size": "A4", "page_numbers": False, "theme": "dark"}
        new = {"page_size": "Letter", "page_numbers": True, "theme": "dark"}
        diffs = compute_settings_diff(old, new)
        assert len(diffs) == 2
        assert any("Page Size: A4 → Letter" in d for d in diffs)
        assert any("Page Numbers: False → True" in d for d in diffs)
