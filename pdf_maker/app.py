"""
PDF Maker Application Bootstrap
================================
Initialises CustomTkinter, loads settings, and launches the main window.
"""

import customtkinter as ctk

from .settings_manager import SettingsManager
from .controller import AppController
from .ui.main_window import MainWindow


class PDFMakerApp:
    """Top-level application launcher."""

    def __init__(self):
        self.settings   = SettingsManager()
        self.controller = AppController(self.settings)

    def run(self) -> None:
        theme     = self.settings.get("theme", "dark")
        ctk_theme = self.settings.get("color_theme", "dark-blue")
        ctk.set_appearance_mode(theme.capitalize())
        ctk.set_default_color_theme(ctk_theme)

        window = MainWindow(self.controller, self.settings)
        window.mainloop()
