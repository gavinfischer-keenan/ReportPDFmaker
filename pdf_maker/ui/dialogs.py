"""
Dialogs
=======
All modal dialogs for PDF Maker:
  - WarningsDialog
  - PageNumberSettingsDialog
  - ResetConfirmDialog
  - AboutDialog
  - ProgressDialog
  - ShortcutsDialog
  - CommandPaletteDialog
"""

import tkinter as tk
from tkinter import ttk
from pathlib import Path
from typing import Optional, Callable
import customtkinter as ctk

from .. import __version__
from ..settings_manager import (
    DEFAULT_SETTINGS,
    FONT_OPTIONS,
    PAGE_NUMBER_STYLES,
    PAGE_SIZE_OPTIONS,
    SettingsManager,
    compute_settings_diff,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _center_on_parent(window: ctk.CTkToplevel, parent: ctk.CTk | ctk.CTkToplevel) -> None:
    """Center a toplevel window over its parent."""
    window.update_idletasks()
    pw = parent.winfo_width()
    ph = parent.winfo_height()
    px = parent.winfo_x()
    py = parent.winfo_y()
    ww = window.winfo_width()
    wh = window.winfo_height()
    x = px + (pw - ww) // 2
    y = py + (ph - wh) // 2
    window.geometry(f"+{x}+{y}")


# ---------------------------------------------------------------------------
# Warnings Dialog
# ---------------------------------------------------------------------------

class WarningsDialog(ctk.CTkToplevel):
    """Shows conversion warnings/errors to the user."""

    def __init__(self, parent, warnings: list[str]):
        super().__init__(parent)
        self.title("Import Warnings")
        self.geometry("520x340")
        self.resizable(True, True)
        self.grab_set()

        ctk.CTkLabel(
            self, text="⚠️  Import Warnings", font=ctk.CTkFont(size=15, weight="bold")
        ).pack(pady=(18, 8), padx=20, anchor="w")

        frame = ctk.CTkScrollableFrame(self, height=220)
        frame.pack(fill="both", expand=True, padx=16, pady=4)

        for w in warnings:
            ctk.CTkLabel(
                frame, text=w, wraplength=460, justify="left", anchor="w",
                font=ctk.CTkFont(size=12)
            ).pack(pady=3, padx=6, anchor="w")

        ctk.CTkButton(self, text="OK", width=100, command=self.destroy).pack(pady=14)
        _center_on_parent(self, parent)


# ---------------------------------------------------------------------------
# Page Number Settings Dialog
# ---------------------------------------------------------------------------

class PageNumberSettingsDialog(ctk.CTkToplevel):
    """Grouped settings dialog with descriptions, sensible defaults, and change diff confirmation."""

    def __init__(self, parent, settings: SettingsManager, on_apply: Optional[Callable] = None, controller=None):
        super().__init__(parent)
        self.settings = settings
        self.on_apply = on_apply
        self.controller = controller
        self.title("Document & Page Number Settings")
        self.geometry("540x680")
        self.resizable(False, False)
        self.grab_set()

        # Title
        ctk.CTkLabel(
            self, text="⚙️  Document & Page Number Settings",
            font=ctk.CTkFont(size=15, weight="bold")
        ).pack(pady=(16, 2), padx=20, anchor="w")
        ctk.CTkLabel(
            self, text="Grouped preferences with sensible defaults. Raw margin offsets are managed automatically.",
            font=ctk.CTkFont(size=11), text_color="gray", wraplength=490, justify="left"
        ).pack(padx=20, anchor="w", pady=(0, 8))

        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=16, pady=4)

        # Group 1: Document Layout
        self._add_group_header(scroll, "1. Document Layout", "Page dimensions and optional page range for PDF export.")
        g1 = ctk.CTkFrame(scroll, corner_radius=8)
        g1.pack(fill="x", pady=(2, 10))
        g1.columnconfigure(1, weight=1)

        self._page_size_var = ctk.StringVar(value=settings.get("page_size", "A4"))
        self._add_row(g1, 0, "Page Size:", "Paper size or Fit to match image dimensions.",
                      ctk.CTkOptionMenu(g1, values=PAGE_SIZE_OPTIONS, variable=self._page_size_var))

        self._range_var = ctk.StringVar(value=settings.get("export_page_range", ""))
        self._add_row(g1, 1, "Export Page Range:", "e.g. 1-3, 5 (leave blank for all pages).",
                      ctk.CTkEntry(g1, textvariable=self._range_var, width=160, placeholder_text="All pages"))

        # Group 2: Page Numbering & Position
        self._add_group_header(scroll, "2. Page Numbering & Position", "Toggle numbers and choose where they appear on each page.")
        g2 = ctk.CTkFrame(scroll, corner_radius=8)
        g2.pack(fill="x", pady=(2, 10))
        g2.columnconfigure(1, weight=1)

        self._enabled_var = ctk.BooleanVar(value=settings.get("page_numbers", False))
        self._add_row(g2, 0, "Enable page numbers:", "Stamp page numbers across exported pages.",
                      ctk.CTkSwitch(g2, variable=self._enabled_var, text=""))

        self._skip_cover_var = ctk.BooleanVar(value=settings.get("skip_cover_page", False))
        self._add_row(g2, 1, "Skip cover page:", "Omit numbering on page 1 while keeping sequence.",
                      ctk.CTkSwitch(g2, variable=self._skip_cover_var, text=""))

        self._position_var = ctk.StringVar(value=settings.get("page_number_position", "bottom"))
        self._add_row(g2, 2, "Position:", "Header (top) or footer (bottom) placement.",
                      ctk.CTkSegmentedButton(g2, values=["top", "bottom"], variable=self._position_var))

        self._align_var = ctk.StringVar(value=settings.get("page_number_alignment", "center"))
        self._add_row(g2, 3, "Alignment:", "Horizontal placement within header or footer.",
                      ctk.CTkSegmentedButton(g2, values=["left", "center", "right"], variable=self._align_var))

        # Group 3: Format & Typography
        self._add_group_header(scroll, "3. Format & Typography", "Visual style, font family, size, and color.")
        g3 = ctk.CTkFrame(scroll, corner_radius=8)
        g3.pack(fill="x", pady=(2, 10))
        g3.columnconfigure(1, weight=1)

        style_opts = list(PAGE_NUMBER_STYLES.keys())
        self._style_var = ctk.StringVar(value=settings.get("page_number_style", "plain"))
        self._add_row(g3, 0, "Number style:", "Display format such as '1' or 'Page 1 of N'.",
                      ctk.CTkOptionMenu(g3, values=style_opts, variable=self._style_var))

        self._font_var = ctk.StringVar(value=settings.get("page_number_font", "Helvetica"))
        self._add_row(g3, 1, "Font:", "PDF standard font used for numbering.",
                      ctk.CTkOptionMenu(g3, values=FONT_OPTIONS, variable=self._font_var))

        self._font_size_var = ctk.IntVar(value=settings.get("page_number_font_size", 10))
        fs_frame = ctk.CTkFrame(g3, fg_color="transparent")
        self._fs_slider = ctk.CTkSlider(fs_frame, from_=6, to=24, variable=self._font_size_var, width=150,
                                        command=lambda v: self._fs_label.configure(text=f"{int(v)} pt"))
        self._fs_label  = ctk.CTkLabel(fs_frame, text=f"{self._font_size_var.get()} pt", width=48)
        self._fs_slider.pack(side="left")
        self._fs_label.pack(side="left", padx=6)
        self._add_row(g3, 2, "Font size:", "Text size in points (6–24 pt).", fs_frame)

        self._color_var = ctk.StringVar(value=settings.get("page_number_color", "#000000"))
        color_frame = ctk.CTkFrame(g3, fg_color="transparent")
        self._color_entry = ctk.CTkEntry(color_frame, textvariable=self._color_var, width=100)
        self._color_entry.pack(side="left")
        ctk.CTkLabel(color_frame, text="  (hex e.g. #000000)", text_color="gray",
                     font=ctk.CTkFont(size=10)).pack(side="left")
        self._add_row(g3, 3, "Color:", "Hex text color for page numbers.", color_frame)

        # Group 4: Watermark & Header/Footer
        self._add_group_header(scroll, "4. Watermark & Header/Footer", "Optional diagonal stamp and top/bottom running text.")
        g4 = ctk.CTkFrame(scroll, corner_radius=8)
        g4.pack(fill="x", pady=(2, 10))
        g4.columnconfigure(1, weight=1)

        self._wm_text_var = ctk.StringVar(value=settings.get("watermark_text", ""))
        self._add_row(g4, 0, "Watermark text:", "Centered diagonal stamp (e.g. DRAFT).",
                      ctk.CTkEntry(g4, textvariable=self._wm_text_var, width=170, placeholder_text="None"))

        self._wm_opacity_var = ctk.IntVar(value=int(round(float(settings.get("watermark_opacity", 0.18)) * 100)))
        wm_op_frame = ctk.CTkFrame(g4, fg_color="transparent")
        self._wm_op_slider = ctk.CTkSlider(
            wm_op_frame, from_=5, to=60, variable=self._wm_opacity_var, width=130,
            command=lambda v: self._wm_op_lbl.configure(text=f"{int(v)}%"),
        )
        self._wm_op_lbl = ctk.CTkLabel(wm_op_frame, text=f"{self._wm_opacity_var.get()}%", width=42)
        self._wm_op_slider.pack(side="left")
        self._wm_op_lbl.pack(side="left", padx=6)
        self._add_row(g4, 1, "Watermark opacity:", "Transparency of watermark (5–60%).", wm_op_frame)

        self._wm_color_var = ctk.StringVar(value=settings.get("watermark_color", "#64748b"))
        self._add_row(g4, 2, "Watermark color:", "Hex color for diagonal watermark.",
                      ctk.CTkEntry(g4, textvariable=self._wm_color_var, width=110))

        self._header_var = ctk.StringVar(value=settings.get("header_text", ""))
        self._add_row(g4, 3, "Header text:", "Top-left running header on every page.",
                      ctk.CTkEntry(g4, textvariable=self._header_var, width=170, placeholder_text="None"))

        self._footer_var = ctk.StringVar(value=settings.get("footer_text", ""))
        self._add_row(g4, 4, "Footer text:", "Bottom-left running footer on every page.",
                      ctk.CTkEntry(g4, textvariable=self._footer_var, width=170, placeholder_text="None"))

        # Group 5: PDF Metadata & Security
        self._add_group_header(scroll, "5. PDF Metadata & Security", "Embedded document properties and optional AES-256 password.")
        g5 = ctk.CTkFrame(scroll, corner_radius=8)
        g5.pack(fill="x", pady=(2, 10))
        g5.columnconfigure(1, weight=1)

        self._pdf_title_var = ctk.StringVar(value=settings.get("pdf_title", ""))
        self._add_row(g5, 0, "Title:", "PDF document title metadata.",
                      ctk.CTkEntry(g5, textvariable=self._pdf_title_var, width=170))

        self._pdf_author_var = ctk.StringVar(value=settings.get("pdf_author", ""))
        self._add_row(g5, 1, "Author:", "PDF author metadata.",
                      ctk.CTkEntry(g5, textvariable=self._pdf_author_var, width=170))

        self._pdf_subject_var = ctk.StringVar(value=settings.get("pdf_subject", ""))
        self._add_row(g5, 2, "Subject:", "PDF subject metadata.",
                      ctk.CTkEntry(g5, textvariable=self._pdf_subject_var, width=170))

        init_pw = getattr(controller, "session_pdf_password", "") if controller else ""
        self._pdf_pw_var = ctk.StringVar(value=init_pw)
        self._add_row(g5, 3, "PDF Password:", "Session only — not saved to disk.",
                      ctk.CTkEntry(g5, textvariable=self._pdf_pw_var, width=170, show="•", placeholder_text="Optional"))

        # Confirmation banner area
        self._diff_label = ctk.CTkLabel(
            self, text="", font=ctk.CTkFont(size=11), text_color="#2ecc71",
            wraplength=470, justify="left"
        )
        self._diff_label.pack(padx=20, pady=(4, 0), anchor="w")

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=12)
        ctk.CTkButton(btn_frame, text="Save & Apply", width=120, command=self._apply).pack(side="left", padx=6)
        ctk.CTkButton(btn_frame, text="Reset Defaults", width=120,
                      fg_color="transparent", border_width=1, command=self._reset_defaults).pack(side="left", padx=6)
        ctk.CTkButton(btn_frame, text="Cancel", width=90,
                      fg_color="transparent", border_width=1, command=self.destroy).pack(side="left", padx=6)

        self.bind("<Escape>", lambda _: self.destroy())
        _center_on_parent(self, parent)

    def _add_group_header(self, parent, title: str, subtitle: str) -> None:
        ctk.CTkLabel(parent, text=title, font=ctk.CTkFont(size=12, weight="bold"), anchor="w").pack(
            fill="x", padx=4, pady=(6, 0)
        )
        ctk.CTkLabel(parent, text=subtitle, font=ctk.CTkFont(size=10), text_color="gray", anchor="w").pack(
            fill="x", padx=4, pady=(0, 4)
        )

    def _add_row(self, parent, row: int, label: str, desc: str, widget) -> None:
        lbl_wrap = ctk.CTkFrame(parent, fg_color="transparent")
        lbl_wrap.grid(row=row, column=0, padx=(10, 12), pady=6, sticky="w")
        ctk.CTkLabel(lbl_wrap, text=label, anchor="w", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(lbl_wrap, text=desc, anchor="w", font=ctk.CTkFont(size=10), text_color="gray", wraplength=200, justify="left").pack(anchor="w")
        widget.grid(row=row, column=1, padx=(0, 10), pady=6, sticky="e")

    def _reset_defaults(self) -> None:
        self._page_size_var.set(DEFAULT_SETTINGS["page_size"])
        self._range_var.set(DEFAULT_SETTINGS["export_page_range"])
        self._enabled_var.set(DEFAULT_SETTINGS["page_numbers"])
        self._skip_cover_var.set(DEFAULT_SETTINGS["skip_cover_page"])
        self._position_var.set(DEFAULT_SETTINGS["page_number_position"])
        self._align_var.set(DEFAULT_SETTINGS["page_number_alignment"])
        self._style_var.set(DEFAULT_SETTINGS["page_number_style"])
        self._font_var.set(DEFAULT_SETTINGS["page_number_font"])
        self._font_size_var.set(DEFAULT_SETTINGS["page_number_font_size"])
        self._fs_label.configure(text=f"{DEFAULT_SETTINGS['page_number_font_size']} pt")
        self._color_var.set(DEFAULT_SETTINGS["page_number_color"])
        self._wm_text_var.set(DEFAULT_SETTINGS["watermark_text"])
        wm_pct = int(round(DEFAULT_SETTINGS["watermark_opacity"] * 100))
        self._wm_opacity_var.set(wm_pct)
        self._wm_op_lbl.configure(text=f"{wm_pct}%")
        self._wm_color_var.set(DEFAULT_SETTINGS["watermark_color"])
        self._header_var.set(DEFAULT_SETTINGS["header_text"])
        self._footer_var.set(DEFAULT_SETTINGS["footer_text"])
        self._pdf_title_var.set(DEFAULT_SETTINGS["pdf_title"])
        self._pdf_author_var.set(DEFAULT_SETTINGS["pdf_author"])
        self._pdf_subject_var.set(DEFAULT_SETTINGS["pdf_subject"])
        self._pdf_pw_var.set("")
        self._diff_label.configure(text="Restored sensible defaults (click Save & Apply to persist).", text_color="#f39c12")

    def _apply(self) -> None:
        updates = {
            "page_size":             self._page_size_var.get(),
            "export_page_range":     self._range_var.get().strip(),
            "page_numbers":          self._enabled_var.get(),
            "skip_cover_page":       self._skip_cover_var.get(),
            "page_number_position":  self._position_var.get(),
            "page_number_alignment": self._align_var.get(),
            "page_number_style":     self._style_var.get(),
            "page_number_font":      self._font_var.get(),
            "page_number_font_size": int(self._font_size_var.get()),
            "page_number_color":     self._color_var.get().strip() or "#000000",
            "watermark_text":        self._wm_text_var.get().strip(),
            "watermark_opacity":     round(int(self._wm_opacity_var.get()) / 100.0, 2),
            "watermark_color":       self._wm_color_var.get().strip() or "#64748b",
            "header_text":           self._header_var.get().strip(),
            "footer_text":           self._footer_var.get().strip(),
            "pdf_title":             self._pdf_title_var.get().strip(),
            "pdf_author":            self._pdf_author_var.get().strip(),
            "pdf_subject":           self._pdf_subject_var.get().strip(),
        }
        if self.controller is not None:
            self.controller.session_pdf_password = self._pdf_pw_var.get()
        old_vals = {k: self.settings.get(k) for k in updates}
        changes = compute_settings_diff(old_vals, updates)
        self.settings.set_many(updates)
        if self.on_apply:
            try:
                self.on_apply(changes)
            except TypeError:
                self.on_apply()
        self.destroy()


# ---------------------------------------------------------------------------
# Reset Confirmation Dialog
# ---------------------------------------------------------------------------

class ResetConfirmDialog(ctk.CTkToplevel):
    """Ask the user to confirm a full reset."""

    def __init__(self, parent, on_confirm: Callable):
        super().__init__(parent)
        self.on_confirm = on_confirm
        self.title("Confirm Reset")
        self.geometry("380x200")
        self.resizable(False, False)
        self.grab_set()

        ctk.CTkLabel(
            self, text="🔄  Reset Everything?",
            font=ctk.CTkFont(size=15, weight="bold")
        ).pack(pady=(22, 6))
        ctk.CTkLabel(
            self,
            text="This will remove all files from the document queue\n"
                 "and reset all settings to their defaults.\n\nThis cannot be undone.",
            justify="center", wraplength=340, font=ctk.CTkFont(size=12)
        ).pack(pady=6)

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=18)
        ctk.CTkButton(
            btn_frame, text="Reset", width=110,
            fg_color="#c0392b", hover_color="#922b21",
            command=self._confirm
        ).pack(side="left", padx=8)
        ctk.CTkButton(
            btn_frame, text="Cancel", width=90,
            fg_color="transparent", border_width=1, command=self.destroy
        ).pack(side="left")
        _center_on_parent(self, parent)

    def _confirm(self) -> None:
        self.destroy()
        self.on_confirm()


