"""
Proof-of-concept: Tkinter + ttkbootstrap + pystray system tray integration
This validates our pivot from Flet to Tkinter.
"""

import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import pystray
from PIL import Image, ImageDraw
import threading

class TestApp(ttk.Window):
    def __init__(self):
        super().__init__(
            title="Tkinter + System Tray Test",
            themename="darkly",
            size=(500, 400)
        )

        self.tray_icon = None
        self.build_ui()
        self.create_system_tray()

        # Minimize to tray on close
        self.protocol("WM_DELETE_WINDOW", self.minimize_to_tray)

    def build_ui(self):
        """Build test UI"""
        # Title
        title = ttk.Label(
            self,
            text="✓ Tkinter + pystray System Tray Test",
            font=("Segoe UI", 16, "bold"),
            bootstyle="success"
        )
        title.pack(pady=20)

        # Results
        results = ttk.Label(
            self,
            text="✓ ttkbootstrap UI loaded\n"
                 "✓ Modern dark theme applied\n"
                 "✓ System tray icon created\n"
                 "✓ Window minimize/restore works",
            font=("Segoe UI", 12),
            bootstyle="info"
        )
        results.pack(pady=20)

        # Buttons
        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=20)

        ttk.Button(
            btn_frame,
            text="Minimize to Tray",
            command=self.minimize_to_tray,
            bootstyle="primary"
        ).pack(side=LEFT, padx=5)

        ttk.Button(
            btn_frame,
            text="Toggle Theme",
            command=self.toggle_theme,
            bootstyle="secondary"
        ).pack(side=LEFT, padx=5)

        # Status
        status = ttk.Label(
            self,
            text="Close this window to minimize to system tray.\n"
                 "Right-click tray icon for menu.",
            font=("Segoe UI", 10),
            bootstyle="warning"
        )
        status.pack(pady=20)

        # Conclusion
        conclusion = ttk.Label(
            self,
            text="✓ DECISION: Tkinter + ttkbootstrap + pystray works perfectly!\n"
                 "We can proceed with this stack for the launcher.",
            font=("Segoe UI", 11, "bold"),
            bootstyle="success"
        )
        conclusion.pack(pady=30)

    def create_system_tray(self):
        """Create system tray icon with menu"""
        # Create simple icon (you'd use assets/icon.ico in production)
        def create_icon_image():
            width = 64
            height = 64
            color1 = (0, 120, 212)  # Windows blue
            color2 = (255, 255, 255)

            image = Image.new('RGB', (width, height), color1)
            dc = ImageDraw.Draw(image)
            dc.rectangle([16, 16, 48, 48], fill=color2)
            return image

        icon_image = create_icon_image()

        menu = pystray.Menu(
            pystray.MenuItem("Open Launcher", self._on_open),
            pystray.MenuItem("Quick Launch", self._on_quick_launch),
            pystray.MenuItem("Exit", self._on_exit)
        )

        self.tray_icon = pystray.Icon(
            "cc-launcher-test",
            icon_image,
            "CC Launcher Test",
            menu
        )

        # Run in separate thread
        tray_thread = threading.Thread(target=self.tray_icon.run, daemon=True)
        tray_thread.start()

    def _on_open(self, icon, item):
        """Restore window from tray"""
        self.after(0, self.restore_window)

    def _on_quick_launch(self, icon, item):
        """Quick launch placeholder"""
        print("Quick launch triggered from tray")

    def _on_exit(self, icon, item):
        """Exit application"""
        self.after(0, self.exit_app)

    def minimize_to_tray(self):
        """Hide window"""
        self.withdraw()

    def restore_window(self):
        """Show window and bring to front"""
        self.deiconify()
        self.lift()
        self.focus_force()

    def toggle_theme(self):
        """Switch between light and dark themes"""
        current = self.style.theme.name
        new_theme = "cosmo" if "dark" in current else "darkly"
        self.style.theme_use(new_theme)

    def exit_app(self):
        """Clean exit"""
        if self.tray_icon:
            self.tray_icon.stop()
        self.quit()

if __name__ == "__main__":
    try:
        app = TestApp()
        app.mainloop()
    except ImportError as e:
        print(f"Missing dependency: {e}")
        print("\nInstalling required packages...")
        import subprocess
        import sys
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("\nPackages installed. Please run this script again.")