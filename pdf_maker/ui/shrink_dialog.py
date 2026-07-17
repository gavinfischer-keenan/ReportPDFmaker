"""
Shrink PDF Dialog
=================
Standalone dialog — no dependency on the main document queue.
Opens a PDF, lets the user choose a compression level, and compresses it.
"""

from __future__ import annotations

import os
import threading
from pathlib import Path
from tkinter import filedialog
from typing import Optional

import customtkinter as ctk

from ..converters.pdf_compressor import (
    COMPRESSION_LEVELS,
    CompressionResult,
    compress_pdf,
    suggest_output_path,
)


# Ordered list so the UI always shows levels in the same sequence
_LEVEL_ORDER = ["light", "standard", "aggressive", "grayscale"]

# Visual accent colours
_COLOUR_NORMAL      = "#4a9eff"   # blue
_COLOUR_DESTRUCTIVE = "#e74c3c"   # red
_COLOUR_SUCCESS     = "#2ecc71"   # green
_COLOUR_WARNING     = "#f39c12"   # amber


class ShrinkPDFDialog(ctk.CTkToplevel):
    """
    Modal dialog for compressing an existing PDF.

    Usage
    -----
    ShrinkPDFDialog(parent)   # opens immediately
    """

    def __init__(self, parent: ctk.CTk) -> None:
        super().__init__(parent)
        self.title("Shrink a PDF")
        self.resizable(False, False)
        self.grab_set()             # modal
        self.focus_set()

        # State
        self._input_path:  Optional[str] = None
        self._output_path: Optional[str] = None
        self._busy = False
        self._level_var = ctk.StringVar(value="standard")

        self._build_ui()
        self._center_on_parent(parent)

        # Bind Enter / Escape
        self.bind("<Return>", lambda _: self._start_compress())
        self.bind("<Escape>", lambda _: self.destroy())

    # ------------------------------------------------------------------ #
    # UI construction                                                      #
    # ------------------------------------------------------------------ #

    def _build_ui(self) -> None:
        PAD = 16
        self.configure(fg_color=("#f0f0f0", "#1e1e2e"))

        # ── Title bar ──────────────────────────────────────────────── #
        title_bar = ctk.CTkFrame(self, fg_color=("#4a9eff", "#4a9eff"), corner_radius=0)
        title_bar.pack(fill="x")
        ctk.CTkLabel(
            title_bar,
            text="📉  Shrink a PDF",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="white",
        ).pack(pady=12, padx=PAD)

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=PAD, pady=(PAD, 0))

        # ── Input file ─────────────────────────────────────────────── #
        ctk.CTkLabel(body, text="Input PDF", font=ctk.CTkFont(weight="bold"),
                     anchor="w").pack(fill="x")

        row_in = ctk.CTkFrame(body, fg_color="transparent")
        row_in.pack(fill="x", pady=(4, 10))

        self._input_label = ctk.CTkLabel(
            row_in,
            text="No file selected",
            anchor="w",
            font=ctk.CTkFont(size=12),
            text_color=("#888888", "#888888"),
        )
        self._input_label.pack(side="left", fill="x", expand=True, padx=(0, 8))

        ctk.CTkButton(
            row_in, text="Browse…", width=90,
            command=self._browse_input,
        ).pack(side="right")

        # ── Compression level ──────────────────────────────────────── #
        ctk.CTkLabel(body, text="Compression Level",
                     font=ctk.CTkFont(weight="bold"), anchor="w").pack(fill="x")

        level_frame = ctk.CTkFrame(body, fg_color=("#e8e8e8", "#2a2a3e"),
                                   corner_radius=8)
        level_frame.pack(fill="x", pady=(4, 10))

        self._description_labels: dict[str, ctk.CTkLabel] = {}
        self._warning_labels:     dict[str, ctk.CTkLabel] = {}

        for level_id in _LEVEL_ORDER:
            cfg   = COMPRESSION_LEVELS[level_id]
            is_d  = cfg["destructive"]
            color = _COLOUR_DESTRUCTIVE if is_d else _COLOUR_NORMAL

            row = ctk.CTkFrame(level_frame, fg_color="transparent")
            row.pack(fill="x", padx=12, pady=(8, 0))

            rb = ctk.CTkRadioButton(
                row,
                text=cfg["label"],
                variable=self._level_var,
                value=level_id,
                font=ctk.CTkFont(size=13, weight="bold"),
                fg_color=color,
                hover_color=color,
                command=self._on_level_change,
            )
            rb.pack(anchor="w")

            desc = ctk.CTkLabel(
                row,
                text=cfg["description"],
                font=ctk.CTkFont(size=11),
                anchor="w",
                wraplength=440,
                justify="left",
            )
            desc.pack(anchor="w", padx=20)

            if cfg.get("warning"):
                warn = ctk.CTkLabel(
                    row,
                    text=cfg["warning"],
                    font=ctk.CTkFont(size=11),
                    anchor="w",
                    wraplength=440,
                    justify="left",
                    text_color=_COLOUR_WARNING if not cfg["grayscale"] else _COLOUR_DESTRUCTIVE,
                )
                warn.pack(anchor="w", padx=20)
                self._warning_labels[level_id] = warn

            self._description_labels[level_id] = desc

        # Spacer at bottom of radio group
        ctk.CTkFrame(level_frame, fg_color="transparent", height=8).pack()

        # ── Output file ────────────────────────────────────────────── #
        ctk.CTkLabel(body, text="Output PDF", font=ctk.CTkFont(weight="bold"),
                     anchor="w").pack(fill="x")

        row_out = ctk.CTkFrame(body, fg_color="transparent")
        row_out.pack(fill="x", pady=(4, 10))

        self._output_label = ctk.CTkLabel(
            row_out,
            text="Auto (alongside original)",
            anchor="w",
            font=ctk.CTkFont(size=12),
            text_color=("#888888", "#888888"),
        )
        self._output_label.pack(side="left", fill="x", expand=True, padx=(0, 8))

        ctk.CTkButton(
            row_out, text="Change…", width=90,
            command=self._browse_output,
        ).pack(side="right")

        # ── Status / progress ──────────────────────────────────────── #
        self._status_frame = ctk.CTkFrame(body, fg_color="transparent")
        self._status_frame.pack(fill="x", pady=(0, 4))

        self._progress_bar = ctk.CTkProgressBar(
            self._status_frame, height=10, progress_color=_COLOUR_NORMAL,
        )
        self._progress_bar.set(0)
        # Hidden until compression starts

        self._status_label = ctk.CTkLabel(
            self._status_frame,
            text="",
            font=ctk.CTkFont(size=12),
            anchor="w",
        )
        self._status_label.pack(fill="x")

        # ── Result panel ──────────────────────────────────────────── #
        self._result_frame = ctk.CTkFrame(
            body, fg_color=("#d4edda", "#1a3a2a"), corner_radius=8,
        )
        # Hidden until done

        self._result_label = ctk.CTkLabel(
            self._result_frame,
            text="",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=_COLOUR_SUCCESS,
        )
        self._result_label.pack(pady=10, padx=16)

        # ── Buttons ────────────────────────────────────────────────── #
        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", padx=PAD, pady=PAD)

        self._cancel_btn = ctk.CTkButton(
            btn_row, text="Close", width=100,
            fg_color=("#cccccc", "#444444"),
            text_color=("#333333", "#dddddd"),
            hover_color=("#bbbbbb", "#555555"),
            command=self.destroy,
        )
        self._cancel_btn.pack(side="right", padx=(8, 0))

        self._compress_btn = ctk.CTkButton(
            btn_row, text="📉  Shrink", width=120,
            fg_color=_COLOUR_NORMAL,
            hover_color="#3a8eef",
            font=ctk.CTkFont(weight="bold"),
            command=self._start_compress,
        )
        self._compress_btn.pack(side="right")

    # ------------------------------------------------------------------ #
    # Level change                                                         #
    # ------------------------------------------------------------------ #

    def _on_level_change(self) -> None:
        """Update button colour to reflect destructive state."""
        level_id = self._level_var.get()
        cfg = COMPRESSION_LEVELS.get(level_id, {})
        if cfg.get("destructive"):
            self._compress_btn.configure(
                fg_color=_COLOUR_DESTRUCTIVE, hover_color="#c0392b",
            )
        else:
            self._compress_btn.configure(
                fg_color=_COLOUR_NORMAL, hover_color="#3a8eef",
            )

    # ------------------------------------------------------------------ #
    # File browsing                                                        #
    # ------------------------------------------------------------------ #

    def _browse_input(self) -> None:
        path = filedialog.askopenfilename(
            title="Select PDF to Shrink",
            filetypes=[("PDF Files", "*.pdf"), ("All Files", "*.*")],
            parent=self,
        )
        if not path:
            return
        self._input_path = path
        fname = Path(path).name
        self._input_label.configure(
            text=f"{fname}  ({self._file_size_label(path)})",
            text_color=("#111111", "#dddddd"),
        )
        # Auto-fill output path
        if not self._output_path:
            suggested = suggest_output_path(path)
            self._output_path = suggested
            self._output_label.configure(
                text=Path(suggested).name,
                text_color=("#111111", "#dddddd"),
            )
        self._hide_result()

    def _browse_output(self) -> None:
        initial_dir  = str(Path(self._input_path).parent) if self._input_path else str(Path.home())
        initial_file = Path(self._output_path).name if self._output_path else "compressed.pdf"
        path = filedialog.asksaveasfilename(
            title="Save Compressed PDF As",
            initialdir=initial_dir,
            initialfile=initial_file,
            defaultextension=".pdf",
            filetypes=[("PDF Files", "*.pdf"), ("All Files", "*.*")],
            parent=self,
        )
        if not path:
            return
        self._output_path = path
        self._output_label.configure(
            text=Path(path).name,
            text_color=("#111111", "#dddddd"),
        )

    # ------------------------------------------------------------------ #
    # Compression                                                          #
    # ------------------------------------------------------------------ #

    def _start_compress(self) -> None:
        if self._busy:
            return
        if not self._input_path:
            self._set_status("⚠️  Please select a PDF first.", error=True)
            return
        if not self._output_path:
            self._output_path = suggest_output_path(self._input_path)

        self._busy = True
        self._compress_btn.configure(state="disabled", text="Working…")
        self._cancel_btn.configure(state="disabled")
        self._hide_result()
        self._show_progress(True)
        self._progress_bar.set(0)
        self._set_status("Starting…")

        level_id = self._level_var.get()
        inp      = self._input_path
        out      = self._output_path

        def _worker():
            result = compress_pdf(
                inp, out, level_id,
                progress_cb=lambda msg, frac: self.after(
                    0, lambda m=msg, f=frac: self._on_progress(m, f)
                ),
            )
            self.after(0, lambda: self._on_done(result))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_progress(self, message: str, fraction: float) -> None:
        if not self.winfo_exists():
            return
        self._progress_bar.set(fraction)
        # Interpolate colour: blue → green
        r = int(74  + (46  - 74)  * fraction)
        g = int(158 + (204 - 158) * fraction)
        b = int(255 + (113 - 255) * fraction)
        self._progress_bar.configure(progress_color=f"#{r:02x}{g:02x}{b:02x}")
        self._set_status(message)

    def _on_done(self, result: CompressionResult) -> None:
        if not self.winfo_exists():
            return
        self._busy = False
        self._compress_btn.configure(state="normal", text="📉  Shrink")
        self._cancel_btn.configure(state="normal", text="Close")
        self._show_progress(False)

        if result.success:
            saved_str = (
                f"{result.savings_pct:+.1f}%"
                if result.savings_pct != 0 else "±0%"
            )
            msg = (
                f"✅  {result.input_label}  →  {result.output_label}  "
                f"({saved_str}  saved)"
            )
            if result.savings_pct < 0:
                msg = (
                    f"⚠️  File grew slightly ({result.output_label}). "
                    "Original PDF may already be optimised."
                )
            self._show_result(msg, success=result.savings_pct >= 0)
            self._set_status(f"Saved to: {self._output_path}")
        else:
            self._set_status(f"❌  Error: {result.error}", error=True)
            self._on_level_change()  # restore button colour

    # ------------------------------------------------------------------ #
    # UI helpers                                                           #
    # ------------------------------------------------------------------ #

    def _set_status(self, text: str, error: bool = False) -> None:
        colour = _COLOUR_DESTRUCTIVE if error else ("#555555", "#aaaaaa")
        self._status_label.configure(text=text, text_color=colour)

    def _show_progress(self, visible: bool) -> None:
        if visible:
            self._progress_bar.pack(fill="x", pady=(0, 4))
        else:
            self._progress_bar.pack_forget()

    def _show_result(self, text: str, success: bool = True) -> None:
        colour = _COLOUR_SUCCESS if success else _COLOUR_WARNING
        self._result_label.configure(text=text, text_color=colour)
        self._result_frame.pack(fill="x", pady=(4, 0))

    def _hide_result(self) -> None:
        self._result_frame.pack_forget()
        self._set_status("")

    def _file_size_label(self, path: str) -> str:
        try:
            n = os.path.getsize(path)
            if n >= 1_048_576:
                return f"{n / 1_048_576:.2f} MB"
            if n >= 1024:
                return f"{n / 1024:.1f} KB"
            return f"{n} B"
        except Exception:
            return "?"

    def _center_on_parent(self, parent: ctk.CTk) -> None:
        self.update_idletasks()
        w, h   = 500, self.winfo_reqheight()
        px, py = parent.winfo_x(), parent.winfo_y()
        pw, ph = parent.winfo_width(), parent.winfo_height()
        x = px + (pw - w) // 2
        y = py + (ph - h) // 2
        self.geometry(f"{w}x{max(h, 620)}+{x}+{y}")
