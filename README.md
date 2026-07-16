# 📄 PDF Maker

A professional desktop application for combining multiple file types into a single, polished PDF. Built with Python and CustomTkinter.

## Features

- **Multi-format input**: JPG, PNG, GIF, BMP, TIFF, WebP, TXT, DOC, DOCX, PDF, GLTF, GLB, OBJ, STL, and more
- **Live PDF preview** with zoom controls and page navigation
- **Page editor**: rotate (0°/90°/180°/270°) per page or all at once
- **Page reordering**: drag-and-drop style up/down controls
- **Page numbers**: fully customizable (position, alignment, font, size, color, offset)
- **Settings persistence**: remembers your output folder, preferences, and window state
- **Smart Word detection**: auto-detects Microsoft Word; falls back gracefully with warning
- **3D file support** (optional): renders GLTF/GLB/OBJ/STL to image (requires trimesh + pyrender)
- **Dark/Light theme** toggle
- **WCAG contrast checking** for all UI elements

## Requirements

- Python 3.10+
- Microsoft Word (optional, for full-fidelity .docx conversion)

## Installation

```bash
# 1. Clone the repo
git clone https://github.com/gavinfischer-keenan/ReportPDFmaker.git
cd ReportPDFmaker

# 2. Install dependencies
pip install -r requirements.txt

# 3. (Optional) 3D file support
pip install trimesh pyrender numpy

# 4. Run
python main.py
```

## Usage

1. Click **➕ Add Files** to select one or more files
2. Use the **File List** (left panel) to reorder or remove pages
3. Click any page to **preview** it in the center panel
4. Use the **Page Editor** (right panel) to rotate pages or apply rotation to the whole document
5. Toggle **Page Numbers** in the bottom bar and click ⚙ to customize them
6. Choose your output folder with **📁** or click **🏠 Docs** to reset to Documents
7. Click **💾 Save PDF** to build and save your document

## Project Structure

```
ReportPDFmaker/
├── main.py                          # Entry point
├── requirements.txt
├── pdf_maker/
│   ├── app.py                       # Application launcher
│   ├── controller.py                # Central state + event bus
│   ├── settings_manager.py          # JSON settings persistence
│   ├── converters/
│   │   ├── image_converter.py       # JPG/PNG/GIF → PDF
│   │   ├── text_converter.py        # TXT → PDF
│   │   ├── docx_converter.py        # DOCX → PDF (Word or text fallback)
│   │   ├── pdf_handler.py           # Import existing PDFs
│   │   ├── gltf_converter.py        # 3D models → image → PDF
│   │   └── pdf_builder.py           # Assemble final PDF + page numbers
│   ├── ui/
│   │   ├── main_window.py           # Root window layout
│   │   ├── file_list_panel.py       # Left panel: page queue
│   │   ├── preview_panel.py         # Center panel: live preview
│   │   ├── page_editor_panel.py     # Right panel: rotation + order
│   │   └── dialogs.py               # All modal dialogs
│   └── utils/
│       ├── color_utils.py           # WCAG contrast utilities
│       └── file_utils.py            # File type detection
```

## Settings

Settings are saved to `%APPDATA%\PDFMaker\settings.json`. Use the **🔄 Reset All** button to clear them.

## License

MIT
