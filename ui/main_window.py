"""Main application window for Claude Code Launcher."""

import asyncio
import logging
import threading
import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from pathlib import Path
from typing import Iterable, List, Optional
from tkinter import messagebox

from core.config_manager import ConfigManager
from core.profile_manager import ProfileManager as ProfileManagerCore
from core.terminal_manager import TerminalManager
from core.server_validator import ServerValidator
from ui.components.server_list import ServerList
from ui.components.profile_manager import ProfileManager
from ui.components.project_selector import ProjectSelector
from ui.components.launch_controls import LaunchCommandPanel
from ui.dialogs.server_dialog import ServerDialog
from ui.dialogs.profile_dialog import ProfileDialog
from utils.constants import (
    APP_NAME,
    WINDOW_DEFAULT_WIDTH,
    WINDOW_DEFAULT_HEIGHT,
    WINDOW_MIN_WIDTH,
    WINDOW_MIN_HEIGHT,
    THEMES
)

logger = logging.getLogger(__name__)


class MainWindow(ttk.Window):
    """Main application window with modern Windows 11 styling."""

    def __init__(self, config_manager: ConfigManager):
        """
        Initialize main window.

        Args:
            config_manager: Configuration manager instance
        """
        # Initialize preferences
        self.config_manager = config_manager
        preferences, servers, global_profiles = config_manager.load()

        # Determine initial theme
        initial_theme = THEMES.get(preferences.theme, "darkly")

        # Initialize ttkbootstrap window
        super().__init__(
            title=APP_NAME,
            themename=initial_theme,
            size=(WINDOW_DEFAULT_WIDTH, WINDOW_DEFAULT_HEIGHT),
            minsize=(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        )

        logger.info(f"MainWindow initialized with theme: {initial_theme}")

        # Store references
        self.current_theme = preferences.theme
        self.tray_manager = None  # Will be set by main.py
        self.servers = servers  # Store server data
        self.preferences = preferences  # Store preferences
        self.preferences.skip_validation = False
        self.preferences.recent_projects = self._sanitize_recent_projects(self.preferences.recent_projects)
        self.global_profiles = global_profiles  # Global profiles from config

        # Initialize profile manager (business logic)
        self.profile_manager_core = ProfileManagerCore(config_manager)
        self.profile_manager_core.set_current_project(self.preferences.last_path or None)
        self.profiles = self.profile_manager_core.get_all_profiles(self.preferences.last_path or None)

        # Initialize terminal manager
        self.terminal_manager = TerminalManager()

        # Initialize server validator
        self.server_validator = ServerValidator(skip_validation=False)

        # Internal flag to prevent recursive refresh loops when selecting profiles programmatically
        self._profile_selection_internal = False

        # Configure grid layout
        self.columnconfigure(0, weight=1)
        # Make both row 3 and row 4 expandable (server list can be in either depending on banner)
        self.rowconfigure(3, weight=1)
        self.rowconfigure(4, weight=1)

        # Build UI
        self._build_ui()
        self._refresh_profiles(select_profile_id=self.preferences.last_profile)
        self._ensure_window_capacity()

        # Configure window close behavior
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

        # Bind keyboard shortcuts
        self.bind("<Control-p>", lambda e: self._focus_profile_combobox())

        logger.info("MainWindow ready")

    def _build_ui(self):
        """Build the user interface with placeholder components."""

        # ===== Header with title and theme toggle =====
        header_frame = ttk.Frame(self, padding=10)
        header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))

        # Configure header grid
        header_frame.columnconfigure(1, weight=1)

        # App title
        title_label = ttk.Label(
            header_frame,
            text=APP_NAME,
            font=("Segoe UI", 16, "bold")
        )
        title_label.grid(row=0, column=0, sticky="w")

        # Theme toggle button
        self.theme_button = ttk.Button(
            header_frame,
            text="☀" if self.current_theme == "dark" else "🌙",
            width=3,
            command=self._toggle_theme,
            bootstyle="secondary"
        )
        self.theme_button.grid(row=0, column=2, sticky="e")

        # ===== Project Path Section =====
        project_frame = ttk.LabelFrame(self, text="Project Directory", padding=10)
        project_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=5)

        # Create ProjectSelector component
        self.project_selector = ProjectSelector(
            project_frame,
            on_path_changed=self._on_project_path_changed,
            initial_path=self.preferences.last_path or "",
            recent_paths=self.preferences.recent_projects
        )
        self.project_selector.pack(fill=X, expand=True)
        self.project_selector.update_recent_paths(self.preferences.recent_projects)

        # ===== Profile Section =====
        profile_frame = ttk.LabelFrame(self, text="Profile", padding=10)
        profile_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=5)

        # Create ProfileManager component
        self.profile_manager = ProfileManager(
            profile_frame,
            profiles=self.profiles,
            current_profile_id=self.preferences.last_profile,
            on_select=self._on_profile_select,
            on_new=self._on_profile_new,
            on_save=self._on_profile_save,
            on_delete=self._on_profile_delete
        )
        self.profile_manager.pack(fill=BOTH, expand=True)

        # ===== Offline Mode Warning Banner (Row 3 when shown) =====
        self.server_frame_row = 3

        # ===== Server List Section =====
        server_frame = ttk.LabelFrame(self, text="MCP Servers", padding=10)
        server_frame.grid(row=self.server_frame_row, column=0, sticky="nsew", padx=10, pady=5)
        self.server_frame = server_frame  # Store reference for regridding

        # Make server frame expandable
        server_frame.columnconfigure(0, weight=1)
        server_frame.rowconfigure(0, weight=1)

        # Create ServerList component
        self.server_list = ServerList(
            server_frame,
            on_server_toggle=self._on_server_toggle,
            on_add_server=self._on_add_server,
            on_edit_server=self._on_edit_server,
            on_delete_server=self._on_delete_server,
            on_validate_server=self._on_validate_server,
            on_validate_all=self._on_validate_all
        )
        self.server_list.grid(row=0, column=0, sticky="nsew")

        # Load servers into list
        self.server_list.load_servers(self.servers)

        # ===== Launch Controls Section =====
        launch_frame = ttk.Frame(self, padding=10)
        launch_frame.grid(row=5, column=0, sticky="ew", padx=10, pady=(5, 10))
        self.launch_frame = launch_frame  # Store reference for regridding

        # Configure launch frame grid
        launch_frame.columnconfigure(0, weight=1)

        # Create command panel component
        self.launch_panel = LaunchCommandPanel(launch_frame)
        self.launch_panel.grid(row=0, column=0, pady=5, sticky="ew")
        self.launch_panel.bind("<<LaunchCommandPanelUpdated>>", lambda _: self._ensure_window_capacity())

        self._refresh_launch_command()

    @staticmethod
    def _normalize_path(path: Optional[str]) -> Optional[str]:
        """Normalize a filesystem path for consistent storage."""
        if not path:
            return None
        try:
            return str(Path(path).resolve())
        except Exception:
            return path

    def _sanitize_recent_projects(self, paths: Iterable[str]) -> List[str]:
        """Ensure recent project paths are unique, normalized, and limited to 10 entries."""
        sanitized: List[str] = []
        seen = set()
        for raw_path in paths or []:
            if not raw_path:
                continue
            normalized = self._normalize_path(raw_path) or raw_path
            if normalized and normalized not in seen:
                sanitized.append(normalized)
                seen.add(normalized)
            if len(sanitized) >= 10:
                break
        return sanitized

    def _update_recent_projects(self, normalized_path: Optional[str]):
        """Insert the provided path at the top of the MRU list and refresh the selector."""
        if not normalized_path:
            return

        current = [normalized_path]
        current.extend(p for p in self.preferences.recent_projects if p and p != normalized_path)
        self.preferences.recent_projects = self._sanitize_recent_projects(current)

        if hasattr(self, "project_selector"):
            self.project_selector.update_recent_paths(self.preferences.recent_projects)

    def _refresh_profiles(self, select_profile_id: Optional[str] = None):
        """Refresh profile listings based on current project selection."""
        project_path = None
        if hasattr(self, "project_selector"):
            project_path = self.project_selector.get_path() or None

        # Fall back to stored preference if selector not available yet
        if not project_path:
            project_path = self.preferences.last_path or None

        project_path = self._normalize_path(project_path)

        self.profile_manager_core.set_current_project(project_path)
        self.global_profiles = self.profile_manager_core.list_profiles()
        combined_profiles = self.profile_manager_core.get_all_profiles(project_path)
        self.profiles = combined_profiles

        if not hasattr(self, "profile_manager"):
            return

        target_profile = select_profile_id or self.profile_manager.get_selected_profile_id()
        if target_profile not in combined_profiles:
            if self.preferences.last_profile in combined_profiles:
                target_profile = self.preferences.last_profile
            else:
                target_profile = next(iter(combined_profiles), None)

        self.profile_manager.load_profiles(combined_profiles, target_profile)
        if target_profile:
            self.profile_manager.select_profile(target_profile)
            # Load servers/states for this profile without triggering recursion
            self._profile_selection_internal = True
            self._on_profile_select(target_profile)
        else:
            # No profile available; reload base config servers for a clean state
            _, servers, _ = self.config_manager.load()
            self.servers = servers
            self.server_list.load_servers(self.servers)

        if target_profile:
            self.preferences.last_profile = target_profile
            if project_path:
                self.preferences.project_last_profiles[project_path] = target_profile
        elif project_path and project_path in self.preferences.project_last_profiles:
            # Remove stale mapping if no profile available
            self.preferences.project_last_profiles.pop(project_path, None)

    def _persist_config(self):
        """Persist current preferences and servers with latest profile state."""
        try:
            if hasattr(self, "current_theme") and self.current_theme:
                self.preferences.theme = self.current_theme

            current_path = None
            if hasattr(self, "project_selector") and self.project_selector:
                current_path = self.project_selector.get_path() or ""

            normalized_path = self._normalize_path(current_path) if current_path else None

            if normalized_path:
                self.preferences.last_path = normalized_path
            elif current_path:
                self.preferences.last_path = current_path
            elif current_path == "":
                self.preferences.last_path = ""

            if hasattr(self, "profile_manager") and self.profile_manager:
                selected_profile = self.profile_manager.get_selected_profile_id()
                if selected_profile:
                    self.preferences.last_profile = selected_profile
                    key = normalized_path or (current_path or None)
                    if key:
                        self.preferences.project_last_profiles[key] = selected_profile

            sanitized_map = {}
            for raw_path, profile_id in (self.preferences.project_last_profiles or {}).items():
                if not profile_id:
                    continue
                normalized = self._normalize_path(raw_path)
                key = normalized or raw_path
                if key:
                    sanitized_map[key] = profile_id
            self.preferences.project_last_profiles = sanitized_map

            self.preferences.recent_projects = self._sanitize_recent_projects(self.preferences.recent_projects)
            if self.preferences.last_path:
                self.preferences.last_path = self._normalize_path(self.preferences.last_path) or self.preferences.last_path

            self.global_profiles = self.profile_manager_core.list_profiles()
            self.config_manager.save(self.preferences, self.servers, self.global_profiles)

        except Exception as exc:
            logger.error("Failed to persist configuration: %s", exc)


    def _toggle_theme(self):
        """Toggle between light and dark themes."""
        try:
            # Toggle theme
            if self.current_theme == "dark":
                new_theme = "light"
                new_theme_name = THEMES["light"]
                self.theme_button.configure(text="🌙")
            else:
                new_theme = "dark"
                new_theme_name = THEMES["dark"]
                self.theme_button.configure(text="☀")

            # Apply theme
            self.style.theme_use(new_theme_name)
            self.current_theme = new_theme

            if hasattr(self, "preferences") and self.preferences:
                self.preferences.theme = new_theme

            try:
                self._persist_config()
            except Exception as persist_exc:
                logger.error("Error persisting theme change: %s", persist_exc)

            logger.info(f"Theme changed to: {new_theme}")

        except Exception as e:
            logger.error(f"Error toggling theme: {e}")

    def _on_project_path_changed(self, path: str):
        """Handle project path changes."""
        logger.info(f"Project path changed: {path}")

        try:
            normalized_path = self._normalize_path(path) if path else ""

            # Update preferences and current project context
            self.preferences.last_path = normalized_path or ""
            self.profile_manager_core.set_current_project(normalized_path or None)

            if normalized_path:
                self._update_recent_projects(normalized_path)

            desired_profile = None
            if normalized_path:
                desired_profile = self.preferences.project_last_profiles.get(normalized_path)

            # Persist change and refresh available profiles
            self._refresh_profiles(select_profile_id=desired_profile)
            self._refresh_launch_command()
            self._persist_config()
        except Exception as e:
            logger.error(f"Error saving project path: {e}")

    def _refresh_launch_command(self):
        """Generate and display the command for launching Claude Code."""
        if not hasattr(self, "launch_panel"):
            return

        project_path = self.project_selector.get_path()

        if not project_path:
            self.launch_panel.show_placeholder("Select a project directory to generate a launch command.")
        else:
            enabled_servers = {sid: server for sid, server in self.servers.items() if server.enabled}
            if not enabled_servers:
                self.launch_panel.show_placeholder("Enable at least one MCP server to build a launch command.")
            else:
                success, result = self.terminal_manager.get_launch_command(self.servers, project_path)
                if success:
                    self.launch_panel.show_command(result)
                else:
                    self.launch_panel.show_error(result)

        self._ensure_window_capacity()

    def _ensure_window_capacity(self):
        """Ensure the window is tall enough to display current content."""
        try:
            self.update_idletasks()
            required_width = max(self.winfo_reqwidth(), WINDOW_MIN_WIDTH)
            required_height = max(self.winfo_reqheight(), WINDOW_MIN_HEIGHT)

            current_width = self.winfo_width() or required_width
            current_height = self.winfo_height() or required_height

            width = max(current_width, required_width)
            height = max(current_height, required_height)

            self.geometry(f"{int(width)}x{int(height)}")
        except Exception as exc:
            logger.debug(f"Unable to adjust window size: {exc}")

    def _on_closing(self):
        """Handle window close event."""
        try:
            self._persist_config()
        except Exception as exc:
            logger.error("Error persisting configuration on close: %s", exc)

        if self.tray_manager and getattr(self.preferences, "close_to_tray", False):
            logger.info("Minimizing to tray on close")
            self.withdraw()
            return

        logger.info("Cleaning up temp MCP config...")
        self.terminal_manager.cleanup_temp_config()

        logger.info("Closing application")
        self.quit()

    def set_tray_manager(self, tray_manager):
        """
        Set the system tray manager reference.

        Args:
            tray_manager: SystemTrayManager instance
        """
        self.tray_manager = tray_manager
        logger.info("Tray manager connected to main window")

    # ===== Server List Callbacks =====

    def _save_server(self, server_id: str, server):
        """
        Save server to config and update UI

        Args:
            server_id: Server ID
            server: MCPServer object
        """
        # Add or update server
        self.servers[server_id] = server

        # Update server list UI
        if server_id in self.server_list.servers:
            self.server_list.update_server(server_id, server)
        else:
            self.server_list.add_server(server_id, server)

        # Save to config
        self._persist_config()
        self._refresh_launch_command()

    def _on_server_toggle(self, server_id: str):
        """Handle server enabled/disabled toggle."""
        try:
            if server_id in self.servers:
                server = self.servers[server_id]
                display_name = server_id.replace("-", " ").title()
                logger.info("Server '%s' toggled: enabled=%s", display_name, server.enabled)
                self._persist_config()
                self._refresh_launch_command()
        except Exception as exc:
            logger.error("Error toggling server '%s': %s", server_id, exc)

    def _on_add_server(self):
        """Handle Add Server button click."""
        logger.info("Add Server button clicked")

        try:
            dialog = ServerDialog(self, mode="add", on_save=self._save_server)
            self.wait_window(dialog)

            if dialog.result:
                logger.info("New server added: %s", dialog.result[0])
            else:
                logger.info("Add Server dialog cancelled")

        except Exception as exc:
            logger.error("Error adding server: %s", exc)

    def _on_edit_server(self, server_id: str):
        """Handle Edit Server action."""
        if server_id not in self.servers:
            return

        server = self.servers[server_id]
        display_name = server_id.replace("-", " ").title()
        logger.info("Edit Server clicked for '%s'", display_name)

        try:
            dialog = ServerDialog(self, mode="edit", server=server, on_save=self._save_server)
            self.wait_window(dialog)

            if dialog.result:
                logger.info("Server edited: %s", dialog.result[0])
            else:
                logger.info("Edit Server dialog cancelled")

        except Exception as exc:
            logger.error("Error editing server '%s': %s", server_id, exc)

    def _on_delete_server(self, server_id: str):
        """Handle Delete Server action."""
        if server_id not in self.servers:
            return

        server = self.servers[server_id]
        display_name = server_id.replace("-", " ").title()

        from tkinter import messagebox

        result = messagebox.askyesno(
            "Confirm Delete",
            f"Are you sure you want to delete server '{display_name}'?\n\nThis action cannot be undone.",
            parent=self
        )

        if not result:
            logger.info("Delete cancelled for '%s'", display_name)
            return

        try:
            del self.servers[server_id]
            self.server_list.remove_server(server_id)
            self._persist_config()
            self._refresh_launch_command()
            logger.info("Server deleted: %s", server_id)

        except Exception as exc:
            logger.error("Error deleting server '%s': %s", server_id, exc)

    def _on_validate_server(self, server_id: str):
        """Handle Validate Server from context menu."""
        if server_id not in self.servers:
            return

        display_name = server_id.replace("-", " ").title()
        logger.info("Validate Server clicked for '%s'", display_name)

        server = self.servers[server_id]
        self.server_list.set_status_message(server_id, "Validating…")

        def worker():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            validated_server = None
            error_message = None
            try:
                validated_server = loop.run_until_complete(
                    self.server_validator.validate_server(server, force_refresh=True)
                )
            except Exception as exc:
                logger.error("Error validating server '%s': %s", server_id, exc)
                error_message = str(exc)
            finally:
                loop.close()

            def finish():
                if error_message:
                    messagebox.showerror(
                        "Validation Error",
                        f"Failed to validate '{display_name}':\n{error_message}",
                        parent=self
                    )
                    self.server_list.refresh_display()
                elif validated_server:
                    self.servers[server_id] = validated_server
                    self.server_list.update_server(server_id, validated_server)
                    self._persist_config()

            self.after(0, finish)

        threading.Thread(target=worker, daemon=True).start()

    def _on_validate_all(self):
        """Handle Validate All button click."""
        logger.info("Validate All clicked")

        if not self.servers:
            return

        for server_id in self.servers:
            self.server_list.set_status_message(server_id, "Validating…")

        if hasattr(self.server_list, "validate_btn"):
            try:
                self.server_list.validate_btn.configure(state=tk.DISABLED)
            except Exception:
                pass

        def worker():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            validated_servers = None
            error_message = None
            try:
                validated_servers = loop.run_until_complete(
                    self.server_validator.validate_all_servers(
                        {sid: server for sid, server in self.servers.items()},
                        force_refresh=True
                    )
                )
            except Exception as exc:
                logger.error("Error validating servers: %s", exc)
                error_message = str(exc)
            finally:
                loop.close()

            def finish():
                if validated_servers:
                    self.servers = validated_servers
                    self.server_list.load_servers(self.servers)
                    self._persist_config()

                if error_message:
                    messagebox.showerror(
                        "Validation Error",
                        f"Failed to validate servers:\n{error_message}",
                        parent=self
                    )
                    self.server_list.refresh_display()

                if hasattr(self.server_list, "validate_btn"):
                    try:
                        self.server_list.validate_btn.configure(state=tk.NORMAL)
                    except Exception:
                        pass

                self._refresh_launch_command()

            self.after(0, finish)

        threading.Thread(target=worker, daemon=True).start()

    # ===== Profile Management Callbacks =====

    def _on_profile_select(self, profile_id: str):
        """Handle profile selection from combobox."""
        logger.info(f"Profile selection changed: {profile_id}")

        internal_selection = getattr(self, "_profile_selection_internal", False)
        self._profile_selection_internal = False

        try:
            success, error, profile, servers = self.profile_manager_core.switch_profile(profile_id)

            if not success:
                from tkinter import messagebox
                messagebox.showerror("Profile Error", error or "Failed to switch profile", parent=self)
                logger.error(f"Failed to switch profile: {error}")
                return

            self.servers = servers
            self.server_list.load_servers(self.servers)
            self.global_profiles = self.profile_manager_core.list_profiles()

            current_project = None
            if hasattr(self, "project_selector"):
                current_project = self._normalize_path(self.project_selector.get_path())

            if current_project:
                self.preferences.project_last_profiles[current_project] = profile_id
            self.preferences.last_profile = profile_id
            if not internal_selection:
                self._refresh_profiles(select_profile_id=profile_id)
                self._persist_config()
            self._refresh_launch_command()

            if profile:
                logger.info(f"Successfully switched to profile: {profile_id} ({len(profile.servers)} servers)")

        except Exception as e:
            logger.error(f"Error switching profile: {e}")

    def _on_profile_new(self):
        """Handle New Profile button click."""
        logger.info("New Profile button clicked")

        try:
            # Prepare existing metadata for validation
            existing_names = [p.name for p in self.profiles.values()]

            dialog = ProfileDialog(
                self,
                mode="new",
                existing_names=existing_names,
                on_save=self._save_new_profile
            )
            self.wait_window(dialog)

            if dialog.result:
                profile_id, name, description = dialog.result
                logger.info(f"New profile created: {profile_id}")
            else:
                logger.info("New profile dialog cancelled")

        except Exception as e:
            logger.error(f"Error creating profile: {e}")

    def _save_new_profile(self, profile_id: str, name: str, description: str):
        """Save new profile with currently enabled servers."""
        try:
            enabled_server_ids = [sid for sid, server in self.servers.items() if server.enabled]

            success, error, profile = self.profile_manager_core.create_profile(
                profile_id=profile_id,
                name=name,
                server_ids=enabled_server_ids,
                description=description
            )

            if not success:
                from tkinter import messagebox
                messagebox.showerror("Profile Error", error or "Failed to create profile", parent=self)
                logger.error(f"Failed to create profile: {error}")
                return

            # Reload application state and refresh UI
            self._refresh_profiles(select_profile_id=profile_id)
            self.profile_manager.select_profile(profile_id)
            self._profile_selection_internal = True
            self._on_profile_select(profile_id)
            self._persist_config()

            server_count = len(profile.servers) if profile else len(enabled_server_ids)
            logger.info(f"Profile saved: {profile_id} with {server_count} servers")

        except Exception as e:
            logger.error(f"Error saving new profile: {e}")

    def _on_profile_save(self, profile_id: str):
        """Handle Save Profile button click (update existing profile with current server state)."""
        logger.info(f"Save Profile button clicked: {profile_id}")

        try:
            success, error = self.profile_manager_core.save_current_state_to_profile(profile_id)

            if not success:
                from tkinter import messagebox
                messagebox.showerror("Profile Error", error or "Failed to save profile", parent=self)
                logger.error(f"Failed to save profile: {error}")
                return

            self._refresh_profiles(select_profile_id=profile_id)
            self._refresh_launch_command()
            self._persist_config()

            profile = self.profiles.get(profile_id)
            if profile:
                logger.info(f"Profile saved: {profile_id} with {len(profile.servers)} servers")

        except Exception as e:
            logger.error(f"Error saving profile: {e}")

    def _on_profile_delete(self, profile_id: str):
        """Handle Delete Profile button click."""
        if profile_id not in self.profiles:
            return

        from tkinter import messagebox
        result = messagebox.askyesno(
            "Confirm Delete",
            f"Are you sure you want to delete profile '{self.profiles[profile_id].name}'?\n\nThis action cannot be undone.",
            parent=self
        )

        if not result:
            logger.info(f"Delete cancelled for profile: {profile_id}")
            return

        try:
            success, error = self.profile_manager_core.delete_profile(profile_id)

            if not success:
                messagebox.showerror("Profile Error", error or "Failed to delete profile", parent=self)
                logger.error(f"Failed to delete profile: {error}")
                return

            self._refresh_profiles()
            self._refresh_launch_command()
            self._persist_config()

            next_profile_id = self.profile_manager.get_selected_profile_id()
            if next_profile_id and next_profile_id != profile_id:
                self._on_profile_select(next_profile_id)

            logger.info(f"Profile deleted: {profile_id}")

        except Exception as e:
            logger.error(f"Error deleting profile: {e}")

    def _focus_profile_combobox(self):
        """Focus the profile combobox (Ctrl+P shortcut)."""
        try:
            self.profile_manager.profile_combo.focus_set()
            self.profile_manager.profile_combo.event_generate('<Button-1>')
            logger.info("Profile combobox focused via keyboard shortcut")
        except Exception as e:
            logger.error(f"Error focusing profile combobox: {e}")

    def get_recent_profiles(self, limit: int = 3):
        """
        Get most recently used profiles for tray menu.

        Args:
            limit: Maximum number of profiles to return

        Returns:
            List of (profile_id, profile_name) tuples
        """
        try:
            # Sort profiles by last_used (most recent first)
            sorted_profiles = sorted(
                [(pid, p) for pid, p in self.profiles.items() if p.last_used],
                key=lambda x: x[1].last_used,
                reverse=True
            )

            # Return top N profiles
            return [(pid, p.name) for pid, p in sorted_profiles[:limit]]

        except Exception as e:
            logger.error(f"Error getting recent profiles: {e}")
            return []