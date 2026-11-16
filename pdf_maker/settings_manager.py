"""
Settings Manager
================
Handles loading and saving all application settings to
%APPDATA%\\PDFMaker\\settings.json
"""

import json
import os
from pathlib import Path
from typing import Any


DEFAULT_SETTINGS: dict[str, Any] = {
    # Output
    "output_folder": str(Path.home() / "Documents"),
    "last_filename": "output.pdf",
    "page_size": "A4",           # "A4" | "Letter"

    # Page Numbers
    "page_numbers": False,
    "page_number_position": "bottom",    # "top" | "bottom"
    "page_number_alignment": "center",   # "left" | "center" | "right"
    "page_number_font": "Helvetica",     # PDF base font name
    "page_number_font_size": 10,         # Points
    "page_number_offset_from_edge": 20,  # Points from top/bottom edge
    "page_number_offset_from_side": 50,  # Points from left/right edge (for left/right align)
    "page_number_style": "plain",        # "plain"=1, "dashes"=— 1 —, "page_x"=Page 1, "page_x_of_y"=Page 1 of N
    "page_number_color": "#000000",
    "skip_cover_page": False,

    # Appearance
    "theme": "dark",             # "dark" | "light" | "system"
    "color_theme": "dark-blue",  # CTk built-in color theme

    # Window
    "window_width": 1280,
    "window_height": 800,
    "window_x": -1,              # -1 = center on screen
    "window_y": -1,

    # Behavior
    "default_rotation": 0,
    "auto_preview": True,        # Auto-refresh preview when pages change
    "confirm_reset": True,       # Ask for confirmation before reset
    "optimize_file_size": False, # Default JPEG quality 95 vs 75
    "word_available": None,      # None = not yet checked; True/False = result of check
}

FONT_OPTIONS = [
    "Helvetica",
    "Times-Roman",
    "Courier",
    "Helvetica-Bold",
    "Times-Bold",
    "Courier-Bold",
]

PAGE_NUMBER_STYLES = {
    "plain": "1",
    "dashes": "— 1 —",
    "page_x": "Page 1",
    "page_x_of_y": "Page 1 of N",
}


class SettingsManager:
    """Manages persistent application settings stored as JSON."""

    def __init__(self):
        self._settings_dir = Path(
            os.environ.get("APPDATA", str(Path.home()))
        ) / "PDFMaker"
        self._settings_file = self._settings_dir / "settings.json"
        self._settings: dict[str, Any] = {}
        self.load()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load(self) -> None:
        """Load settings from disk, falling back to defaults for missing keys."""
        try:
            if self._settings_file.exists():
                with open(self._settings_file, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                # Merge: loaded values override defaults, but new default keys are added
                self._settings = {**DEFAULT_SETTINGS, **loaded}
            else:
                self._settings = DEFAULT_SETTINGS.copy()
        except Exception as e:
            print(f"[Settings] Failed to load settings: {e} — using defaults")
            self._settings = DEFAULT_SETTINGS.copy()

    def save(self) -> None:
        """Save current settings to disk."""
        try:
            self._settings_dir.mkdir(parents=True, exist_ok=True)
            with open(self._settings_file, "w", encoding="utf-8") as f:
                json.dump(self._settings, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[Settings] Failed to save settings: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """Get a setting value."""
        if key in self._settings:
            return self._settings[key]
        if default is not None:
            return default
        return DEFAULT_SETTINGS.get(key)

    def set(self, key: str, value: Any, auto_save: bool = True) -> None:
        """Set a setting value and optionally save to disk."""
        self._settings[key] = value
        if auto_save:
            self.save()

    def set_many(self, updates: dict[str, Any], auto_save: bool = True) -> None:
        """Set multiple settings at once."""
        self._settings.update(updates)
        if auto_save:
            self.save()

    def reset(self) -> None:
        """Reset all settings to defaults and save."""
        self._settings = DEFAULT_SETTINGS.copy()
        self.save()

    def get_page_number_settings(self) -> dict[str, Any]:
        """Return all page number-related settings as a dict."""
        return {
            "enabled": self.get("page_numbers"),
            "position": self.get("page_number_position"),
            "alignment": self.get("page_number_alignment"),
            "font": self.get("page_number_font"),
            "font_size": self.get("page_number_font_size"),
            "offset_from_edge": self.get("page_number_offset_from_edge"),
            "offset_from_side": self.get("page_number_offset_from_side"),
            "style": self.get("page_number_style"),
            "color": self.get("page_number_color"),
            "skip_cover_page": self.get("skip_cover_page", False),
        }

    @property
    def output_folder(self) -> str:
        folder = self.get("output_folder")
        # Validate the folder still exists; fall back to Documents
        if not os.path.isdir(folder):
            folder = str(Path.home() / "Documents")
            self.set("output_folder", folder)
        return folder

    @output_folder.setter
    def output_folder(self, value: str) -> None:
        self.set("output_folder", value)

    @property
    def settings_file_path(self) -> str:
        return str(self._settings_file)


SETTING_LABELS: dict[str, str] = {
    "page_size": "Page Size",
    "page_numbers": "Page Numbers",
    "page_number_position": "Position",
    "page_number_alignment": "Alignment",
    "page_number_style": "Number Style",
    "page_number_font": "Font",
    "page_number_font_size": "Font Size",
    "page_number_color": "Text Color",
    "skip_cover_page": "Skip Cover Page",
    "theme": "Theme",
    "optimize_file_size": "Optimize File Size",
    "confirm_reset": "Confirm Before Reset",
}


def compute_settings_diff(
    old_values: dict[str, Any], new_values: dict[str, Any]
) -> list[str]:
    """Return human-readable descriptions of changed setting keys."""
    changes: list[str] = []
    for key, new_val in new_values.items():
        old_val = old_values.get(key)
        if old_val != new_val:
            label = SETTING_LABELS.get(key, key.replace("_", " ").title())
            changes.append(f"{label}: {old_val} → {new_val}")
    return changes
