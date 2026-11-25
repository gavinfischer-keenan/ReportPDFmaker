# PDF Maker · Paper Nautilus

<div align="center">

**Combine, edit, crop, number, watermark, and compress multi-format files into a single PDF — as a Windows Desktop GUI or a 100% client-side Web App.**

![Version](https://img.shields.io/badge/version-2.0.0-blue)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Web-lightgrey)
![License](https://img.shields.io/badge/license-MIT-green)

</div>

---

## ✨ Features

### Core Document Builder (Desktop & Web)
- **Multi-format import** — Images, PDFs, Word documents, plain text, and 3D models (see [Supported File Types](#-supported-file-types)), with drag-and-drop import on both Windows Desktop and Web
- **Live interactive preview** — Inspect every page before exporting, zoom in/out/fit, drag **green corner handles** to resize images (aspect-ratio locked), drag inside an image to pan/reposition, or use the **Image Scale** slider (`10%–300%`)
- **Interactive Image Cropping** — Switch between **Resize** and **Crop** modes, adjust the blue dashed crop box, and click **✂️ Apply Crop**
- **Multi-step Undo / Redo (`Ctrl+Z` / `Ctrl+Y`)** — Full document-level history across edits, reordering, deletion, rotation, resizing, and cropping
- **Independent rotation & orientation** — Rotate image content (`0°`/`90°`/`180°`/`270°`) independently of per-page **Portrait / Landscape** orientation, plus **Entire Document** batch actions (Rotate All, All Portrait/Landscape, Reverse, Sort A→Z)
- **Page management & selective export** — Reorder pages via drag-and-drop cards/rows, `Alt+↑`/`Alt+↓`, or buttons; **Duplicate** pages, insert **Blank / Divider** pages, and filter exports with **Export Page Range** (e.g. `1-3, 5`)
- **Custom Page Sizes & Match-Image (`Fit`)** — Choose `A4`, `Letter`, `Legal`, `A3`, `A5`, or `Fit` (auto-sized to match each image's aspect ratio)
- **Page numbers, watermarks & headers/footers** — Live preview overlay for customizable page numbers (including **Skip Cover Page**), diagonal **Watermarks** (text, opacity `5%–60%`, color), and running **Header / Footer** text
- **PDF Metadata** — Embed `Title`, `Author`, and `Subject` metadata properties directly into exported PDFs
- **Shrink a PDF (`S`)** — Dedicated 4-level compression tool (`Light`, `Standard`, `Aggressive`, `Grayscale`)
- **Command Palette (`Ctrl+K`) & Keyboard Shortcuts (`?`)** — Search pages, project actions, and settings with automatic input-focus guards
- **Dark / Light theme & persistent settings** — Saved automatically between sessions (`%APPDATA%\PDFMaker\settings.json` on Desktop; `localStorage` on Web)

### Edition-Specific Highlights
- **Windows Desktop (`pdf_maker/`)**:
  - **`.nautilus` Project Files (`Ctrl+O` / `Ctrl+Shift+S`)** — Save and reopen your complete page queue, per-page crops/rotations/scales, blank/divider pages, and settings
  - **Session-only AES-256 PDF Password Protection** — Optionally encrypt exported PDFs without ever writing passwords to disk
  - **⚡ Optimize for file size** — Save-bar toggle (`150 dpi · JPEG 75%` + stream/font/image deflate)
  - **Lossless Light PDF Shrink** — Uses PyMuPDF to deduplicate objects, strip metadata/thumbnails, subset fonts, and compress streams without resampling images
  - **Full-fidelity Word conversion** — Uses Microsoft Word (`docx2pdf`) when detected on startup, with automatic fallback to `python-docx` text extraction
- **Paper Nautilus Web Edition (`web/`)**:
  - **Zero uploads & IndexedDB auto-recovery** — 100% client-side processing at [pdfmaker.11mosswood.us/app/](https://pdfmaker.11mosswood.us/app/), with automatic local session restore across page reloads
  - **Native vector text export** — Unedited TXT and DOCX pages export as crisp, searchable vector PDF text via `PDF-Lib` (with automatic raster fallback for non-WinAnsi characters)
  - **Sample Report & Sample PDF** — Load a built-in 3-page Sample Report or sample PDF immediately
  - **Export Quality presets & Framing defaults** — Choose `Archival`, `Balanced`, or `Compact` export quality, default import orientation, and edge-to-edge vs. margin framing
  - **Interactive 3D Snapshot modal** — Orbit and zoom `.gltf`/`.glb` models in WebGL (Three.js) and capture a snapshot page
  - **Accessible & responsive UI** — Non-blocking toast notifications, modal focus trapping, inline confirmation dialogs, and mobile/tablet pane switcher (`≤ 960px`)

---

## 📁 Supported File Types

| Category | Desktop App (`pdf_maker/`) | Paper Nautilus Web (`web/`) |
|---|---|---|
| **Images** | `.jpg` `.jpeg` `.png` `.gif` *(all frames)* `.bmp` `.tiff` `.tif` `.webp` | `.jpg` `.jpeg` `.png` `.gif` `.bmp` `.webp` `.svg` |
| **Text** | `.txt` | `.txt` `.md` `.csv` `.log` `.json` |
| **Word** | `.doc` `.docx` *(MS Word via `docx2pdf`, or `python-docx` plain-text fallback)* | `.docx` *(text extraction via Mammoth.js; `.doc` unsupported)* |
| **PDF** | `.pdf` *(per-page split/passthrough)* | `.pdf` *(native vector passthrough when unedited)* |
| **3D Models** | `.gltf` `.glb` `.obj` `.stl` `.fbx` *(optional `trimesh` + `pyrender`)* | `.gltf` `.glb` *(interactive WebGL snapshot modal)* |
| **Projects** | `.nautilus` *(project save/load)* | Auto-saved in browser IndexedDB |

---

## 📦 Requirements

### Desktop Application
| Dependency | Version | Purpose |
|---|---|---|
| Python | 3.10+ | Runtime |
| `customtkinter` | ≥ 5.2.0 | Modern Tkinter UI |
| `pymupdf` | ≥ 1.24.0 | PDF rendering, assembly, encryption, and compression |
| `pypdf` | ≥ 4.0.0 | PDF support utilities |
| `Pillow` | ≥ 10.4.0 | Image processing & previews |
| `reportlab` | ≥ 4.2.0 | Text-to-PDF pagination |
| `python-docx` | ≥ 1.1.0 | Word fallback text extraction |
| `docx2pdf` | ≥ 0.1.8 | Full-fidelity Word conversion *(requires Microsoft Word)* |
| `trimesh`, `pyrender`, `numpy` | *(optional)* | 3D model rendering (`pip install .[3d]`) |

### Web Edition
- Any modern desktop or mobile browser (hosted statically, no server runtime needed for visitors).
- **Developer regression checks only:** Node.js 22+ (`cd web && npm ci && npm test`).

---

## 🚀 Installation & Running

### Option A — Paper Nautilus Web Edition
- **Hosted:** Open [https://pdfmaker.11mosswood.us/app/](https://pdfmaker.11mosswood.us/app/)
- **Local static preview:**
  ```bash
  python web/server.py 8080
  # Open http://localhost:8080
  ```
- **Self-hosting / Docker / Nginx:** See [web/DEPLOYMENT.md](web/DEPLOYMENT.md).

### Option B — Desktop App from Source
```bash
git clone https://github.com/gavinfischer-keenan/ReportPDFmaker.git
cd ReportPDFmaker
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

### Option C — Install Desktop Package or Build Windows `.exe`
```bash
# Install as a CLI entry point:
pip install .
pdfmaker

# Or build a standalone Windows bundle (requires pyinstaller):
pip install pyinstaller
build_exe.bat
# Outputs dist\PDFMaker\PDFMaker.exe and dist\PDFMaker-2.0.0.zip
```

---

## 🖥️ Quick Start

### Windows Desktop
1. Launch `PDFMaker.exe` (or `python main.py` / `pdfmaker`).
2. Click **➕ Add Files** (`A`) or drag files from Windows Explorer onto the window.
3. Click any row in **Document Pages** (or drag rows / press `Alt+↑`/`Alt+↓`) to reorder and preview pages.
4. Use the **Page Editor** (right) to switch between **Resize** (green handles, canvas drag-to-pan, or scale slider) and **Crop** (blue dashed box + **✂️ Apply**), rotate images, duplicate or insert blank pages, reverse/sort, or undo/redo (`Ctrl+Z` / `Ctrl+Y`).
5. Click **⚙** in the bottom bar to configure **Page Size** (`A4`–`A5`/`Fit`), **Export Page Range**, **Page Numbers** (including **Skip cover page**), **Watermarks**, **Headers/Footers**, **PDF Metadata**, and optional session **AES-256 Password**.
6. Save your workspace anytime as a `.nautilus` project (`Ctrl+Shift+S`), or click **💾 Save PDF** (`E`).

### Paper Nautilus Web
1. Visit the web app and drop files into **Document Pages** (or click **✨ Load 3-Page Sample Report**).
2. Drag green corner handles to resize, drag inside the image to pan, switch to **✂️ Crop** to trim images, or use **Entire Document** controls for batch orientation/rotation/reverse/sort.
3. Press `Ctrl/⌘+K` for the Command Palette, `?` for Keyboard Shortcuts, `G` for full Settings (including Watermarks, Headers/Footers, Page Range, and Metadata), `S` for **Shrink PDF**, and `E` to **Download PDF**.

> See [INSTRUCTIONS.md](INSTRUCTIONS.md) for the complete step-by-step user guide.

---

## 🧪 Running Tests & CI

```bash
# Desktop Python test suite (188 tests, strict FutureWarning check)
pip install pytest
python -W error::FutureWarning -m pytest tests/ -v

# Web Edition regression checks (Node 22+)
cd web
npm ci
npm test
```

GitHub Actions CI ([.github/workflows/ci.yml](.github/workflows/ci.yml)) runs both suites on every push and pull request.

---

## 🏗️ Project Structure

```text
ReportPDFmaker/
├── .github/workflows/ci.yml      # GitHub Actions CI (Python + Node suites)
├── main.py                       # Desktop entry point
├── build_exe.bat                 # Windows PyInstaller build script
├── pdfmaker.spec                 # PyInstaller spec file
├── pyproject.toml                # Python package & pytest config
├── requirements.txt              # Desktop dependencies
├── README.md
├── INSTRUCTIONS.md               # Detailed Desktop & Web user guide
├── RELEASE_NOTES.md              # Release & changelog notes
├── LICENSE                       # MIT License
├── pdf_maker/
│   ├── __init__.py               # Package version (__version__)
│   ├── app.py                    # Application bootstrap & CLI main()
│   ├── controller.py             # Central state, multi-step undo/redo & event bus
│   ├── project_manager.py        # .nautilus project save/load serialization
│   ├── settings_manager.py       # Persistent JSON settings & diff helper
│   ├── converters/
│   │   ├── pdf_builder.py        # Assembly, ranges, watermarks, metadata & encryption
│   │   ├── pdf_compressor.py     # 4-level standalone PDF compressor
│   │   ├── image_converter.py    # Image / animated GIF → temp PDF
│   │   ├── text_converter.py     # Plain text → PDF
│   │   ├── docx_converter.py     # Word → PDF (docx2pdf + python-docx fallback)
│   │   ├── pdf_handler.py        # PDF split & error page helpers
│   │   └── gltf_converter.py     # 3D model → PDF + sidecar PNG (optional)
│   ├── ui/
│   │   ├── main_window.py        # Root window, toolbar, shortcuts, save/project bar
│   │   ├── file_list_panel.py    # Left panel: page queue & drag-to-reorder
│   │   ├── preview_panel.py      # Centre panel: preview, resize, pan & crop
│   │   ├── page_editor_panel.py  # Right panel: mode, scale slider, rotation, batch
│   │   ├── dialogs.py            # Settings, Shortcuts, Palette, About, Warnings
│   │   └── shrink_dialog.py      # Shrink a PDF modal dialog
│   └── utils/
│       ├── file_utils.py         # File type detection, icons, dialog filters
│       ├── color_utils.py        # WCAG contrast & sRGB LUT utilities
│       └── win_dnd.py            # Native Windows Explorer WM_DROPFILES hook
├── tests/                        # Desktop automated test suite (188 tests)
│   ├── conftest.py
│   ├── test_color_utils.py
│   ├── test_controller.py
│   ├── test_file_utils.py
│   ├── test_optimizations.py
│   ├── test_pdf_builder.py
│   ├── test_phase1_fixes.py
│   ├── test_phase2_parity.py
│   ├── test_phase3_features.py
│   ├── test_phase4_projects.py
│   └── test_settings_manager.py
└── web/                          # Paper Nautilus client-side Web Edition
    ├── index.html
    ├── DEPLOYMENT.md             # Static hosting, security & dev checks
    ├── server.py                 # Local static dev server
    ├── Dockerfile
    ├── docker-compose.yml
    ├── nginx.conf
    ├── package.json
    ├── LICENSE.txt
    ├── assets/
    ├── css/styles.css
    ├── js/                       # Modular ES modules (app, state, builder, session-store, ui-feedback, etc.)
    ├── tests/                    # Node regression suites (security, browser-core, ui-features)
    └── vendor/                   # Vendored PDF-Lib, PDF.js, Mammoth, Three.js, fonts & notices
```

---

## ⚙️ Settings & Session Storage

- **Desktop:** Saved automatically to `%APPDATA%\PDFMaker\settings.json` (output folder, filename, `page_size`, `export_page_range`, `page_numbers`, `skip_cover_page`, numbering style/font/size/color/offsets, `watermark_*`, `header_text`, `footer_text`, `pdf_*` metadata, `theme`, `optimize_file_size`, `confirm_reset`, and window geometry). Session PDF passwords are never saved to `settings.json` or `.nautilus` files.
- **Web:** Preferences are saved in browser `localStorage` (`reportpdfmaker_settings` and `reportpdfmaker_recents`); the active page workspace is auto-saved locally in browser `IndexedDB` (`paper_nautilus_session`).

---

## 📝 License & Acknowledgements

MIT License — see [LICENSE](LICENSE) for details.

- **Desktop stack:** [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter), [PyMuPDF](https://pymupdf.readthedocs.io/), [Pillow](https://python-pillow.org/), [ReportLab](https://www.reportlab.com/), [python-docx](https://python-docx.readthedocs.io/), [pypdf](https://pypdf.readthedocs.io/), [docx2pdf](https://github.com/AlJohri/docx2pdf).
- **Web stack:** PDF-Lib, PDF.js, Mammoth.js, and Three.js — see [web/vendor/THIRD-PARTY-NOTICES.txt](web/vendor/THIRD-PARTY-NOTICES.txt).
