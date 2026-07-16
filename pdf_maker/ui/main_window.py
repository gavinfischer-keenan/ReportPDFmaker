"""
Main Window
===========
The root CTk window that assembles all panels into the 3-column layout.
Also owns the toolbar, status bar, and bottom save/settings bar.

Layout:
  ┌─────────────────────────────────────────────────────┐
  │  TOOLBAR: Add | Remove | ↑ | ↓ | ──────── | Reset   │
  ├──────────────┬──────────────────────┬───────────────┤
  │ File List    │    Preview           │  Page Editor  │
  │ (240px)      │    (flex)            │  (220px)      │
  ├──────────────┴──────────────────────┴───────────────┤
  │  STATUS BAR                                          │
  ├──────────────────────────────────────────────────────┤
  │ [Page Nums: ◉/○] [⚙Settings]  Path: [...]  [💾 Save]│
  └──────────────────────────────────────────────────────┘
"""

import os
import threading
from pathlib import Path
from tkinter import filedialog
from typing import TYPE_CHECKING

import customtkinter as ctk

from ..controller import AppController, EVT_STATUS, EVT_WARNINGS, EVT_RESET
from ..settings_manager import SettingsManager
from ..utils.file_utils import get_dialog_filetypes
from .file_list_panel import FileListPanel
from .preview_panel import PreviewPanel
from .page_editor_panel import PageEditorPanel
from .dialogs import (
    WarningsDialog,
    PageNumberSettingsDialog,
    ResetConfirmDialog,
    AboutDialog,
    ProgressDialog,
)


