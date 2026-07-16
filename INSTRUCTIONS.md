# PDF Maker — User Guide

## Getting Started

### Launching the App
- **Windows Executable:** Double-click `PDFMaker.exe`
- **From source:** Open a terminal and run `python main.py`

---

## The Interface

The window is divided into three panels:

```
┌──────────────┬──────────────────────┬─────────────────┐
│  Document    │                      │   Page Editor   │
│   Pages      │      Preview         │   (controls)    │
│  (left)      │     (centre)         │   (right)       │
└──────────────┴──────────────────────┴─────────────────┘
│  [Page Numbers toggle]          [Output Folder] [💾 Save PDF]  │
└────────────────────────────────────────────────────────────┘
```

---

## Step-by-Step Workflow

### 1. Add Files
Click **➕ Add Files** in the top toolbar.

- Hold **Ctrl** to select multiple individual files
- Hold **Shift** to select a range of files
- The progress bar (red → blue) shows import progress for large batches
- Supported types: JPG, PNG, GIF, BMP, TIFF, WebP, TXT, DOC, DOCX, PDF

### 2. Review and Reorder Pages
Pages appear in the **Document Pages** panel (left side).

- The **selected page** has a green border
- Click any row to select and preview that page
- Use **▲ Up** / **▼ Down** buttons (or the Page Editor panel) to reorder pages
- Use **✕ Remove** to delete a page from the document

### 3. Edit Individual Pages
With a page selected, use the **Page Editor** panel (right side):

#### Image Rotation
Rotates the **image content** on the page (the page canvas stays the same size):
- **0° / 90° / 180° / 270°** buttons
- The active rotation is highlighted in blue
- Check **Apply to all pages** to rotate every image at once

#### Page Orientation
Changes the **page canvas** between portrait and landscape:
- **⬜ Portrait** — tall page (e.g. 595×842 pts for A4)
- **⬛ Landscape** — wide page (e.g. 842×595 pts for A4)

#### Page Order
Move the selected page up or down in the document order.

#### Entire Document
Apply image rotation or orientation to every page at once.

### 4. Resize Images in the Preview
When an image page is selected, **four green corner handles** appear around the image in the preview panel.

- **Drag any corner** to resize the image (aspect ratio is always locked)
- The image clips to the page edge with no white border
- Click **⊞ Fill Page** (green button) to reset the image to fill the page edge-to-edge

### 5. Set Page Numbers
In the bottom save bar:

1. Toggle the **Page Numbers** switch to enable numbering
2. Click **⚙** to open page number settings:
   - **Style:** Plain (1), Dashes (— 1 —), Page X, Page X of Y
   - **Position:** Top or Bottom of the page
   - **Alignment:** Left, Center, or Right
   - **Font:** Choose from Helvetica, Times, Courier (and Bold variants)
   - **Font Size:** In points
   - **Offset from Edge:** Distance from the top/bottom edge in points
   - **Offset from Side:** Distance from the left/right edge (for left/right alignment)
   - **Color:** Choose a text color

When Page Numbers are enabled, they appear **overlaid on the preview** exactly as they will in the final PDF.

### 6. Save the PDF
1. Set the **output folder** using the 📁 button or click **🏠 Docs** to use your Documents folder
2. Click **💾 Save PDF**
3. Choose a filename in the save dialog
4. The PDF is assembled and saved — a progress bar shows assembly progress

---

## Tips & Shortcuts

| Action | How |
|---|---|
| Select multiple files | Ctrl+click or Shift+click in the file dialog |
| Preview next/previous page | Click ◀ ▶ in the preview panel |
| Zoom in/out | Click − and + in the preview panel |
| Reset zoom | Click ⊡ Fit |
| Reset everything | Click 🔄 Reset All in the toolbar |
| Switch dark/light theme | Click ☀/🌙 in the top-right of the toolbar |

---

## Frequently Asked Questions

**Q: Word documents aren't importing — I see a warning.**
A: Microsoft Word must be installed for `.doc`/`.docx` conversion. The app uses Word's built-in PDF export. If Word isn't available, use a pre-converted PDF instead.

**Q: The image doesn't fill the whole page.**
A: Click **⊞ Fill Page** in the preview panel to reset the scale to fill the page edge-to-edge.

**Q: How do I change the page size (A4 vs Letter)?**
A: The page size setting is in the application settings (saved in `%APPDATA%\PDFMaker\settings.json`). A settings dialog will be added in a future release.

**Q: Where are my settings saved?**
A: `%APPDATA%\PDFMaker\settings.json` — this file is created automatically on first run.

**Q: Can I rotate only the page, not the image on it?**
A: Yes — use the **Page Orientation** buttons (Portrait/Landscape) in the Page Editor. The **Image Rotation** buttons rotate only the image content.

---

## Troubleshooting

| Issue | Fix |
|---|---|
| App won't start | Ensure Python 3.10+ is installed; run `pip install -r requirements.txt` |
| Progress bar stays red | Multi-file import failed; check the warnings dialog that appears |
| Blank preview | The file may not have converted correctly; try removing and re-adding it |
| PDF won't save | Check the output folder exists and you have write permissions |

---

*PDF Maker v1.0.0 — https://github.com/gavinfischer-keenan/ReportPDFmaker*
