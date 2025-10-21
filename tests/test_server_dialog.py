import tkinter as tk

from models.server import MCPServer
from ui.dialogs.server_dialog import ServerDialog


def build_stdio_server(enabled: bool) -> MCPServer:
    return MCPServer(
        id="sample",
        type="stdio",
        command="cmd",
        args=["/c", "echo", "hello"],
        env={},
        enabled=enabled,
        description="Original description",
        category="tools",
        order=5,
    )


def test_edit_dialog_preserves_enabled_state(monkeypatch):
    root = tk.Tk()
    root.withdraw()

    existing_server = build_stdio_server(enabled=False)
    saved = {}

    def capture(server_id, server):
        saved["server"] = server

    dialog = ServerDialog(root, mode="edit", server=existing_server, on_save=capture)
    dialog.description_var.set("Updated description")

    dialog._on_save()
    root.update_idletasks()

    assert "server" in saved
    assert saved["server"].enabled is False

    root.destroy()
