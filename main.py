"""Claude Code MCP Manager - Main entry point."""

import logging
import sys
from pathlib import Path

from core.config_manager import ConfigManager
from core.system_tray import SystemTrayManager
from ui.main_window import MainWindow
from utils.logger import setup_logging
from utils.constants import CONFIG_DIR


def main():
    """Main entry point for Claude Code MCP Manager."""
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("=" * 60)
    logger.info("Claude Code MCP Manager starting...")
    logger.info("=" * 60)

    try:
        logger.info("Initializing configuration manager...")
        config_manager = ConfigManager()

        logger.info("Loading configuration...")
        config = config_manager.load()
        logger.info(f"Configuration loaded successfully")

        logger.info("Creating main window...")
        app = MainWindow(config_manager)

        logger.info("Creating system tray manager...")
        icon_path = Path(__file__).parent / "assets" / "icon.ico"

        tray_manager = SystemTrayManager(
            tk_root=app,
            restore_callback=app.deiconify,
            launch_callback=lambda: logger.info("Quick launch placeholder"),
            icon_path=icon_path,
            get_recent_profiles_callback=app.get_recent_profiles,
            switch_profile_callback=app._on_profile_select
        )

        app.set_tray_manager(tray_manager)

        logger.info("Starting system tray icon...")
        if not tray_manager.create_tray_icon():
            logger.info("System tray not started; continuing without tray icon")

        logger.info("Starting UI event loop...")
        app.mainloop()

        logger.info("Cleaning up...")
        if tray_manager.icon:
            tray_manager.icon.stop()

        logger.info("Application closed normally")

    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
        sys.exit(0)

    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()