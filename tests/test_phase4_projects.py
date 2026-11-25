"""
Phase 4 tests: .nautilus project save/load round-trip, blank/divider restoration,
missing file handling, corrupt/invalid version rejection, and password exclusion.
"""
import json

import pytest

from pdf_maker.controller import AppController
from pdf_maker.project_manager import load_project_file
from pdf_maker.settings_manager import SettingsManager


def _make_settings(tmp_path):
    mgr = SettingsManager.__new__(SettingsManager)
    mgr._settings_dir = tmp_path
    mgr._settings_file = tmp_path / "settings.json"
    mgr._settings = {}
    mgr.load()
    return mgr


class TestNautilusProjects:
    def test_project_save_load_roundtrip_and_password_exclusion(self, tmp_path, dummy_png):
        c1 = AppController(_make_settings(tmp_path / "s1"))
        c2 = AppController(_make_settings(tmp_path / "s2"))
        try:
            items, _ = c1._convert_file(dummy_png, "image")
            c1.pages.extend(items)
            c1.current_index = 0
            c1.rotate_page(0, 90)
            c1.set_page_landscape(0, True)
            c1.resize_image(0, 1.4, offset_x=12.5, offset_y=-8.0)
            c1.set_image_crop(0, (0.1, 0.2, 0.9, 0.8))
            c1.insert_blank_page(after_index=0, title="Divider Title")
            c1.settings.set_many({"page_size": "Legal", "watermark_text": "DRAFT"})
            c1.session_pdf_password = "never-persist-this"

            proj_file = tmp_path / "demo.nautilus"
            ok, err = c1.save_project(str(proj_file))
            assert ok, err
            raw = proj_file.read_text(encoding="utf-8")
            assert "never-persist-this" not in raw

            ok_load, warnings = c2.load_project(str(proj_file))
            assert ok_load
            assert warnings == []
            assert len(c2.pages) == 2
            assert c2.pages[0].image_rotation == 90
            assert c2.pages[0].page_landscape is True
            assert c2.pages[0].image_scale == pytest.approx(1.4)
            assert c2.pages[0].image_offset_x == pytest.approx(12.5)
            assert c2.pages[0].image_crop == (0.1, 0.2, 0.9, 0.8)
            assert c2.pages[1].is_blank is True
            assert c2.pages[1].display_name == "Divider Title"
            assert c2.settings.get("page_size") == "Legal"
            assert c2.settings.get("watermark_text") == "DRAFT"
            assert c2.session_pdf_password == ""
        finally:
            c1.cleanup()
            c2.cleanup()

    def test_project_missing_source_and_invalid_files(self, tmp_path):
        bad_json = tmp_path / "bad.nautilus"
        bad_json.write_text("{broken", encoding="utf-8")
        data, err = load_project_file(str(bad_json))
        assert data is None and err

        bad_ver = tmp_path / "ver.nautilus"
        bad_ver.write_text(json.dumps({"version": 99, "pages": []}), encoding="utf-8")
        data2, err2 = load_project_file(str(bad_ver))
        assert data2 is None and "version" in err2.lower()

        missing_src = tmp_path / "missing_src.nautilus"
        missing_src.write_text(
            json.dumps({"version": 1, "current_index": 0, "settings": {}, "pages": [{"source_file": str(tmp_path / "nope.png")}]}),
            encoding="utf-8",
        )
        c = AppController(_make_settings(tmp_path / "s3"))
        try:
            ok, warns = c.load_project(str(missing_src))
            assert ok
            assert len(c.pages) == 0
            assert len(warns) == 1
        finally:
            c.cleanup()
