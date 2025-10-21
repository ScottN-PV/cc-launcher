"""
Test Flet system tray integration on Windows.
This is a critical Phase 1 test to determine if Flet can support system tray properly.
If this fails, we'll pivot to Tkinter+ttkbootstrap or PySide6.
"""

import flet as ft
import sys

def main(page: ft.Page):
    page.title = "Flet System Tray Test"
    page.window.width = 400
    page.window.height = 300

    status_text = ft.Text("Testing system tray integration...", size=16)
    result_text = ft.Text("", color="blue")

    def test_minimize_to_tray():
        """Test if window can be minimized to system tray"""
        try:
            # Check if Flet supports window visibility control
            if hasattr(page.window, 'visible'):
                page.window.visible = False
                page.update()
                result_text.value = "✓ Window visibility control available"
                result_text.color = "green"
            else:
                result_text.value = "✗ Window visibility control NOT available"
                result_text.color = "red"
        except Exception as e:
            result_text.value = f"✗ Error: {str(e)}"
            result_text.color = "red"
        page.update()

    def test_window_restore():
        """Test if window can be restored from tray"""
        try:
            if hasattr(page.window, 'visible'):
                page.window.visible = True
                page.update()
                result_text.value = "✓ Window restore works"
                result_text.color = "green"
            else:
                result_text.value = "✗ Cannot restore window"
                result_text.color = "red"
        except Exception as e:
            result_text.value = f"✗ Error: {str(e)}"
            result_text.color = "red"
        page.update()

    def check_system_tray_apis():
        """Check what system tray APIs are available in Flet"""
        try:
            apis = []

            # Check for window properties
            if hasattr(page.window, 'visible'):
                apis.append("✓ page.window.visible")
            else:
                apis.append("✗ page.window.visible")

            if hasattr(page.window, 'minimized'):
                apis.append("✓ page.window.minimized")
            else:
                apis.append("✗ page.window.minimized")

            if hasattr(page.window, 'to_front'):
                apis.append("✓ page.window.to_front()")
            else:
                apis.append("✗ page.window.to_front()")

            # Check for system tray support
            if hasattr(ft, 'SystemTray') or hasattr(page, 'system_tray'):
                apis.append("✓ System tray API available")
            else:
                apis.append("✗ System tray API NOT available")

            result_text.value = "\n".join(apis)
            result_text.color = "blue"
        except Exception as e:
            result_text.value = f"Error checking APIs: {str(e)}"
            result_text.color = "red"
        page.update()

    # Run API check on startup
    check_system_tray_apis()

    page.add(
        ft.Column([
            status_text,
            ft.Divider(),
            result_text,
            ft.Divider(),
            ft.ElevatedButton("Check System Tray APIs", on_click=lambda _: check_system_tray_apis()),
            ft.ElevatedButton("Test Minimize to Tray", on_click=lambda _: test_minimize_to_tray()),
            ft.ElevatedButton("Test Restore Window", on_click=lambda _: test_window_restore()),
            ft.Divider(),
            ft.Text("Conclusion:", weight=ft.FontWeight.BOLD),
            ft.Text(
                "If system tray API is NOT available, we need to pivot to:\n"
                "1. Tkinter + ttkbootstrap + pystray\n"
                "2. PySide6/PyQt6 (better Windows integration)",
                size=12,
                color="orange"
            )
        ], spacing=10)
    )

if __name__ == "__main__":
    # First check if flet is installed
    try:
        ft.app(target=main)
    except ImportError:
        print("Flet not installed. Installing...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "flet>=0.25.0"])
        print("Flet installed. Please run this script again.")