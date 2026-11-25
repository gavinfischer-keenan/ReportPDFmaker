# PDF Maker · Paper Nautilus — User Guide

This guide covers both the **Windows Desktop Application** (`PDFMaker.exe` / `python main.py` / `pdfmaker`) and the **Paper Nautilus Web Edition** ([pdfmaker.11mosswood.us/app/](https://pdfmaker.11mosswood.us/app/)).

---

## Part 1 — Windows Desktop Application

### Launching the App
- **Standalone executable:** Double-click `PDFMaker.exe` (inside `dist\PDFMaker\` if built locally)
- **Installed package:** Run `pdfmaker`
- **From source:** Open a terminal in the repository root and run `python main.py`

### The Interface

```text
┌─────────────────────────────────────────────────────────────────────────┐
│  TOOLBAR: Add | Remove | ▲ | ▼ | ─── | Reset | ☀/🌙 | ⌘K | ? | ℹ | Shrink │
├──────────────┬──────────────────────┬───────────────────────────────────┤
│  Document    │                      │   Page Editor                     │
│   Pages      │      Preview         │   (Resize/Crop, Scale, Rotate,    │
│  (left)      │     (centre)         │    Orientation, Order, Batch)     │
├──────────────┴──────────────────────┴───────────────────────────────────┤
│  STATUS BAR  (status text · import progress bar · Word: ✓ / ✕)          │
├─────────────────────────────────────────────────────────────────────────┤
│ [Page Numbers] [⚙] | [⚡ Optimize] | Output: [...] [🏠 Docs] [📁] [💾 Save] │
└─────────────────────────────────────────────────────────────────────────┘
```

### Step-by-Step Workflow

#### 1. Add Files
Click **➕ Add Files** in the toolbar (`A`), or drag and drop files directly from **Windows Explorer** onto the application window.

- Hold **Ctrl** or **Shift** in the file dialog for multi-select
- An animated progress bar (red → blue) tracks multi-file imports in the status bar
- Supported types: `.jpg`, `.jpeg`, `.png`, `.gif` *(all frames)*, `.bmp`, `.tiff`, `.tif`, `.webp`, `.pdf`, `.doc`, `.docx` (MS Word or `python-docx` fallback), `.txt`, `.nautilus` projects (`Ctrl+O`), and optional 3D models (`.gltf`, `.glb`, `.obj`, `.stl`, `.fbx`)

#### 2. Review and Reorder Pages
Pages appear in the **Document Pages** panel on the left.

- The selected page has a **green border**
- **Drag and drop** page rows directly in the list, press `Alt+↑` / `Alt+↓`, or use **▲ Up** / **▼ Down**
- Use **✕ Remove** (or `Delete` / `Backspace`) to remove a page — press `Ctrl+Z` anytime to undo

#### 3. Edit Individual Pages & Batch Operations
With a page selected, use the **Page Editor** panel on the right:

- **Image Editing (`Resize` / `Crop`):**
  - **Resize mode:** Drag the **four green corner handles** to resize (aspect ratio locked), drag **inside the image** to pan/reposition, or adjust the **Image Scale** slider (`10%–300%`). Click **Reset** (or **⊞ Fill Page**) to reset scale, offsets, and crop.
  - **Crop mode:** Switch to **Crop**, drag the **blue dashed corner handles**, and click **✂️ Apply**.
  - **↩️ Undo / ↪️ Redo (`Ctrl+Z` / `Ctrl+Y`):** Step backward or forward through up to 50 document edits.
- **Image Rotation (`0°` / `90°` / `180°` / `270°`):** Rotates image content independently of page orientation (check **Apply to all pages** to rotate all pages together).
- **Page Orientation (`Portrait` / `Landscape`):** Switches page canvas orientation.
- **Page Order & Creation:** **▲ Move Up**, **▼ Move Down**, **📄 Duplicate**, and **➕ Blank Page**.
- **Entire Document:** Batch-rotate all pages, **All Portrait** / **All Landscape**, **⇅ Reverse**, and **🔤 Sort A→Z**.

#### 4. Document, Overlay, Metadata & Security Settings (`⚙`)
Toggle **Page Numbers** (`N`) for a live overlay, and click **⚙** to open **Document & Page Number Settings**:

1. **Document Layout:** Choose **Page Size** (`A4`, `Letter`, `Legal`, `A3`, `A5`, or `Fit` to match image dimensions) and optional **Export Page Range** (e.g. `1-3, 5`).
2. **Page Numbering & Position:** Enable numbering, **Skip cover page (Page 1)**, **Position** (`top`/`bottom`), **Alignment** (`left`/`center`/`right`).
3. **Format & Typography:** Style (`plain`, `dashes`, `page_x`, `page_x_of_y`), Font, Font Size (`6–24 pt`), Color (hex).
4. **Watermark & Header/Footer:** Optional centered diagonal **Watermark** (text, opacity `5%–60%`, hex color), top-left **Header**, and bottom-left **Footer** — all previewed live in the centre panel.
5. **PDF Metadata & Security:** Optional embedded `Title`, `Author`, `Subject`, and session-only **AES-256 PDF Password** (kept in memory only — never written to disk).

#### 5. Projects (`.nautilus`) & Exporting PDFs
- **Save / Open Project:** Press `Ctrl+Shift+S` to save a `.nautilus` project file preserving your page queue, crops, rotations, scales, blank pages, and settings; press `Ctrl+O` (or select from the Command Palette `Ctrl+K`) to reopen it later.
- **Export PDF (`E`):** Optionally check **⚡ Optimize for file size** (`150 dpi · JPEG 75%`), choose an output folder (`📁` / `🏠 Docs`), and click **💾 Save PDF**.

#### 6. Shrink an Existing PDF (`📉 Shrink a PDF`, `S`)
Compress any standalone PDF with 4 presets:
- **Light — Non-destructive:** Object deduplication, metadata/thumbnail strip, font subsetting, and stream compression with zero image resampling.
- **Standard — Adobe Free / Apple Quartz:** 150 DPI / JPEG 75%.
- **Aggressive — Maximum Size Reduction:** 96 DPI / JPEG 50% (destructive: visible photo loss, removes annotations and flattens form fields).
- **Grayscale — Smallest Possible:** 120 DPI / JPEG 65% grayscale (destructive: permanently removes color, annotations, and forms).

---

## Part 2 — Paper Nautilus Web Edition

### Launching, Privacy & Session Auto-Recovery
- Open [https://pdfmaker.11mosswood.us/app/](https://pdfmaker.11mosswood.us/app/) (or run `python web/server.py` locally and visit `http://localhost:8080`).
- **100% client-side:** All conversion, rendering, compression, and PDF assembly happen in your browser.
- **Automatic Session Recovery:** Your active page queue and edits are automatically saved locally in browser **IndexedDB** and restored if you reload the tab.

### Workflow
1. **Add Files or Try a Sample:** Drop files into **Document Pages**, click **➕ Add Files** (`A`), or click **✨ Load 3-Page Sample Report**. Supports images (`.jpg`, `.jpeg`, `.png`, `.gif`, `.bmp`, `.webp`, `.svg`), `.pdf`, `.docx`, text (`.txt`, `.md`, `.csv`, `.log`, `.json`), and 3D (`.gltf`, `.glb`).
2. **Reorder & Manage Pages:** Drag and drop page cards, press `Alt+↑` / `Alt+↓`, or use **📄 Duplicate**, **➕ Blank Page**, **⇅ Reverse**, and **🔤 Sort A→Z**.
3. **Interactive Canvas Preview:**
   - **Resize mode (`↔️ Resize`):** Drag green corner handles to resize (aspect-ratio locked), drag inside the image to pan, or use the **Image Scale** slider (`10%–300%`).
   - **Crop mode (`✂️ Crop`):** Switch to Crop, drag the blue dashed corner handles over the image, and click **✂️ Apply Crop**.
   - **↩️ Undo / ↪️ Redo (`Ctrl/⌘+Z` / `Ctrl/⌘+Y`):** Multi-step history across all page actions.
   - Zoom with **−** / **+** / **Fit** (`F`) or `Ctrl/⌘ + scroll`. On screens `≤ 960px`, switch between **Pages / Preview / Editor** tabs.
4. **3D Model Snapshots (`.gltf` / `.glb`):** Orbit and zoom in the WebGL modal, then click **📸 Capture to Page**.
5. **Quick Settings & Full Settings (`G`):**
   - Configure **Page Size** (`A4`, `Letter`, `Legal`, `A3`, `A5`, `Fit`), **Page Numbering** (including **Skip page 1**), **Export Quality** (`Archival`, `Balanced`, `Compact`), and **Output Filename** in the sidebar.
   - Press `G` (or click **⚙️ Settings**) for Default Import Orientation, Image Framing (`Edge-to-Edge Fill` vs. `Fit with Page Margins`), **Export Page Range**, **Watermark** (text, opacity `5%–60%`, color), **Running Header / Footer**, **PDF Metadata** (`Title`, `Author`, `Subject`), Theme, live change-diff preview, and **↺ Reset Defaults**.
6. **Shrink PDF (`S`):** Compress an existing PDF (or click **📄 Use Sample PDF**) using **Light** (`200 DPI`), **Standard** (`150 DPI`), **Aggressive** (`96 DPI`), or **Grayscale** (`120 DPI`).
   > **Note:** Browser compression rasterizes pages via PDF.js (removing searchable text and links). If rasterization does not reduce size, the original PDF is automatically kept.
7. **Download PDF (`E`):** Click **💾 Download PDF** (`E` or `Ctrl/⌘ + S`). Unedited `.txt`/`.docx` pages export as searchable native vector text.

---

## Command Palette & Keyboard Shortcuts

Both editions include a searchable **Command Palette (`Ctrl+K` / `⌘K`)** and **Keyboard Shortcuts (`?`)** overlay. Single-key shortcuts automatically pause while typing in text inputs.

| Shortcut | Windows Desktop | Paper Nautilus Web |
|---|---|---|
| `Ctrl+K` / `⌘+K` | Open Command Palette | Open Command Palette |
| `Ctrl+Z` / `⌘+Z` | Undo Last Action | Undo Last Change |
| `Ctrl+Y` / `Ctrl+Shift+Z` | Redo Last Action | Redo Change |
| `Ctrl+O` | Open `.nautilus` Project | — |
| `Ctrl+Shift+S` | Save `.nautilus` Project | — |
| `Alt + ↑ / ↓` | Reorder Selected Page Up / Down | Reorder Selected Page Up / Down |
| `?` | Show Keyboard Shortcuts | Show Keyboard Shortcuts |
| `A` | Add Files | Add Files |
| `E` | Save / Export PDF | Download / Export PDF |
| `Ctrl/⌘ + S` | — | Quick Save / Export PDF |
| `S` | Open Shrink a PDF | Open Shrink / Compress PDF |
| `R` | Rotate Selected Page +90° | Rotate Selected Image +90° |
| `O` | Toggle Portrait / Landscape | Toggle Portrait / Landscape |
| `N` | Toggle Page Numbers | Toggle Page Numbers |
| `F` | Fit Preview Zoom | Fit Page to Preview |
| `G` | — | Open Document Settings |
| `T` | Toggle Dark / Light Theme | Toggle Dark / Light Theme |
| `←` / `→` | Previous / Next Page | Previous / Next Page *(also `[` / `]`)* |
| `+` / `−` | Zoom buttons in preview | Zoom In / Zoom Out *(also `Ctrl/⌘+Scroll`)* |
| `Delete` / `Backspace` | Remove Selected Page | Delete Selected Page |
| `Esc` | Close Active Dialog | Close Active Overlay |

---

## Frequently Asked Questions

**Q: How do I change the page size (A4, Letter, Legal, A3, A5, or Fit)?**
A: On Desktop, click **⚙** next to the Page Numbers switch and choose from the **Page Size** menu. On Web, use the **Page Size** dropdown in the right sidebar or press `G` to open Settings. **Fit** automatically matches each image's aspect ratio.

**Q: Word documents show a warning or lose formatting — why?**
A: On Desktop, full-fidelity `.doc`/`.docx` conversion uses Microsoft Word (`docx2pdf`). If Word is not installed, it falls back to `python-docx` plain-text extraction. On Web, `.docx` files use Mammoth.js text extraction, and legacy `.doc` files are unsupported.

**Q: Can I undo multiple steps or save my work-in-progress?**
A: Yes — both editions support up to 50 steps of Undo/Redo (`Ctrl+Z` / `Ctrl+Y`). Desktop can save/reopen `.nautilus` project files (`Ctrl+Shift+S` / `Ctrl+O`), and Web automatically persists your active workspace in browser IndexedDB.

**Q: Is my Desktop PDF password stored anywhere?**
A: No. The optional AES-256 password is held strictly in memory for the current session and is never written to `settings.json` or `.nautilus` project files.

---

## Troubleshooting

| Issue | Fix |
|---|---|
| Desktop app won't start | Ensure Python 3.10+ is installed and run `pip install -r requirements.txt` |
| Desktop progress bar stays red | Multi-file import encountered an error; check the Import Warnings dialog |
| Blank preview on Desktop | The file may have failed conversion; try removing and re-adding it |
| PDF won't save on Desktop | Verify the output folder exists, page range syntax is valid, and you have write permissions |
| Web 3D viewer fails to open | Your browser/device needs WebGL enabled; all other PDF tools continue working without WebGL |

---

*PDF Maker · Paper Nautilus v2.0.0 — https://github.com/gavinfischer-keenan/ReportPDFmaker*
