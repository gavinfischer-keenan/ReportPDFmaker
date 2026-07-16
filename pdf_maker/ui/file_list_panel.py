"""
File List Panel
===============
Left panel showing all pages in the document queue.
Selected row gets a green border highlight.
"""

import tkinter as tk
from pathlib import Path
from typing import Optional, TYPE_CHECKING
import customtkinter as ctk

from ..utils.file_utils import get_file_icon, get_file_type

if TYPE_CHECKING:
    from ..controller import AppController

# Color map for file type badges
TYPE_COLORS = {
    "image":   ("#4a9eff", "#1a5fa8"),
    "text":    ("#2ecc71", "#1a7a43"),
    "word":    ("#5b7fdb", "#2c4a8a"),
    "pdf":     ("#e74c3c", "#922b21"),
    "3d":      ("#9b59b6", "#5b2c6f"),
    "unknown": ("#95a5a6", "#596262"),
}

SELECTED_BG     = ("#dce8ff", "#1a3a5c")
SELECTED_BORDER = "#2ecc71"   # Green border for selected page
HOVER_BG        = ("#f0f4ff", "#1f2d40")
HOVER_BORDER    = ("gray70",  "gray50")
NORMAL_BG       = "transparent"   # Must be a string for CTk 6+
NORMAL_BORDER   = "transparent"


