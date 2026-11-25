"""
Phase 2 parity tests: multi-step Undo/Redo, arbitrary move_page reordering,
and Windows Explorer drag-and-drop file filtering.
"""
import pytest

from pdf_maker.controller import AppController
from pdf_maker.converters.pdf_builder import PageItem
from pdf_maker.settings_manager import SettingsManager
from pdf_maker.utils.win_dnd import filter_dropped_files


def _make_settings(tmp_path):
    mgr = SettingsManager.__new__(SettingsManager)
    mgr._settings_dir = tmp_path
    mgr._settings_file = tmp_path / "settings.json"
    mgr._settings = {}
    mgr.load()
    return mgr


class TestDesktopMultiStepUndoRedo:
    def test_multi_step_undo_and_redo_across_actions(self, tmp_path, dummy_png):
        ctrl = AppController(_make_settings(tmp_path))
        try:
            p1 = PageItem(id="p1", source_file=dummy_png, source_type="image", converted_pdf="")
            p2 = PageItem(id="p2", source_file=dummy_png, source_type="image", converted_pdf="")
            ctrl.pages.extend([p1, p2])
            ctrl.current_index = 0

            assert not ctrl.can_undo
            assert not ctrl.can_redo

            ctrl.rotate_page(0, 90)
            ctrl.set_page_landscape(0, True)
            ctrl.move_page(0, 1)
            ctrl.set_image_crop(1, (0.1, 0.1, 0.9, 0.9))
            ctrl.remove_page(1)

            assert len(ctrl.pages) == 1
            assert ctrl.pages[0].id == "p2"
            assert ctrl.can_undo

            # Step back through all 5 actions
            assert ctrl.undo() is True  # restore removed p1
            assert len(ctrl.pages) == 2
            assert ctrl.pages[1].id == "p1"
            assert ctrl.pages[1].image_crop == (0.1, 0.1, 0.9, 0.9)

            assert ctrl.undo() is True  # undo crop
            assert ctrl.pages[1].image_crop is None

            assert ctrl.undo() is True  # undo move
            assert ctrl.pages[0].id == "p1"

            assert ctrl.undo() is True  # undo landscape
            assert ctrl.pages[0].page_landscape is False

            assert ctrl.undo() is True  # undo rotate
            assert ctrl.pages[0].image_rotation == 0
            assert not ctrl.can_undo
            assert ctrl.can_redo

            # Redo forward 2 steps
            assert ctrl.redo() is True
            assert ctrl.pages[0].image_rotation == 90
            assert ctrl.redo() is True
            assert ctrl.pages[0].page_landscape is True

            # New mutation clears redo stack
            ctrl.resize_image(0, 1.5)
            assert not ctrl.can_redo
        finally:
            ctrl.cleanup()

    def test_undo_stack_capped_at_max_undo(self, tmp_path, dummy_png):
        ctrl = AppController(_make_settings(tmp_path))
        try:
            ctrl._max_undo = 5
            ctrl.pages.append(PageItem(id="p1", source_file=dummy_png, source_type="image", converted_pdf=""))
            ctrl.current_index = 0
            for i in range(10):
                ctrl.resize_image(0, 1.0 + (i + 1) * 0.1)
            steps = 0
            while ctrl.undo():
                steps += 1
            assert steps == 5
        finally:
            ctrl.cleanup()


class TestMovePageAndWinDnd:
    def test_move_page_arbitrary_positions(self, tmp_path, dummy_png):
        ctrl = AppController(_make_settings(tmp_path))
        try:
            ctrl.pages = [
                PageItem(id="a", source_file=dummy_png, source_type="image", converted_pdf=""),
                PageItem(id="b", source_file=dummy_png, source_type="image", converted_pdf=""),
                PageItem(id="c", source_file=dummy_png, source_type="image", converted_pdf=""),
            ]
            ctrl.move_page(0, 2)
            assert [p.id for p in ctrl.pages] == ["b", "c", "a"]
            assert ctrl.current_index == 2

            # Out of range & no-op are safe
            ctrl.move_page(2, 2)
            ctrl.move_page(-1, 1)
            ctrl.move_page(0, 99)
            assert [p.id for p in ctrl.pages] == ["b", "c", "a"]
        finally:
            ctrl.cleanup()

    def test_filter_dropped_files_dedupes_and_ignores_dirs(self, tmp_path):
        f1 = tmp_path / "one.png"
        f2 = tmp_path / "two.pdf"
        sub = tmp_path / "folder"
        f1.write_bytes(b"a")
        f2.write_bytes(b"b")
        sub.mkdir()

        filtered = filter_dropped_files([
            str(f1),
            str(sub),
            str(tmp_path / "missing.txt"),
            str(f1),
            str(f2),
            "",
        ])
        assert filtered == [str(f1.resolve()), str(f2.resolve())]
