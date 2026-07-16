"""
PDF Builder
===========
Assembles all PageItems into a final output PDF using PyMuPDF.

Features:
  - Applies per-page rotation
  - Optionally inserts page numbers with full customization
    (position, alignment, font, size, color, style, offsets)
  - Saves to the user-chosen output path
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, TYPE_CHECKING

import fitz  # PyMuPDF

if TYPE_CHECKING:
    pass

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class PageItem:
    """Represents one page in the assembled output document."""

    id: str                          # Unique ID (e.g. uuid)
    source_file: str                 # Original source file path
    source_type: str                 # 'image' | 'text' | 'word' | 'pdf' | '3d' | 'unknown'
    converted_pdf: str               # Path to single-page temp PDF
    rotation: int = 0                # 0 | 90 | 180 | 270
    display_name: str = ""           # User-visible label
    warnings: list[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.display_name:
            self.display_name = Path(self.source_file).name


# ---------------------------------------------------------------------------
# Page-number insertion
# ---------------------------------------------------------------------------

# Map our font name strings to PyMuPDF base-14 font names
FONT_MAP = {
    "Helvetica":      "helv",
    "Helvetica-Bold": "hebo",
    "Times-Roman":    "tiro",
    "Times-Bold":     "tibo",
    "Courier":        "cour",
    "Courier-Bold":   "cobo",
}


def _format_page_number(page_num: int, total: int, style: str) -> str:
    """Format a page number string according to the chosen style."""
    if style == "dashes":
        return f"\u2014 {page_num} \u2014"
    elif style == "page_x":
        return f"Page {page_num}"
    elif style == "page_x_of_y":
        return f"Page {page_num} of {total}"
    else:  # "plain"
        return str(page_num)


def _hex_to_fitz_color(hex_color: str) -> tuple[float, float, float]:
    """Convert #rrggbb to a fitz RGB tuple (0.0-1.0 per channel)."""
    h = hex_color.lstrip("#")
    return (
        int(h[0:2], 16) / 255.0,
        int(h[2:4], 16) / 255.0,
        int(h[4:6], 16) / 255.0,
    )


def _insert_page_number(
    page: fitz.Page,
    page_num: int,
    total_pages: int,
    settings: dict,
) -> None:
    """Insert a page number onto a fitz Page according to user settings."""
    position     = settings.get("position", "bottom")       # "top" | "bottom"
    alignment    = settings.get("alignment", "center")      # "left" | "center" | "right"
    font_name    = settings.get("font", "Helvetica")
    font_size    = float(settings.get("font_size", 10))
    edge_offset  = float(settings.get("offset_from_edge", 20))
    side_offset  = float(settings.get("offset_from_side", 50))
    style        = settings.get("style", "plain")
    color_hex    = settings.get("color", "#000000")

    fitz_font = FONT_MAP.get(font_name, "helv")
    color     = _hex_to_fitz_color(color_hex)
    text      = _format_page_number(page_num, total_pages, style)

    pw = page.rect.width
    ph = page.rect.height

    # Approximate text width for alignment calculation
    # Fitz doesn't easily give us text width without rendering, so we estimate:
    # average char width ≈ font_size * 0.55 for Helvetica
    text_width_est = len(text) * font_size * 0.55

    # Y coordinate
    if position == "top":
        y = edge_offset + font_size      # Baseline above top edge
    else:
        y = ph - edge_offset             # Baseline above bottom edge

    # X coordinate
    if alignment == "left":
        x = side_offset
    elif alignment == "right":
        x = pw - side_offset - text_width_est
    else:  # center
        x = (pw - text_width_est) / 2

    x = max(0.0, x)  # Clamp to page

    try:
        page.insert_text(
            (x, y),
            text,
            fontname=fitz_font,
            fontsize=font_size,
            color=color,
        )
    except Exception as e:
        print(f"[PDFBuilder] Page number insertion failed on page {page_num}: {e}")


# ---------------------------------------------------------------------------
# Main build function
# ---------------------------------------------------------------------------

def build_pdf(
    pages: list[PageItem],
    output_path: str,
    page_number_settings: Optional[dict] = None,
    progress_callback=None,
) -> tuple[bool, str]:
    """
    Assemble a list of PageItems into a single output PDF.

    Args:
        pages:                  Ordered list of PageItems to include.
        output_path:            File path for the saved PDF.
        page_number_settings:   Dict from SettingsManager.get_page_number_settings()
                                Pass None or {'enabled': False} to skip page numbers.
        progress_callback:      Optional callable(current: int, total: int, message: str)

    Returns:
        (success: bool, error_message: str)
    """
    if not pages:
        return False, "No pages to assemble."

    out_doc = fitz.open()
    total = len(pages)

    for i, item in enumerate(pages):
        if progress_callback:
            progress_callback(i, total, f"Processing page {i + 1} of {total}…")

        try:
            src_doc = fitz.open(item.converted_pdf)
            if len(src_doc) == 0:
                src_doc.close()
                raise ValueError("Converted PDF is empty")

            # Insert the page into output document
            out_doc.insert_pdf(src_doc, from_page=0, to_page=0)
            src_doc.close()

            # Apply rotation to the newly added last page
            dest_page = out_doc[-1]
            if item.rotation != 0:
                dest_page.set_rotation(item.rotation)

        except Exception as e:
            print(f"[PDFBuilder] Error adding page {i + 1} ({item.display_name}): {e}")
            # Add an error placeholder page
            err_page = out_doc.new_page()
            err_page.insert_text(
                (50, 100),
                f"Error loading page {i + 1}:\n{item.display_name}\n{e}",
                fontsize=11,
                color=(0.8, 0.1, 0.1),
            )

    # ------------------------------------------------------------------ #
    # Add page numbers (after all pages are assembled so we know total)
    # ------------------------------------------------------------------ #
    if page_number_settings and page_number_settings.get("enabled", False):
        final_total = len(out_doc)
        for i, page in enumerate(out_doc):
            _insert_page_number(page, i + 1, final_total, page_number_settings)

    # ------------------------------------------------------------------ #
    # Save
    # ------------------------------------------------------------------ #
    if progress_callback:
        progress_callback(total, total, "Saving PDF…")

    try:
        # Ensure output directory exists
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        out_doc.save(output_path, garbage=4, deflate=True)
        out_doc.close()
        return True, ""
    except Exception as e:
        out_doc.close()
        return False, f"Failed to save PDF: {e}"


def render_page_preview(
    page_item: PageItem,
    zoom: float = 1.0,
) -> Optional[bytes]:
    """
    Render a PageItem to a PNG byte string for display in the preview panel.
    Returns PNG bytes or None on error.
    """
    try:
        doc = fitz.open(page_item.converted_pdf)
        page = doc[0]

        # Build rotation matrix
        mat = fitz.Matrix(zoom, zoom).prerotate(page_item.rotation)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        png_bytes = pix.tobytes("png")
        doc.close()
        return png_bytes
    except Exception as e:
        print(f"[PDFBuilder] Preview render failed: {e}")
        return None
