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

import pymupdf
from PIL import Image, ImageOps

# ---------------------------------------------------------------------------
# Page dimensions (points, 1pt = 1/72 inch)
# ---------------------------------------------------------------------------
A4_PORTRAIT   = (595.28, 841.89)
A4_LANDSCAPE  = (841.89, 595.28)
LTR_PORTRAIT  = (612.0,  792.0)
LTR_LANDSCAPE = (792.0,  612.0)

PAGE_SIZE_PRESETS: dict[str, tuple[float, float]] = {
    "A4":     (595.28, 841.89),
    "Letter": (612.0,  792.0),
    "Legal":  (612.0,  1008.0),
    "A3":     (841.89, 1190.55),
    "A5":     (419.53, 595.28),
}


def _page_dims(
    landscape: bool,
    page_size: str = "A4",
    image_dims: Optional[tuple[int, int]] = None,
) -> tuple[float, float]:
    if page_size == "Fit" and image_dims and image_dims[0] > 0 and image_dims[1] > 0:
        iw, ih = image_dims
        scale = 841.89 / max(iw, ih)
        return (max(72.0, round(iw * scale, 2)), max(72.0, round(ih * scale, 2)))
    base_w, base_h = PAGE_SIZE_PRESETS.get(page_size, A4_PORTRAIT)
    return (base_h, base_w) if landscape else (base_w, base_h)


def parse_page_range(spec: Optional[str], total_pages: int) -> list[int]:
    """
    Parse a 1-based page range string (e.g. '1-3, 5') into 0-based indices.
    Blank / 'all' returns all indices [0 .. total_pages - 1].
    """
    if total_pages <= 0:
        return []
    raw = str(spec or "").strip()
    if not raw or raw.lower() == "all":
        return list(range(total_pages))

    selected: list[int] = []
    seen: set[int] = set()
    for token in raw.split(","):
        part = token.strip()
        if not part:
            raise ValueError(f"Empty token in page range '{raw}'.")
        if "-" in part:
            pieces = [p.strip() for p in part.split("-")]
            if len(pieces) != 2 or not pieces[0].isdigit() or not pieces[1].isdigit():
                raise ValueError(f"Invalid range '{part}'.")
            start, end = int(pieces[0]), int(pieces[1])
            if start < 1 or end < 1 or start > total_pages or end > total_pages:
                raise ValueError(f"Range '{part}' out of bounds (1-{total_pages}).")
            step = 1 if start <= end else -1
            for num in range(start, end + step, step):
                idx = num - 1
                if idx not in seen:
                    seen.add(idx)
                    selected.append(idx)
        else:
            if not part.isdigit():
                raise ValueError(f"Invalid page number '{part}'.")
            num = int(part)
            if num < 1 or num > total_pages:
                raise ValueError(f"Page '{num}' out of bounds (1-{total_pages}).")
            idx = num - 1
            if idx not in seen:
                seen.add(idx)
                selected.append(idx)
    return selected


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

    # Image-specific settings (only used when source_type in ('image', '3d'))
    image_rotation: int = 0             # Rotates the image content only (not the page)
    image_scale: float = 1.0            # 1.0=fill page edge-to-edge; >1 clips at edge
    image_offset_x: float = 0.0        # Horizontal offset from centre (points)
    image_offset_y: float = 0.0        # Vertical offset from centre (points)
    image_crop: tuple[float, float, float, float] | None = None  # (left, top, right, bottom) as percentages 0.0-1.0
    image_frame_index: int = 0          # Frame index for multi-frame animated images (e.g. GIF)
    source_image_path: str = ""         # Optional raster image override (e.g. rendered 3D PNG)
    source_page_index: int = 0          # 0-based page/frame index within multi-page source
    is_blank: bool = False              # True for inserted blank / section divider pages

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

def _resolve_image_path(page_item: PageItem) -> Optional[str]:
    """Return the filesystem path of the raster image backing page_item."""
    if page_item.source_image_path and os.path.isfile(page_item.source_image_path):
        return page_item.source_image_path
    if page_item.source_type == "3d" and page_item.converted_pdf:
        sidecar = str(Path(page_item.converted_pdf).with_suffix(".png"))
        if os.path.isfile(sidecar):
            return sidecar
    return page_item.source_file or None


