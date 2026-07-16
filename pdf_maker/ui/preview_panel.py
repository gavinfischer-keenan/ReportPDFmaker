"""
Preview Panel
=============
Center panel: renders the currently selected page as a live preview.
Uses PyMuPDF to render PDF pages and displays them on a Canvas.
Supports zoom in/out and page navigation.
"""

import io
import threading
import tkinter as tk
from typing import Optional, TYPE_CHECKING

import customtkinter as ctk
from PIL import Image, ImageTk

if TYPE_CHECKING:
    from ..controller import AppController

ZOOM_STEPS = [0.4, 0.5, 0.6, 0.75, 0.85, 1.0, 1.2, 1.5, 2.0]
ZOOM_DEFAULT_IDX = 4  # 0.85x


class PreviewPanel(ctk.CTkFrame):
    """Displays a live preview of the selected PDF page."""

    def __init__(self, parent, controller: "AppController"):
        super().__init__(parent, corner_radius=8, border_width=1)
        self.controller = controller
        self._zoom_idx = ZOOM_DEFAULT_IDX
        self._current_photo: Optional[ImageTk.PhotoImage] = None
        self._render_thread: Optional[threading.Thread] = None
        self._render_pending = False

        self._build_ui()
        self._register_events()

    # ------------------------------------------------------------------ #
    # Layout
    # ------------------------------------------------------------------ #

    def _build_ui(self) -> None:
        # Header
        header = ctk.CTkFrame(self, fg_color=("gray85", "gray20"), corner_radius=6)
        header.pack(fill="x", padx=6, pady=(6, 0))

        ctk.CTkLabel(
            header, text="🔍  Preview",
            font=ctk.CTkFont(size=13, weight="bold"), anchor="w"
        ).pack(side="left", padx=10, pady=6)

        self._page_info_label = ctk.CTkLabel(
            header, text="No page selected",
            font=ctk.CTkFont(size=11), text_color="gray"
        )
        self._page_info_label.pack(side="right", padx=10)

        # Canvas area with scrollbars
        canvas_container = ctk.CTkFrame(self, fg_color=("gray90", "gray15"), corner_radius=6)
        canvas_container.pack(fill="both", expand=True, padx=6, pady=4)

        self._canvas = tk.Canvas(
            canvas_container,
            bg="#1a1a2e",
            highlightthickness=0,
            cursor="crosshair"
        )
        vsb = ttk_scrollbar(canvas_container, orient="vertical",   command=self._canvas.yview)
        hsb = ttk_scrollbar(canvas_container, orient="horizontal", command=self._canvas.xview)
        self._canvas.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        vsb.pack(side="right",  fill="y")
        hsb.pack(side="bottom", fill="x")
        self._canvas.pack(fill="both", expand=True)

        # Bind resize to re-center image
        self._canvas.bind("<Configure>", lambda e: self._update_canvas_image())

        # Bottom nav bar
        nav = ctk.CTkFrame(self, fg_color="transparent")
        nav.pack(fill="x", padx=6, pady=(0, 6))

        # Page navigation
        self._prev_btn = ctk.CTkButton(
            nav, text="◀", width=36, height=30,
            font=ctk.CTkFont(size=14), command=self._prev_page,
            fg_color=("gray80", "gray30"), hover_color=("gray70", "gray40"),
            text_color=("black", "white")
        )
        self._prev_btn.pack(side="left", padx=(0, 2))

        self._nav_label = ctk.CTkLabel(
            nav, text="— / —", width=80,
            font=ctk.CTkFont(size=12), anchor="center"
        )
        self._nav_label.pack(side="left", padx=2)

        self._next_btn = ctk.CTkButton(
            nav, text="▶", width=36, height=30,
            font=ctk.CTkFont(size=14), command=self._next_page,
            fg_color=("gray80", "gray30"), hover_color=("gray70", "gray40"),
            text_color=("black", "white")
        )
        self._next_btn.pack(side="left", padx=(2, 12))

        # Zoom controls
        ctk.CTkButton(
            nav, text="−", width=32, height=30,
            font=ctk.CTkFont(size=14), command=self._zoom_out,
            fg_color=("gray80", "gray30"), hover_color=("gray70", "gray40"),
            text_color=("black", "white")
        ).pack(side="left", padx=2)

        self._zoom_label = ctk.CTkLabel(
            nav, text=f"{int(ZOOM_STEPS[self._zoom_idx]*100)}%",
            width=52, font=ctk.CTkFont(size=11)
        )
        self._zoom_label.pack(side="left", padx=2)

        ctk.CTkButton(
            nav, text="+", width=32, height=30,
            font=ctk.CTkFont(size=14), command=self._zoom_in,
            fg_color=("gray80", "gray30"), hover_color=("gray70", "gray40"),
            text_color=("black", "white")
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            nav, text="⊡ Fit", width=54, height=30,
            font=ctk.CTkFont(size=11), command=self._zoom_fit,
            fg_color=("gray80", "gray30"), hover_color=("gray70", "gray40"),
            text_color=("black", "white")
        ).pack(side="left", padx=6)

        # Placeholder text
        self._placeholder = self._canvas.create_text(
            300, 300,
            text="Add files to preview the document",
            fill="#4a5568",
            font=("Helvetica", 14),
            tags="placeholder"
        )

    # ------------------------------------------------------------------ #
    # Events
    # ------------------------------------------------------------------ #

    def _register_events(self) -> None:
        from ..controller import (EVT_PAGES_CHANGED, EVT_PAGE_SELECTED,
                           EVT_PAGE_ROTATED, EVT_RESET)
        self.controller.on(EVT_PAGES_CHANGED, lambda _: self._on_pages_changed())
        self.controller.on(EVT_PAGE_SELECTED, lambda idx: self._on_page_selected(idx))
        self.controller.on(EVT_PAGE_ROTATED,  lambda idx: self._on_page_selected(idx))
        self.controller.on(EVT_RESET,         lambda _: self._clear())

    def _on_pages_changed(self) -> None:
        self._update_nav()
        self._schedule_render()

    def _on_page_selected(self, index: int) -> None:
        self._update_nav()
        self._schedule_render()

    # ------------------------------------------------------------------ #
    # Rendering
    # ------------------------------------------------------------------ #

    def _schedule_render(self) -> None:
        """Schedule a render on the next idle cycle (avoids flood)."""
        if not self._render_pending:
            self._render_pending = True
            self.after(50, self._do_render)

    def _do_render(self) -> None:
        self._render_pending = False
        idx = self.controller.current_index
        if idx < 0 or not self.controller.pages:
            self._clear()
            return

        zoom = ZOOM_STEPS[self._zoom_idx]

        def _worker():
            png_bytes = self.controller.render_page(idx, zoom)
            self.after(0, lambda: self._display_image(png_bytes))

        threading.Thread(target=_worker, daemon=True).start()

    def _display_image(self, png_bytes: Optional[bytes]) -> None:
        """Display rendered PNG bytes on the canvas (called on main thread)."""
        self._canvas.delete("preview_img")
        self._canvas.delete("placeholder")

        if not png_bytes:
            self._show_placeholder("⚠️  Could not render page")
            return

        img = Image.open(io.BytesIO(png_bytes))
        self._current_photo = ImageTk.PhotoImage(img)
        self._update_canvas_image()

    def _update_canvas_image(self) -> None:
        """Re-center the image on the canvas (called on resize or zoom)."""
        if not self._current_photo:
            return
        self._canvas.delete("preview_img")
        cw = self._canvas.winfo_width()
        ch = self._canvas.winfo_height()
        iw = self._current_photo.width()
        ih = self._current_photo.height()
        x = max(cw // 2, iw // 2 + 10)
        y = max(ch // 2, ih // 2 + 10)
        self._canvas.create_image(x, y, anchor="center", image=self._current_photo, tags="preview_img")
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _clear(self) -> None:
        self._canvas.delete("all")
        self._current_photo = None
        self._show_placeholder("Add files to preview the document")
        self._page_info_label.configure(text="No page selected")
        self._nav_label.configure(text="— / —")

    def _show_placeholder(self, text: str) -> None:
        cw = max(self._canvas.winfo_width(), 200)
        ch = max(self._canvas.winfo_height(), 200)
        self._canvas.create_text(
            cw // 2, ch // 2, text=text, fill="#4a5568",
            font=("Helvetica", 13), tags="placeholder"
        )

    # ------------------------------------------------------------------ #
    # Navigation
    # ------------------------------------------------------------------ #

    def _update_nav(self) -> None:
        total = self.controller.page_count
        cur   = self.controller.current_index
        if total == 0:
            self._nav_label.configure(text="— / —")
            self._page_info_label.configure(text="No pages")
        else:
            self._nav_label.configure(text=f"{cur + 1} / {total}")
            page = self.controller.current_page
            if page:
                info = page.display_name
                if page.rotation:
                    info += f"  (↻{page.rotation}°)"
                self._page_info_label.configure(text=info)

    def _prev_page(self) -> None:
        idx = self.controller.current_index
        if idx > 0:
            self.controller.select_page(idx - 1)

    def _next_page(self) -> None:
        idx = self.controller.current_index
        if idx < self.controller.page_count - 1:
            self.controller.select_page(idx + 1)

    # ------------------------------------------------------------------ #
    # Zoom
    # ------------------------------------------------------------------ #

    def _zoom_in(self) -> None:
        if self._zoom_idx < len(ZOOM_STEPS) - 1:
            self._zoom_idx += 1
            self._apply_zoom()

    def _zoom_out(self) -> None:
        if self._zoom_idx > 0:
            self._zoom_idx -= 1
            self._apply_zoom()

    def _zoom_fit(self) -> None:
        self._zoom_idx = ZOOM_DEFAULT_IDX
        self._apply_zoom()

    def _apply_zoom(self) -> None:
        self._zoom_label.configure(text=f"{int(ZOOM_STEPS[self._zoom_idx]*100)}%")
        self._schedule_render()


# ---------------------------------------------------------------------------
# Helper: cross-platform ttk scrollbar styled for dark mode
# ---------------------------------------------------------------------------

import tkinter.ttk as ttk_mod

def ttk_scrollbar(parent, orient: str, command) -> ttk_mod.Scrollbar:
    sb = ttk_mod.Scrollbar(parent, orient=orient, command=command)
    return sb
