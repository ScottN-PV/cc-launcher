"""Project Path Selector UI Component for Claude Code Launcher."""

import logging
import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from tkinter import filedialog
from pathlib import Path
from typing import Callable, List, Optional

from utils.validators import validate_path

logger = logging.getLogger(__name__)


class ProjectSelector(ttk.Frame):
    """Project path selector component with browse button and validation."""

    def __init__(
        self,
        parent,
        on_path_changed: Callable[[str], None],
        initial_path: str = "",
        recent_paths: Optional[List[str]] = None,
        **kwargs
    ):
        """
        Initialize project selector.

        Args:
            parent: Parent widget
            on_path_changed: Callback when path changes (receives path string)
            initial_path: Initial project path
            **kwargs: Additional frame options
        """
        super().__init__(parent, **kwargs)

        self.on_path_changed = on_path_changed
        self.current_path = initial_path
        self.recent_paths: List[str] = list(recent_paths or [])

        self._create_widgets()
        self._layout_widgets()

        # Set initial path if provided
        if initial_path:
            self.set_path(initial_path)

    def _create_widgets(self):
        """Create UI widgets."""
        # Path entry
        self.path_var = tk.StringVar(value=self.current_path)
        self.path_var.trace_add("write", self._on_path_entry_changed)

        self.path_combo = ttk.Combobox(
            self,
            textvariable=self.path_var,
            values=self.recent_paths,
            font=("Segoe UI", 10)
        )
        # Allow manual text entry
        self.path_combo.configure(state="normal")

        # Browse button
        self.browse_button = ttk.Button(
            self,
            text="📁 Browse",
            command=self._on_browse_clicked,
            bootstyle="secondary",
            width=12
        )

        # Validation indicator
        self.indicator_label = ttk.Label(
            self,
            text="",
            font=("Segoe UI", 12)
        )

    def _layout_widgets(self):
        """Layout widgets in grid."""
        self.columnconfigure(1, weight=1)

        self.indicator_label.grid(row=0, column=0, padx=(0, 5))
        self.path_combo.grid(row=0, column=1, sticky=EW, padx=5)
        self.browse_button.grid(row=0, column=2, padx=(5, 0))

    def _on_browse_clicked(self):
        """Handle browse button click."""
        logger.info("Browse button clicked")

        # Open directory picker
        initial_dir = self.current_path if self.current_path and Path(self.current_path).exists() else str(Path.home())

        selected_path = filedialog.askdirectory(
            title="Select Project Directory",
            initialdir=initial_dir
        )

        if selected_path:
            self.set_path(selected_path)

    def _on_path_entry_changed(self, *args):
        """Handle path entry changes."""
        new_path = self.path_var.get()
        self._validate_and_update(new_path)

    def _validate_and_update(self, path: str):
        """
        Validate path and update indicator.

        Args:
            path: Path to validate
        """
        if not path:
            self.indicator_label.configure(text="")
            self.current_path = ""
            return

        # Validate path
        valid, message = validate_path(path)

        if valid:
            self.indicator_label.configure(text="✓", foreground="green")
            self.current_path = path

            # Trigger callback
            try:
                self.on_path_changed(path)
            except Exception as e:
                logger.error(f"Error in path changed callback: {e}")
        else:
            self.indicator_label.configure(text="✗", foreground="red")
            self.current_path = ""

    def set_path(self, path: str):
        """
        Set project path programmatically.

        Args:
            path: Project path to set
        """
        self.path_var.set(path)
        self._validate_and_update(path)

    def get_path(self) -> str:
        """
        Get current valid project path.

        Returns:
            Current project path (empty string if invalid)
        """
        return self.current_path

    def is_valid(self) -> bool:
        """
        Check if current path is valid.

        Returns:
            True if path is valid
        """
        return bool(self.current_path)

    def update_recent_paths(self, paths: List[str]):
        """Update the recent paths dropdown values."""
        self.recent_paths = list(dict.fromkeys(paths))  # preserve order, ensure unique
        self.path_combo.configure(values=self.recent_paths)
