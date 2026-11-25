"""
Application Controller
======================
Central state management and event bus for PDF Maker.
All UI panels share a single instance of this class.
"""

import os
import tempfile
import threading
import uuid
import dataclasses
from pathlib import Path
from typing import Callable, Optional

from .settings_manager import SettingsManager
from .converters.pdf_builder import PageItem, build_pdf, render_page_preview
from .utils.file_utils import get_file_type


# ---------------------------------------------------------------------------
# Event names (used by all UI panels to subscribe/publish)
# ---------------------------------------------------------------------------
EVT_PAGES_CHANGED    = "pages_changed"
EVT_PAGE_SELECTED    = "page_selected"
EVT_PAGE_ROTATED     = "page_rotated"
EVT_PAGE_LANDSCAPE   = "page_landscape"
EVT_PROGRESS         = "progress"
EVT_STATUS           = "status"
EVT_RESET            = "reset"
EVT_WARNINGS         = "warnings"
EVT_MODE_CHANGED     = "mode_changed"
EVT_APPLY_CROP       = "apply_crop"
EVT_HISTORY_CHANGED  = "history_changed"


class AppController:
    """
    Central application controller.

    Holds all document state and dispatches events to UI listeners.
    UI panels register listeners via `on(event, callback)`.
    """

    def __init__(self, settings: SettingsManager):
        self.settings:       SettingsManager    = settings
        self.pages:          list[PageItem]     = []
        self.current_index:  int                = -1
        self.editor_mode:    str                = "resize"  # "resize" | "crop"
        self._listeners:     dict[str, list[Callable]] = {}
        self._temp_dir:      str                = tempfile.mkdtemp(prefix="pdfmaker_")
        self._lock                              = threading.Lock()

        # Multi-step document undo / redo stacks
        self._undo_stack: list[tuple[list[PageItem], int]] = []
        self._redo_stack: list[tuple[list[PageItem], int]] = []
        self._max_undo:   int = 50
        self.session_pdf_password: str = ""

    # ------------------------------------------------------------------ #
    # Event bus
    # ------------------------------------------------------------------ #

    def on(self, event: str, callback: Callable) -> None:
        """Register a listener for an event."""
        self._listeners.setdefault(event, []).append(callback)

    def emit(self, event: str, data=None) -> None:
        """Fire all listeners for an event."""
        for cb in self._listeners.get(event, []):
            try:
                cb(data)
            except Exception as e:
                print(f"[AppController] Listener error on '{event}': {e}")

    # ------------------------------------------------------------------ #
    # File adding
    # ------------------------------------------------------------------ #

    def add_files(
        self,
        file_paths: list[str],
        done_callback: Optional[Callable] = None,
        import_progress_callback: Optional[Callable] = None,
    ) -> None:
        """
        Convert and add files in a background thread.

        import_progress_callback(current, total, filename) fires for each file
        so the UI can show a progress bar.
        """
        def _worker():
            all_warnings: list[str] = []
            new_pages:    list[PageItem] = []
            total = len(file_paths)

            for i, fpath in enumerate(file_paths):
                fname = Path(fpath).name
                # Notify progress BEFORE processing so bar starts at 0
                if import_progress_callback:
                    import_progress_callback(i, total, fname)
                self.emit(EVT_STATUS, f"Converting {fname}…")

                ftype = get_file_type(fpath)
                try:
                    pages, warnings = self._convert_file(fpath, ftype)
                    all_warnings.extend(warnings)
                    new_pages.extend(pages)
                except Exception as e:
                    import traceback
                    detail = traceback.format_exc()
                    print(f"[Controller] Error converting {fname}:\n{detail}")
                    all_warnings.append(f"❌ Failed: '{fname}': {e}")

            # Update state once (lock protects the list)
            with self._lock:
                self.pages.extend(new_pages)
                if self.current_index < 0 and self.pages:
                    self.current_index = 0

            # Signal completion progress (fires done callback in UI)
            if import_progress_callback:
                import_progress_callback(total, total, "")

            # Emit UI events — the UI panels must schedule these on the main thread
            self.emit(EVT_PAGES_CHANGED, None)
            if all_warnings:
                self.emit(EVT_WARNINGS, all_warnings)
            self.emit(EVT_STATUS, f"Ready — {len(self.pages)} page(s)")

            if done_callback:
                done_callback(new_pages, all_warnings)

        threading.Thread(target=_worker, daemon=True).start()


    def _convert_file(self, fpath: str, ftype: str) -> tuple[list[PageItem], list[str]]:
        """Dispatch to the appropriate converter and wrap results in PageItems."""
        page_size = self.settings.get("page_size", "A4")

        if ftype == "image":
            from .converters.image_converter import convert_image_to_pages
            temp_pdfs = convert_image_to_pages(fpath, page_size, temp_dir=self._temp_dir)
            return self._wrap(fpath, ftype, temp_pdfs, [])

        elif ftype == "text":
            from .converters.text_converter import convert_text_to_pages
            temp_pdfs, warnings = convert_text_to_pages(fpath, page_size, temp_dir=self._temp_dir)
            return self._wrap(fpath, ftype, temp_pdfs, warnings)

        elif ftype == "word":
            from .converters.docx_converter import convert_docx_to_pages
            temp_pdfs, warnings = convert_docx_to_pages(fpath, page_size, temp_dir=self._temp_dir)
            return self._wrap(fpath, ftype, temp_pdfs, warnings)

        elif ftype == "pdf":
            from .converters.pdf_handler import convert_pdf_to_pages
            temp_pdfs, warnings = convert_pdf_to_pages(fpath, page_size, temp_dir=self._temp_dir)
            return self._wrap(fpath, ftype, temp_pdfs, warnings)

        elif ftype == "3d":
            from .converters.gltf_converter import convert_3d_to_pages
            temp_pdfs, warnings = convert_3d_to_pages(fpath, page_size, temp_dir=self._temp_dir)
            return self._wrap(fpath, ftype, temp_pdfs, warnings)

        else:
            from .converters.image_converter import convert_image_to_pages
            try:
                temp_pdfs = convert_image_to_pages(fpath, page_size, temp_dir=self._temp_dir)
                warnings  = [f"ℹ️ '{Path(fpath).name}' treated as image (unknown type)."]
                return self._wrap(fpath, "unknown", temp_pdfs, warnings)
            except Exception as e:
                from .converters.pdf_handler import _make_error_page
                err   = _make_error_page(
                    f"Unsupported file:\n{Path(fpath).name}\n\n{e}",
                    temp_dir=self._temp_dir,
                )
                warns = [f"❌ Could not import '{Path(fpath).name}': {e}"]
                return self._wrap(fpath, "unknown", [err], warns)

    @staticmethod
    def _wrap(
        source_file: str,
        source_type: str,
        temp_pdfs:   list[str],
        warnings:    list[str],
    ) -> tuple[list[PageItem], list[str]]:
        fname = Path(source_file).name
        items = []
        for i, pdf_path in enumerate(temp_pdfs):
            label = fname if len(temp_pdfs) == 1 else f"{fname} (p.{i + 1})"
            items.append(PageItem(
                id=str(uuid.uuid4()),
                source_file=source_file,
                source_type=source_type,
                converted_pdf=pdf_path,
                rotation=0,
                image_frame_index=i if (source_type == "image" and len(temp_pdfs) > 1) else 0,
                source_page_index=i,
                display_name=label,
                warnings=warnings if i == 0 else [],
            ))
        return items, warnings

    # ------------------------------------------------------------------ #
    # Page manipulation
    # ------------------------------------------------------------------ #

    def select_page(self, index: int) -> None:
        if 0 <= index < len(self.pages):
            self.current_index = index
            self.emit(EVT_PAGE_SELECTED, index)

    def remove_page(self, index: int) -> None:
        if 0 <= index < len(self.pages):
            self._push_undo_snapshot()
            removed = self.pages.pop(index)
            if self.current_index >= len(self.pages):
                self.current_index = len(self.pages) - 1
            self._cleanup_page_temp(removed)
            self.emit(EVT_PAGES_CHANGED, None)

    def move_page(self, from_index: int, to_index: int) -> None:
        """Move a page from `from_index` to `to_index` and keep selection on it."""
        if not (0 <= from_index < len(self.pages)) or not (0 <= to_index < len(self.pages)):
            return
        if from_index == to_index:
            return
        self._push_undo_snapshot()
        moved = self.pages.pop(from_index)
        self.pages.insert(to_index, moved)
        self.current_index = to_index
        self.emit(EVT_PAGES_CHANGED, None)
        self.emit(EVT_PAGE_SELECTED, self.current_index)

    def move_page_up(self, index: int) -> None:
        if index > 0:
            self.move_page(index, index - 1)

    def move_page_down(self, index: int) -> None:
        if index < len(self.pages) - 1:
            self.move_page(index, index + 1)

    def rotate_page(self, index: int, degrees: int) -> None:
        """
        Rotate a page.
        - For IMAGE pages: rotates only the image content (page stays portrait/landscape).
        - For non-image pages: rotates the whole page (PDF-level set_rotation).
        """
        if 0 <= index < len(self.pages):
            self._push_undo_snapshot()
            page = self.pages[index]
            if page.is_image:
                page.image_rotation = degrees % 360
            else:
                page.rotation = degrees % 360
            self.emit(EVT_PAGE_ROTATED, index)

    def rotate_all_pages(self, degrees: int) -> None:
        """Rotate all pages (image_rotation for images, rotation for others)."""
        if not self.pages:
            return
        self._push_undo_snapshot()
        for page in self.pages:
            if page.is_image:
                page.image_rotation = degrees % 360
            else:
                page.rotation = degrees % 360
        self.emit(EVT_PAGES_CHANGED, None)

    def set_page_landscape(self, index: int, landscape: bool) -> None:
        """Toggle portrait / landscape for a single page (image pages only)."""
        if 0 <= index < len(self.pages):
            self._push_undo_snapshot()
            self.pages[index].page_landscape = landscape
            self.emit(EVT_PAGE_ROTATED, index)   # Reuses PAGE_ROTATED to trigger re-render

    def toggle_page_landscape(self, index: int) -> None:
        """Toggle the orientation of a single page."""
        if 0 <= index < len(self.pages):
            self._push_undo_snapshot()
            self.pages[index].page_landscape = not self.pages[index].page_landscape
            self.emit(EVT_PAGE_ROTATED, index)

    def set_all_landscape(self, landscape: bool) -> None:
        """Set all pages to portrait or landscape."""
        if not self.pages:
            return
        self._push_undo_snapshot()
        for page in self.pages:
            page.page_landscape = landscape
        self.emit(EVT_PAGES_CHANGED, None)

    def resize_image(
        self,
        index: int,
        scale: float,
        offset_x: float = 0.0,
        offset_y: float = 0.0,
        save_undo: bool = True,
    ) -> None:
        """
        Resize an image page by setting image_scale.
        scale=1.0 means fill page edge-to-edge.
        offset_x/y shift the image from centre (in points).
        """
        if 0 <= index < len(self.pages):
            page = self.pages[index]
            if page.is_image:
                if save_undo:
                    self._push_undo_snapshot()
                page.image_scale    = max(0.05, min(10.0, scale))
                page.image_offset_x = offset_x
                page.image_offset_y = offset_y
                self.emit(EVT_PAGE_ROTATED, index)  # trigger preview re-render

    def set_image_crop(self, index: int, crop: tuple[float, float, float, float] | None) -> None:
        """Set the crop box (left, top, right, bottom percentages) for an image page."""
        if 0 <= index < len(self.pages):
            page = self.pages[index]
            if page.is_image:
                self._push_undo_snapshot()
                page.image_crop = crop
                self.emit(EVT_PAGE_ROTATED, index)

    def _snapshot_pages(self) -> tuple[list[PageItem], int]:
        return ([dataclasses.replace(p) for p in self.pages], self.current_index)

    def _push_undo_snapshot(self) -> None:
        """Push a full document snapshot onto the undo stack and clear redo."""
        discarded_redo = list(self._redo_stack)
        self._redo_stack.clear()
        self._undo_stack.append(self._snapshot_pages())
        evicted: list[tuple[list[PageItem], int]] = []
        while len(self._undo_stack) > self._max_undo:
            evicted.append(self._undo_stack.pop(0))
        for snap_pages, _ in discarded_redo + evicted:
            for p in snap_pages:
                self._cleanup_page_temp(p)
        self.emit(EVT_HISTORY_CHANGED, None)

    def save_undo_state(self, index: int | None = None) -> None:
        """Public helper to snapshot the document before a multi-step drag action."""
        self._push_undo_snapshot()

    def undo(self) -> bool:
        """Restore the previous document snapshot, pushing current state to redo."""
        if not self._undo_stack:
            return False
        self._redo_stack.append(self._snapshot_pages())
        prev_pages, prev_idx = self._undo_stack.pop()
        self.pages = [dataclasses.replace(p) for p in prev_pages]
        if not self.pages:
            self.current_index = -1
        else:
            self.current_index = max(0, min(prev_idx, len(self.pages) - 1))
        self.emit(EVT_HISTORY_CHANGED, None)
        self.emit(EVT_PAGES_CHANGED, None)
        if self.current_index >= 0:
            self.emit(EVT_PAGE_SELECTED, self.current_index)
        return True

    def redo(self) -> bool:
        """Re-apply the most recently undone document snapshot."""
        if not self._redo_stack:
            return False
        self._undo_stack.append(self._snapshot_pages())
        next_pages, next_idx = self._redo_stack.pop()
        self.pages = [dataclasses.replace(p) for p in next_pages]
        if not self.pages:
            self.current_index = -1
        else:
            self.current_index = max(0, min(next_idx, len(self.pages) - 1))
        self.emit(EVT_HISTORY_CHANGED, None)
        self.emit(EVT_PAGES_CHANGED, None)
        if self.current_index >= 0:
            self.emit(EVT_PAGE_SELECTED, self.current_index)
        return True

    def undo_last_action(self) -> None:
        """Restore the last saved document state (backwards-compatible alias)."""
        self.undo()

    def set_editor_mode(self, mode: str) -> None:
        """Set mode ('resize' or 'crop') and notify."""
        if mode in ("resize", "crop") and self.editor_mode != mode:
            self.editor_mode = mode
            self.emit(EVT_MODE_CHANGED, mode)

    def duplicate_page(self, index: int) -> None:
        """Duplicate the page at `index` immediately after it."""
        if not (0 <= index < len(self.pages)):
            return
        self._push_undo_snapshot()
        orig = self.pages[index]
        copy_item = dataclasses.replace(
            orig,
            id=str(uuid.uuid4()),
            display_name=f"{orig.display_name} (copy)",
            warnings=list(orig.warnings),
        )
        self.pages.insert(index + 1, copy_item)
        self.current_index = index + 1
        self.emit(EVT_PAGES_CHANGED, None)
        self.emit(EVT_PAGE_SELECTED, self.current_index)

    def insert_blank_page(self, after_index: Optional[int] = None, title: str = "") -> None:
        """Insert a blank (or section-divider) page into the document."""
        import pymupdf
        from .converters.pdf_builder import _page_dims

        page_size = self.settings.get("page_size", "A4")
        pw, ph = _page_dims(False, page_size)
        doc = pymupdf.open()
        pg = doc.new_page(width=pw, height=ph)
        clean_title = (title or "").strip()
        if clean_title:
            tw = pymupdf.get_text_length(clean_title, fontname="hebo", fontsize=24)
            pg.insert_text(
                (max(36.0, (pw - tw) / 2.0), ph / 2.0),
                clean_title,
                fontname="hebo",
                fontsize=24,
                color=(0.15, 0.2, 0.28),
            )
        tmp = tempfile.NamedTemporaryFile(suffix=".pdf", dir=self._temp_dir, delete=False)
        tmp_path = tmp.name
        tmp.close()
        doc.save(tmp_path)
        doc.close()

        self._push_undo_snapshot()
        label = clean_title or "Blank Page"
        item = PageItem(
            id=str(uuid.uuid4()),
            source_file=tmp_path,
            source_type="pdf",
            converted_pdf=tmp_path,
            display_name=label,
            is_blank=True,
        )
        insert_at = len(self.pages) if after_index is None or after_index < 0 else min(len(self.pages), after_index + 1)
        self.pages.insert(insert_at, item)
        self.current_index = insert_at
        self.emit(EVT_PAGES_CHANGED, None)
        self.emit(EVT_PAGE_SELECTED, self.current_index)

    def reverse_pages(self) -> None:
        """Reverse the order of all pages."""
        if len(self.pages) < 2:
            return
        self._push_undo_snapshot()
        cur_id = self.current_page.id if self.current_page else None
        self.pages.reverse()
        if cur_id:
            for i, p in enumerate(self.pages):
                if p.id == cur_id:
                    self.current_index = i
                    break
        self.emit(EVT_PAGES_CHANGED, None)
        if self.current_index >= 0:
            self.emit(EVT_PAGE_SELECTED, self.current_index)

    def sort_pages_by_name(self, reverse: bool = False) -> None:
        """Sort pages naturally by display_name."""
        import re
        if len(self.pages) < 2:
            return
        self._push_undo_snapshot()
        cur_id = self.current_page.id if self.current_page else None

        def _nat_key(p: PageItem):
            return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", p.display_name or "")]

        self.pages.sort(key=_nat_key, reverse=reverse)
        if cur_id:
            for i, p in enumerate(self.pages):
                if p.id == cur_id:
                    self.current_index = i
                    break
        self.emit(EVT_PAGES_CHANGED, None)
        if self.current_index >= 0:
            self.emit(EVT_PAGE_SELECTED, self.current_index)

    # ------------------------------------------------------------------ #
    # Project save / load (.nautilus)
    # ------------------------------------------------------------------ #

    def save_project(self, project_path: str) -> tuple[bool, str]:
        """Save the current page queue, edits, and settings as a `.nautilus` project."""
        from .project_manager import save_project_file
        return save_project_file(project_path, self.pages, self.settings, self.current_index)

    def load_project(self, project_path: str) -> tuple[bool, list[str]]:
        """Load a `.nautilus` project file, rebuilding pages and restoring edits/settings."""
        import pymupdf
        from .converters.pdf_builder import _page_dims
        from .project_manager import load_project_file
        from .settings_manager import DEFAULT_SETTINGS

        data, err = load_project_file(project_path)
        if data is None:
            return False, [f"❌ {err}"]

        warnings: list[str] = []
        raw_settings = data.get("settings")
        if isinstance(raw_settings, dict):
            valid_updates = {k: v for k, v in raw_settings.items() if k in DEFAULT_SETTINGS}
            if valid_updates:
                self.settings.set_many(valid_updates)

        page_size = self.settings.get("page_size", "A4")
        converted_cache: dict[tuple[str, str], list[PageItem]] = {}
        rebuilt_pages: list[PageItem] = []

        for entry in data.get("pages", []):
            if not isinstance(entry, dict):
                continue
            if entry.get("is_blank"):
                title = "" if entry.get("display_name") == "Blank Page" else str(entry.get("display_name") or "")
                pw, ph = _page_dims(bool(entry.get("page_landscape", False)), page_size)
                doc = pymupdf.open()
                pg = doc.new_page(width=pw, height=ph)
                if title.strip():
                    tw = pymupdf.get_text_length(title.strip(), fontname="hebo", fontsize=24)
                    pg.insert_text(
                        (max(36.0, (pw - tw) / 2.0), ph / 2.0),
                        title.strip(),
                        fontname="hebo",
                        fontsize=24,
                        color=(0.15, 0.2, 0.28),
                    )
                tmp = tempfile.NamedTemporaryFile(suffix=".pdf", dir=self._temp_dir, delete=False)
                tmp_path = tmp.name
                tmp.close()
                doc.save(tmp_path)
                doc.close()
                rebuilt_pages.append(PageItem(
                    id=str(uuid.uuid4()),
                    source_file=tmp_path,
                    source_type="pdf",
                    converted_pdf=tmp_path,
                    rotation=int(entry.get("rotation", 0)),
                    page_landscape=bool(entry.get("page_landscape", False)),
                    display_name=title or "Blank Page",
                    is_blank=True,
                ))
                continue

            src_file = str(entry.get("source_file") or "")
            if not src_file or not os.path.isfile(src_file):
                warnings.append(f"⚠️ Missing source file skipped: {src_file or '(unknown)'}")
                continue

            ftype = get_file_type(src_file)
            cache_key = (src_file, ftype)
            if cache_key not in converted_cache:
                try:
                    items, conv_warns = self._convert_file(src_file, ftype)
                    warnings.extend(conv_warns)
                    converted_cache[cache_key] = items
                except Exception as e:
                    warnings.append(f"❌ Failed to load '{Path(src_file).name}': {e}")
                    continue

            pool = converted_cache[cache_key]
            idx_in_src = int(entry.get("source_page_index", entry.get("image_frame_index", 0)))
            template = pool[idx_in_src] if 0 <= idx_in_src < len(pool) else pool[0]
            crop_raw = entry.get("image_crop")
            crop_tuple = tuple(float(c) for c in crop_raw) if isinstance(crop_raw, list) and len(crop_raw) == 4 else None

            rebuilt_pages.append(dataclasses.replace(
                template,
                id=str(uuid.uuid4()),
                display_name=str(entry.get("display_name") or template.display_name),
                rotation=int(entry.get("rotation", 0)),
                page_landscape=bool(entry.get("page_landscape", False)),
                image_rotation=int(entry.get("image_rotation", 0)),
                image_scale=float(entry.get("image_scale", 1.0)),
                image_offset_x=float(entry.get("image_offset_x", 0.0)),
                image_offset_y=float(entry.get("image_offset_y", 0.0)),
                image_crop=crop_tuple,
            ))

        old_pages = list(self.pages)
        old_undo = list(self._undo_stack)
        old_redo = list(self._redo_stack)
        self.pages = rebuilt_pages
        self._undo_stack.clear()
        self._redo_stack.clear()
        self.session_pdf_password = ""
        for p in old_pages:
            self._cleanup_page_temp(p)
        for snap_pages, _ in old_undo + old_redo:
            for p in snap_pages:
                self._cleanup_page_temp(p)

        if not self.pages:
            self.current_index = -1
        else:
            saved_idx = int(data.get("current_index", 0))
            self.current_index = max(0, min(saved_idx, len(self.pages) - 1))

        self.emit(EVT_HISTORY_CHANGED, None)
        self.emit(EVT_PAGES_CHANGED, None)
        if self.current_index >= 0:
            self.emit(EVT_PAGE_SELECTED, self.current_index)
        if warnings:
            self.emit(EVT_WARNINGS, warnings)
        self.emit(EVT_STATUS, f"Loaded project — {len(self.pages)} page(s)")
        return True, warnings



    # ------------------------------------------------------------------ #
    # Save
    # ------------------------------------------------------------------ #

    def save_pdf(
        self,
        output_path:       str,
        progress_callback: Optional[Callable] = None,
        done_callback:     Optional[Callable] = None,
        jpeg_quality:      int = 95,
    ) -> None:
        pages_snapshot = list(self.pages)
        pn_settings    = self.settings.get_page_number_settings()
        overlay_cfg    = self.settings.get_overlay_settings()
        meta_cfg       = self.settings.get_metadata_settings()
        page_range     = self.settings.get("export_page_range", "")
        page_size      = self.settings.get("page_size", "A4")
        password       = self.session_pdf_password or None
        _quality       = jpeg_quality

        def _worker():
            success, error = build_pdf(
                pages=pages_snapshot,
                output_path=output_path,
                page_number_settings=pn_settings,
                progress_callback=progress_callback,
                page_size=page_size,
                jpeg_quality=_quality,
                page_range=page_range,
                document_overlays=overlay_cfg,
                metadata=meta_cfg,
                password=password,
            )
            if done_callback:
                done_callback(success, error, output_path)

        threading.Thread(target=_worker, daemon=True).start()

    # ------------------------------------------------------------------ #
    # Preview
    # ------------------------------------------------------------------ #

    def render_page(self, index: int, zoom: float = 1.0) -> Optional[bytes]:
        if 0 <= index < len(self.pages):
            return render_page_preview(
                self.pages[index],
                zoom,
                page_size=self.settings.get("page_size", "A4"),
            )
        return None

    # ------------------------------------------------------------------ #
    # Reset & cleanup
    # ------------------------------------------------------------------ #

    def reset(self) -> None:
        removed = list(self.pages)
        old_undo = list(self._undo_stack)
        old_redo = list(self._redo_stack)
        self.pages.clear()
        self.current_index = -1
        self._undo_stack.clear()
        self._redo_stack.clear()
        self.session_pdf_password = ""
        for page in removed:
            self._cleanup_page_temp(page)
        for snap_pages, _ in old_undo + old_redo:
            for page in snap_pages:
                self._cleanup_page_temp(page)
        self.settings.reset()
        self.emit(EVT_HISTORY_CHANGED, None)
        self.emit(EVT_RESET, None)

    def _all_referenced_temp_paths(self) -> set[str]:
        refs: set[str] = set()
        all_lists = [self.pages] + [sp for sp, _ in self._undo_stack] + [sp for sp, _ in self._redo_stack]
        for plist in all_lists:
            for p in plist:
                if p.converted_pdf:
                    refs.add(os.path.abspath(p.converted_pdf))
                    if p.source_type == "3d":
                        refs.add(os.path.abspath(str(Path(p.converted_pdf).with_suffix(".png"))))
        return refs

    def _cleanup_page_temp(self, page: PageItem) -> None:
        """Delete page's temp files if inside self._temp_dir and unreferenced."""
        candidates = []
        if page.converted_pdf:
            candidates.append(page.converted_pdf)
            if page.source_type == "3d":
                candidates.append(str(Path(page.converted_pdf).with_suffix(".png")))

        still_referenced = self._all_referenced_temp_paths()
        temp_root = os.path.abspath(self._temp_dir)
        for path in candidates:
            try:
                abs_path = os.path.abspath(path)
                if (
                    os.path.commonpath([temp_root, abs_path]) == temp_root
                    and abs_path not in still_referenced
                    and os.path.exists(abs_path)
                ):
                    os.unlink(abs_path)
            except Exception:
                pass

    def cleanup(self) -> None:
        import shutil
        try:
            shutil.rmtree(self._temp_dir, ignore_errors=True)
        except Exception:
            pass
        for page in self.pages:
            try:
                if os.path.exists(page.converted_pdf):
                    os.unlink(page.converted_pdf)
            except Exception:
                pass

    # ------------------------------------------------------------------ #
    # Properties
    # ------------------------------------------------------------------ #

    @property
    def can_undo(self) -> bool:
        return bool(self._undo_stack)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo_stack)

    @property
    def page_count(self) -> int:
        return len(self.pages)

    @property
    def current_page(self) -> Optional[PageItem]:
        if 0 <= self.current_index < len(self.pages):
            return self.pages[self.current_index]
        return None
