import tkinter as tk
from tkinter import TclError

import pytest

from models.server import MCPServer
from ui.components.server_list import ServerList


@pytest.fixture
def tk_root():
    try:
        root = tk.Tk()
    except TclError as exc:
        pytest.skip(f"Tkinter not available: {exc}")
    root.withdraw()
    yield root
    root.destroy()


def build_server(server_id: str, category: str) -> MCPServer:
    return MCPServer(
        id=server_id,
        type="stdio",
        command="cmd",
        args=["/c", "echo", server_id],
        env={},
        enabled=True,
        category=category
    )


def test_category_filter_populates_and_filters(tk_root):
    component = ServerList(tk_root)
    component.pack()

    servers = {
        "alpha": build_server("alpha", "Utilities"),
        "beta": build_server("beta", "AI"),
        "gamma": build_server("gamma", "Utilities"),
        "delta": build_server("delta", "")
    }

    component.load_servers(servers)
    tk_root.update_idletasks()

    values = tuple(component.category_filter.cget("values"))
    assert values[0] == "All Categories"
    assert set(values[1:]) == {"AI", "Uncategorized", "Utilities"}

    component.filter_var.set("Utilities")
    component._apply_category_filter()
    tk_root.update_idletasks()

    utilities_items = component.tree.get_children()
    assert set(utilities_items) == {"alpha", "gamma"}

    component.filter_var.set("AI")
    component._apply_category_filter()
    tk_root.update_idletasks()

    ai_items = component.tree.get_children()
    assert ai_items == ("beta",)

    component.filter_var.set("All Categories")
    component._apply_category_filter()
    tk_root.update_idletasks()

    all_items = set(component.tree.get_children())
    assert all_items == set(servers.keys())
