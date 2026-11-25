"""
Project Manager (.nautilus)
===========================
Serializes and deserializes PDF Maker document projects (page queue,
per-page edits, and document settings) as JSON `.nautilus` files.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional

from .converters.pdf_builder import PageItem
from .settings_manager import DEFAULT_SETTINGS, SettingsManager

PROJECT_VERSION = 1
PROJECT_EXTENSION = ".nautilus"


def serialize_project(
    pages: list[PageItem],
    settings: SettingsManager,
    current_index: int = 0,
) -> dict[str, Any]:
    """Build a JSON-serializable manifest dictionary for the current project."""
    safe_settings = {
        k: settings.get(k)
        for k in DEFAULT_SETTINGS
        if "password" not in k.lower()
    }
    serialized_pages: list[dict[str, Any]] = []
    for p in pages:
        serialized_pages.append({
            "source_file": "" if p.is_blank else p.source_file,
            "source_type": p.source_type,
            "display_name": p.display_name,
            "rotation": int(p.rotation or 0),
            "page_landscape": bool(p.page_landscape),
            "image_rotation": int(p.image_rotation or 0),
            "image_scale": float(p.image_scale if p.image_scale is not None else 1.0),
            "image_offset_x": float(p.image_offset_x or 0.0),
            "image_offset_y": float(p.image_offset_y or 0.0),
            "image_crop": list(p.image_crop) if p.image_crop else None,
            "image_frame_index": int(p.image_frame_index or 0),
            "source_page_index": int(p.source_page_index or 0),
            "is_blank": bool(p.is_blank),
        })

    return {
        "version": PROJECT_VERSION,
        "current_index": int(current_index),
        "settings": safe_settings,
        "pages": serialized_pages,
    }


def save_project_file(
    project_path: str,
    pages: list[PageItem],
    settings: SettingsManager,
    current_index: int = 0,
) -> tuple[bool, str]:
    """Write the project manifest to disk."""
    try:
        out = Path(project_path)
        if out.suffix.lower() != PROJECT_EXTENSION:
            out = out.with_suffix(PROJECT_EXTENSION)
        out.parent.mkdir(parents=True, exist_ok=True)
        data = serialize_project(pages, settings, current_index)
        with open(out, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True, ""
    except Exception as e:
        return False, f"Could not save project: {e}"


def load_project_file(project_path: str) -> tuple[Optional[dict[str, Any]], str]:
    """Read and validate a `.nautilus` project file from disk."""
    if not os.path.isfile(project_path):
        return None, f"Project file not found: {project_path}"
    try:
        with open(project_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return None, f"Invalid project file: {e}"

    if not isinstance(data, dict) or data.get("version") != PROJECT_VERSION:
        return None, "Unsupported or corrupted .nautilus project version."
    if not isinstance(data.get("pages"), list):
        return None, "Project file is missing a valid pages list."
    return data, ""
