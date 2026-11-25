# PDF Maker · Paper Nautilus — Release Notes

## 🚀 v2.0.0 — Paper Nautilus Web Edition & Desktop Parity Release

Since the initial v1.0.0 release, both the **Windows Desktop Application** and the **Paper Nautilus Web Edition** have received major bug fixes, feature parity upgrades, new PDF capabilities, and session persistence:

### Desktop & Web Feature Parity & New Capabilities
- **Paper Nautilus Web Edition (`web/`)** — Full 100% client-side browser PDF maker (images, native PDF vector passthrough/merge, native vector TXT/DOCX text export, interactive Three.js 3D `.gltf`/`.glb` snapshots, canvas resize/pan/crop, live overlays, and responsive mobile/tablet tabs).
- **Multi-Step Undo / Redo (`Ctrl+Z` / `Ctrl+Y`)** — 50-step document-level undo/redo across both Desktop and Web.
- **Interactive Cropping & Canvas Panning on Both Editions** — Web Crop UI (`Resize` / `Crop` toggle + blue handles + `✂️ Apply Crop`), Desktop canvas drag-to-pan, **Image Scale** slider (`10%–300%`), drag-to-reorder page rows, and native Windows Explorer drag-and-drop (`win_dnd.py`).
- **Page Management & Selective Export** — **Duplicate**, **Blank / Section Divider Page**, **Reverse Order**, natural **Sort A→Z**, keyboard reordering (`Alt+↑`/`Alt+↓`), and **Export Page Range** (`1-3, 5`).
- **Custom Page Sizes & Match-Image (`Fit`)** — Added `Legal`, `A3`, `A5`, and `Fit` alongside `A4` and `Letter`.
- **Watermarks, Headers/Footers, Metadata & Security** — Diagonal watermarks (text, opacity `5%–60%`, color) and running headers/footers with live previews on both editions; PDF `Title`/`Author`/`Subject` metadata; and session-only **AES-256 PDF Password Protection** on Desktop.
- **Shrink a PDF (`pdf_compressor.py` / Web Shrink Modal)** — 4-level PDF compressor (`Light`, `Standard`, `Aggressive`, `Grayscale`) plus Desktop `⚡ Optimize for file size` toggle (`150 dpi · JPEG 75%`).
- **Session Persistence & Accessibility** — Desktop `.nautilus` project save/load (`Ctrl+O` / `Ctrl+Shift+S`), Web IndexedDB automatic session recovery, non-blocking toast notifications & inline confirmation dialogs (zero `alert()`/`confirm()`), and modal focus trapping.

### Reliability, Performance & Testing
- **Core Bug Fixes** — Fixed `pdf_maker.app:main` CLI entry point, transparent PNG/WebP white-background compositing, multi-frame animated GIF rendering, 3D converter unpack/sidecar PNG preview, malformed hex color safety, PyMuPDF `page.replace_image()` SMask-safe compression, `Reset All` checkbox sync, temp file lifecycle cleanup, Web rotation button semantics, and Web Shrink DPI labels.
- **PyMuPDF Migration & CI** — Migrated `import fitz` → `import pymupdf` (zero `FutureWarning`s) and added `.github/workflows/ci.yml`.
- **Automated Test Suite** — Expanded from 154 to **188 Python `pytest` tests** plus **3 Node.js Web regression suites** (`security.mjs`, `browser-core.mjs`, `ui-features.mjs`).

---

## 🎉 v1.0.0 — First Stable Release

PDF Maker is a desktop GUI application for combining JPG, PNG, GIF, BMP, TIFF, WebP, TXT, DOC, DOCX, PDF, and optional 3D files into a single, polished PDF document.

### Core Features in v1.0.0
- **Multi-format import** — JPG, PNG, GIF, BMP, TIFF, WebP, TXT, DOC, DOCX, PDF (plus experimental 3D support)
- **Live preview & corner resize handles** — Aspect-ratio-locked edge-to-edge scaling
- **Image controls & page orientation** — Rotate image content independently of Portrait/Landscape
- **Page reordering & customizable page numbers** — Live preview overlay and persistent settings

---

## 🔗 Links
- [Full README](README.md)
- [User Instructions](INSTRUCTIONS.md)
- [Web Deployment Guide](web/DEPLOYMENT.md)
- [Source Code](https://github.com/gavinfischer-keenan/ReportPDFmaker)