class MainWindow(ctk.CTk):
    """Root application window."""

    def __init__(self, controller: AppController, settings: SettingsManager):
        super().__init__()
        self.controller = controller
        self.settings   = settings

        self._setup_window()
        self._build_ui()
        self._register_events()
        self._restore_window_state()

    # ------------------------------------------------------------------ #
    # Window setup
    # ------------------------------------------------------------------ #

    def _setup_window(self) -> None:
        self.title("PDF Maker")
        self.minsize(960, 620)
        w = self.settings.get("window_width",  1280)
        h = self.settings.get("window_height", 800)
        self.geometry(f"{w}x{h}")
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # App icon (cross-platform emoji fallback)
        try:
            self.iconbitmap()
        except Exception:
            pass

    def _restore_window_state(self) -> None:
        x = self.settings.get("window_x", -1)
        y = self.settings.get("window_y", -1)
        if x >= 0 and y >= 0:
            self.geometry(f"+{x}+{y}")
        else:
            self.update_idletasks()
            sw = self.winfo_screenwidth()
            sh = self.winfo_screenheight()
            ww = self.winfo_width()
            wh = self.winfo_height()
            self.geometry(f"+{(sw - ww) // 2}+{(sh - wh) // 2}")

    # ------------------------------------------------------------------ #
    # UI Construction
    # ------------------------------------------------------------------ #

    def _build_ui(self) -> None:
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # ── Toolbar ───────────────────────────────────────────────────
        self._toolbar = self._build_toolbar()
        self._toolbar.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 0))

        # ── Main 3-column area ────────────────────────────────────────
        main_area = ctk.CTkFrame(self, fg_color="transparent")
        main_area.grid(row=1, column=0, sticky="nsew", padx=8, pady=4)
        main_area.grid_rowconfigure(0, weight=1)
        main_area.grid_columnconfigure(1, weight=1)

        self._file_panel    = FileListPanel(main_area, self.controller)
        self._preview_panel = PreviewPanel(main_area, self.controller)
        self._editor_panel  = PageEditorPanel(main_area, self.controller)

        self._file_panel.grid(   row=0, column=0, sticky="nsew", padx=(0, 4))
        self._preview_panel.grid(row=0, column=1, sticky="nsew", padx=4)
        self._editor_panel.grid( row=0, column=2, sticky="nsew", padx=(4, 0))

        # Fixed widths for side panels
        self._file_panel.configure(  width=240)
        self._editor_panel.configure(width=240)

        # ── Status bar ────────────────────────────────────────────────
        self._status_bar = self._build_status_bar()
        self._status_bar.grid(row=2, column=0, sticky="ew", padx=8, pady=(0, 0))

        # ── Save bar ──────────────────────────────────────────────────
        self._save_bar = self._build_save_bar()
        self._save_bar.grid(row=3, column=0, sticky="ew", padx=8, pady=(0, 8))

    def _build_toolbar(self) -> ctk.CTkFrame:
        tb = ctk.CTkFrame(self, height=50, corner_radius=8)

        # App title
        ctk.CTkLabel(
            tb, text="📄 PDF Maker",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(side="left", padx=(14, 20))

        # Add Files
        ctk.CTkButton(
            tb, text="➕  Add Files", width=110, height=36,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=("#4a9eff", "#1a5fa8"),
            hover_color=("#3a8eef", "#144d8c"),
            command=self._add_files,
        ).pack(side="left", padx=4)

        # Remove selected
        ctk.CTkButton(
            tb, text="✕  Remove", width=90, height=36,
            font=ctk.CTkFont(size=12),
            fg_color=("#e74c3c", "#c0392b"),
            hover_color=("#c0392b", "#a93226"),
            command=self._remove_selected,
        ).pack(side="left", padx=4)

        # Move Up / Down
        ctk.CTkButton(
            tb, text="▲", width=38, height=36,
            font=ctk.CTkFont(size=14),
            fg_color=("gray80", "gray30"),
            hover_color=("gray70", "gray40"),
            text_color=("black", "white"),
            command=lambda: self.controller.move_page_up(self.controller.current_index),
        ).pack(side="left", padx=(4, 0))

        ctk.CTkButton(
            tb, text="▼", width=38, height=36,
            font=ctk.CTkFont(size=14),
            fg_color=("gray80", "gray30"),
            hover_color=("gray70", "gray40"),
            text_color=("black", "white"),
            command=lambda: self.controller.move_page_down(self.controller.current_index),
        ).pack(side="left", padx=(0, 16))

        # Right-side controls
        ctk.CTkButton(
            tb, text="ℹ  About", width=80, height=36,
            font=ctk.CTkFont(size=11),
            fg_color="transparent", border_width=1,
            command=lambda: AboutDialog(self),
        ).pack(side="right", padx=4)

        # Theme toggle
        self._theme_btn = ctk.CTkButton(
            tb, text="☀", width=38, height=36,
            font=ctk.CTkFont(size=16),
            fg_color="transparent", border_width=1,
            command=self._toggle_theme,
        )
        self._theme_btn.pack(side="right", padx=4)

        # Reset
        ctk.CTkButton(
            tb, text="🔄  Reset All", width=100, height=36,
            font=ctk.CTkFont(size=11),
            fg_color=("gray75", "gray25"),
            hover_color=("gray65", "gray20"),
            text_color=("black", "white"),
            command=self._confirm_reset,
        ).pack(side="right", padx=(16, 4))

        return tb

    def _build_status_bar(self) -> ctk.CTkFrame:
        bar = ctk.CTkFrame(self, height=36, corner_radius=6,
                           fg_color=("gray85", "gray20"))

        # Status text (left)
        self._status_label = ctk.CTkLabel(
            bar, text="Ready",
            font=ctk.CTkFont(size=11), text_color="gray", anchor="w"
        )
        self._status_label.pack(side="left", padx=12)

        # Import progress bar (hidden by default)
        self._import_bar_frame = ctk.CTkFrame(bar, fg_color="transparent")
        self._import_file_label = ctk.CTkLabel(
            self._import_bar_frame, text="",
            font=ctk.CTkFont(size=10), text_color="gray", width=200, anchor="w"
        )
        self._import_file_label.pack(side="left", padx=(0, 6))
        self._import_progress = ctk.CTkProgressBar(
            self._import_bar_frame, width=180, height=12, corner_radius=4
        )
        self._import_progress.pack(side="left")
        self._import_progress.set(0)
        # Don't pack the frame yet — only shown during import

        # Word status indicator (right)
        self._word_label = ctk.CTkLabel(
            bar, text="", font=ctk.CTkFont(size=11), anchor="e"
        )
        self._word_label.pack(side="right", padx=12)
        self.after(500, self._check_word_status)

        return bar

    def _build_save_bar(self) -> ctk.CTkFrame:
        bar = ctk.CTkFrame(self, height=54, corner_radius=8)

        # Page Numbers toggle
        self._pn_var = ctk.BooleanVar(value=self.settings.get("page_numbers"))
        pn_switch = ctk.CTkSwitch(
            bar, text="Page Numbers",
            variable=self._pn_var,
            font=ctk.CTkFont(size=12),
            command=self._on_page_numbers_toggle,
        )
        pn_switch.pack(side="left", padx=(14, 4))

        # Page number settings button
        ctk.CTkButton(
            bar, text="⚙", width=34, height=30,
            font=ctk.CTkFont(size=14),
            fg_color="transparent", border_width=1,
            command=self._open_pn_settings,
        ).pack(side="left", padx=(0, 16))

        # Save button
        ctk.CTkButton(
            bar, text="💾  Save PDF", width=120, height=38,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=("#2ecc71", "#1a7a43"),
            hover_color=("#27ae60", "#166337"),
            command=self._save_pdf,
        ).pack(side="right", padx=14)

        # Path display + browse
        ctk.CTkButton(
            bar, text="📁", width=34, height=30,
            font=ctk.CTkFont(size=14),
            fg_color="transparent", border_width=1,
            command=self._browse_output_folder,
        ).pack(side="right", padx=4)

        ctk.CTkButton(
            bar, text="🏠 Docs", width=68, height=30,
            font=ctk.CTkFont(size=11),
            fg_color="transparent", border_width=1,
            command=self._reset_to_documents,
        ).pack(side="right", padx=(0, 4))

        self._path_label = ctk.CTkLabel(
            bar, text=self._short_path(self.settings.output_folder),
            font=ctk.CTkFont(size=11), text_color="gray",
            anchor="e", wraplength=320,
        )
        self._path_label.pack(side="right", padx=4)

        ctk.CTkLabel(bar, text="Output:", font=ctk.CTkFont(size=11)).pack(
            side="right", padx=(16, 2)
        )

        return bar

    # ------------------------------------------------------------------ #
    # Event handling
    # ------------------------------------------------------------------ #

    def _register_events(self) -> None:
        # Wrap with after(0,...) so UI ops always run on the main thread,
        # even when the controller fires from a background worker thread.
        self.controller.on(EVT_STATUS,   lambda msg: self.after(0, lambda m=msg: self._set_status(m)))
        self.controller.on(EVT_WARNINGS, lambda w:   self.after(0, lambda ws=w: self._show_warnings(ws)))
        self.controller.on(EVT_RESET,    lambda _:   self.after(0, self._on_reset))

    def _set_status(self, msg: str) -> None:
        self._status_label.configure(text=msg)

    def _show_warnings(self, warnings: list) -> None:
        if warnings:
            WarningsDialog(self, warnings)

    def _on_reset(self) -> None:
        self._pn_var.set(False)
        self._path_label.configure(
            text=self._short_path(self.settings.output_folder)
        )

    # ------------------------------------------------------------------ #
    # Toolbar actions
    # ------------------------------------------------------------------ #

    def _add_files(self) -> None:
        files = filedialog.askopenfilenames(
            title="Select Files to Add",
            filetypes=get_dialog_filetypes(),
            parent=self,
        )
        if not files:
            return

        total = len(files)
        self._set_status(f"Importing {total} file{'s' if total > 1 else ''}…")
        self._show_import_progress(0, total, "")

        def _progress(current: int, ttl: int, fname: str) -> None:
            """Called from background thread — schedule on main thread."""
            self.after(0, lambda c=current, t=ttl, f=fname:
                       self._update_import_progress(c, t, f))

        self.controller.add_files(list(files), import_progress_callback=_progress)

    def _show_import_progress(self, current: int, total: int, fname: str) -> None:
        """Show the progress bar in the status bar, starting red."""
        self._import_progress.set(0)
        self._import_progress.configure(progress_color="#e74c3c")  # Start red
        self._import_file_label.configure(text="")
        self._import_bar_frame.pack(side="left", padx=(8, 0))

    def _update_import_progress(self, current: int, total: int, fname: str) -> None:
        """Update or hide the progress bar, interpolating red→blue as it fills."""
        if total <= 0 or current >= total:
            # Done — hide the bar
            self._import_bar_frame.pack_forget()
            return
        ratio = current / total
        self._import_progress.set(ratio)
        # Interpolate RGB: red #e74c3c → blue #4a9eff
        r = int(231 + (74  - 231) * ratio)
        g = int(76  + (158 - 76)  * ratio)
        b = int(60  + (255 - 60)  * ratio)
        self._import_progress.configure(progress_color=f"#{r:02x}{g:02x}{b:02x}")
        label = f"{current + 1}/{total}  {fname[:30]}{'…' if len(fname) > 30 else ''}"
        self._import_file_label.configure(text=label)


    def _remove_selected(self) -> None:
        idx = self.controller.current_index
        if idx >= 0:
            self.controller.remove_page(idx)


    def _toggle_theme(self) -> None:
        current = ctk.get_appearance_mode()
        new_mode = "Light" if current == "Dark" else "Dark"
        ctk.set_appearance_mode(new_mode)
        self._theme_btn.configure(text="☀" if new_mode == "Dark" else "🌙")
        self.settings.set("theme", new_mode.lower())

    def _confirm_reset(self) -> None:
        if self.settings.get("confirm_reset", True):
            ResetConfirmDialog(self, on_confirm=self.controller.reset)
        else:
            self.controller.reset()

    # ------------------------------------------------------------------ #
    # Save bar actions
    # ------------------------------------------------------------------ #

    def _on_page_numbers_toggle(self) -> None:
        self.settings.set("page_numbers", self._pn_var.get())
        # Re-render preview so user sees the overlay immediately
        self.after(0, self._preview_panel._schedule_render)

    def _open_pn_settings(self) -> None:
        def _on_apply():
            self._pn_var.set(self.settings.get("page_numbers"))
            # Re-render preview to reflect new settings
            self.after(0, self._preview_panel._schedule_render)
        PageNumberSettingsDialog(self, self.settings, on_apply=_on_apply)

    def _browse_output_folder(self) -> None:
        folder = filedialog.askdirectory(
            title="Select Output Folder",
            initialdir=self.settings.output_folder,
            parent=self,
        )
        if folder:
            self.settings.output_folder = folder
            self._path_label.configure(text=self._short_path(folder))

    def _reset_to_documents(self) -> None:
        docs = str(Path.home() / "Documents")
        self.settings.output_folder = docs
        self._path_label.configure(text=self._short_path(docs))

    def _save_pdf(self) -> None:
        if self.controller.page_count == 0:
            self._set_status("⚠️  No pages to save — add some files first.")
            return

        # Sync page numbers setting from switch
        self.settings.set("page_numbers", self._pn_var.get(), auto_save=False)

        default_name = self.settings.get("last_filename", "output.pdf")
        output_path = filedialog.asksaveasfilename(
            title="Save PDF As",
            initialdir=self.settings.output_folder,
            initialfile=default_name,
            defaultextension=".pdf",
            filetypes=[("PDF Files", "*.pdf"), ("All Files", "*.*")],
            parent=self,
        )
        if not output_path:
            return

        # Remember the folder and filename
        self.settings.set_many({
            "output_folder": str(Path(output_path).parent),
            "last_filename": Path(output_path).name,
        })
        self._path_label.configure(
            text=self._short_path(str(Path(output_path).parent))
        )

        # Show progress dialog
        progress_dlg = ProgressDialog(self, title="Building PDF…")

        def _progress(current, total, msg):
            self.after(0, lambda: progress_dlg.update_progress(current, total, msg))

        def _done(success, error, path):
            self.after(0, lambda: _handle_done(success, error, path))

        def _handle_done(success, error, path):
            progress_dlg.close()
            if success:
                self._set_status(f"✅  Saved: {Path(path).name}")
            else:
                self._set_status(f"❌  Save failed: {error}")
                WarningsDialog(self, [f"Save failed:\n{error}"])

        self.controller.save_pdf(output_path, _progress, _done)

    # ------------------------------------------------------------------ #
    # Word status check
    # ------------------------------------------------------------------ #

    def _check_word_status(self) -> None:
        def _check():
            from ..converters.docx_converter import detect_word
            available, msg = detect_word()
            color = "#2ecc71" if available else "#f39c12"
            text  = "Word: ✓" if available else "Word: ✕"
            tooltip = msg
            self.after(0, lambda: self._word_label.configure(
                text=text, text_color=color
            ))
        threading.Thread(target=_check, daemon=True).start()

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _short_path(path: str, max_len: int = 40) -> str:
        """Shorten a path for display."""
        if len(path) <= max_len:
            return path
        parts = Path(path).parts
        if len(parts) <= 2:
            return path
        return str(Path(parts[0]) / "…" / Path(*parts[-2:]))

    def _on_close(self) -> None:
        """Save window state and clean up before exit."""
        self.settings.set_many({
            "window_width":  self.winfo_width(),
            "window_height": self.winfo_height(),
            "window_x":      self.winfo_x(),
            "window_y":      self.winfo_y(),
        })
        self.controller.cleanup()
        self.destroy()
