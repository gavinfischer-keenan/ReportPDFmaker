"""
PDF Builder
===========
Assembles all PageItems into a final output PDF using PyMuPDF.

Key behaviours
--------------
* IMAGE pages are re-rendered from the original source file at save time so
  that image_rotation, page_landscape, image_scale, and image_offset are all
  honoured at full quality.  The temp PDF is only a fallback.
* Non-image pages use fitz page.set_rotation() for orientation.
* Page numbers are inserted after all pages are assembled.
"""

import io
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import fitz  # PyMuPDF
from PIL import Image, ImageOps

# ---------------------------------------------------------------------------
# Page dimensions (points, 1pt = 1/72 inch)
# ---------------------------------------------------------------------------
A4_PORTRAIT   = (595.28, 841.89)
A4_LANDSCAPE  = (841.89, 595.28)
LTR_PORTRAIT  = (612.0,  792.0)
LTR_LANDSCAPE = (792.0,  612.0)


def _page_dims(landscape: bool, page_size: str = "A4") -> tuple[float, float]:
    if page_size == "Letter":
        return LTR_LANDSCAPE if landscape else LTR_PORTRAIT
    return A4_LANDSCAPE if landscape else A4_PORTRAIT


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class PageItem:
    """Represents one page in the assembled output document."""

    id: str                              # Unique ID
    source_file: str                     # Original source file path
    source_type: str                     # 'image'|'text'|'word'|'pdf'|'3d'|'unknown'
    converted_pdf: str                   # Path to single-page temp PDF (fallback)

    # Page-level settings
    rotation: int = 0                    # For non-image pages: whole-page rotation
    page_landscape: bool = False         # Portrait vs Landscape orientation

    # Image-specific settings (only used when source_type == 'image')
    image_rotation: int = 0             # Rotates the image content only (not the page)
    image_scale: float = 1.0            # 1.0=fill page edge-to-edge; >1 clips at edge
    image_offset_x: float = 0.0        # Horizontal offset from centre (points)
    image_offset_y: float = 0.0        # Vertical offset from centre (points)

    display_name: str = ""
    warnings: list[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.display_name:
            self.display_name = Path(self.source_file).name

    @property
    def is_image(self) -> bool:
        return self.source_type in ("image", "3d")


# ---------------------------------------------------------------------------
# Image page rendering (shared by preview and final PDF build)
# ---------------------------------------------------------------------------

def _load_source_image(page_item: PageItem) -> Optional[Image.Image]:
    """Open, EXIF-correct, and convert the source image to RGB."""
    try:
        img = Image.open(page_item.source_file)
        img = ImageOps.exif_transpose(img)
        if img.mode not in ("RGB",):
            img = img.convert("RGB")
        return img
    except Exception as e:
        print(f"[PDFBuilder] Cannot load image {page_item.source_file}: {e}")
        return None


def _render_image_to_pil(
    page_item: PageItem,
    pw_px: int,
    ph_px: int,
    zoom: float = 1.0,
) -> Image.Image:
    """
    Compose an image page as a PIL image of size (pw_px, ph_px).

    The image is:
      1. Rotated by image_rotation (90/180/270 CW)
      2. Scaled to fill the page (no margin) then multiplied by image_scale
      3. Clipped hard at the page edges — no buffer
      4. Offset by image_offset_x / image_offset_y
    """
    page_img = Image.new("RGB", (pw_px, ph_px), (255, 255, 255))

    src = _load_source_image(page_item)
    if src is None:
        return page_img

    # Apply image rotation (PIL rotates CCW, so negate for CW)
    if page_item.image_rotation:
        src = src.rotate(-page_item.image_rotation, expand=True)

    img_w, img_h = src.size
    if img_w == 0 or img_h == 0:
        return page_img

    # Scale to fill page edge-to-edge (no margin) then apply user scale
    fit_scale = min(pw_px / img_w, ph_px / img_h)
    final_scale = fit_scale * page_item.image_scale

    scaled_w = max(1, int(img_w * final_scale))
    scaled_h = max(1, int(img_h * final_scale))

    src_scaled = src.resize((scaled_w, scaled_h), Image.LANCZOS)

    # Centre + user offset (offset is in pts, convert to px using zoom)
    cx = pw_px // 2 + int(page_item.image_offset_x * zoom)
    cy = ph_px // 2 + int(page_item.image_offset_y * zoom)

    x = cx - scaled_w // 2
    y = cy - scaled_h // 2

    # Clip to page — no buffer on any edge
    paste_x = max(0, x)
    paste_y = max(0, y)
    crop_x1 = max(0, -x)
    crop_y1 = max(0, -y)
    crop_x2 = min(scaled_w, pw_px - x)
    crop_y2 = min(scaled_h, ph_px - y)

    if crop_x2 > crop_x1 and crop_y2 > crop_y1:
        cropped = src_scaled.crop((crop_x1, crop_y1, crop_x2, crop_y2))
        page_img.paste(cropped, (paste_x, paste_y))

    return page_img


def get_image_canvas_bounds(
    page_item: PageItem,
    canvas_w: int,
    canvas_h: int,
    zoom: float = 1.0,
    page_size: str = "A4",
) -> Optional[tuple[int, int, int, int]]:
    """
    Return (cx, cy, img_w_px, img_h_px) for the image within the canvas.

    cx, cy  — canvas pixel coords of the image centre
    img_w/h — pixel dimensions of the (possibly clipped) image as displayed

    Used by the preview panel to position resize handles.
    Returns None if not an image page.
    """
    if not page_item.is_image:
        return None

    try:
        src = _load_source_image(page_item)
        if src is None:
            return None
        if page_item.image_rotation:
            src = src.rotate(-page_item.image_rotation, expand=True)
        img_w, img_h = src.size
    except Exception:
        return None

    pw_pt, ph_pt = _page_dims(page_item.page_landscape, page_size)
    pw_px = int(pw_pt * zoom)
    ph_px = int(ph_pt * zoom)

    fit_scale = min(pw_px / img_w, ph_px / img_h)
    final_scale = fit_scale * page_item.image_scale

    scaled_w = max(1, int(img_w * final_scale))
    scaled_h = max(1, int(img_h * final_scale))

    # Centre of the page on the canvas (page is centred)
    page_canvas_x = max(canvas_w // 2, pw_px // 2 + 10)
    page_canvas_y = max(canvas_h // 2, ph_px // 2 + 10)

    # Image centre within the page (in canvas coords)
    img_cx = page_canvas_x + int(page_item.image_offset_x * zoom)
    img_cy = page_canvas_y + int(page_item.image_offset_y * zoom)

    # Clamp to displayed width (image may be clipped)
    displayed_w = min(scaled_w, pw_px)
    displayed_h = min(scaled_h, ph_px)

    return (img_cx, img_cy, displayed_w, displayed_h)


# ---------------------------------------------------------------------------
# Page-number insertion
# ---------------------------------------------------------------------------

FONT_MAP = {
    "Helvetica":      "helv",
    "Helvetica-Bold": "hebo",
    "Times-Roman":    "tiro",
    "Times-Bold":     "tibo",
    "Courier":        "cour",
    "Courier-Bold":   "cobo",
}


def _format_page_number(page_num: int, total: int, style: str) -> str:
    if style == "dashes":
        return f"\u2014 {page_num} \u2014"
    elif style == "page_x":
        return f"Page {page_num}"
    elif style == "page_x_of_y":
        return f"Page {page_num} of {total}"
    return str(page_num)


def _hex_to_fitz_color(hex_color: str) -> tuple[float, float, float]:
    h = hex_color.lstrip("#")
    return int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0


def _insert_page_number(page: fitz.Page, page_num: int, total: int, s: dict) -> None:
    fitz_font = FONT_MAP.get(s.get("font", "Helvetica"), "helv")
    font_size = float(s.get("font_size", 10))
    color     = _hex_to_fitz_color(s.get("color", "#000000"))
    text      = _format_page_number(page_num, total, s.get("style", "plain"))
    pw, ph    = page.rect.width, page.rect.height
    text_w    = len(text) * font_size * 0.55

    y = ph - float(s.get("offset_from_edge", 20)) if s.get("position", "bottom") == "bottom" \
        else float(s.get("offset_from_edge", 20)) + font_size

    align = s.get("alignment", "center")
    if align == "left":
        x = float(s.get("offset_from_side", 50))
    elif align == "right":
        x = pw - float(s.get("offset_from_side", 50)) - text_w
    else:
        x = (pw - text_w) / 2

    try:
        page.insert_text((max(0.0, x), y), text,
                         fontname=fitz_font, fontsize=font_size, color=color)
    except Exception as e:
        print(f"[PDFBuilder] Page number error on p{page_num}: {e}")


# ---------------------------------------------------------------------------
# Build final PDF
# ---------------------------------------------------------------------------

def _add_image_page(item: PageItem, out_doc: fitz.Document, page_size: str = "A4") -> None:
    """Render an image PageItem and append it to out_doc at full quality."""
    pw_pt, ph_pt = _page_dims(item.page_landscape, page_size)

    # Render at 2× for good print quality
    SCALE = 2.0
    pil_img = _render_image_to_pil(item, int(pw_pt * SCALE), int(ph_pt * SCALE), zoom=SCALE)

    out_page = out_doc.new_page(width=pw_pt, height=ph_pt)
    buf = io.BytesIO()
    pil_img.save(buf, format="JPEG", quality=95)
    out_page.insert_image(fitz.Rect(0, 0, pw_pt, ph_pt), stream=buf.getvalue())


def build_pdf(
    pages: list[PageItem],
    output_path: str,
    page_number_settings: Optional[dict] = None,
    progress_callback=None,
    page_size: str = "A4",
) -> tuple[bool, str]:
    if not pages:
        return False, "No pages to assemble."

    out_doc = fitz.open()
    total = len(pages)

    for i, item in enumerate(pages):
        if progress_callback:
            progress_callback(i, total, f"Processing page {i + 1} of {total}…")
        try:
            if item.is_image:
                _add_image_page(item, out_doc, page_size)
            else:
                src = fitz.open(item.converted_pdf)
                if len(src) == 0:
                    src.close()
                    raise ValueError("Empty converted PDF")
                out_doc.insert_pdf(src, from_page=0, to_page=0)
                src.close()
                if item.rotation:
                    out_doc[-1].set_rotation(item.rotation)
        except Exception as e:
            print(f"[PDFBuilder] Page {i + 1} error: {e}")
            ep = out_doc.new_page()
            ep.insert_text((50, 100),
                           f"Error: page {i + 1}\n{item.display_name}\n{e}",
                           fontsize=11, color=(0.8, 0.1, 0.1))

    if page_number_settings and page_number_settings.get("enabled", False):
        ft = len(out_doc)
        for i, pg in enumerate(out_doc):
            _insert_page_number(pg, i + 1, ft, page_number_settings)

    if progress_callback:
        progress_callback(total, total, "Saving PDF…")

    try:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        out_doc.save(output_path, garbage=4, deflate=True)
        out_doc.close()
        return True, ""
    except Exception as e:
        out_doc.close()
        return False, f"Failed to save PDF: {e}"


# ---------------------------------------------------------------------------
# Preview rendering
# ---------------------------------------------------------------------------

def render_page_preview(
    page_item: PageItem,
    zoom: float = 1.0,
    page_size: str = "A4",
) -> Optional[bytes]:
    """
    Render a PageItem to PNG bytes for the preview panel.

    Image pages are rendered live from the source file so that
    image_rotation, image_scale, and image_offset are reflected immediately
    without needing to rebuild the temp PDF.
    """
    try:
        if page_item.is_image:
            pw_pt, ph_pt = _page_dims(page_item.page_landscape, page_size)
            pil_img = _render_image_to_pil(
                page_item,
                int(pw_pt * zoom),
                int(ph_pt * zoom),
                zoom=zoom,
            )
            buf = io.BytesIO()
            pil_img.save(buf, format="PNG")
            return buf.getvalue()
        else:
            doc  = fitz.open(page_item.converted_pdf)
            page = doc[0]
            mat  = fitz.Matrix(zoom, zoom).prerotate(page_item.rotation)
            pix  = page.get_pixmap(matrix=mat, alpha=False)
            png  = pix.tobytes("png")
            doc.close()
            return png
    except Exception as e:
        print(f"[PDFBuilder] Preview render failed: {e}")
        return None