class FileListPanel(ctk.CTkFrame):
    """Scrollable page list with selection highlight and manipulation controls."""

    def __init__(self, parent, controller: "AppController"):
        super().__init__(parent, corner_radius=8, border_width=1)
        self.controller = controller
        self._row_frames: list[ctk.CTkFrame] = []
        self._selected_index: int = -1

        self._build_ui()
        self._register_events()

    # ------------------------------------------------------------------ #
    # Layout
    # ------------------------------------------------------------------ #

    def _build_ui(self) -> None:
        header = ctk.CTkFrame(self, fg_color=("gray85", "gray20"), corner_radius=6)
        header.pack(fill="x", padx=6, pady=(6, 0))

        ctk.CTkLabel(
            header, text="📋  Document Pages",
            font=ctk.CTkFont(size=13, weight="bold"), anchor="w"
        ).pack(side="left", padx=10, pady=6)

        self._page_count_label = ctk.CTkLabel(
            header, text="0 pages", font=ctk.CTkFont(size=11), text_color="gray"
        )
        self._page_count_label.pack(side="right", padx=10)

        self._scroll_frame = ctk.CTkScrollableFrame(self, label_text="")
        self._scroll_frame.pack(fill="both", expand=True, padx=6, pady=4)

        ctrl = ctk.CTkFrame(self, fg_color="transparent")
        ctrl.pack(fill="x", padx=6, pady=(0, 6))

        self._up_btn = ctk.CTkButton(
            ctrl, text="▲ Up", width=70, height=30,
            font=ctk.CTkFont(size=11), command=self._move_up,
            fg_color=("gray80", "gray30"), hover_color=("gray70", "gray40"),
            text_color=("black", "white")
        )
        self._up_btn.pack(side="left", padx=(0, 3))

        self._down_btn = ctk.CTkButton(
            ctrl, text="▼ Down", width=70, height=30,
            font=ctk.CTkFont(size=11), command=self._move_down,
            fg_color=("gray80", "gray30"), hover_color=("gray70", "gray40"),
            text_color=("black", "white")
        )
        self._down_btn.pack(side="left", padx=3)

        self._del_btn = ctk.CTkButton(
            ctrl, text="✕ Remove", width=80, height=30,
            font=ctk.CTkFont(size=11), command=self._remove_selected,
            fg_color=("#e74c3c", "#c0392b"), hover_color=("#c0392b", "#a93226"),
        )
        self._del_btn.pack(side="right")

    # ------------------------------------------------------------------ #
    # Event registration
    # ------------------------------------------------------------------ #

    def _register_events(self) -> None:
        from ..controller import EVT_PAGES_CHANGED, EVT_PAGE_SELECTED, EVT_RESET
        self.controller.on(EVT_PAGES_CHANGED, lambda _: self._refresh())
        self.controller.on(EVT_PAGE_SELECTED,  lambda idx: self._highlight(idx))
        self.controller.on(EVT_RESET,          lambda _: self._refresh())

    # ------------------------------------------------------------------ #
    # Rendering
    # ------------------------------------------------------------------ #

    def _refresh(self) -> None:
        for frame in self._row_frames:
            frame.destroy()
        self._row_frames.clear()

        pages = self.controller.pages
        self._page_count_label.configure(
            text=f"{len(pages)} page{'s' if len(pages) != 1 else ''}"
        )

        for idx, page in enumerate(pages):
            row = self._build_row(idx, page)
            row.pack(fill="x", pady=1)
            self._row_frames.append(row)

        self._highlight(self.controller.current_index)

    def _build_row(self, idx: int, page) -> ctk.CTkFrame:
        row = ctk.CTkFrame(
            self._scroll_frame,
            corner_radius=5,
            height=46,
            cursor="hand2",
            border_width=2,
            border_color=NORMAL_BORDER,
            fg_color=NORMAL_BG,
        )
        row.pack_propagate(False)

        colors = TYPE_COLORS.get(page.source_type, TYPE_COLORS["unknown"])
        badge = ctk.CTkLabel(
            row, text=get_file_icon(page.source_type),
            width=34, height=34, corner_radius=4,
            fg_color=colors,
            font=ctk.CTkFont(size=16),
        )
        badge.pack(side="left", padx=(6, 4), pady=6)

        text_frame = ctk.CTkFrame(row, fg_color="transparent")
        text_frame.pack(side="left", fill="both", expand=True, pady=4)

        name_label = ctk.CTkLabel(
            text_frame, text=page.display_name,
            anchor="w", font=ctk.CTkFont(size=11, weight="bold"),
            wraplength=130
        )
        name_label.pack(anchor="w", padx=2)

        sub_text = f"#{idx + 1}"
        if getattr(page, 'image_rotation', 0):
            sub_text += f"  ↻{page.image_rotation}°"
        elif page.rotation:
            sub_text += f"  ↻{page.rotation}°"
        if page.page_landscape:
            sub_text += "  ⬛↔"
        if page.warnings:
            sub_text += "  ⚠"
        sub_label = ctk.CTkLabel(
            text_frame, text=sub_text,
            anchor="w", font=ctk.CTkFont(size=10), text_color="gray"
        )
        sub_label.pack(anchor="w", padx=2)

        for widget in [row, badge, text_frame, name_label, sub_label]:
            widget.bind("<Button-1>", lambda e, i=idx: self._on_row_click(i))
            widget.bind("<Enter>",    lambda e, r=row, i=idx: self._on_hover(r, i, True))
            widget.bind("<Leave>",    lambda e, r=row, i=idx: self._on_hover(r, i, False))

        return row

    def _highlight(self, index: int) -> None:
        self._selected_index = index
        for i, frame in enumerate(self._row_frames):
            if i == index:
                # Green border + selected background
                frame.configure(
                    fg_color=SELECTED_BG,
                    border_color=SELECTED_BORDER,
                    border_width=2,
                )
            else:
                frame.configure(
                    fg_color=NORMAL_BG,
                    border_color=NORMAL_BORDER,
                    border_width=2,
                )

    def _on_hover(self, row: ctk.CTkFrame, idx: int, entering: bool) -> None:
        if idx != self._selected_index:
            if entering:
                row.configure(fg_color=HOVER_BG, border_color=HOVER_BORDER)
            else:
                row.configure(fg_color=NORMAL_BG, border_color=NORMAL_BORDER)

    def _on_row_click(self, idx: int) -> None:
        self.controller.select_page(idx)

    # ------------------------------------------------------------------ #
    # Controls
    # ------------------------------------------------------------------ #

    def _move_up(self) -> None:
        idx = self.controller.current_index
        if idx > 0:
            self.controller.move_page_up(idx)

    def _move_down(self) -> None:
        idx = self.controller.current_index
        if idx >= 0 and idx < self.controller.page_count - 1:
            self.controller.move_page_down(idx)

    def _remove_selected(self) -> None:
        idx = self.controller.current_index
        if idx >= 0:
            self.controller.remove_page(idx)
