"""
Dialogs
=======
All modal dialogs for PDF Maker:
  - WarningsDialog
  - PageNumberSettingsDialog
  - ResetConfirmDialog
  - AboutDialog
  - ProgressDialog
"""

import tkinter as tk
from tkinter import ttk
from pathlib import Path
from typing import Optional, Callable
import customtkinter as ctk

from ..settings_manager import SettingsManager, FONT_OPTIONS, PAGE_NUMBER_STYLES


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
    """Full customization dialog for page number formatting."""

    def __init__(self, parent, settings: SettingsManager, on_apply: Optional[Callable] = None):
        super().__init__(parent)
        self.settings = settings
        self.on_apply = on_apply
        self.title("Page Number Settings")
        self.geometry("480x560")
        self.resizable(False, False)
        self.grab_set()

        # Title
        ctk.CTkLabel(
            self, text="📑 Page Number Settings",
            font=ctk.CTkFont(size=15, weight="bold")
        ).pack(pady=(18, 2), padx=20, anchor="w")
        ctk.CTkLabel(
            self, text="Customise how page numbers appear in the output PDF.",
            font=ctk.CTkFont(size=11), text_color="gray"
        ).pack(padx=20, anchor="w", pady=(0, 12))

        form = ctk.CTkFrame(self, fg_color="transparent")
        form.pack(fill="both", expand=True, padx=20, pady=4)
        form.columnconfigure(1, weight=1)

        row = 0

        # Enabled toggle
        self._enabled_var = ctk.BooleanVar(value=settings.get("page_numbers"))
        self._add_row(form, row, "Enable page numbers:", ctk.CTkSwitch(
            form, variable=self._enabled_var, text=""
        ))
        row += 1

        # Position
        self._position_var = ctk.StringVar(value=settings.get("page_number_position"))
        self._add_row(form, row, "Position:", ctk.CTkSegmentedButton(
            form, values=["top", "bottom"], variable=self._position_var
        ))
        row += 1

        # Alignment
        self._align_var = ctk.StringVar(value=settings.get("page_number_alignment"))
        self._add_row(form, row, "Alignment:", ctk.CTkSegmentedButton(
            form, values=["left", "center", "right"], variable=self._align_var
        ))
        row += 1

        # Style
        style_opts = list(PAGE_NUMBER_STYLES.keys())
        style_labels = [f"{k}  →  {v}" for k, v in PAGE_NUMBER_STYLES.items()]
        self._style_var = ctk.StringVar(value=settings.get("page_number_style"))
        self._add_row(form, row, "Number style:", ctk.CTkOptionMenu(
            form, values=style_opts, variable=self._style_var
        ))
        row += 1

        # Font
        self._font_var = ctk.StringVar(value=settings.get("page_number_font"))
        self._add_row(form, row, "Font:", ctk.CTkOptionMenu(
            form, values=FONT_OPTIONS, variable=self._font_var
        ))
        row += 1

        # Font size
        self._font_size_var = ctk.IntVar(value=settings.get("page_number_font_size"))
        fs_frame = ctk.CTkFrame(form, fg_color="transparent")
        self._fs_slider = ctk.CTkSlider(fs_frame, from_=6, to=24, variable=self._font_size_var, width=160,
                                         command=lambda v: self._fs_label.configure(text=f"{int(v)} pt"))
        self._fs_label  = ctk.CTkLabel(fs_frame, text=f"{self._font_size_var.get()} pt", width=50)
        self._fs_slider.pack(side="left")
        self._fs_label.pack(side="left", padx=6)
        self._add_row(form, row, "Font size:", fs_frame)
        row += 1

        # Offset from edge
        self._edge_var = ctk.IntVar(value=settings.get("page_number_offset_from_edge"))
        edge_frame = ctk.CTkFrame(form, fg_color="transparent")
        self._edge_slider = ctk.CTkSlider(edge_frame, from_=5, to=80, variable=self._edge_var, width=160,
                                           command=lambda v: self._edge_label.configure(text=f"{int(v)} pt"))
        self._edge_label  = ctk.CTkLabel(edge_frame, text=f"{self._edge_var.get()} pt", width=50)
        self._edge_slider.pack(side="left")
        self._edge_label.pack(side="left", padx=6)
        self._add_row(form, row, "Offset from edge:", edge_frame)
        row += 1

        # Offset from side (for left/right alignment)
        self._side_var = ctk.IntVar(value=settings.get("page_number_offset_from_side"))
        side_frame = ctk.CTkFrame(form, fg_color="transparent")
        self._side_slider = ctk.CTkSlider(side_frame, from_=5, to=150, variable=self._side_var, width=160,
                                           command=lambda v: self._side_label.configure(text=f"{int(v)} pt"))
        self._side_label  = ctk.CTkLabel(side_frame, text=f"{self._side_var.get()} pt", width=50)
        self._side_slider.pack(side="left")
        self._side_label.pack(side="left", padx=6)
        self._add_row(form, row, "Offset from side:", side_frame)
        row += 1

        # Color
        self._color_var = ctk.StringVar(value=settings.get("page_number_color"))
        color_frame = ctk.CTkFrame(form, fg_color="transparent")
        self._color_entry = ctk.CTkEntry(color_frame, textvariable=self._color_var, width=100)
        self._color_entry.pack(side="left")
        ctk.CTkLabel(color_frame, text="  (hex, e.g. #000000)", text_color="gray",
                     font=ctk.CTkFont(size=11)).pack(side="left")
        self._add_row(form, row, "Color:", color_frame)
        row += 1

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=16)
        ctk.CTkButton(btn_frame, text="Apply", width=110, command=self._apply).pack(side="left", padx=8)
        ctk.CTkButton(btn_frame, text="Cancel", width=90,
                      fg_color="transparent", border_width=1, command=self.destroy).pack(side="left", padx=4)

        _center_on_parent(self, parent)

    def _add_row(self, parent, row: int, label: str, widget) -> None:
        ctk.CTkLabel(parent, text=label, anchor="e", width=170,
                     font=ctk.CTkFont(size=12)).grid(row=row, column=0, padx=(0, 12), pady=7, sticky="e")
        widget.grid(row=row, column=1, pady=7, sticky="w")

    def _apply(self) -> None:
        self.settings.set_many({
            "page_numbers":                   self._enabled_var.get(),
            "page_number_position":           self._position_var.get(),
            "page_number_alignment":          self._align_var.get(),
            "page_number_style":              self._style_var.get(),
            "page_number_font":               self._font_var.get(),
            "page_number_font_size":          int(self._font_size_var.get()),
            "page_number_offset_from_edge":   int(self._edge_var.get()),
            "page_number_offset_from_side":   int(self._side_var.get()),
            "page_number_color":              self._color_var.get(),
        })
        if self.on_apply:
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
        ctk.CTkLabel(self, text="Version 1.0.0", font=ctk.CTkFont(size=12), text_color="gray").pack()
        ctk.CTkLabel(
            self,
            text="Combine images, PDFs, Word documents, text files,\n"
                 "and 3D models into a single beautiful PDF.",
            justify="center", wraplength=300, font=ctk.CTkFont(size=12)
        ).pack(pady=14)
        ctk.CTkLabel(
            self, text="github.com/gavinfischer-keenan/ReportPDFmaker",
            text_color="#4a9eff", font=ctk.CTkFont(size=11)
        ).pack()
        ctk.CTkButton(self, text="Close", width=100, command=self.destroy).pack(pady=18)
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
