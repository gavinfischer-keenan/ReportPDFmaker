"""
Phase 3 regression tests: page range parsing, custom page sizes (Legal/A3/A5/Fit),
duplicate/blank/reverse/sort actions, watermarks, headers/footers, PDF metadata,
and AES-256 session-only password encryption.
"""
import json
import pymupdf
import pytest
from PIL import Image

from pdf_maker.controller import AppController
from pdf_maker.converters.pdf_builder import (
    PageItem,
    _page_dims,
    build_pdf,
    parse_page_range,
    render_page_preview,
)
from pdf_maker.settings_manager import SettingsManager


def _make_settings(tmp_path):
    mgr = SettingsManager.__new__(SettingsManager)
    mgr._settings_dir = tmp_path
    mgr._settings_file = tmp_path / "settings.json"
    mgr._settings = {}
    mgr.load()
    return mgr


class TestPageRangesAndCustomSizes:
    def test_parse_page_range_variants(self):
        assert parse_page_range("", 4) == [0, 1, 2, 3]
        assert parse_page_range("all", 3) == [0, 1, 2]
        assert parse_page_range("1, 3-4", 5) == [0, 2, 3]
        assert parse_page_range("4-2, 2", 5) == [3, 2, 1]

        for bad in ("0", "6", "abc", "1-2-3", "1, "):
            with pytest.raises(ValueError):
                parse_page_range(bad, 5)

    def test_custom_page_sizes_and_fit(self):
        assert _page_dims(False, "Legal") == pytest.approx((612.0, 1008.0))
        assert _page_dims(True, "A3") == pytest.approx((1190.55, 841.89))
        assert _page_dims(False, "A5") == pytest.approx((419.53, 595.28))
        # Fit preserves 2:1 aspect ratio scaled to 841.89 longest side
        w, h = _page_dims(False, "Fit", image_dims=(2000, 1000))
        assert w == pytest.approx(841.89, abs=0.5)
        assert h == pytest.approx(420.95, abs=0.5)


class TestControllerPageOperations:
    def test_duplicate_blank_reverse_and_sort(self, tmp_path, dummy_png):
        ctrl = AppController(_make_settings(tmp_path))
        try:
            p10 = PageItem(id="10", source_file=dummy_png, source_type="image", converted_pdf="", display_name="page10.png")
            p2 = PageItem(id="2", source_file=dummy_png, source_type="image", converted_pdf="", display_name="page2.png")
            ctrl.pages.extend([p10, p2])
            ctrl.current_index = 0

            ctrl.sort_pages_by_name()
            assert [p.display_name for p in ctrl.pages] == ["page2.png", "page10.png"]

            ctrl.duplicate_page(0)
            assert len(ctrl.pages) == 3
            assert ctrl.pages[1].display_name == "page2.png (copy)"

            ctrl.insert_blank_page(after_index=1, title="Section 2")
            assert len(ctrl.pages) == 4
            assert ctrl.pages[2].display_name == "Section 2"

            ctrl.reverse_pages()
            assert ctrl.pages[0].display_name == "page10.png"

            # Undo restores back through operations
            assert ctrl.undo() is True
            assert ctrl.pages[-1].display_name == "page10.png"
        finally:
            ctrl.cleanup()


class TestOverlaysMetadataAndEncryption:
    def test_build_pdf_range_watermark_header_footer_metadata_and_password(self, tmp_path):
        wide_png = tmp_path / "wide.png"
        Image.new("RGB", (400, 200), (220, 240, 255)).save(str(wide_png))

        pages = [
            PageItem(id="1", source_file=str(wide_png), source_type="image", converted_pdf=""),
            PageItem(id="2", source_file=str(wide_png), source_type="image", converted_pdf=""),
            PageItem(id="3", source_file=str(wide_png), source_type="image", converted_pdf=""),
        ]
        overlays = {
            "watermark_text": "CONFIDENTIAL",
            "watermark_opacity": 0.25,
            "watermark_color": "#dc2626",
            "header_text": "Nautilus Header",
            "footer_text": "Nautilus Footer",
        }
        metadata = {
            "title": "Quarterly Audit",
            "author": "Paper Nautilus",
            "subject": "Phase 3 Verification",
        }
        out = tmp_path / "secured.pdf"
        ok, err = build_pdf(
            pages=pages,
            output_path=str(out),
            page_size="Fit",
            page_range="1, 3",
            document_overlays=overlays,
            metadata=metadata,
            password="nautilus-secret",
        )
        assert ok, err
        assert out.exists()

        doc = pymupdf.open(str(out))
        assert doc.needs_pass
        assert doc.authenticate("wrong") == 0
        assert doc.authenticate("nautilus-secret") > 0
        assert len(doc) == 2
        assert doc[0].rect.width > doc[0].rect.height
        assert doc.metadata.get("title") == "Quarterly Audit"
        assert doc.metadata.get("author") == "Paper Nautilus"
        assert doc.metadata.get("subject") == "Phase 3 Verification"

        txt = doc[0].get_text()
        assert "Nautilus Header" in txt
        assert "Nautilus Footer" in txt
        assert "CONFIDENTIAL" in txt
        doc.close()

        # Preview with overlays & Fit renders valid PNG
        preview_bytes = render_page_preview(pages[0], zoom=0.5, page_size="Fit", document_overlays=overlays)
        assert preview_bytes is not None and preview_bytes[:4] == b"\x89PNG"

    def test_password_is_never_persisted_to_settings_json(self, tmp_path):
        mgr = _make_settings(tmp_path)
        ctrl = AppController(mgr)
        try:
            ctrl.session_pdf_password = "top-secret-password"
            mgr.save()
            raw = mgr._settings_file.read_text(encoding="utf-8")
            assert "top-secret-password" not in raw
            parsed = json.loads(raw)
            assert "password" not in parsed
            ctrl.reset()
            assert ctrl.session_pdf_password == ""
        finally:
            ctrl.cleanup()
