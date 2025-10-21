"""
Server List UI Component

Displays MCP servers in a Treeview with columns for enabled status, name, description, and validation status.
Supports context menu for edit/delete/validate operations.
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Dict, Optional
import tkinter.font as tkfont
import ttkbootstrap as ttb
from models.server import MCPServer


class ServerList(ttk.Frame):
    """Server list component with Treeview"""

    def __init__(self, parent, on_server_toggle: Optional[Callable] = None,
                 on_add_server: Optional[Callable] = None,
                 on_edit_server: Optional[Callable] = None,
                 on_delete_server: Optional[Callable] = None,
                 on_validate_server: Optional[Callable] = None,
                 on_validate_all: Optional[Callable] = None):
        """
        Initialize server list component

        Args:
            parent: Parent widget
            on_server_toggle: Callback when server enabled/disabled (server_id)
            on_add_server: Callback when Add Server clicked
            on_edit_server: Callback when Edit clicked (server_id)
            on_delete_server: Callback when Delete clicked (server_id)
            on_validate_server: Callback when Validate clicked (server_id)
            on_validate_all: Callback when Validate All clicked
        """
        super().__init__(parent)

        # Store callbacks
        self.on_server_toggle = on_server_toggle
        self.on_add_server = on_add_server
        self.on_edit_server = on_edit_server
        self.on_delete_server = on_delete_server
        self.on_validate_server = on_validate_server
        self.on_validate_all = on_validate_all

        # Server data storage: {server_id: MCPServer}
        self.servers: Dict[str, MCPServer] = {}

        self._create_widgets()
        self._create_context_menu()

    def _create_widgets(self):
        """Create UI widgets"""
        # Button toolbar at top
        toolbar = ttk.Frame(self)
        toolbar.grid(row=0, column=0, sticky="ew", padx=5, pady=5)

        self.add_btn = ttb.Button(
            toolbar,
            text="Add Server",
            bootstyle="success",
            command=self._handle_add_server
        )
        self.add_btn.pack(side=tk.LEFT, padx=(0, 5))

        self.delete_btn = ttb.Button(
            toolbar,
            text="Delete Server",
            bootstyle="danger",
            command=self._handle_delete_server,
            state=tk.DISABLED
        )
        self.delete_btn.pack(side=tk.LEFT, padx=(15, 5))

        filter_wrapper = ttk.Frame(toolbar)
        filter_wrapper.pack(side=tk.LEFT, expand=True)

        self.filter_var = tk.StringVar(value="All Categories")
        self.category_filter = ttb.Combobox(
            filter_wrapper,
            textvariable=self.filter_var,
            state="readonly",
            width=28
        )
        self.category_filter.pack(pady=2)
        self.category_filter.bind("<<ComboboxSelected>>", lambda _event: self._apply_category_filter())

        self.validate_btn = ttb.Button(
            toolbar,
            text="Validate All",
            bootstyle="info",
            command=self._handle_validate_all
        )
        self.validate_btn.pack(side=tk.RIGHT)

        # Treeview frame with scrollbar
        tree_frame = ttk.Frame(self)
        tree_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        # Scrollbar
        scrollbar = ttb.Scrollbar(tree_frame, bootstyle="round")
        scrollbar.grid(row=0, column=1, sticky="ns")

        # Treeview with columns
        columns = ("name", "description", "status")
        self.tree = ttb.Treeview(tree_frame, columns=columns, show="tree headings",
                                  yscrollcommand=scrollbar.set, height=10)
        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.config(command=self.tree.yview)

        # Column configuration
        self.tree.column("#0", width=50, minwidth=40, stretch=False, anchor=tk.CENTER)
        self.tree.column("name", width=180, minwidth=120, anchor="w")
        self.tree.column("description", width=320, minwidth=180, anchor="w")
        self.tree.column("status", width=140, minwidth=100, stretch=False, anchor="w")

        # Headings
        self.tree.heading("#0", text="✓", anchor=tk.CENTER)
        self.tree.heading("name", text="Name", anchor="w")
        self.tree.heading("description", text="Description", anchor="w")
        self.tree.heading("status", text="Status", anchor="w")

        # Bind events
        self.tree.bind("<Double-Button-1>", self._handle_double_click)
        self.tree.bind("<Button-3>", self._handle_right_click)  # Right-click for context menu
        self.tree.bind("<space>", self._handle_space_toggle)  # Space to toggle checkbox
        self.tree.bind("<<TreeviewSelect>>", lambda _event: self._update_delete_button_state())

        # Configure grid weights
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

    def _create_context_menu(self):
        """Create right-click context menu"""
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="Edit", command=self._handle_edit_server)
        self.context_menu.add_command(label="Delete", command=self._handle_delete_server)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Validate", command=self._handle_validate_server)

    def _resolve_tree_font(self) -> tkfont.Font:
        """Return the font used by the Treeview headings/items."""
        style_name = self.tree.cget("style") or "Treeview"
        font_name = self.tree.tk.call("ttk::style", "lookup", style_name, "-font")
        if not font_name:
            font_name = "TkDefaultFont"
        try:
            return tkfont.nametofont(font_name)
        except tk.TclError:
            return tkfont.nametofont("TkDefaultFont")

    def _get_checkbox_symbol(self, enabled: bool) -> str:
        """Get checkbox symbol for enabled state"""
        return "✅" if enabled else "⬜"

    def _get_status_display(self, server: MCPServer) -> str:
        """Return a user-friendly status message for the server."""
        validation = server.validation
        if not validation:
            return "Not validated"

        if validation.error_message:
            return f"❌ {validation.error_message}"

        if validation.npm_available is False:
            return "❌ Package not found"

        if validation.cached:
            base = "🟡 Cached"
        else:
            base = "✅ Ready"

        details = []
        if validation.npm_version:
            details.append(f"v{validation.npm_version}")
        if validation.locally_installed:
            details.append("local")

        if server.type == "http" and not validation.npm_version:
            base = "🌐 Ready"

        if details:
            base = f"{base} ({', '.join(details)})"

        return base

    def load_servers(self, servers: Dict[str, MCPServer]):
        """
        Load servers into the list

        Args:
            servers: Dictionary of server_id -> MCPServer
        """
        self.servers = servers.copy()
        self.refresh_display()

    def refresh_display(self):
        """Refresh the Treeview display with current server data"""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)

        categories = sorted({server.category or "Uncategorized" for server in self.servers.values()})
        options = ["All Categories"] + categories
        self.category_filter.configure(values=options)
        if self.filter_var.get() not in options:
            self.filter_var.set("All Categories")

        active_category = self.filter_var.get()

        # Sort servers by order field
        sorted_servers = sorted(self.servers.items(),
                               key=lambda x: x[1].order if x[1].order is not None else 999)

        inserted = 0

        # Add servers to tree
        for server_id, server in sorted_servers:
            server_category = server.category or "Uncategorized"
            if active_category != "All Categories" and server_category != active_category:
                continue

            checkbox = self._get_checkbox_symbol(server.enabled)
            status = self._get_status_display(server)

            # Use ID as the display name (servers don't have separate name field)
            display_name = server_id.replace("-", " ").title()
            self.tree.insert("", "end", iid=server_id, text=checkbox,
                           values=(display_name, server.description or "", status))
            inserted += 1

        desired_height = min(max(inserted + 2, 6), 18)
        self.tree.configure(height=desired_height)

        self._update_column_widths()
        self._update_delete_button_state()

    def _update_delete_button_state(self):
        if not hasattr(self, "delete_btn"):
            return

        selection = self.tree.selection()
        state = tk.NORMAL if selection else tk.DISABLED
        try:
            self.delete_btn.configure(state=state)
        except tk.TclError:
            pass

    def _update_column_widths(self):
        if not self.winfo_ismapped():
            # Delay until widget is displayed to avoid inaccurate measurements
            self.after(50, self._update_column_widths)
            return

        try:
            font = self._resolve_tree_font()
        except tk.TclError:
            font = tkfont.nametofont("TkDefaultFont")
        padding = 24

        items = self.tree.get_children()
        name_samples = [self.tree.heading("name", "text")]
        desc_samples = [self.tree.heading("description", "text")]
        status_samples = [self.tree.heading("status", "text")]

        for item in items:
            values = self.tree.item(item, "values")
            if not values:
                continue
            name_samples.append(values[0])
            desc_samples.append(values[1])
            status_samples.append(values[2])

        try:
            name_width = max(font.measure(text) for text in name_samples) + padding if name_samples else 180
            desc_width = max(font.measure(text) for text in desc_samples) + padding if desc_samples else 320
            status_width = max(font.measure(text) for text in status_samples) + padding if status_samples else 140
        except tk.TclError:
            name_width, desc_width, status_width = 180, 320, 140

        checkbox_width = max(48, font.measure("✅ ") + padding // 2)

        self.tree.column("#0", width=checkbox_width, minwidth=40)
        self.tree.column("name", width=name_width, minwidth=120, stretch=False)
        self.tree.column("description", width=desc_width, minwidth=200, stretch=False)
        self.tree.column("status", width=status_width, minwidth=120, stretch=False)

        total_width = checkbox_width + name_width + desc_width + status_width + 40

        try:
            top_level = self.winfo_toplevel()
            top_level.update_idletasks()
            current_width = top_level.winfo_width()
            desired_width = max(total_width, top_level.winfo_reqwidth())
            if desired_width > current_width:
                height = top_level.winfo_height() or top_level.winfo_reqheight()
                top_level.geometry(f"{int(desired_width)}x{int(height)}")
        except tk.TclError:
            pass

    def _handle_double_click(self, event):
        """Handle double-click on item (toggle or edit)"""
        item = self.tree.identify_row(event.y)
        region = self.tree.identify_region(event.x, event.y)

        if not item:
            return

        # If clicked on checkbox column, toggle
        if region == "tree":
            self._toggle_server(item)
        # If clicked elsewhere, edit
        else:
            if self.on_edit_server:
                self.on_edit_server(item)

    def _handle_space_toggle(self, event):
        """Handle space key to toggle selected server"""
        selection = self.tree.selection()
        if selection:
            self._toggle_server(selection[0])

    def _toggle_server(self, server_id: str):
        """Toggle server enabled state"""
        if server_id in self.servers:
            server = self.servers[server_id]
            server.enabled = not server.enabled

            # Update display
            checkbox = self._get_checkbox_symbol(server.enabled)
            self.tree.item(server_id, text=checkbox)

            # Notify callback
            if self.on_server_toggle:
                self.on_server_toggle(server_id)

            # Update checkbox display immediately
            self.tree.item(server_id, text=self._get_checkbox_symbol(server.enabled))

    def _handle_right_click(self, event):
        """Handle right-click to show context menu"""
        # Select the item under cursor
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)

    def _handle_add_server(self):
        """Handle Add Server button click"""
        if self.on_add_server:
            self.on_add_server()

    def _handle_edit_server(self):
        """Handle Edit from context menu"""
        selection = self.tree.selection()
        if selection and self.on_edit_server:
            self.on_edit_server(selection[0])

    def _handle_delete_server(self):
        """Handle Delete from context menu"""
        selection = self.tree.selection()
        if selection and self.on_delete_server:
            self.on_delete_server(selection[0])
        self.after(10, self._update_delete_button_state)

    def _handle_validate_server(self):
        """Handle Validate from context menu"""
        selection = self.tree.selection()
        if selection and self.on_validate_server:
            self.on_validate_server(selection[0])

    def _handle_validate_all(self):
        """Handle Validate All button click"""
        if self.on_validate_all:
            self.on_validate_all()

    def _apply_category_filter(self):
        self.refresh_display()

    def get_selected_server_id(self) -> Optional[str]:
        """Get currently selected server ID"""
        selection = self.tree.selection()
        return selection[0] if selection else None

    def update_server(self, server_id: str, server: MCPServer):
        """
        Update a specific server and refresh display

        Args:
            server_id: Server ID to update
            server: Updated MCPServer object
        """
        if server_id in self.servers:
            self.servers[server_id] = server
            self.refresh_display()

    def remove_server(self, server_id: str):
        """
        Remove a server from the list

        Args:
            server_id: Server ID to remove
        """
        if server_id in self.servers:
            del self.servers[server_id]
            self.refresh_display()

    def add_server(self, server_id: str, server: MCPServer):
        """
        Add a new server to the list

        Args:
            server_id: Server ID
            server: MCPServer object
        """
        self.servers[server_id] = server
        self.refresh_display()

    def set_status_message(self, server_id: str, message: str):
        """Update only the status column for a server."""
        if server_id in self.servers and self.tree.exists(server_id):
            values = list(self.tree.item(server_id, "values"))
            if len(values) >= 3:
                values[2] = message
                self.tree.item(server_id, values=values)
                self._update_column_widths()