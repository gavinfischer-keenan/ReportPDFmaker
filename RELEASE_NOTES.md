# PDF Maker v1.0.0

## 🎉 First stable release!

PDF Maker is a desktop GUI application for combining JPG, PNG, GIF, TXT, DOC, DOCX, and PDF files into a single, polished PDF document.

---

## ✨ What's in v1.0.0

### Core Features
- **Multi-format import** — JPG, PNG, GIF, BMP, TIFF, WebP, TXT, DOC, DOCX, PDF
- **Multi-file select** — Hold Ctrl/Shift in the file dialog; import progress bar animates red → blue
- **Live preview** — Every page rendered in real-time before you save
- **Image controls** — Rotate image content independently of page orientation
- **Page orientation** — Per-page Portrait / Landscape toggle
- **Corner resize handles** — Drag green corners to scale images (aspect-ratio locked, clips to page edge with zero buffer)
- **Page reordering** — Move pages up/down in the document
- **Page numbers** — Fully customisable: style, position, alignment, font, size, color, offsets
- **Live page number preview** — Numbers appear in the preview exactly as in the final PDF
- **Settings persistence** — All settings saved to `%APPDATA%\PDFMaker\settings.json`
- **Dark / Light theme** — Full dark mode and light mode support

### Technical
- **Threading safety** — All controller events dispatched to the main thread via `after(0, ...)`
- **Edge-to-edge fill** — Images fill the page with zero margin; scale > 1 clips at the exact page edge
- **154 automated tests** — Full pytest suite covering file utils, settings, PDF builder, controller, and color utilities

---

## 📦 Installation

### Option A — Python Package (pip)
```bash
pip install pdfmaker-1.0.0-py3-none-any.whl
pdfmaker
```

### Option B — From Source
```bash
git clone https://github.com/gavinfischer-keenan/ReportPDFmaker.git
cd ReportPDFmaker
pip install -r requirements.txt
python main.py
```

---

## 📋 Requirements
- Python 3.10+
- Dependencies: customtkinter, PyMuPDF, Pillow, reportlab, python-docx, pypdf, docx2pdf
- Microsoft Word (optional — required only for .doc/.docx conversion)

---

## 🔗 Links
- [Full README](README.md)
- [User Instructions](INSTRUCTIONS.md)
- [Source Code](https://github.com/gavinfischer-keenan/ReportPDFmaker)
