"""
Preview Panel
=============
Centre panel: live preview of the selected page.

Features
--------
* Renders image pages from source PIL for instant updates.
* Zoom controls (-, +, Fit).
* Page navigation arrows.
* Corner resize handles for image pages:
    - Drag any of the 4 green corner squares to resize the image.
    - Scale is locked to original aspect ratio.
    - Image clips hard to page edge with no buffer.
* 'Fit' button resets scale to 1.0 (fill page edge-to-edge).
"""

import io
import threading
import tkinter as tk
import tkinter.ttk as ttk
from typing import Optional, TYPE_CHECKING

import customtkinter as ctk
from PIL import Image, ImageTk

if TYPE_CHECKING:
    from ..controller import AppController

ZOOM_STEPS  = [0.3, 0.4, 0.5, 0.6, 0.75, 0.85, 1.0, 1.25, 1.5, 2.0]
ZOOM_DEFAULT = 4   # index → 0.75

HANDLE_SIZE = 6    # half-side of each corner handle square (px)
HANDLE_HIT  = 14   # hit-test radius around handle centre (px)


class PreviewPanel(ctk.CTkFrame):
    """Live preview with zoom and image-page corner-drag resizing."""

    def __init__(self, parent, controller: "AppController"):
        super().__init__(parent, corner_radius=8, border_width=1)
        self.controller = controller
        self._zoom_idx  = ZOOM_DEFAULT
        self._photo:     Optional[ImageTk.PhotoImage] = None
        self._render_pending = False

        # Corner handle drag state
        self._drag_corner:      Optional[str]  = None   # 'nw'|'ne'|'sw'|'se'
        self._drag_start_x:     int = 0
        self._drag_start_y:     int = 0
        self._drag_start_scale: float = 1.0
        self._drag_start_ox:    float = 0.0  # offset_x at drag start
        self._drag_start_oy:    float = 0.0  # offset_y at drag start
        self._handle_positions: dict[str, tuple[int, int]] = {}  # corner_id → (cx,cy)

        # Where the image is on the canvas (set after each render)
        self._img_cx:    int = 0   # canvas px — image centre x
        self._img_cy:    int = 0   # canvas px — image centre y
        self._img_disp_w: int = 0  # canvas px — displayed image width
        self._img_disp_h: int = 0  # canvas px — displayed image height
        self._page_x:    int = 0   # canvas px — page left edge
        self._page_y:    int = 0   # canvas px — page top edge
        self._page_pw:   int = 0   # canvas px — page width
        self._page_ph:   int = 0   # canvas px — page height

        self._build_ui()
        self._register_events()

    # ------------------------------------------------------------------ #
    # UI
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

        # Canvas
        canvas_container = tk.Frame(self, bg="#141414")
        canvas_container.pack(fill="both", expand=True, padx=6, pady=4)

        self._canvas = tk.Canvas(
            canvas_container,
            bg="#1a1a2e",
            highlightthickness=0,
        )
        vsb = ttk.Scrollbar(canvas_container, orient="vertical",   command=self._canvas.yview)
        hsb = ttk.Scrollbar(canvas_container, orient="horizontal", command=self._canvas.xview)
        self._canvas.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        vsb.pack(side="right",  fill="y")
        hsb.pack(side="bottom", fill="x")
        self._canvas.pack(fill="both", expand=True)

        self._canvas.bind("<Configure>", lambda e: self._on_canvas_resize())

        # Mouse events for drag handles
        self._canvas.bind("<ButtonPress-1>",   self._on_mouse_press)
        self._canvas.bind("<B1-Motion>",        self._on_mouse_drag)
        self._canvas.bind("<ButtonRelease-1>",  self._on_mouse_release)

        # Bottom nav
        nav = ctk.CTkFrame(self, fg_color="transparent")
        nav.pack(fill="x", padx=6, pady=(0, 6))

        self._prev_btn = ctk.CTkButton(
            nav, text="◀", width=36, height=30, font=ctk.CTkFont(size=14),
            command=self._prev_page,
            fg_color=("gray80", "gray30"), hover_color=("gray70", "gray40"),
            text_color=("black", "white")
        )
        self._prev_btn.pack(side="left", padx=(0, 2))

        self._nav_label = ctk.CTkLabel(
            nav, text="— / —", width=80, font=ctk.CTkFont(size=12), anchor="center"
        )
        self._nav_label.pack(side="left", padx=2)

        self._next_btn = ctk.CTkButton(
            nav, text="▶", width=36, height=30, font=ctk.CTkFont(size=14),
            command=self._next_page,
            fg_color=("gray80", "gray30"), hover_color=("gray70", "gray40"),
            text_color=("black", "white")
        )
        self._next_btn.pack(side="left", padx=(2, 12))

        # Zoom
        ctk.CTkButton(
            nav, text="−", width=32, height=30, font=ctk.CTkFont(size=14),
            command=self._zoom_out,
            fg_color=("gray80", "gray30"), hover_color=("gray70", "gray40"),
            text_color=("black", "white")
        ).pack(side="left", padx=2)

        self._zoom_label = ctk.CTkLabel(
            nav, text=self._zoom_text(), width=52, font=ctk.CTkFont(size=11)
        )
        self._zoom_label.pack(side="left", padx=2)

        ctk.CTkButton(
            nav, text="+", width=32, height=30, font=ctk.CTkFont(size=14),
            command=self._zoom_in,
            fg_color=("gray80", "gray30"), hover_color=("gray70", "gray40"),
            text_color=("black", "white")
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            nav, text="⊡ Fit", width=60, height=30, font=ctk.CTkFont(size=11),
            command=self._zoom_fit,
            fg_color=("gray80", "gray30"), hover_color=("gray70", "gray40"),
            text_color=("black", "white")
        ).pack(side="left", padx=6)

        # Image-specific: reset scale button
        self._reset_scale_btn = ctk.CTkButton(
            nav, text="⊞ Fill Page", width=80, height=30, font=ctk.CTkFont(size=11),
            command=self._reset_image_scale,
            fg_color=("#2ecc71", "#1a7a43"), hover_color=("#27ae60", "#166337"),
        )
        self._reset_scale_btn.pack(side="left", padx=4)

    # ------------------------------------------------------------------ #
    # Events
    # ------------------------------------------------------------------ #

    def _register_events(self) -> None:
        from ..controller import (EVT_PAGES_CHANGED, EVT_PAGE_SELECTED,
                                   EVT_PAGE_ROTATED, EVT_RESET)
        self.controller.on(EVT_PAGES_CHANGED, lambda _: self.after(0, self._on_change))
        self.controller.on(EVT_PAGE_SELECTED, lambda _: self.after(0, self._on_change))
        self.controller.on(EVT_PAGE_ROTATED,  lambda _: self.after(0, self._on_change))
        self.controller.on(EVT_RESET,         lambda _: self.after(0, self._clear))

    def _on_change(self) -> None:
        self._update_nav()
        self._schedule_render()

    def _on_canvas_resize(self) -> None:
        self._update_canvas_image()
        self._draw_handles()

    # ------------------------------------------------------------------ #
    # Rendering
    # ------------------------------------------------------------------ #

    def _schedule_render(self) -> None:
        if not self._render_pending:
            self._render_pending = True
            self.after(40, self._do_render)

    def _do_render(self) -> None:
        self._render_pending = False
        idx = self.controller.current_index
        if idx < 0 or not self.controller.pages:
            self._clear()
            return

        zoom      = ZOOM_STEPS[self._zoom_idx]
        page      = self.controller.pages[idx]
        page_num  = idx + 1
        total     = self.controller.page_count
        page_size = self.controller.settings.get("page_size", "A4")

        # Snapshot page number settings at render time so the overlay is live
        pn_settings = self.controller.settings.get_page_number_settings()

        def _worker():
            from ..converters.pdf_builder import render_page_preview
            png = render_page_preview(
                page, zoom,
                page_size=page_size,
                page_number_settings=pn_settings,
                page_num=page_num,
                total_pages=total,
            )
            self.after(0, lambda: self._display(png, page, zoom))

        threading.Thread(target=_worker, daemon=True).start()

    def _display(self, png: Optional[bytes], page, zoom: float) -> None:
        self._canvas.delete("preview_img")
        self._canvas.delete("placeholder")
        self._canvas.delete("handle")
        self._handle_positions.clear()

        if not png:
            self._show_placeholder("⚠️  Could not render page")
            return

        img = Image.open(io.BytesIO(png))
        self._photo = ImageTk.PhotoImage(img)

        # Compute page position on canvas
        cw = self._canvas.winfo_width()
        ch = self._canvas.winfo_height()
        pw, ph = img.width, img.height
        cx = max(cw // 2, pw // 2 + 10)
        cy = max(ch // 2, ph // 2 + 10)

        self._page_x = cx - pw // 2
        self._page_y = cy - ph // 2
        self._page_pw = pw
        self._page_ph = ph

        self._canvas.create_image(cx, cy, anchor="center",
                                   image=self._photo, tags="preview_img")
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

        # Compute where the image is within the page for handle placement
        self._compute_image_bounds(page, pw, ph, cx, cy, zoom)

        # Draw handles if this is an image page
        if page.is_image:
            self._draw_handles()

    def _compute_image_bounds(self, page, pw_px, ph_px, page_cx, page_cy, zoom) -> None:
        """Compute canvas coords of the image centre and displayed size."""
        if not page.is_image:
            self._img_cx = self._img_cy = 0
            self._img_disp_w = self._img_disp_h = 0
            return

        try:
            from PIL import Image, ImageOps
            from ..converters.pdf_builder import _page_dims

            src = Image.open(page.source_file)
            src = ImageOps.exif_transpose(src)
            if src.mode != "RGB":
                src = src.convert("RGB")
            if page.image_rotation:
                src = src.rotate(-page.image_rotation, expand=True)
            img_w, img_h = src.size
            src.close()

            fit_scale  = min(pw_px / img_w, ph_px / img_h)
            final_px_w = int(img_w * fit_scale * page.image_scale)
            final_px_h = int(img_h * fit_scale * page.image_scale)

            # Image centre on canvas
            ox_px = int(page.image_offset_x * zoom)
            oy_px = int(page.image_offset_y * zoom)
            self._img_cx = page_cx + ox_px
            self._img_cy = page_cy + oy_px

            # Displayed size is clamped to page
            self._img_disp_w = min(final_px_w, pw_px)
            self._img_disp_h = min(final_px_h, ph_px)
        except Exception:
            self._img_cx = page_cx
            self._img_cy = page_cy
            self._img_disp_w = pw_px
            self._img_disp_h = ph_px

    def _update_canvas_image(self) -> None:
        if not self._photo:
            return
        self._canvas.delete("preview_img")
        cw = self._canvas.winfo_width()
        ch = self._canvas.winfo_height()
        iw = self._photo.width()
        ih = self._photo.height()
        cx = max(cw // 2, iw // 2 + 10)
        cy = max(ch // 2, ih // 2 + 10)
        self._canvas.create_image(cx, cy, anchor="center",
                                   image=self._photo, tags="preview_img")
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    # ------------------------------------------------------------------ #
    # Corner handles
    # ------------------------------------------------------------------ #

    def _draw_handles(self) -> None:
        """Draw green corner squares around the image bounds."""
        self._canvas.delete("handle")
        self._handle_positions.clear()

        page = self.controller.current_page
        if not page or not page.is_image:
            return
        if self._img_disp_w == 0:
            return

        hw = self._img_disp_w // 2
        hh = self._img_disp_h // 2
        cx, cy = self._img_cx, self._img_cy

        corners = {
            "nw": (cx - hw, cy - hh),
            "ne": (cx + hw, cy - hh),
            "sw": (cx - hw, cy + hh),
            "se": (cx + hw, cy + hh),
        }

        hs = HANDLE_SIZE
        for cid, (hx, hy) in corners.items():
            self._canvas.create_rectangle(
                hx - hs, hy - hs, hx + hs, hy + hs,
                fill="#2ecc71", outline="#ffffff", width=1,
                tags=("handle", f"handle_{cid}"),
            )
            self._handle_positions[cid] = (hx, hy)

    def _hit_test_handle(self, x: int, y: int) -> Optional[str]:
        """Return the corner ID ('nw'/'ne'/'sw'/'se') if (x,y) hits a handle."""
        for cid, (hx, hy) in self._handle_positions.items():
            if abs(x - hx) <= HANDLE_HIT and abs(y - hy) <= HANDLE_HIT:
                return cid
        return None

    # ------------------------------------------------------------------ #
    # Mouse drag for resizing
    # ------------------------------------------------------------------ #

    def _on_mouse_press(self, event: tk.Event) -> None:
        corner = self._hit_test_handle(event.x, event.y)
        if corner is None:
            return
        self._drag_corner     = corner
        self._drag_start_x    = event.x
        self._drag_start_y    = event.y
        page = self.controller.current_page
        if page:
            self._drag_start_scale = page.image_scale
            self._drag_start_ox    = page.image_offset_x
            self._drag_start_oy    = page.image_offset_y

    def _on_mouse_drag(self, event: tk.Event) -> None:
        if not self._drag_corner:
            return
        page = self.controller.current_page
        idx  = self.controller.current_index
        if not page or not page.is_image or idx < 0:
            return

        # Distance from image centre at drag start vs now
        # Use the corner that's being dragged as reference
        hx, hy = self._handle_positions.get(self._drag_corner, (self._img_cx, self._img_cy))

        # Vector from image centre to cursor
        dx = event.x - self._img_cx
        dy = event.y - self._img_cy

        # Original distance from centre to the corner
        orig_hw = self._img_disp_w / 2
        orig_hh = self._img_disp_h / 2

        # New distance in the dominant axis (to maintain aspect ratio)
        orig_dist = max(abs(hx - self._img_cx), abs(hy - self._img_cy))
        curr_dist = max(abs(dx), abs(dy))

        if orig_dist <= 0:
            return

        delta_ratio = curr_dist / orig_dist
        new_scale   = max(0.05, self._drag_start_scale * delta_ratio)

        self.controller.resize_image(idx, new_scale,
                                     self._drag_start_ox,
                                     self._drag_start_oy)

    def _on_mouse_release(self, event: tk.Event) -> None:
        self._drag_corner = None

    # ------------------------------------------------------------------ #
    # Scale reset
    # ------------------------------------------------------------------ #

    def _reset_image_scale(self) -> None:
        idx  = self.controller.current_index
        page = self.controller.current_page
        if idx >= 0 and page and page.is_image:
            self.controller.resize_image(idx, 1.0, 0.0, 0.0)

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
                orient = "⬛↔" if page.page_landscape else "⬜↕"
                rot    = page.image_rotation if page.is_image else page.rotation
                info   = f"{page.display_name}  {orient}"
                if rot:
                    info += f"  ↻{rot}°"
                self._page_info_label.configure(text=info)

    def _prev_page(self) -> None:
        idx = self.controller.current_index
        if idx > 0:
            self.controller.select_page(idx - 1)

    def _next_page(self) -> None:
        idx = self.controller.current_index
        if idx < self.controller.page_count - 1:
            self.controller.select_page(idx + 1)

    def _clear(self) -> None:
        self._canvas.delete("all")
        self._photo = None
        self._handle_positions.clear()
        self._show_placeholder("Add files to preview the document")
        self._page_info_label.configure(text="No page selected")
        self._nav_label.configure(text="— / —")

    def _show_placeholder(self, text: str) -> None:
        cw = max(self._canvas.winfo_width(), 200)
        ch = max(self._canvas.winfo_height(), 200)
        self._canvas.create_text(
            cw // 2, ch // 2, text=text,
            fill="#4a5568", font=("Helvetica", 13), tags="placeholder"
        )

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
        self._zoom_idx = ZOOM_DEFAULT
        self._apply_zoom()

    def _apply_zoom(self) -> None:
        self._zoom_label.configure(text=self._zoom_text())
        self._schedule_render()

    def _zoom_text(self) -> str:
        return f"{int(ZOOM_STEPS[self._zoom_idx] * 100)}%"
