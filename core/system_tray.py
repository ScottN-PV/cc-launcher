"""System tray integration for Claude Code Launcher."""

import logging
import threading
from pathlib import Path
from typing import Callable

import pystray
from PIL import Image

from utils.constants import APP_NAME

logger = logging.getLogger(__name__)


class SystemTrayManager:
    """Manages system tray icon and menu using pystray."""

    def __init__(
        self,
        tk_root,
        restore_callback: Callable,
        launch_callback: Callable,
        icon_path: Path,
        get_recent_profiles_callback: Callable = None,
        switch_profile_callback: Callable = None
    ):
        """
        Initialize system tray manager.

        Args:
            tk_root: Tkinter root window
            restore_callback: Function to restore main window
            launch_callback: Function to launch Claude Code
            icon_path: Path to icon file
            get_recent_profiles_callback: Function to get recent profiles
            switch_profile_callback: Function to switch profile
        """
        self.tk_root = tk_root
        self.restore_callback = restore_callback
        self.launch_callback = launch_callback
        self.icon_path = icon_path
        self.get_recent_profiles_callback = get_recent_profiles_callback
        self.switch_profile_callback = switch_profile_callback
        self.icon = None
        self.tray_thread = None

        logger.info("SystemTrayManager initialized")

    def create_tray_icon(self):
        """
        Create and start system tray icon with menu.
        Runs in a separate thread to avoid blocking Tkinter event loop.
        """
        try:
            # Load icon image
            icon_image = Image.open(self.icon_path)
            logger.info(f"Loaded icon from: {self.icon_path}")

            # Create menu with recent profiles
            menu_items = [
                pystray.MenuItem("Open Launcher", self._on_open),
                pystray.MenuItem("Quick Launch", self._on_quick_launch),
            ]

            # Add recent profiles submenu if callback provided
            if self.get_recent_profiles_callback and self.switch_profile_callback:
                menu_items.append(pystray.Menu.SEPARATOR)
                menu_items.append(
                    pystray.MenuItem("Recent Profiles", self._create_profiles_menu)
                )

            menu_items.extend([
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Exit", self._on_exit)
            ])

            menu = pystray.Menu(*menu_items)

            # Create icon
            self.icon = pystray.Icon(
                "cc-launcher",
                icon_image,
                APP_NAME,
                menu
            )

            # Run in separate thread
            self.tray_thread = threading.Thread(
                target=self._run_tray_icon,
                daemon=True
            )
            self.tray_thread.start()

            logger.info("System tray icon created and started")

        except Exception as e:
            logger.error(f"Failed to create system tray icon: {e}")
            raise

    def _run_tray_icon(self):
        """Run the system tray icon (blocking call, runs in thread)."""
        try:
            self.icon.run()
        except Exception as e:
            logger.error(f"System tray error: {e}")

    def _on_open(self, icon, item):
        """Handle 'Open Launcher' menu item - must be thread-safe."""
        logger.info("Open Launcher clicked from tray")
        # Schedule callback in Tkinter main thread
        self.tk_root.after(0, self.restore_callback)

    def _on_quick_launch(self, icon, item):
        """Handle 'Quick Launch' menu item - must be thread-safe."""
        logger.info("Quick Launch clicked from tray")
        # Schedule callback in Tkinter main thread
        self.tk_root.after(0, self.launch_callback)

    def _on_exit(self, icon, item):
        """Handle 'Exit' menu item - must be thread-safe."""
        logger.info("Exit clicked from tray")
        # Schedule callback in Tkinter main thread
        self.tk_root.after(0, self.exit_app)

    def _create_profiles_menu(self, item):
        """
        Create submenu with recent profiles.
        Called dynamically when Recent Profiles is clicked.
        """
        try:
            recent_profiles = self.get_recent_profiles_callback()

            if not recent_profiles:
                return pystray.Menu(
                    pystray.MenuItem("(No recent profiles)", None, enabled=False)
                )

            # Create menu items for each profile
            profile_items = []
            for profile_id, profile_name in recent_profiles:
                # Create a closure to capture profile_id
                def make_handler(pid):
                    return lambda icon, item: self._on_profile_selected(pid)

                profile_items.append(
                    pystray.MenuItem(profile_name, make_handler(profile_id))
                )

            return pystray.Menu(*profile_items)

        except Exception as e:
            logger.error(f"Error creating profiles menu: {e}")
            return pystray.Menu(
                pystray.MenuItem("(Error loading profiles)", None, enabled=False)
            )

    def _on_profile_selected(self, profile_id: str):
        """Handle profile selection from tray menu."""
        logger.info(f"Profile '{profile_id}' selected from tray")
        # Schedule callback in Tkinter main thread
        if self.switch_profile_callback:
            self.tk_root.after(0, lambda: self.switch_profile_callback(profile_id))

    def minimize_to_tray(self):
        """Hide the main window (minimize to tray)."""
        logger.info("Minimizing to tray")
        self.tk_root.withdraw()

    def restore_window(self):
        """Show and bring main window to front."""
        logger.info("Restoring window from tray")
        self.tk_root.deiconify()
        self.tk_root.lift()
        self.tk_root.focus_force()

    def exit_app(self):
        """Clean exit: stop tray icon and close application."""
        logger.info("Exiting application")
        try:
            if self.icon:
                self.icon.stop()
            self.tk_root.quit()
        except Exception as e:
            logger.error(f"Error during exit: {e}")
            # Force quit if necessary
            import sys
            sys.exit(0)