# ---------------------------------------------------------------------------
# About Dialog
# ---------------------------------------------------------------------------

class AboutDialog(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("About PDF Maker")
        self.geometry("360x260")
        self.resizable(False, False)
        self.grab_set()

        ctk.CTkLabel(self, text="📄 PDF Maker", font=ctk.CTkFont(size=22, weight="bold")).pack(pady=(24, 4))
        ctk.CTkLabel(self, text=f"Version {__version__}", font=ctk.CTkFont(size=12), text_color="gray").pack()
        ctk.CTkLabel(
            self,
            text="Combine, edit, crop, number, and compress images, PDFs,\n"
                 "Word documents, text files, and 3D models into one PDF.",
            justify="center", wraplength=310, font=ctk.CTkFont(size=12)
        ).pack(pady=14)
        ctk.CTkLabel(
            self, text="github.com/gavinfischer-keenan/ReportPDFmaker",
            text_color="#4a9eff", font=ctk.CTkFont(size=11)
        ).pack()
        ctk.CTkButton(self, text="Close", width=100, command=self.destroy).pack(pady=18)
        self.bind("<Escape>", lambda _: self.destroy())
        _center_on_parent(self, parent)


# ---------------------------------------------------------------------------
# Progress Dialog
# ---------------------------------------------------------------------------

class ProgressDialog(ctk.CTkToplevel):
    """Shows progress of PDF generation."""

    def __init__(self, parent, title: str = "Building PDF…"):
        super().__init__(parent)
        self.title(title)
        self.geometry("380x150")
        self.resizable(False, False)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", lambda: None)  # Prevent closing during build

        self._label = ctk.CTkLabel(self, text="Starting…", font=ctk.CTkFont(size=13))
        self._label.pack(pady=(24, 12))

        self._bar = ctk.CTkProgressBar(self, width=320)
        self._bar.pack(padx=20)
        self._bar.set(0)

        _center_on_parent(self, parent)

    def update_progress(self, current: int, total: int, message: str) -> None:
        """Update the progress bar and label (call from main thread via after())."""
        if total > 0:
            self._bar.set(current / total)
        self._label.configure(text=message)
        self.update_idletasks()

    def close(self) -> None:
        self.destroy()


# ---------------------------------------------------------------------------
# Keyboard Shortcuts Overlay ("?")
# ---------------------------------------------------------------------------

DESKTOP_SHORTCUTS = [
    ("Ctrl + K", "Open Command Palette"),
    ("Ctrl + O", "Open .nautilus Project"),
    ("Ctrl + Shift + S", "Save .nautilus Project"),
    ("Ctrl + Z", "Undo Last Action"),
    ("Ctrl + Y", "Redo Last Action"),
    ("Alt + ↑ / ↓", "Reorder Page Up / Down"),
    ("?", "Show Keyboard Shortcuts"),
    ("A", "Add Files to Document"),
    ("E", "Save / Export PDF"),
    ("S", "Open Shrink PDF Tool"),
    ("R", "Rotate Selected Page +90°"),
    ("O", "Toggle Portrait / Landscape"),
    ("N", "Toggle Page Numbers"),
    ("F", "Fit Preview Zoom"),
    ("Delete / Backspace", "Remove Selected Page"),
    ("← / →", "Previous / Next Page"),
    ("T", "Toggle Dark / Light Theme"),
    ("Esc", "Close Active Dialog"),
]


class ShortcutsDialog(ctk.CTkToplevel):
    """Keyboard shortcuts reference overlay."""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Keyboard Shortcuts")
        self.geometry("440x480")
        self.resizable(False, False)
        self.grab_set()

        ctk.CTkLabel(
            self, text="⌨️  Keyboard Shortcuts",
            font=ctk.CTkFont(size=15, weight="bold")
        ).pack(pady=(16, 4), padx=20, anchor="w")
        ctk.CTkLabel(
            self, text="Single-key shortcuts pause automatically while typing in text inputs.",
            font=ctk.CTkFont(size=11), text_color="gray"
        ).pack(padx=20, anchor="w", pady=(0, 8))

        frame = ctk.CTkScrollableFrame(self)
        frame.pack(fill="both", expand=True, padx=16, pady=4)
        for key, desc in DESKTOP_SHORTCUTS:
            row = ctk.CTkFrame(frame, fg_color="transparent")
            row.pack(fill="x", pady=3, padx=6)
            ctk.CTkLabel(row, text=desc, font=ctk.CTkFont(size=12), anchor="w").pack(side="left")
            ctk.CTkLabel(
                row, text=f"  {key}  ", font=ctk.CTkFont(size=11, weight="bold"),
                fg_color=("gray82", "gray28"), corner_radius=5
            ).pack(side="right")

        ctk.CTkButton(self, text="Close", width=100, command=self.destroy).pack(pady=12)
        self.bind("<Escape>", lambda _: self.destroy())
        _center_on_parent(self, parent)


# ---------------------------------------------------------------------------
# Command Palette Dialog (Ctrl+K)
# ---------------------------------------------------------------------------

class CommandPaletteDialog(ctk.CTkToplevel):
    """Quick command palette searching pages, actions, and recent items."""

    def __init__(self, parent, items: list[tuple[str, str, Callable]]):
        super().__init__(parent)
        self._items = items
        self._filtered: list[tuple[str, str, Callable]] = list(items)
        self.title("Command Palette")
        self.geometry("500x400")
        self.resizable(False, False)
        self.grab_set()

        self._query_var = ctk.StringVar()
        self._entry = ctk.CTkEntry(
            self,
            textvariable=self._query_var,
            placeholder_text="Search pages, actions, settings…",
            height=38,
            font=ctk.CTkFont(size=13),
        )
        self._entry.pack(fill="x", padx=16, pady=(16, 8))
        self._entry.bind("<KeyRelease>", lambda _: self._render_results())
        self._entry.bind("<Return>", lambda _: self._run_first())

        self._results = ctk.CTkScrollableFrame(self)
        self._results.pack(fill="both", expand=True, padx=16, pady=(0, 14))

        self.bind("<Escape>", lambda _: self.destroy())
        self._render_results()
        _center_on_parent(self, parent)
        self.after(30, self._entry.focus_set)

    def _render_results(self) -> None:
        for w in self._results.winfo_children():
            w.destroy()
        q = self._query_var.get().strip().lower()
        self._filtered = [
            it for it in self._items
            if not q or q in it[0].lower() or q in it[1].lower()
        ]
        if not self._filtered:
            ctk.CTkLabel(
                self._results,
                text="No matching pages or actions found.",
                text_color="gray",
                font=ctk.CTkFont(size=12),
            ).pack(pady=30)
            return
        for title, cat, cb in self._filtered[:25]:
            btn = ctk.CTkButton(
                self._results,
                text=f"[{cat}]  {title}",
                anchor="w",
                height=34,
                fg_color=("gray88", "gray24"),
                hover_color=("gray78", "gray32"),
                text_color=("black", "white"),
                command=lambda fn=cb: self._trigger(fn),
            )
            btn.pack(fill="x", pady=2)

    def _run_first(self) -> None:
        if self._filtered:
            self._trigger(self._filtered[0][2])

    def _trigger(self, cb: Callable) -> None:
        self.destroy()
        cb()
