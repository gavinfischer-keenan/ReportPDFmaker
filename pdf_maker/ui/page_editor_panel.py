"""
Page Editor Panel
=================
Right panel: per-page controls for rotation and order.
Rotation buttons (0°/90°/180°/270°) with "Apply to All" option.
Move Up / Move Down / Delete Page buttons.
"""

from typing import TYPE_CHECKING
import customtkinter as ctk

if TYPE_CHECKING:
    from ..controller import AppController

# Rotation options
ROTATIONS = [
    ("0°",   0),
    ("90°",  90),
    ("180°", 180),
    ("270°", 270),
]

ROT_ICONS = {0: "⬆", 90: "➡", 180: "⬇", 270: "⬅"}


class PageEditorPanel(ctk.CTkFrame):
    """Controls for manipulating a single selected page."""

    def __init__(self, parent, controller: "AppController"):
        super().__init__(parent, corner_radius=8, border_width=1)
        self.controller = controller
        self._rot_buttons: dict[int, ctk.CTkButton] = {}
        self._apply_all_var = ctk.BooleanVar(value=False)

        self._build_ui()
        self._register_events()
        self._update_state()

    # ------------------------------------------------------------------ #
    # Layout
    # ------------------------------------------------------------------ #

    def _build_ui(self) -> None:
        # Header
        header = ctk.CTkFrame(self, fg_color=("gray85", "gray20"), corner_radius=6)
        header.pack(fill="x", padx=6, pady=(6, 0))
        ctk.CTkLabel(
            header, text="✏️  Page Editor",
            font=ctk.CTkFont(size=13, weight="bold"), anchor="w"
        ).pack(side="left", padx=10, pady=6)

        # Page info
        self._info_label = ctk.CTkLabel(
            self, text="No page selected",
            font=ctk.CTkFont(size=11), text_color="gray",
            wraplength=200, justify="center"
        )
        self._info_label.pack(pady=(10, 4), padx=10)

        self._divider()

        # ── Rotation ──────────────────────────────────────
        ctk.CTkLabel(
            self, text="Rotation",
            font=ctk.CTkFont(size=12, weight="bold"), anchor="w"
        ).pack(padx=14, pady=(8, 4), anchor="w")

        rot_grid = ctk.CTkFrame(self, fg_color="transparent")
        rot_grid.pack(padx=14, pady=2, anchor="w")

        for i, (label, deg) in enumerate(ROTATIONS):
            btn = ctk.CTkButton(
                rot_grid,
                text=f"{ROT_ICONS[deg]}\n{label}",
                width=52, height=52,
                font=ctk.CTkFont(size=11),
                corner_radius=8,
                fg_color=("gray80", "gray30"),
                hover_color=("gray70", "gray40"),
                text_color=("black", "white"),
                command=lambda d=deg: self._set_rotation(d),
            )
            btn.grid(row=0, column=i, padx=3, pady=3)
            self._rot_buttons[deg] = btn

        # Apply to all
        self._apply_all_cb = ctk.CTkCheckBox(
            self, text="Apply to all pages",
            variable=self._apply_all_var,
            font=ctk.CTkFont(size=11),
            checkbox_width=16, checkbox_height=16,
        )
        self._apply_all_cb.pack(padx=14, pady=(4, 2), anchor="w")

        self._divider()

        # ── Order ─────────────────────────────────────────
        ctk.CTkLabel(
            self, text="Page Order",
            font=ctk.CTkFont(size=12, weight="bold"), anchor="w"
        ).pack(padx=14, pady=(8, 4), anchor="w")

        order_frame = ctk.CTkFrame(self, fg_color="transparent")
        order_frame.pack(padx=14, pady=2, anchor="w")

        self._up_btn = ctk.CTkButton(
            order_frame, text="▲  Move Up", width=100, height=34,
            font=ctk.CTkFont(size=11), command=self._move_up,
            fg_color=("gray80", "gray30"), hover_color=("gray70", "gray40"),
            text_color=("black", "white")
        )
        self._up_btn.pack(side="left", padx=(0, 6))

        self._down_btn = ctk.CTkButton(
            order_frame, text="▼  Move Down", width=110, height=34,
            font=ctk.CTkFont(size=11), command=self._move_down,
            fg_color=("gray80", "gray30"), hover_color=("gray70", "gray40"),
            text_color=("black", "white")
        )
        self._down_btn.pack(side="left")

        self._divider()

        # ── Document-wide rotation ──────────────────────────
        ctk.CTkLabel(
            self, text="Entire Document",
            font=ctk.CTkFont(size=12, weight="bold"), anchor="w"
        ).pack(padx=14, pady=(8, 4), anchor="w")

        doc_rot_frame = ctk.CTkFrame(self, fg_color="transparent")
        doc_rot_frame.pack(padx=14, pady=2, anchor="w")

        for label, deg in ROTATIONS:
            ctk.CTkButton(
                doc_rot_frame,
                text=f"{ROT_ICONS[deg]}\n{label}",
                width=50, height=50,
                font=ctk.CTkFont(size=11),
                corner_radius=8,
                fg_color=("#1a5fa8", "#0d3d6e"),
                hover_color=("#1249847", "#0a2e52"),
                text_color="white",
                command=lambda d=deg: self._rotate_all(d),
            ).grid_configure() if False else None

        # Simpler row for document-wide rotation
        for label, deg in ROTATIONS:
            b = ctk.CTkButton(
                doc_rot_frame,
                text=f"{ROT_ICONS[deg]}\n{label}",
                width=50, height=50,
                font=ctk.CTkFont(size=11),
                corner_radius=8,
                fg_color=("#1a5fa8", "#0d3d6e"),
                hover_color=("#1249a8", "#092d52"),
                text_color="white",
                command=lambda d=deg: self._rotate_all(d),
            )
            b.pack(side="left", padx=2)

        ctk.CTkLabel(
            self, text="Rotates every page at once",
            font=ctk.CTkFont(size=10), text_color="gray", anchor="w"
        ).pack(padx=14, anchor="w")

        self._divider()

        # ── Delete ────────────────────────────────────────
        self._del_btn = ctk.CTkButton(
            self,
            text="🗑  Delete This Page",
            height=36,
            font=ctk.CTkFont(size=12),
            fg_color=("#e74c3c", "#c0392b"),
            hover_color=("#c0392b", "#a93226"),
            command=self._delete_page,
        )
        self._del_btn.pack(fill="x", padx=14, pady=(8, 4))

        # Spacer
        ctk.CTkFrame(self, height=1, fg_color="transparent").pack(expand=True)

    def _divider(self) -> None:
        ctk.CTkFrame(self, height=1, fg_color=("gray80", "gray30")).pack(
            fill="x", padx=14, pady=4
        )

    # ------------------------------------------------------------------ #
    # Events
    # ------------------------------------------------------------------ #

    def _register_events(self) -> None:
        from ..controller import (EVT_PAGES_CHANGED, EVT_PAGE_SELECTED,
                           EVT_PAGE_ROTATED, EVT_RESET)
        self.controller.on(EVT_PAGES_CHANGED, lambda _: self._update_state())
        self.controller.on(EVT_PAGE_SELECTED, lambda _: self._update_state())
        self.controller.on(EVT_PAGE_ROTATED,  lambda _: self._update_state())
        self.controller.on(EVT_RESET,         lambda _: self._update_state())

    # ------------------------------------------------------------------ #
    # State update
    # ------------------------------------------------------------------ #

    def _update_state(self) -> None:
        """Refresh info label and button states based on current selection."""
        page   = self.controller.current_page
        idx    = self.controller.current_index
        total  = self.controller.page_count
        has_pg = page is not None

        # Info label
        if page:
            self._info_label.configure(
                text=f"Page {idx + 1} of {total}\n{page.display_name}"
            )
        else:
            self._info_label.configure(text="No page selected")

        # Highlight active rotation button
        for deg, btn in self._rot_buttons.items():
            active = has_pg and page.rotation == deg
            btn.configure(
                fg_color=("#4a9eff", "#1a5fa8") if active else ("gray80", "gray30"),
                text_color="white" if active else ("black", "white"),
            )

        # Enable/disable buttons
        state = "normal" if has_pg else "disabled"
        for btn in [self._up_btn, self._down_btn, self._del_btn]:
            btn.configure(state=state)
        for btn in self._rot_buttons.values():
            btn.configure(state=state)

        if has_pg:
            self._up_btn.configure(state="normal" if idx > 0 else "disabled")
            self._down_btn.configure(state="normal" if idx < total - 1 else "disabled")

    # ------------------------------------------------------------------ #
    # Actions
    # ------------------------------------------------------------------ #

    def _set_rotation(self, degrees: int) -> None:
        idx = self.controller.current_index
        if idx < 0:
            return
        if self._apply_all_var.get():
            self.controller.rotate_all_pages(degrees)
        else:
            self.controller.rotate_page(idx, degrees)

    def _rotate_all(self, degrees: int) -> None:
        self.controller.rotate_all_pages(degrees)

    def _move_up(self) -> None:
        self.controller.move_page_up(self.controller.current_index)

    def _move_down(self) -> None:
        self.controller.move_page_down(self.controller.current_index)

    def _delete_page(self) -> None:
        idx = self.controller.current_index
        if idx >= 0:
            self.controller.remove_page(idx)
