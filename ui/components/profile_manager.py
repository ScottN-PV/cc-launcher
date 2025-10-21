"""
Profile Manager UI Component - Profile selection and management controls.

Provides a combobox for profile selection with New/Save/Delete buttons.
Shows profile metadata (last used, modified date) below the combobox.
"""

import logging
import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from typing import Callable, Dict, Optional
from datetime import datetime

from models.profile import Profile

logger = logging.getLogger(__name__)


class ProfileManager(ttk.Frame):
    """Profile selection and management UI component."""

    def __init__(
        self,
        parent,
        profiles: Dict[str, Profile],
        current_profile_id: Optional[str] = None,
        on_select: Optional[Callable[[str], None]] = None,
        on_new: Optional[Callable[[], None]] = None,
        on_save: Optional[Callable[[str], None]] = None,
        on_delete: Optional[Callable[[str], None]] = None
    ):
        """
        Initialize profile manager component.

        Args:
            parent: Parent widget
            profiles: Dictionary of profile_id -> Profile
            current_profile_id: Currently selected profile ID
            on_select: Callback when profile is selected (profile_id)
            on_new: Callback when New Profile is clicked
            on_save: Callback when Save Profile is clicked (profile_id)
            on_delete: Callback when Delete Profile is clicked (profile_id)
        """
        super().__init__(parent)

        self.profiles = profiles
        self.current_profile_id = current_profile_id
        self.on_select = on_select
        self.on_new = on_new
        self.on_save = on_save
        self.on_delete = on_delete

        # Configure grid
        self.columnconfigure(0, weight=1)  # Profile selector expands
        self.columnconfigure(1, weight=0)  # Buttons fixed width

        self._build_ui()
        self._update_profile_list()

    def _build_ui(self):
        """Build the profile manager UI."""

        # ===== Row 0: Profile Selector and Buttons =====
        selector_frame = ttk.Frame(self)
        selector_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 5))
        selector_frame.columnconfigure(0, weight=1)

        # Profile combobox
        self.profile_var = tk.StringVar()
        self.profile_combo = ttk.Combobox(
            selector_frame,
            textvariable=self.profile_var,
            state="readonly",
            width=30
        )
        self.profile_combo.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        self.profile_combo.bind("<<ComboboxSelected>>", self._on_profile_selected)

        # Button frame
        button_frame = ttk.Frame(selector_frame)
        button_frame.grid(row=0, column=1, sticky="e")

        # New Profile button
        self.new_button = ttk.Button(
            button_frame,
            text="New",
            command=self._on_new_clicked,
            bootstyle="primary-outline",
            width=8
        )
        self.new_button.pack(side=LEFT, padx=2)

        # Save Profile button
        self.save_button = ttk.Button(
            button_frame,
            text="Save",
            command=self._on_save_clicked,
            bootstyle="success-outline",
            width=8
        )
        self.save_button.pack(side=LEFT, padx=2)

        # Delete Profile button
        self.delete_button = ttk.Button(
            button_frame,
            text="Delete",
            command=self._on_delete_clicked,
            bootstyle="danger-outline",
            width=8
        )
        self.delete_button.pack(side=LEFT, padx=2)

        # ===== Row 1: Profile Metadata =====
        self.metadata_label = ttk.Label(
            self,
            text="No profile selected",
            font=("Segoe UI", 9),
            foreground="gray"
        )
        self.metadata_label.grid(row=1, column=0, columnspan=2, sticky="w", pady=(2, 0))

    def _update_profile_list(self):
        """Update the profile combobox with current profiles."""
        # Get profile display names (sorted by name)
        profile_items = sorted(
            [(pid, p.name) for pid, p in self.profiles.items()],
            key=lambda x: x[1].lower()
        )

        # Update combobox values
        display_names = [name for _, name in profile_items]
        self.profile_combo["values"] = display_names

        # Create reverse lookup for display name -> profile ID
        self.display_to_id = {name: pid for pid, name in profile_items}
        self.id_to_display = {pid: name for pid, name in profile_items}

        # Select current profile if set
        if self.current_profile_id and self.current_profile_id in self.id_to_display:
            self.profile_var.set(self.id_to_display[self.current_profile_id])
            self._update_metadata_display()
        elif display_names:
            # Select first profile by default
            self.profile_var.set(display_names[0])
            self.current_profile_id = self.display_to_id[display_names[0]]
            self._update_metadata_display()

        # Enable/disable buttons based on selection
        self._update_button_states()

    def _update_metadata_display(self):
        """Update the metadata label with current profile info."""
        if not self.current_profile_id or self.current_profile_id not in self.profiles:
            self.metadata_label.configure(text="No profile selected")
            return

        profile = self.profiles[self.current_profile_id]

        # Format metadata
        parts = []

        # Server count
        parts.append(f"{len(profile.servers)} server(s)")

        # Last used
        if profile.last_used:
            last_used_str = self._format_datetime(profile.last_used)
            parts.append(f"Last used: {last_used_str}")

        # Modified
        modified_str = self._format_datetime(profile.modified)
        parts.append(f"Modified: {modified_str}")

        # Description (if present)
        if profile.description:
            parts.append(f"• {profile.description}")

        metadata_text = " | ".join(parts)
        self.metadata_label.configure(text=metadata_text)

    def _format_datetime(self, dt: datetime) -> str:
        """
        Format datetime for display.

        Args:
            dt: datetime object

        Returns:
            Formatted string like "2 hours ago" or "Jan 15, 2024"
        """
        now = datetime.now()
        delta = now - dt

        # Less than 1 minute
        if delta.total_seconds() < 60:
            return "just now"

        # Less than 1 hour
        if delta.total_seconds() < 3600:
            minutes = int(delta.total_seconds() / 60)
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"

        # Less than 24 hours
        if delta.total_seconds() < 86400:
            hours = int(delta.total_seconds() / 3600)
            return f"{hours} hour{'s' if hours != 1 else ''} ago"

        # Less than 7 days
        if delta.days < 7:
            return f"{delta.days} day{'s' if delta.days != 1 else ''} ago"

        # More than 7 days - show date
        return dt.strftime("%b %d, %Y")

    def _update_button_states(self):
        """Enable/disable buttons based on current state."""
        has_selection = self.current_profile_id is not None

        # Save and Delete require a selection
        if has_selection:
            self.save_button.configure(state="normal")
            self.delete_button.configure(state="normal")
        else:
            self.save_button.configure(state="disabled")
            self.delete_button.configure(state="disabled")

        # New is always enabled
        self.new_button.configure(state="normal")

    def _on_profile_selected(self, event=None):
        """Handle profile selection from combobox."""
        display_name = self.profile_var.get()

        if display_name not in self.display_to_id:
            logger.warning(f"Unknown profile selected: {display_name}")
            return

        profile_id = self.display_to_id[display_name]

        if profile_id == self.current_profile_id:
            return  # No change

        self.current_profile_id = profile_id
        self._update_metadata_display()
        self._update_button_states()

        logger.info(f"Profile selected: {profile_id}")

        # Call callback
        if self.on_select:
            self.on_select(profile_id)

    def _on_new_clicked(self):
        """Handle New Profile button click."""
        logger.info("New Profile button clicked")
        if self.on_new:
            self.on_new()

    def _on_save_clicked(self):
        """Handle Save Profile button click."""
        if not self.current_profile_id:
            logger.warning("Save Profile clicked but no profile selected")
            return

        logger.info(f"Save Profile button clicked: {self.current_profile_id}")
        if self.on_save:
            self.on_save(self.current_profile_id)

    def _on_delete_clicked(self):
        """Handle Delete Profile button click."""
        if not self.current_profile_id:
            logger.warning("Delete Profile clicked but no profile selected")
            return

        logger.info(f"Delete Profile button clicked: {self.current_profile_id}")
        if self.on_delete:
            self.on_delete(self.current_profile_id)

    # ===== Public Methods =====

    def load_profiles(self, profiles: Dict[str, Profile], current_profile_id: Optional[str] = None):
        """
        Load profiles into the component.

        Args:
            profiles: Dictionary of profile_id -> Profile
            current_profile_id: Profile to select (optional)
        """
        self.profiles = profiles

        if current_profile_id:
            self.current_profile_id = current_profile_id

        self._update_profile_list()
        logger.info(f"Loaded {len(profiles)} profile(s)")

    def select_profile(self, profile_id: str):
        """
        Programmatically select a profile.

        Args:
            profile_id: Profile ID to select
        """
        if profile_id not in self.profiles:
            logger.warning(f"Cannot select unknown profile: {profile_id}")
            return

        self.current_profile_id = profile_id

        if profile_id in self.id_to_display:
            self.profile_var.set(self.id_to_display[profile_id])
            self._update_metadata_display()
            self._update_button_states()
            logger.info(f"Profile selected: {profile_id}")

    def get_selected_profile_id(self) -> Optional[str]:
        """
        Get the currently selected profile ID.

        Returns:
            Profile ID or None
        """
        return self.current_profile_id

    def refresh_metadata(self):
        """Refresh the metadata display for current profile."""
        self._update_metadata_display()