def _load_source_image(page_item: PageItem) -> Optional[Image.Image]:
    """Open, seek frame, EXIF-correct, and composite onto white RGB."""
    img_path = _resolve_image_path(page_item)
    if not img_path or not os.path.isfile(img_path):
        return None
    try:
        with Image.open(img_path) as raw:
            if page_item.image_frame_index > 0:
                try:
                    raw.seek(page_item.image_frame_index)
                except EOFError:
                    raw.seek(0)
            img = ImageOps.exif_transpose(raw).copy()

        if img.mode in ("RGBA", "LA", "P"):
            if img.mode == "P":
                img = img.convert("RGBA")
            bg = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode in ("RGBA", "LA"):
                bg.paste(img, mask=img.split()[-1])
            else:
                bg.paste(img)
            img = bg
        elif img.mode != "RGB":
            img = img.convert("RGB")
        return img
    except Exception as e:
        print(f"[PDFBuilder] Cannot load image {img_path}: {e}")
        return None


def _render_image_to_pil(
    page_item: PageItem,
    pw_px: int,
    ph_px: int,
    zoom: float = 1.0,
    ignore_crop: bool = False,
    src_img: Optional[Image.Image] = None,
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

    src = src_img if src_img is not None else _load_source_image(page_item)
    if src is None:
        return page_img

    # Apply image rotation (PIL rotates CCW, so negate for CW)
    if page_item.image_rotation:
        src = src.rotate(-page_item.image_rotation, expand=True)

    # Apply crop box if defined (and not ignored for preview mode)
    if page_item.image_crop and not ignore_crop:
        img_w, img_h = src.size
        l, t, r, b = page_item.image_crop
        crop_rect = (
            int(l * img_w),
            int(t * img_h),
            int(r * img_w),
            int(b * img_h)
        )
        src = src.crop(crop_rect)

    img_w, img_h = src.size
    if img_w == 0 or img_h == 0:
        return page_img

    # Scale to fill page edge-to-edge (no margin) then apply user scale
    fit_scale = min(pw_px / img_w, ph_px / img_h)
    
    eff_scale = 1.0 if ignore_crop else page_item.image_scale
    final_scale = fit_scale * eff_scale

    scaled_w = max(1, int(img_w * final_scale))
    scaled_h = max(1, int(img_h * final_scale))

    src_scaled = src.resize((scaled_w, scaled_h), Image.LANCZOS)

    # Centre + user offset (offset is in pts, convert to px using zoom)
    eff_ox = 0.0 if ignore_crop else page_item.image_offset_x
    eff_oy = 0.0 if ignore_crop else page_item.image_offset_y
    cx = pw_px // 2 + int(eff_ox * zoom)
    cy = ph_px // 2 + int(eff_oy * zoom)

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


def get_source_image_dimensions(
    page_item: PageItem,
    apply_crop: bool = False,
) -> Optional[tuple[int, int]]:
    """
    Return effective (width, height) of a PageItem's source image in O(1)
    by reading only the image header and EXIF orientation tag without decoding pixels.
    """
    img_path = _resolve_image_path(page_item)
    if not img_path:
        return None
    try:
        with Image.open(img_path) as img:
            w, h = img.size
            try:
                exif = img.getexif()
                orientation = exif.get(0x0112, 1) if exif else 1
                if orientation in (5, 6, 7, 8):
                    w, h = h, w
            except Exception:
                pass
    except Exception as e:
        print(f"[PDFBuilder] Cannot read image dimensions {img_path}: {e}")
        return None

    if (page_item.image_rotation or 0) % 180 != 0:
        w, h = h, w

    if apply_crop and page_item.image_crop:
        l, t, r, b = page_item.image_crop
        w = max(1, int(w * max(0.01, r - l)))
        h = max(1, int(h * max(0.01, b - t)))

    return (w, h)


def get_image_canvas_bounds(
    page_item: PageItem,
    canvas_w: int,
    canvas_h: int,
    zoom: float = 1.0,
    page_size: str = "A4",
    ignore_crop: bool = False,
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

    dims = get_source_image_dimensions(page_item, apply_crop=not ignore_crop)
    if dims is None:
        return None
    img_w, img_h = dims
    if img_w <= 0 or img_h <= 0:
        return None

    pw_pt, ph_pt = _page_dims(
        page_item.page_landscape,
        page_size,
        image_dims=(img_w, img_h) if page_size == "Fit" else None,
    )
    pw_px = int(pw_pt * zoom)
    ph_px = int(ph_pt * zoom)

    fit_scale = min(pw_px / img_w, ph_px / img_h)
    eff_scale = 1.0 if ignore_crop else page_item.image_scale
    final_scale = fit_scale * eff_scale

    scaled_w = max(1, int(img_w * final_scale))
    scaled_h = max(1, int(img_h * final_scale))

    # Centre of the page on the canvas (page is centred)
    page_canvas_x = max(canvas_w // 2, pw_px // 2 + 10)
    page_canvas_y = max(canvas_h // 2, ph_px // 2 + 10)

    # Image centre within the page (in canvas coords)
    eff_ox = 0.0 if ignore_crop else page_item.image_offset_x
    eff_oy = 0.0 if ignore_crop else page_item.image_offset_y
    img_cx = page_canvas_x + int(eff_ox * zoom)
    img_cy = page_canvas_y + int(eff_oy * zoom)

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


def _parse_hex_rgb(hex_color: str) -> tuple[int, int, int]:
    """Parse #rgb or #rrggbb hex string into (r, g, b) ints, defaulting to (0, 0, 0)."""
    h = str(hex_color or "").strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) != 6:
        return (0, 0, 0)
    try:
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    except ValueError:
        return (0, 0, 0)


def _hex_to_fitz_color(hex_color: str) -> tuple[float, float, float]:
    r, g, b = _parse_hex_rgb(hex_color)
    return r / 255.0, g / 255.0, b / 255.0


def _insert_page_number(page: pymupdf.Page, page_num: int, total: int, s: dict) -> None:
    if page_num == 1 and s.get("skip_cover_page", False):
        return
    fitz_font = FONT_MAP.get(s.get("font", "Helvetica"), "helv")
    font_size = float(s.get("font_size", 10))
    color     = _hex_to_fitz_color(s.get("color", "#000000"))
    text      = _format_page_number(page_num, total, s.get("style", "plain"))
    pw, ph    = page.rect.width, page.rect.height
    try:
        text_w = pymupdf.get_text_length(text, fontname=fitz_font, fontsize=font_size)
    except Exception:
        text_w = len(text) * font_size * 0.55

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
# PIL page-number overlay (used by preview only)
# ---------------------------------------------------------------------------

_WINDOWS_FONT_MAP = {
    "Helvetica":      ["arial.ttf",    "calibri.ttf"],
    "Helvetica-Bold": ["arialbd.ttf",  "calibrib.ttf"],
    "Times-Roman":    ["times.ttf",    "georgia.ttf"],
    "Times-Bold":     ["timesbd.ttf",  "georgiab.ttf"],
    "Courier":        ["cour.ttf",     "consola.ttf"],
    "Courier-Bold":   ["courbd.ttf",   "consolab.ttf"],
}


def _pil_font(font_name: str, size_px: int):
    from PIL import ImageFont
    import os
    candidates = _WINDOWS_FONT_MAP.get(font_name, ["arial.ttf"])
    font_dir = r"C:\Windows\Fonts"
    for fname in candidates:
        path = os.path.join(font_dir, fname)
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size_px)
            except Exception:
                continue
    # Cross-platform fallbacks
    for name in ["DejaVuSans.ttf", "FreeSans.ttf"]:
        for d in ["/usr/share/fonts", "/usr/local/share/fonts"]:
            path = os.path.join(d, name)
            if os.path.exists(path):
                try:
                    return ImageFont.truetype(path, size_px)
                except Exception:
                    continue
    try:
        return ImageFont.load_default(size=size_px)
    except Exception:
        return ImageFont.load_default()


def _draw_page_number_pil(
    img: Image.Image,
    settings: dict,
    page_num: int,
    total: int,
    zoom: float,
) -> Image.Image:
    """
    Overlay a page number on a PIL image using the same positioning logic
    as _insert_page_number (fitz version used in the final PDF).
    """
    from PIL import ImageDraw

    if page_num == 1 and settings.get("skip_cover_page", False):
        return img

    text      = _format_page_number(page_num, total, settings.get("style", "plain"))
    font_name = settings.get("font", "Helvetica")
    font_size_pt = float(settings.get("font_size", 10))
    font_size_px = max(8, int(font_size_pt * zoom * 1.33))  # pt→px at 96dpi
    color = _parse_hex_rgb(settings.get("color", "#000000"))

    font = _pil_font(font_name, font_size_px)
    draw = ImageDraw.Draw(img)

    # Measure text
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
    except Exception:
        text_w = len(text) * font_size_px // 2
        text_h = font_size_px

    pw, ph = img.size
    edge_px = int(float(settings.get("offset_from_edge", 20)) * zoom)
    side_px = int(float(settings.get("offset_from_side", 50)) * zoom)

    position  = settings.get("position",  "bottom")
    alignment = settings.get("alignment", "center")

    y = ph - edge_px - text_h if position == "bottom" else edge_px

    if alignment == "left":
        x = side_px
    elif alignment == "right":
        x = pw - side_px - text_w
    else:
        x = (pw - text_w) // 2

    x = max(0, min(x, pw - text_w))
    y = max(0, min(y, ph - text_h))

    # Semi-transparent backdrop so numbers are legible on any image
    pad = 3
    try:
        overlay = Image.new("RGBA", img.size)
        ov_draw = ImageDraw.Draw(overlay)
        ov_draw.rectangle(
            [x - pad, y - pad, x + text_w + pad, y + text_h + pad],
            fill=(255, 255, 255, 160),
        )
        if img.mode != "RGBA":
            img = img.convert("RGBA")
        img = Image.alpha_composite(img, overlay).convert("RGB")
        draw = ImageDraw.Draw(img)
    except Exception:
        pass

    draw.text((x, y), text, fill=color, font=font)
    return img


def _insert_document_overlays(page: pymupdf.Page, overlays: dict) -> None:
    """Stamp optional watermark, header, and footer text onto a PDF page."""
    pw, ph = page.rect.width, page.rect.height
    header_text = str(overlays.get("header_text", "") or "").strip()
    footer_text = str(overlays.get("footer_text", "") or "").strip()
    watermark_text = str(overlays.get("watermark_text", "") or "").strip()

    if header_text:
        try:
            page.insert_text((40.0, 24.0), header_text, fontname="helv", fontsize=9.0, color=(0.35, 0.4, 0.48))
        except Exception:
            pass
    if footer_text:
        try:
            page.insert_text((40.0, max(16.0, ph - 18.0)), footer_text, fontname="helv", fontsize=9.0, color=(0.35, 0.4, 0.48))
        except Exception:
            pass
    if watermark_text:
        try:
            opacity = max(0.05, min(0.8, float(overlays.get("watermark_opacity", 0.18))))
            color = _hex_to_fitz_color(overlays.get("watermark_color", "#64748b"))
            font_size = max(24.0, min(64.0, min(pw, ph) * 0.09))
            try:
                text_w = pymupdf.get_text_length(watermark_text, fontname="hebo", fontsize=font_size)
            except Exception:
                text_w = len(watermark_text) * font_size * 0.55
            cx, cy = pw / 2.0, ph / 2.0
            page.insert_text(
                (cx - text_w / 2.0, cy + font_size * 0.3),
                watermark_text,
                fontname="hebo",
                fontsize=font_size,
                color=color,
                fill_opacity=opacity,
                morph=(pymupdf.Point(cx, cy), pymupdf.Matrix(45)),
            )
        except Exception as e:
            print(f"[PDFBuilder] Watermark error: {e}")


def _draw_document_overlays_pil(img: Image.Image, overlays: dict, zoom: float) -> Image.Image:
    """Composite live watermark, header, and footer overlays onto a preview PIL image."""
    from PIL import ImageDraw

    header_text = str(overlays.get("header_text", "") or "").strip()
    footer_text = str(overlays.get("footer_text", "") or "").strip()
    watermark_text = str(overlays.get("watermark_text", "") or "").strip()
    if not (header_text or footer_text or watermark_text):
        return img

    pw, ph = img.size
    if img.mode != "RGBA":
        img = img.convert("RGBA")

    if watermark_text:
        try:
            opacity = max(0.05, min(0.8, float(overlays.get("watermark_opacity", 0.18))))
            r, g, b = _parse_hex_rgb(overlays.get("watermark_color", "#64748b"))
            alpha = int(round(opacity * 255))
            font_px = max(14, int(min(pw, ph) * 0.09))
            font = _pil_font("Helvetica-Bold", font_px)
            wm_layer = Image.new("RGBA", (pw * 2, ph * 2), (0, 0, 0, 0))
            wm_draw = ImageDraw.Draw(wm_layer)
            bbox = wm_draw.textbbox((0, 0), watermark_text, font=font)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
            wm_draw.text((pw - tw // 2, ph - th // 2), watermark_text, fill=(r, g, b, alpha), font=font)
            rotated = wm_layer.rotate(45, resample=Image.BICUBIC)
            cx, cy = rotated.width // 2, rotated.height // 2
            cropped = rotated.crop((cx - pw // 2, cy - ph // 2, cx - pw // 2 + pw, cy - ph // 2 + ph))
            img = Image.alpha_composite(img, cropped)
        except Exception:
            pass

    if header_text or footer_text:
        txt_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
        tdraw = ImageDraw.Draw(txt_layer)
        hfont = _pil_font("Helvetica", max(8, int(9.0 * zoom * 1.33)))
        side_px = int(40 * zoom)
        if header_text:
            tdraw.text((side_px, max(4, int(14 * zoom))), header_text, fill=(90, 102, 122, 220), font=hfont)
        if footer_text:
            tdraw.text((side_px, max(4, ph - int(22 * zoom))), footer_text, fill=(90, 102, 122, 220), font=hfont)
        img = Image.alpha_composite(img, txt_layer)

    return img.convert("RGB")


def _add_image_page(
    item: PageItem,
    out_doc: pymupdf.Document,
    page_size: str = "A4",
    jpeg_quality: int = 95,
    src_img: Optional[Image.Image] = None,
) -> None:
    """Render an image PageItem and append it to out_doc.

    Parameters
    ----------
    jpeg_quality : JPEG quality for the embedded image (1-95).
                  95 = archival quality (default).
                  75 = Standard compression (Adobe/Quartz equivalent).
    """
    img_dims = None
    if page_size == "Fit":
        img_dims = src_img.size if src_img is not None else get_source_image_dimensions(item, apply_crop=True)
        if src_img is not None and img_dims is not None and (item.image_rotation or 0) % 180 != 0:
            img_dims = (img_dims[1], img_dims[0])
        if src_img is not None and img_dims is not None and item.image_crop:
            l, t, r, b = item.image_crop
            img_dims = (max(1, int(img_dims[0] * max(0.01, r - l))), max(1, int(img_dims[1] * max(0.01, b - t))))

    pw_pt, ph_pt = _page_dims(item.page_landscape, page_size, image_dims=img_dims)

    # Render at 2× for good print quality
    SCALE = 2.0
    pil_img = _render_image_to_pil(
        item, int(pw_pt * SCALE), int(ph_pt * SCALE), zoom=SCALE, src_img=src_img
    )

    out_page = out_doc.new_page(width=pw_pt, height=ph_pt)
    buf = io.BytesIO()
    pil_img.save(buf, format="JPEG", quality=jpeg_quality)
    out_page.insert_image(pymupdf.Rect(0, 0, pw_pt, ph_pt), stream=buf.getvalue())


def build_pdf(
    pages: list[PageItem],
    output_path: str,
    page_number_settings: Optional[dict] = None,
    progress_callback=None,
    page_size: str = "A4",
    jpeg_quality: int = 95,
    page_range: Optional[str] = None,
    document_overlays: Optional[dict] = None,
    metadata: Optional[dict] = None,
    password: Optional[str] = None,
) -> tuple[bool, str]:
    """
    Assemble pages into a PDF file.

    Parameters
    ----------
    jpeg_quality : JPEG quality for image pages (1–95).
                  95 = archival quality (default).
                  75 = Standard compression equivalent (Adobe / Quartz).
                  Lower values = smaller file, more visible quality loss.
    """
    if not pages:
        return False, "No pages to assemble."

    try:
        indices = parse_page_range(page_range, len(pages))
    except ValueError as e:
        return False, f"Invalid page range: {e}"

    if not indices:
        return False, "No pages matched the export range."

    selected_pages = [pages[idx] for idx in indices]
    out_doc = pymupdf.open()
    total = len(selected_pages)

    for i, item in enumerate(selected_pages):
        if progress_callback:
            progress_callback(i, total, f"Processing page {i + 1} of {total}…")
        try:
            src_img = _load_source_image(item) if item.is_image else None
            if item.is_image and (src_img is not None or not (item.converted_pdf and os.path.isfile(item.converted_pdf))):
                _add_image_page(item, out_doc, page_size, jpeg_quality=jpeg_quality, src_img=src_img)
            else:
                src = pymupdf.open(item.converted_pdf)
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

    if document_overlays:
        for pg in out_doc:
            _insert_document_overlays(pg, document_overlays)

    if page_number_settings and page_number_settings.get("enabled", False):
        ft = len(out_doc)
        for i, pg in enumerate(out_doc):
            _insert_page_number(pg, i + 1, ft, page_number_settings)

    if metadata:
        clean_meta = {
            k: str(v).strip()
            for k, v in metadata.items()
            if k in ("title", "author", "subject", "keywords", "creator") and str(v or "").strip()
        }
        if clean_meta:
            out_doc.set_metadata(clean_meta)

    if progress_callback:
        progress_callback(total, total, "Saving PDF…")

    try:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        # Use full compression when optimising for file size
        _compressing = jpeg_quality < 95
        save_kwargs = dict(
            garbage=4,
            deflate=True,
            deflate_images=_compressing,
            deflate_fonts=_compressing,
            clean=_compressing,
        )
        if password:
            save_kwargs.update(
                encryption=pymupdf.PDF_ENCRYPT_AES_256,
                user_pw=password,
                owner_pw=password,
            )
        out_doc.save(output_path, **save_kwargs)
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
    zoom: float,
    page_size: str = "A4",
    page_number_settings: Optional[dict] = None,
    page_num: int = 1,
    total_pages: int = 1,
    ignore_crop: bool = False,
    document_overlays: Optional[dict] = None,
) -> Optional[bytes]:
    """
    Render a PageItem to PNG bytes for the preview panel.

    If page_number_settings is provided and enabled, the page number is
    composited onto the preview image at the same position/style as the
    final PDF output.
    """
    pil_img: Optional[Image.Image] = None

    try:
        src_img = _load_source_image(page_item) if page_item.is_image else None
        if page_item.is_image and (src_img is not None or not (page_item.converted_pdf and os.path.isfile(page_item.converted_pdf))):
            img_dims = None
            if page_size == "Fit":
                img_dims = get_source_image_dimensions(page_item, apply_crop=not ignore_crop)
            pw_pt, ph_pt = _page_dims(page_item.page_landscape, page_size, image_dims=img_dims)
            pil_img = _render_image_to_pil(
                page_item,
                int(pw_pt * zoom),
                int(ph_pt * zoom),
                zoom=zoom,
                ignore_crop=ignore_crop,
                src_img=src_img,
            )
        else:
            doc  = pymupdf.open(page_item.converted_pdf)
            page = doc[0]
            mat  = pymupdf.Matrix(zoom, zoom).prerotate(page_item.rotation)
            pix  = page.get_pixmap(matrix=mat, alpha=False)
            doc.close()
            pil_img = Image.open(io.BytesIO(pix.tobytes("png")))

        if pil_img is not None and document_overlays:
            pil_img = _draw_document_overlays_pil(pil_img, document_overlays, zoom)

        # Overlay page number if enabled
        if (pil_img is not None
                and page_number_settings
                and page_number_settings.get("enabled", False)):
            pil_img = _draw_page_number_pil(
                pil_img, page_number_settings, page_num, total_pages, zoom
            )

        if pil_img is None:
            return None

        buf = io.BytesIO()
        pil_img.save(buf, format="PNG")
        return buf.getvalue()

    except Exception as e:
        print(f"[PDFBuilder] Preview render failed: {e}")
        import traceback; traceback.print_exc()
        return None
