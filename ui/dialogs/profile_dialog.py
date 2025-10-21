"""
Profile Dialog - Create/edit profile dialog window.

Simple dialog for entering profile name and description.
Validates that profile names are unique.
"""

import logging
import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from typing import Optional, Callable, List
import re

logger = logging.getLogger(__name__)


class ProfileDialog(ttk.Toplevel):
    """Dialog for creating or editing a profile."""

    def __init__(
        self,
        parent,
        mode: str = "new",  # "new" or "edit"
        profile_id: Optional[str] = None,
        profile_name: Optional[str] = None,
        description: Optional[str] = None,
        existing_names: Optional[List[str]] = None,
        on_save: Optional[Callable[[str, str, str], None]] = None
    ):
        """Initialize profile dialog."""
        super().__init__(parent)

        self.mode = mode
        self.profile_id = profile_id
        self.existing_names = existing_names or []
        self.on_save = on_save
        self.result = None  # (profile_id, name, description) if saved

        # Configure window
        title = "New Profile" if mode == "new" else "Edit Profile"
        self.title(title)
        self.geometry("")
        self.minsize(520, 360)
        self.resizable(True, True)

        # Center on parent
        self.transient(parent)
        self.grab_set()
        self._center_on_parent(parent)
        self._auto_resize()
        self._auto_resize()

        # Build UI
        self._build_ui(profile_name, description)

        # Focus on name field
        self.name_entry.focus_set()

        logger.info(f"ProfileDialog opened in {mode} mode")
    def _center_on_parent(self, parent):
        """Center dialog on parent window."""
        self.update_idletasks()
        parent_x = parent.winfo_x()
        parent_y = parent.winfo_y()
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()

        dialog_width = self.winfo_width()
        dialog_height = self.winfo_height()

        x = parent_x + (parent_width - dialog_width) // 2
        y = parent_y + (parent_height - dialog_height) // 2

        self.geometry(f"+{x}+{y}")

    def _build_ui(self, initial_name: Optional[str], initial_description: Optional[str]):
        """Build the dialog UI."""

        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill=BOTH, expand=True)

        main_frame.columnconfigure(0, weight=0)
        main_frame.columnconfigure(1, weight=1)

        # Profile name
        name_label = ttk.Label(main_frame, text="Profile Name:", font=("Segoe UI", 10))
        name_label.grid(row=0, column=0, sticky="w", pady=(0, 10))

        self.name_var = tk.StringVar(value=initial_name or "")
        self.name_entry = ttk.Entry(main_frame, textvariable=self.name_var, width=40)
        self.name_entry.grid(row=0, column=1, sticky="ew", pady=(0, 10))

        self.name_error_label = ttk.Label(
            main_frame,
            text="",
            font=("Segoe UI", 9),
            foreground="red"
        )
        self.name_error_label.grid(row=1, column=1, sticky="w", pady=(0, 10))

        next_row = 2

        # Description
        desc_label = ttk.Label(main_frame, text="Description:", font=("Segoe UI", 10))
        desc_label.grid(row=next_row, column=0, sticky="nw", pady=(0, 10))

        self.desc_text = tk.Text(
            main_frame,
            height=6,
            width=40,
            font=("Segoe UI", 10),
            wrap=tk.WORD
        )
        self.desc_text.grid(row=next_row, column=1, sticky="nsew", pady=(0, 10))
        main_frame.rowconfigure(next_row, weight=1)

        if initial_description:
            self.desc_text.insert("1.0", initial_description)

        desc_scrollbar = ttk.Scrollbar(main_frame, orient=VERTICAL, command=self.desc_text.yview)
        desc_scrollbar.grid(row=next_row, column=2, sticky="ns", pady=(0, 10))
        self.desc_text.configure(yscrollcommand=desc_scrollbar.set)

        button_row = next_row + 1
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=button_row, column=0, columnspan=3, pady=(10, 0))

        self.save_button = ttk.Button(
            button_frame,
            text="Save" if self.mode == "edit" else "Create",
            command=self._on_save,
            bootstyle="success",
            width=12
        )
        self.save_button.pack(side=LEFT, padx=5)

        cancel_button = ttk.Button(
            button_frame,
            text="Cancel",
            command=self._on_cancel,
            bootstyle="secondary",
            width=12
        )
        cancel_button.pack(side=LEFT, padx=5)

        self.bind("<Return>", lambda e: self._on_save())
        self.bind("<Escape>", lambda e: self._on_cancel())

    def _auto_resize(self):
        """Ensure the window fits its content and respects the minimum size."""
        try:
            self.update_idletasks()
            width = max(self.winfo_reqwidth() + 20, self.minsize()[0])
            height = max(self.winfo_reqheight() + 20, self.minsize()[1])
            self.geometry(f"{int(width)}x{int(height)}")
        except tk.TclError:
            pass
    def _validate_input(self) -> tuple[bool, str]:
        """Validate input fields."""
        name = self.name_var.get().strip()

        if not name:
            return False, "Profile name is required"

        if len(name) > 50:
            return False, "Profile name too long (max 50 characters)"

        if not re.match(r'^[a-zA-Z0-9 _-]+$', name):
            return False, "Profile name can only contain letters, numbers, spaces, hyphens, and underscores"

        existing_lower = [existing_name.lower() for existing_name in self.existing_names]
        if self.mode == "new" or (self.mode == "edit" and name.lower() not in existing_lower):
            for existing_name in self.existing_names:
                if existing_name.lower() == name.lower():
                    return False, f"Profile '{name}' already exists"

        return True, ""
    def _on_save(self):
        """Handle Save button click."""
        is_valid, error_message = self._validate_input()

        if not is_valid:
            self.name_error_label.configure(text=error_message)
            logger.warning(f"Profile validation failed: {error_message}")
            return

        self.name_error_label.configure(text="")

        name = self.name_var.get().strip()
        description = self.desc_text.get("1.0", "end-1c").strip()

        if self.mode == "new":
            profile_id = re.sub(r'[^a-z0-9-]', '', name.lower().replace(' ', '-'))
            if not profile_id:
                profile_id = "profile"
            base_id = profile_id
            counter = 1
            used_ids = {existing_name.lower().replace(' ', '-') for existing_name in self.existing_names}
            while profile_id.lower() in used_ids:
                profile_id = f"{base_id}-{counter}"
                counter += 1
        else:
            profile_id = self.profile_id

        self.result = (profile_id, name, description)
        logger.info(f"Profile saved: {profile_id} (mode={self.mode})")

        if self.on_save:
            self.on_save(profile_id, name, description)

        self.destroy()
    def _on_cancel(self):
        """Handle Cancel button click."""
        logger.info("Profile dialog cancelled")
        self.result = None
        self.destroy()