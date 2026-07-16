"""
PDF Maker — Entry Point
=======================
Combines multiple file types (images, PDFs, Word docs, text files, 3D models)
into a single PDF with a modern GUI for page editing and preview.
"""

import sys
import os
import traceback


def check_dependencies() -> list[str]:
    """Check required packages and return list of missing ones."""
    required = {
        "customtkinter": "customtkinter",
        "fitz": "pymupdf",
        "PIL": "Pillow",
        "reportlab": "reportlab",
    }
    missing = []
    for module, package in required.items():
        try:
            __import__(module)
        except ImportError:
            missing.append(package)
    return missing


def main():
    """Application entry point."""
    # Check core dependencies first
    missing = check_dependencies()
    if missing:
        print("=" * 60)
        print("PDF Maker — Missing Required Packages")
        print("=" * 60)
        print(f"\nPlease install missing packages:\n")
        print(f"  pip install {' '.join(missing)}\n")
        print("Or run:  pip install -r requirements.txt")
        print("=" * 60)
        sys.exit(1)

    try:
        from pdf_maker.app import PDFMakerApp
        app = PDFMakerApp()
        app.run()
    except Exception as e:
        # Try to show a GUI error dialog if possible
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror(
                "PDF Maker — Fatal Error",
                f"An unexpected error occurred:\n\n{traceback.format_exc()}"
            )
            root.destroy()
        except Exception:
            print(f"Fatal Error: {e}")
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
