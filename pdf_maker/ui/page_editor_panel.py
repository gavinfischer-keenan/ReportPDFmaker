"""
Page Editor Panel
=================
Right panel: per-page controls.

Image Rotation   — rotates the image content on the page (page stays portrait/landscape).
Page Orientation — switches the page canvas between Portrait and Landscape.
Page Order       — move up/down in the document.
Entire Document  — apply image rotation to every image page at once.
"""

from typing import TYPE_CHECKING
import customtkinter as ctk

if TYPE_CHECKING:
    from ..controller import AppController

ROTATIONS = [
    ("0°",   0),
    ("90°",  90),
    ("180°", 180),
    ("270°", 270),
]

ROT_ICONS = {0: "⬆", 90: "➡", 180: "⬇", 270: "⬅"}

BTN_NORMAL   = ("gray80", "gray30")
BTN_HOVER    = ("gray70", "gray40")
BTN_ACTIVE   = ("#4a9eff", "#1a5fa8")
BTN_ACTIVE_T = "white"
BTN_NORMAL_T = ("black", "white")


class PageEditorPanel(ctk.CTkFrame):
    """Controls for manipulating a single selected page."""

    def __init__(self, parent, controller: "AppController"):
        super().__init__(parent, corner_radius=8, border_width=1)
        self.controller = controller
        self._rot_buttons: dict[int, ctk.CTkButton] = {}
        self._apply_all_var = ctk.BooleanVar(value=False)
        self._landscape_btn: ctk.CTkButton = None
        self._portrait_btn:  ctk.CTkButton = None

        self._build_ui()
        self._register_events()
        self._update_state()

    # ------------------------------------------------------------------ #
    # Layout
    # ------------------------------------------------------------------ #

    def _build_ui(self) -> None:
        # ── Header ────────────────────────────────────────────────────
        header = ctk.CTkFrame(self, fg_color=("gray85", "gray20"), corner_radius=6)
        header.pack(fill="x", padx=6, pady=(6, 0))
        ctk.CTkLabel(
            header, text="✏️  Page Editor",
            font=ctk.CTkFont(size=13, weight="bold"), anchor="w"
        ).pack(side="left", padx=10, pady=6)

        # ── Page info ─────────────────────────────────────────────────
        self._info_label = ctk.CTkLabel(
            self, text="No page selected",
            font=ctk.CTkFont(size=11), text_color="gray",
            wraplength=220, justify="center"
        )
        self._info_label.pack(pady=(10, 4), padx=10)

        self._divider()

        # ── Image Edit Mode ───────────────────────────────────────────
        ctk.CTkLabel(
            self, text="Image Editing",
            font=ctk.CTkFont(size=12, weight="bold"), anchor="w"
        ).pack(padx=14, pady=(8, 2), anchor="w")

        self._mode_seg = ctk.CTkSegmentedButton(
            self, values=["Resize", "Crop"],
            font=ctk.CTkFont(size=11),
            command=self._on_mode_change
        )
        self._mode_seg.set("Resize")
        self._mode_seg.pack(padx=14, pady=(2, 6), fill="x")

        # Action buttons frame (Undo & Apply Crop)
        self._actions_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._actions_frame.pack(padx=14, pady=(0, 6), fill="x")

        self._undo_btn = ctk.CTkButton(
            self._actions_frame, text="↩️ Undo",
            font=ctk.CTkFont(size=11), width=60,
            fg_color=BTN_NORMAL, hover_color=BTN_HOVER, text_color=BTN_NORMAL_T,
            command=self._on_undo
        )
        self._undo_btn.pack(side="left", fill="x", expand=True, padx=(0, 4))

        self._apply_crop_btn = ctk.CTkButton(
            self._actions_frame, text="✂️ Apply Crop",
            font=ctk.CTkFont(size=11, weight="bold"), width=90,
            fg_color=("#e67e22", "#d35400"), hover_color=("#d35400", "#b54400"),
            text_color="white",
            command=self._apply_crop
        )
        # We will grid/pack this only when in crop mode
        # self._apply_crop_btn.pack(side="left", fill="x", expand=True)

        self._divider()

        # ── Image Rotation ────────────────────────────────────────────
        ctk.CTkLabel(
            self, text="Image Rotation",
            font=ctk.CTkFont(size=12, weight="bold"), anchor="w"
        ).pack(padx=14, pady=(8, 2), anchor="w")
        ctk.CTkLabel(
            self, text="Rotates the image on the page, not the page itself.",
            font=ctk.CTkFont(size=10), text_color="gray", anchor="w", wraplength=220
        ).pack(padx=14, anchor="w")

        rot_grid = ctk.CTkFrame(self, fg_color="transparent")
        rot_grid.pack(padx=14, pady=(4, 2), anchor="w")

        for i, (label, deg) in enumerate(ROTATIONS):
            btn = ctk.CTkButton(
                rot_grid,
                text=f"{ROT_ICONS[deg]}\n{label}",
                width=52, height=52,
                font=ctk.CTkFont(size=11),
                corner_radius=8,
                fg_color=BTN_NORMAL,
                hover_color=BTN_HOVER,
                text_color=BTN_NORMAL_T,
                command=lambda d=deg: self._set_rotation(d),
            )
            btn.grid(row=0, column=i, padx=3, pady=3)
            self._rot_buttons[deg] = btn

        self._apply_all_cb = ctk.CTkCheckBox(
            self, text="Apply to all pages",
            variable=self._apply_all_var,
            font=ctk.CTkFont(size=11),
            checkbox_width=16, checkbox_height=16,
        )
        self._apply_all_cb.pack(padx=14, pady=(2, 4), anchor="w")

        self._divider()

        # ── Page Orientation ──────────────────────────────────────────
        ctk.CTkLabel(
            self, text="Page Orientation",
            font=ctk.CTkFont(size=12, weight="bold"), anchor="w"
        ).pack(padx=14, pady=(8, 2), anchor="w")
        ctk.CTkLabel(
            self, text="Rotates the page canvas (Portrait vs Landscape).",
            font=ctk.CTkFont(size=10), text_color="gray", anchor="w", wraplength=220
        ).pack(padx=14, anchor="w")

        orient_frame = ctk.CTkFrame(self, fg_color="transparent")
        orient_frame.pack(padx=14, pady=(6, 2), anchor="w")

        self._portrait_btn = ctk.CTkButton(
            orient_frame, text="⬜\nPortrait",
            width=68, height=56,
            font=ctk.CTkFont(size=10),
            corner_radius=8,
            fg_color=BTN_NORMAL, hover_color=BTN_HOVER, text_color=BTN_NORMAL_T,
            command=self._set_portrait,
        )
        self._portrait_btn.pack(side="left", padx=(0, 6))

        self._landscape_btn = ctk.CTkButton(
            orient_frame, text="⬛\nLandscape",
            width=68, height=56,
            font=ctk.CTkFont(size=10),
            corner_radius=8,
            fg_color=BTN_NORMAL, hover_color=BTN_HOVER, text_color=BTN_NORMAL_T,
            command=self._set_landscape,
        )
        self._landscape_btn.pack(side="left")

        ctk.CTkLabel(
            self, text="Tip: works best for image pages.",
            font=ctk.CTkFont(size=10), text_color="gray", anchor="w"
        ).pack(padx=14, anchor="w")

        self._divider()

        # ── Page Order ────────────────────────────────────────────────
        ctk.CTkLabel(
            self, text="Page Order",
            font=ctk.CTkFont(size=12, weight="bold"), anchor="w"
        ).pack(padx=14, pady=(8, 4), anchor="w")

        order_frame = ctk.CTkFrame(self, fg_color="transparent")
        order_frame.pack(padx=14, pady=2, anchor="w")

        self._up_btn = ctk.CTkButton(
            order_frame, text="▲  Move Up", width=100, height=34,
            font=ctk.CTkFont(size=11), command=self._move_up,
            fg_color=BTN_NORMAL, hover_color=BTN_HOVER, text_color=BTN_NORMAL_T,
        )
        self._up_btn.pack(side="left", padx=(0, 6))

        self._down_btn = ctk.CTkButton(
            order_frame, text="▼  Move Down", width=110, height=34,
            font=ctk.CTkFont(size=11), command=self._move_down,
            fg_color=BTN_NORMAL, hover_color=BTN_HOVER, text_color=BTN_NORMAL_T,
        )
        self._down_btn.pack(side="left")

        self._divider()

        # ── Entire Document ───────────────────────────────────────────
        ctk.CTkLabel(
            self, text="Entire Document",
            font=ctk.CTkFont(size=12, weight="bold"), anchor="w"
        ).pack(padx=14, pady=(8, 2), anchor="w")
        ctk.CTkLabel(
            self, text="Rotate image on every page at once.",
            font=ctk.CTkFont(size=10), text_color="gray", anchor="w"
        ).pack(padx=14, anchor="w")

        doc_rot_frame = ctk.CTkFrame(self, fg_color="transparent")
        doc_rot_frame.pack(padx=14, pady=(4, 2), anchor="w")

        for label, deg in ROTATIONS:
            ctk.CTkButton(
                doc_rot_frame,
                text=f"{ROT_ICONS[deg]}\n{label}",
                width=50, height=50,
                font=ctk.CTkFont(size=10),
                corner_radius=8,
                fg_color=("#1a5fa8", "#0d3d6e"),
                hover_color=("#1249a8", "#092d52"),
                text_color="white",
                command=lambda d=deg: self._rotate_all(d),
            ).pack(side="left", padx=2)

        # All-page orientation row
        all_orient_frame = ctk.CTkFrame(self, fg_color="transparent")
        all_orient_frame.pack(padx=14, pady=(6, 4), anchor="w")

        ctk.CTkButton(
            all_orient_frame, text="All Portrait", width=96, height=30,
            font=ctk.CTkFont(size=10),
            fg_color=("#1a5fa8", "#0d3d6e"), hover_color=("#1249a8", "#092d52"),
            text_color="white",
            command=lambda: self.controller.set_all_landscape(False),
        ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            all_orient_frame, text="All Landscape", width=96, height=30,
            font=ctk.CTkFont(size=10),
            fg_color=("#1a5fa8", "#0d3d6e"), hover_color=("#1249a8", "#092d52"),
            text_color="white",
            command=lambda: self.controller.set_all_landscape(True),
        ).pack(side="left")

        self._divider()

        # ── Delete ────────────────────────────────────────────────────
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

        ctk.CTkFrame(self, height=1, fg_color="transparent").pack(expand=True)

    def _divider(self) -> None:
        ctk.CTkFrame(self, height=1, fg_color=("gray80", "gray30")).pack(
            fill="x", padx=14, pady=4
        )

    # ------------------------------------------------------------------ #
    # Events
    # ------------------------------------------------------------------ #

    def _register_events(self) -> None:
        from ..controller import (EVT_PAGE_SELECTED, EVT_PAGES_CHANGED,
                                  EVT_PAGE_ROTATED, EVT_MODE_CHANGED, EVT_RESET)
        self.controller.on(EVT_PAGE_SELECTED, lambda _: self.after(0, self._update_state))
        self.controller.on(EVT_PAGES_CHANGED, lambda _: self.after(0, self._update_state))
        self.controller.on(EVT_PAGE_ROTATED,  lambda _: self.after(0, self._update_state))
        self.controller.on(EVT_MODE_CHANGED,  lambda _: self.after(0, self._update_state))
        self.controller.on(EVT_RESET,         lambda _: self.after(0, self._update_state))

    # ------------------------------------------------------------------ #
    # State update
    # ------------------------------------------------------------------ #

    def _update_state(self) -> None:
        idx = self.controller.current_index
        page = self.controller.current_page
        total = self.controller.page_count
        has_pg = page is not None
        
        # Mode & Action visibility
        is_image = bool(page and page.is_image)
        state = "normal" if is_image else "disabled"
        self._mode_seg.configure(state=state)
        
        # Undo button state
        can_undo = (self.controller._last_action_state is not None and 
                    is_image and 
                    self.controller._last_action_state.id == page.id)
        self._undo_btn.configure(state="normal" if can_undo else "disabled")

        if is_image:
            self._mode_seg.set(self.controller.editor_mode.capitalize())
            if self.controller.editor_mode == "crop":
                self._apply_crop_btn.pack(side="left", fill="x", expand=True)
            else:
                self._apply_crop_btn.pack_forget()
        else:
            self._mode_seg.set("Resize")
            self._apply_crop_btn.pack_forget()

        if not page:
            self._info_label.configure(text="No page selected")
            for btn in self._rot_buttons.values():
                btn.configure(state="disabled", fg_color=BTN_NORMAL)

        # Info label
        if page:
            orient = "Landscape" if page.page_landscape else "Portrait"
            rot    = page.image_rotation if is_image else page.rotation
            self._info_label.configure(
                text=f"Page {idx + 1} of {total}\n{page.display_name}\n"
                     f"{orient}  |  Rotation: {rot}°"
            )
        else:
            self._info_label.configure(text="No page selected")

        # Rotation buttons — highlight active degree (image_rotation for images)
        active_rot = page.image_rotation if is_image else (page.rotation if page else 0)
        for deg, btn in self._rot_buttons.items():
            active = bool(page) and active_rot == deg
            btn.configure(
                fg_color=BTN_ACTIVE if active else BTN_NORMAL,
                text_color=BTN_ACTIVE_T if active else BTN_NORMAL_T,
            )

        # Orientation buttons
        if page:
            is_land = page.page_landscape
            self._portrait_btn.configure(
                fg_color=BTN_ACTIVE if not is_land else BTN_NORMAL,
                text_color=BTN_ACTIVE_T if not is_land else BTN_NORMAL_T,
            )
            self._landscape_btn.configure(
                fg_color=BTN_ACTIVE if is_land else BTN_NORMAL,
                text_color=BTN_ACTIVE_T if is_land else BTN_NORMAL_T,
            )
        else:
            for b in [self._portrait_btn, self._landscape_btn]:
                b.configure(fg_color=BTN_NORMAL, text_color=BTN_NORMAL_T)

        # Enable / disable
        state = "normal" if has_pg else "disabled"
        for btn in [self._up_btn, self._down_btn, self._del_btn,
                    self._portrait_btn, self._landscape_btn]:
            btn.configure(state=state)
        for btn in self._rot_buttons.values():
            btn.configure(state=state)

        if has_pg:
            self._up_btn.configure(  state="normal" if idx > 0         else "disabled")
            self._down_btn.configure(state="normal" if idx < total - 1  else "disabled")

    def _on_mode_change(self, value: str) -> None:
        mode = "crop" if value == "Crop" else "resize"
        self.controller.set_editor_mode(mode)
        self._update_state()

    def _apply_crop(self) -> None:
        from ..controller import EVT_APPLY_CROP
        self.controller.emit(EVT_APPLY_CROP)
        self.controller.set_editor_mode("resize")
        self._update_state()

    def _on_undo(self) -> None:
        self.controller.undo_last_action()
        self._update_state()

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

    def _set_portrait(self) -> None:
        self.controller.set_page_landscape(self.controller.current_index, False)

    def _set_landscape(self) -> None:
        self.controller.set_page_landscape(self.controller.current_index, True)

    def _move_up(self) -> None:
        self.controller.move_page_up(self.controller.current_index)

    def _move_down(self) -> None:
        self.controller.move_page_down(self.controller.current_index)

    def _delete_page(self) -> None:
        idx = self.controller.current_index
        if idx >= 0:
            self.controller.remove_page(idx)
