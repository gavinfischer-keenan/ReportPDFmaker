"""
Phase 1 regression tests covering bug fixes, reliability, compression,
converters, temp-file lifecycle, and CLI entry point.
"""
import io
import os
import sys
import types
from pathlib import Path

import numpy as np
import pymupdf
import pytest
from PIL import Image

from pdf_maker.controller import AppController
from pdf_maker.converters.docx_converter import convert_docx_to_pages
from pdf_maker.converters.gltf_converter import convert_3d_to_pages
from pdf_maker.converters.pdf_builder import (
    PageItem,
    _hex_to_fitz_color,
    _render_image_to_pil,
    build_pdf,
    render_page_preview,
)
from pdf_maker.converters.pdf_compressor import COMPRESSION_LEVELS, compress_pdf
from pdf_maker.settings_manager import SettingsManager


def _make_settings(tmp_path: Path) -> SettingsManager:
    mgr = SettingsManager.__new__(SettingsManager)
    mgr._settings_dir = tmp_path
    mgr._settings_file = tmp_path / "settings.json"
    mgr._settings = {}
    mgr.load()
    return mgr


class TestEntryPointAndColorSafety:
    def test_app_main_callable(self):
        import pdf_maker.app as app_mod

        assert callable(getattr(app_mod, "main", None))

    def test_malformed_hex_colors_do_not_crash(self, dummy_png):
        for bad in ("#fff", "#12345", "not-a-hex", "", "#xyz123"):
            r, g, b = _hex_to_fitz_color(bad)
            assert 0.0 <= r <= 1.0
            assert 0.0 <= g <= 1.0
            assert 0.0 <= b <= 1.0

            item = PageItem(id="h1", source_file=dummy_png, source_type="image", converted_pdf="")
            png = render_page_preview(
                item,
                zoom=0.5,
                page_number_settings={"enabled": True, "color": bad},
            )
            assert png is not None and png[:4] == b"\x89PNG"


class TestImageTransparencyAndAnimatedGif:
    def test_rgba_transparent_pixels_composite_onto_white(self, tmp_path):
        rgba_path = tmp_path / "transparent.png"
        img = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
        # Draw solid red square in center
        for x in range(40, 60):
            for y in range(40, 60):
                img.putpixel((x, y), (255, 0, 0, 255))
        img.save(str(rgba_path))

        item = PageItem(id="rgba1", source_file=str(rgba_path), source_type="image", converted_pdf="")
        rendered = _render_image_to_pil(item, 200, 200)
        # Transparent corner must be white, not black
        assert rendered.getpixel((5, 5)) == (255, 255, 255)
        # Center must be red
        assert rendered.getpixel((100, 100))[0] > 200

    def test_animated_gif_renders_distinct_frames(self, tmp_path):
        gif_path = tmp_path / "anim.gif"
        f0 = Image.new("RGB", (60, 60), (255, 0, 0))
        f1 = Image.new("RGB", (60, 60), (0, 0, 255))
        f0.save(str(gif_path), save_all=True, append_images=[f1], duration=100, loop=0)

        p0 = PageItem(
            id="g0", source_file=str(gif_path), source_type="image",
            converted_pdf="", image_frame_index=0,
        )
        p1 = PageItem(
            id="g1", source_file=str(gif_path), source_type="image",
            converted_pdf="", image_frame_index=1,
        )
        r0 = _render_image_to_pil(p0, 100, 100)
        r1 = _render_image_to_pil(p1, 100, 100)
        assert r0.getpixel((50, 50))[0] > 200  # Frame 0: red
        assert r1.getpixel((50, 50))[2] > 200  # Frame 1: blue


class TestPdfCompressorEndToEnd:
    def _build_sample_pdf(self, path: Path) -> None:
        doc = pymupdf.open()
        for idx in range(2):
            page = doc.new_page(width=595.28, height=841.89)
            # High-res uncompressed PNG with alpha channel to exercise resampling + SMask cleanup
            arr = np.zeros((1200, 1200, 4), dtype=np.uint8)
            arr[:, :, 0] = (np.arange(1200) % 255).reshape(1200, 1)
            arr[:, :, 1] = (idx * 80 + 40) % 255
            arr[:, :, 2] = 180
            arr[:, :, 3] = 220
            buf = io.BytesIO()
            Image.fromarray(arr, mode="RGBA").save(buf, format="PNG")
            page.insert_image(pymupdf.Rect(0, 0, 595.28, 841.89), stream=buf.getvalue())
            page.insert_text((40, 40), f"Sample page {idx + 1}", fontsize=14)
        doc.save(str(path))
        doc.close()

    @pytest.mark.parametrize("level", list(COMPRESSION_LEVELS.keys()))
    def test_all_compression_levels_produce_valid_pdf(self, tmp_path, level):
        src = tmp_path / "source.pdf"
        out = tmp_path / f"out_{level}.pdf"
        self._build_sample_pdf(src)

        result = compress_pdf(str(src), str(out), level)
        assert result.success, result.error
        assert out.exists()
        assert result.output_bytes > 0

        compressed = pymupdf.open(str(out))
        assert len(compressed) == 2
        compressed.close()

    def test_invalid_level_and_missing_file(self, tmp_path):
        r1 = compress_pdf(str(tmp_path / "missing.pdf"), str(tmp_path / "out.pdf"), "bogus")
        assert not r1.success
        r2 = compress_pdf(str(tmp_path / "missing.pdf"), str(tmp_path / "out.pdf"), "standard")
        assert not r2.success


