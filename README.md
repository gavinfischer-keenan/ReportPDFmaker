# PDF Maker

<div align="center">

**A powerful desktop application for combining and editing multi-format files into a single PDF.**

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Platform](https://img.shields.io/badge/platform-Windows-lightgrey)
![License](https://img.shields.io/badge/license-MIT-green)

</div>

---

## ✨ Features

- **Multi-format import** — Drag and drop or browse for JPG, PNG, GIF, BMP, TIFF, WebP, TXT, DOC, DOCX, and PDF files
- **Live preview** — See every page rendered before you commit to saving
- **Image controls** — Rotate image content (0°/90°/180°/270°), resize with corner handles (aspect-ratio locked), and position images anywhere on the page
- **Page orientation** — Set individual pages to Portrait or Landscape independently
- **Page reordering** — Move pages up or down in the document
- **Page numbers** — Add customisable page numbers with control over position, alignment, font, size, color, and style
- **Live page number preview** — When enabled, page numbers appear on the preview exactly as they will in the final PDF
- **Settings persistence** — All settings and output paths are saved between sessions
- **Dark / Light theme** — Fully themeable UI built on CustomTkinter
- **Import progress bar** — Animated red→blue progress bar during multi-file imports

---

## 📦 Requirements

| Dependency | Version |
|---|---|
| Python | 3.10+ |
| customtkinter | ≥ 5.2.0 |
| PyMuPDF (fitz) | ≥ 1.24.0 |
| Pillow | ≥ 10.4.0 |
| reportlab | ≥ 4.2.0 |
| python-docx | ≥ 1.1.0 |
| pypdf | ≥ 4.0.0 |
| docx2pdf | ≥ 0.1.8 |

> **Word documents (.doc/.docx):** Microsoft Word must be installed on the machine for `.doc`/`.docx` conversion. The app detects Word availability on startup and warns you if it is missing.

---

## 🚀 Installation

### Option A — Standalone Executable (Windows, recommended)
Download `PDFMaker-1.0.0-Setup.exe` from the [Releases](../../releases) page and run it. No Python required.

### Option B — Install from PyPI / source

```bash
# 1. Clone the repository
git clone https://github.com/gavinfischer-keenan/ReportPDFmaker.git
cd ReportPDFmaker

# 2. Create a virtual environment (recommended)
python -m venv .venv
.venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the app
python main.py
```

### Option C — Install as a package

```bash
pip install .
# Then launch with:
pdfmaker
```

---

## 🖥️ Quick Start

1. **Launch** `PDFMaker.exe` (or `python main.py`)
2. Click **➕ Add Files** and select one or more files (hold Ctrl/Shift for multi-select)
3. The files appear in the **Document Pages** panel on the left
4. Click any page to select it — a live preview appears in the centre
5. Use the **Page Editor** panel on the right to:
   - Rotate the image content (0°/90°/180°/270°)
   - Switch the page between Portrait and Landscape
   - Move the page up or down
6. In the centre preview, drag the **green corner handles** to resize an image (aspect ratio locked)
7. Toggle **Page Numbers** in the bottom bar and click ⚙ to customise them
8. Set your output folder and filename, then click **💾 Save PDF**

---

## 📁 Supported File Types

| Type | Extensions |
|---|---|
| Images | `.jpg` `.jpeg` `.png` `.gif` `.bmp` `.tiff` `.webp` |
| Text | `.txt` |
| Word | `.doc` `.docx` *(requires Microsoft Word)* |
| PDF | `.pdf` |
| 3D Models | `.gltf` `.glb` `.obj` `.stl` `.fbx` *(experimental)* |

---

## 🧪 Running Tests

```bash
pip install pytest
python -m pytest tests/ -v
```

---

## 🏗️ Project Structure

```
ReportPDFmaker/
├── main.py                    # Entry point
├── requirements.txt
├── pyproject.toml             # Installable package definition
├── INSTRUCTIONS.md            # User guide
├── tests/                     # Automated test suite
│   ├── conftest.py
│   ├── test_file_utils.py
│   ├── test_settings_manager.py
│   ├── test_pdf_builder.py
│   ├── test_controller.py
│   └── test_color_utils.py
└── pdf_maker/
    ├── app.py                 # Application bootstrap
    ├── controller.py          # Central state & event bus
    ├── settings_manager.py    # Persistent settings (JSON)
    ├── converters/
    │   ├── pdf_builder.py     # Final PDF assembly (PyMuPDF)
    │   ├── image_converter.py # PIL → single-page PDF
    │   ├── text_converter.py  # Plain text → PDF
    │   ├── docx_converter.py  # Word → PDF (via docx2pdf)
    │   ├── pdf_handler.py     # PDF passthrough / split
    │   └── gltf_converter.py  # 3D model → PDF (experimental)
    ├── ui/
    │   ├── main_window.py     # Root window, toolbar, status bar
    │   ├── file_list_panel.py # Left panel: page list
    │   ├── preview_panel.py   # Centre panel: live preview + handles
    │   └── page_editor_panel.py # Right panel: rotation, orientation, order
    └── utils/
        ├── file_utils.py      # File type detection, icons, dialogs
        └── color_utils.py     # WCAG contrast & color blending
```

---

## ⚙️ Settings

Settings are saved automatically to `%APPDATA%\PDFMaker\settings.json`. They include:

- Output folder and last filename
- Page size (A4 / Letter)
- Page number configuration
- Theme (Dark / Light / System)
- Window size and position

---

## 📝 License

MIT License — see [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgements

Built with:
- [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) — modern Tkinter UI framework
- [PyMuPDF](https://pymupdf.readthedocs.io/) — PDF rendering and assembly
- [Pillow](https://python-pillow.org/) — image processing
- [ReportLab](https://www.reportlab.com/) — PDF generation
- [python-docx](https://python-docx.readthedocs.io/) — Word document reading