class TestConvertersAnd3DFallback:
    def test_docx_fallback_uses_python_docx_without_word(self, tmp_path, monkeypatch):
        from docx import Document
        import pdf_maker.converters.docx_converter as dc

        docx_path = tmp_path / "sample.docx"
        doc = Document()
        doc.add_paragraph("Fallback paragraph content")
        doc.save(str(docx_path))

        temp_dir = tmp_path / "temp"
        temp_dir.mkdir()
        monkeypatch.setattr(dc, "detect_word", lambda: (False, "Word not installed"))

        pages, warnings = convert_docx_to_pages(str(docx_path), temp_dir=str(temp_dir))
        assert len(pages) == 1
        assert Path(pages[0]).parent == temp_dir
        assert any("Word not installed" in w for w in warnings)

        rendered = pymupdf.open(pages[0])
        assert "Fallback paragraph content" in rendered[0].get_text()
        rendered.close()

    def test_3d_missing_stack_returns_fallback_error_page(self, tmp_path, monkeypatch):
        import pdf_maker.converters.gltf_converter as gc

        temp_dir = tmp_path / "temp"
        temp_dir.mkdir()
        monkeypatch.setattr(gc, "is_3d_available", lambda: (False, "No 3D libs"))

        pages, warnings = convert_3d_to_pages(str(tmp_path / "model.glb"), temp_dir=str(temp_dir))
        assert len(pages) == 1
        assert Path(pages[0]).parent == temp_dir
        assert any("No 3D libs" in w for w in warnings)

        # build_pdf and render_page_preview should fall back to converted_pdf instead of blank page
        item = PageItem(id="3d_err", source_file=str(tmp_path / "model.glb"), source_type="3d", converted_pdf=pages[0])
        preview = render_page_preview(item, zoom=0.5)
        assert preview is not None and preview[:4] == b"\x89PNG"

        out_pdf = tmp_path / "3d_err.pdf"
        ok, err = build_pdf([item], str(out_pdf))
        assert ok, err
        doc = pymupdf.open(str(out_pdf))
        assert "3D rendering not available" in doc[0].get_text()
        doc.close()

    def test_3d_mocked_render_creates_sidecar_png_without_unpack_error(self, tmp_path, monkeypatch):
        import pdf_maker.converters.gltf_converter as gc

        fake_trimesh = types.ModuleType("trimesh")
        fake_trimesh.Scene = type("Scene", (), {})
        fake_trimesh.load = lambda path, force="scene": fake_trimesh.Scene()

        class FakeNode:
            pass

        class FakeScene:
            @classmethod
            def from_trimesh_scene(cls, _):
                return cls()

            def add(self, *args, **kwargs):
                return FakeNode()

        class FakeRenderer:
            def __init__(self, w, h):
                self.w, self.h = w, h

            def render(self, _scene):
                arr = np.full((self.h, self.w, 3), 120, dtype=np.uint8)
                return arr, None

            def delete(self):
                pass

        fake_pyrender = types.ModuleType("pyrender")
        fake_pyrender.Scene = FakeScene
        fake_pyrender.PerspectiveCamera = lambda **kw: object()
        fake_pyrender.DirectionalLight = lambda **kw: object()
        fake_pyrender.OffscreenRenderer = FakeRenderer

        monkeypatch.setitem(sys.modules, "trimesh", fake_trimesh)
        monkeypatch.setitem(sys.modules, "pyrender", fake_pyrender)
        monkeypatch.setattr(gc, "is_3d_available", lambda: (True, "ok"))

        temp_dir = tmp_path / "temp"
        temp_dir.mkdir()
        pages, warnings = convert_3d_to_pages(
            str(tmp_path / "cube.glb"), image_width=128, image_height=128, temp_dir=str(temp_dir)
        )
        assert len(pages) == 1
        sidecar = Path(pages[0]).with_suffix(".png")
        assert sidecar.exists()

        item = PageItem(id="3d_ok", source_file=str(tmp_path / "cube.glb"), source_type="3d", converted_pdf=pages[0])
        preview = render_page_preview(item, zoom=0.5)
        assert preview is not None and preview[:4] == b"\x89PNG"


class TestControllerTempLifecycleAndDragUndo:
    def test_drag_resize_undo_restores_initial_scale(self, tmp_path, dummy_png):
        ctrl = AppController(_make_settings(tmp_path))
        try:
            ctrl.pages.append(PageItem(id="u1", source_file=dummy_png, source_type="image", converted_pdf=""))
            ctrl.current_index = 0
            ctrl.save_undo_state(0)
            ctrl.resize_image(0, 1.3, save_undo=False)
            ctrl.resize_image(0, 1.8, save_undo=False)
            ctrl.resize_image(0, 2.2, save_undo=False)
            assert ctrl.pages[0].image_scale == pytest.approx(2.2)

            ctrl.undo_last_action()
            assert ctrl.pages[0].image_scale == pytest.approx(1.0)
        finally:
            ctrl.cleanup()

    def test_remove_and_reset_cleanup_temp_files(self, tmp_path, dummy_png):
        ctrl = AppController(_make_settings(tmp_path))
        try:
            p1, _ = ctrl._convert_file(dummy_png, "image")
            p2, _ = ctrl._convert_file(dummy_png, "image")
            ctrl.pages.extend(p1 + p2)
            t1 = Path(p1[0].converted_pdf)
            t2 = Path(p2[0].converted_pdf)
            assert t1.exists() and t2.exists()
            assert os.path.commonpath([ctrl._temp_dir, str(t1)]) == os.path.abspath(ctrl._temp_dir)

            ctrl.remove_page(0)
            # Deleted page temp file remains preserved while in undo stack
            assert t1.exists()
            assert t2.exists()

            # Undoing remove_page restores the page and its temp PDF
            assert ctrl.undo() is True
            assert len(ctrl.pages) == 2

            ctrl.reset()
            assert not t1.exists()
            assert not t2.exists()
        finally:
            ctrl.cleanup()
