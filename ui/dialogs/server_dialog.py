"""
Server Dialog for Adding/Editing MCP Servers

Provides a dialog window for creating new servers or editing existing ones.
Supports both stdio and http server types with type-specific fields.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Callable
import ttkbootstrap as ttb
import uuid

from models.server import MCPServer
from utils.validators import validate_path, validate_url, validate_command
from utils.constants import ERROR_MESSAGES


class ServerDialog(ttb.Toplevel):
    """Dialog for adding or editing MCP servers"""

    def __init__(self, parent, mode: str = "add", server: Optional[MCPServer] = None,
                 on_save: Optional[Callable[[str, MCPServer], None]] = None):
        """
        Initialize server dialog

        Args:
            parent: Parent window
            mode: "add" or "edit"
            server: Existing MCPServer (for edit mode)
            on_save: Callback when server is saved (server_id, server)
        """
        super().__init__(parent)

        self.mode = mode
        self.server = server
        self.on_save = on_save
        self.result = None

        # Configure dialog
        self.title(f"{'Add' if mode == 'add' else 'Edit'} MCP Server")
        self.geometry("")
        self.resizable(True, True)

        # Make modal
        self.transient(parent)
        self.grab_set()

        # Center on parent
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

        self._create_widgets()
        self._populate_fields()
        self.after(0, self._adjust_size)

    def _create_widgets(self):
        """Create dialog widgets"""
        # Main container with padding
        main_frame = ttb.Frame(self, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Server ID field (read-only for edit mode)
        id_frame = ttb.Frame(main_frame)
        id_frame.pack(fill=tk.X, pady=(0, 10))

        ttb.Label(id_frame, text="Server ID:", width=15, anchor=tk.W).pack(side=tk.LEFT)
        self.id_var = tk.StringVar()
        self.id_entry = ttb.Entry(id_frame, textvariable=self.id_var, width=40)
        self.id_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))

        if self.mode == "edit":
            self.id_entry.configure(state="readonly")

        # Server Type dropdown
        type_frame = ttb.Frame(main_frame)
        type_frame.pack(fill=tk.X, pady=(0, 10))

        ttb.Label(type_frame, text="Type:", width=15, anchor=tk.W).pack(side=tk.LEFT)
        self.type_var = tk.StringVar(value="stdio")
        self.type_combo = ttb.Combobox(type_frame, textvariable=self.type_var,
                                        values=["stdio", "http"], state="readonly", width=37)
        self.type_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        self.type_combo.bind("<<ComboboxSelected>>", self._on_type_changed)

        # Description field
        desc_frame = ttb.Frame(main_frame)
        desc_frame.pack(fill=tk.X, pady=(0, 10))

        ttb.Label(desc_frame, text="Description:", width=15, anchor=tk.W).pack(side=tk.LEFT)
        self.description_var = tk.StringVar()
        ttb.Entry(desc_frame, textvariable=self.description_var, width=40).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))

        # Category field
        cat_frame = ttb.Frame(main_frame)
        cat_frame.pack(fill=tk.X, pady=(0, 10))

        ttb.Label(cat_frame, text="Category:", width=15, anchor=tk.W).pack(side=tk.LEFT)
        self.category_var = tk.StringVar(value="general")
        ttb.Combobox(cat_frame, textvariable=self.category_var,
                     values=["general", "core", "documentation", "database", "ui", "tools"],
                     width=37).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))

        # Separator
        ttb.Separator(main_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)

        # ===== stdio-specific fields =====
        self.stdio_frame = ttb.LabelFrame(main_frame, text="stdio Configuration", padding=10)
        self.stdio_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Command field
        cmd_frame = ttb.Frame(self.stdio_frame)
        cmd_frame.pack(fill=tk.X, pady=(0, 10))

        ttb.Label(cmd_frame, text="Command:", width=12, anchor=tk.W).pack(side=tk.LEFT)
        self.command_var = tk.StringVar()
        ttb.Entry(cmd_frame, textvariable=self.command_var).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))

        # Args field (multiline)
        args_label = ttb.Label(self.stdio_frame, text="Arguments (one per line):", anchor=tk.W)
        args_label.pack(fill=tk.X, pady=(0, 5))

        args_scroll = ttb.Scrollbar(self.stdio_frame, bootstyle="round")
        args_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.args_text = tk.Text(self.stdio_frame, height=5, width=50, yscrollcommand=args_scroll.set)
        self.args_text.pack(fill=tk.BOTH, expand=True)
        args_scroll.config(command=self.args_text.yview)

        # Env vars field (multiline, KEY=VALUE format)
        env_label = ttb.Label(self.stdio_frame, text="Environment Variables (KEY=VALUE):", anchor=tk.W)
        env_label.pack(fill=tk.X, pady=(10, 5))

        env_scroll = ttb.Scrollbar(self.stdio_frame, bootstyle="round")
        env_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.env_text = tk.Text(self.stdio_frame, height=5, width=50, yscrollcommand=env_scroll.set)
        self.env_text.pack(fill=tk.BOTH, expand=True)
        env_scroll.config(command=self.env_text.yview)

        # ===== http-specific fields =====
        self.http_frame = ttb.LabelFrame(main_frame, text="HTTP Configuration", padding=10)
        self.http_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # URL field
        url_frame = ttb.Frame(self.http_frame)
        url_frame.pack(fill=tk.X, pady=(0, 10))

        ttb.Label(url_frame, text="URL:", width=12, anchor=tk.W).pack(side=tk.LEFT)
        self.url_var = tk.StringVar()
        ttb.Entry(url_frame, textvariable=self.url_var).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))

        # Headers field (multiline, KEY=VALUE format)
        headers_label = ttb.Label(self.http_frame, text="Headers (KEY=VALUE):", anchor=tk.W)
        headers_label.pack(fill=tk.X, pady=(0, 5))

        headers_scroll = ttb.Scrollbar(self.http_frame, bootstyle="round")
        headers_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.headers_text = tk.Text(self.http_frame, height=4, width=50, yscrollcommand=headers_scroll.set)
        self.headers_text.pack(fill=tk.BOTH, expand=True)
        headers_scroll.config(command=self.headers_text.yview)

        # ===== Button bar =====
        button_frame = ttb.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))

        ttb.Button(button_frame, text="Cancel", command=self._on_cancel,
                   bootstyle="secondary", width=15).pack(side=tk.RIGHT, padx=(5, 0))
        ttb.Button(button_frame, text="Save", command=self._on_save,
                   bootstyle="success", width=15).pack(side=tk.RIGHT)

        # Initialize visibility
        self._on_type_changed()

        # Enable dynamic resizing for multiline inputs
        self._bind_auto_resize(self.args_text, min_lines=4, max_lines=14)
        self._bind_auto_resize(self.env_text, min_lines=3, max_lines=12)
        self._bind_auto_resize(self.headers_text, min_lines=3, max_lines=12)
        self._auto_resize_text(self.args_text, min_lines=4, max_lines=14)
        self._auto_resize_text(self.env_text, min_lines=3, max_lines=12)
        self._auto_resize_text(self.headers_text, min_lines=3, max_lines=12)

    def _on_type_changed(self, event=None):
        """Handle server type change to show/hide relevant fields"""
        server_type = self.type_var.get()

        if server_type == "stdio":
            self.http_frame.pack_forget()
            self.stdio_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        else:  # http
            self.stdio_frame.pack_forget()
            self.http_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        self._adjust_size()

    def _bind_auto_resize(self, text_widget: tk.Text, min_lines: int, max_lines: int) -> None:
        """Bind a Text widget to resize based on its content."""

        def _on_modified(event, widget=text_widget, min_l=min_lines, max_l=max_lines):
            if widget.edit_modified():
                widget.edit_modified(False)
                self._auto_resize_text(widget, min_l, max_l)
                self._adjust_size()

        text_widget.bind("<<Modified>>", _on_modified)
        text_widget.edit_modified(False)

    @staticmethod
    def _auto_resize_text(text_widget: tk.Text, min_lines: int, max_lines: int) -> None:
        """Resize a Text widget between min and max lines based on its content."""
        content = text_widget.get("1.0", "end-1c")
        line_count = content.count("\n") + 1 if content else 1
        height = max(min_lines, min(max_lines, line_count))
        text_widget.configure(height=height)

    def _adjust_size(self) -> None:
        """Ensure the dialog is large enough for current content."""
        try:
            self.update_idletasks()
            min_width = max(640, self.winfo_reqwidth() + 20)
            min_height = max(560, self.winfo_reqheight() + 20)
            self.minsize(min_width, min_height)

            current_width = max(self.winfo_width(), min_width)
            current_height = max(self.winfo_height(), min_height)
            self.geometry(f"{int(current_width)}x{int(current_height)}")
        except tk.TclError:
            pass

    def _populate_fields(self):
        """Populate fields with existing server data (edit mode)"""
        if self.mode == "edit" and self.server:
            self.id_var.set(self.server.id)
            self.type_var.set(self.server.type)
            self.description_var.set(self.server.description or "")
            self.category_var.set(self.server.category or "general")

            if self.server.type == "stdio":
                self.command_var.set(self.server.command or "")

                # Populate args
                if self.server.args:
                    self.args_text.delete("1.0", tk.END)
                    self.args_text.insert("1.0", "\n".join(self.server.args))

                # Populate env
                if self.server.env:
                    self.env_text.delete("1.0", tk.END)
                    env_lines = [f"{k}={v}" for k, v in self.server.env.items()]
                    self.env_text.insert("1.0", "\n".join(env_lines))

            elif self.server.type == "http":
                self.url_var.set(self.server.url or "")

                # Populate headers
                if self.server.headers:
                    self.headers_text.delete("1.0", tk.END)
                    header_lines = [f"{k}={v}" for k, v in self.server.headers.items()]
                    self.headers_text.insert("1.0", "\n".join(header_lines))

            self._on_type_changed()

        # Ensure text widgets sized appropriately after population
        self._auto_resize_text(self.args_text, min_lines=4, max_lines=14)
        self._auto_resize_text(self.env_text, min_lines=3, max_lines=12)
        self._auto_resize_text(self.headers_text, min_lines=3, max_lines=12)
        self._adjust_size()

    def _parse_key_value_text(self, text_widget) -> dict:
        """Parse KEY=VALUE format from text widget"""
        result = {}
        content = text_widget.get("1.0", tk.END).strip()

        if not content:
            return result

        for line in content.split("\n"):
            line = line.strip()
            if not line:
                continue

            if "=" in line:
                key, value = line.split("=", 1)
            elif ":" in line:
                key, value = line.split(":", 1)
            else:
                continue

            result[key.strip()] = value.strip()

        return result

    def _validate_fields(self) -> Optional[str]:
        """
        Validate all fields

        Returns:
            Error message if validation fails, None if valid
        """
        # Validate server ID
        server_id = self.id_var.get().strip()
        if not server_id:
            return "Server ID is required"

        # ID must be alphanumeric with hyphens/underscores
        if not all(c.isalnum() or c in "-_" for c in server_id):
            return "Server ID must contain only letters, numbers, hyphens, and underscores"

        server_type = self.type_var.get()

        if server_type == "stdio":
            # Validate command
            command = self.command_var.get().strip()
            if not command:
                return "Command is required for stdio servers"

            args_content = self.args_text.get("1.0", tk.END).strip()
            args = [line.strip() for line in args_content.split("\n") if line.strip()]
            if not args:
                return "At least one argument is required for stdio servers"

            # Validate command for injection
            is_valid, error = validate_command(command, args)
            if not is_valid:
                return f"Invalid command: {error}"

        elif server_type == "http":
            # Validate URL
            url = self.url_var.get().strip()
            if not url:
                return "URL is required for HTTP servers"

            is_valid, error = validate_url(url)
            if not is_valid:
                return f"Invalid URL: {error}"

        return None

    def _on_save(self):
        """Handle save button click"""
        # Validate fields
        error = self._validate_fields()
        if error:
            messagebox.showerror("Validation Error", error, parent=self)
            return

        # Build server object
        server_id = self.id_var.get().strip()
        server_type = self.type_var.get()

        # Get order (preserve existing order or use 999 for new)
        order = self.server.order if self.server else 999

        # Base fields
        enabled_state = self.server.enabled if self.server else True

        server_data = {
            "id": server_id,
            "type": server_type,
            "enabled": enabled_state,
            "is_template": False,  # User-created servers are not templates
            "order": order,
            "description": self.description_var.get().strip(),
            "category": self.category_var.get().strip(),
        }

        if server_type == "stdio":
            # Parse args
            args_content = self.args_text.get("1.0", tk.END).strip()
            args = [line.strip() for line in args_content.split("\n") if line.strip()]

            # Parse env vars
            env = self._parse_key_value_text(self.env_text)

            server_data.update({
                "command": self.command_var.get().strip(),
                "args": args,
                "env": env,
                "url": None,
                "headers": None,
            })

        elif server_type == "http":
            # Parse headers
            headers = self._parse_key_value_text(self.headers_text)

            server_data.update({
                "url": self.url_var.get().strip(),
                "headers": headers if headers else None,
                "command": None,
                "args": None,
                "env": None,
            })

        # Create MCPServer object
        server = MCPServer.from_dict(server_data)

        # Call save callback
        if self.on_save:
            self.on_save(server_id, server)

        # Close dialog
        self.result = (server_id, server)
        self.destroy()

    def _on_cancel(self):
        """Handle cancel button click"""
        self.result = None
        self.destroy()

    def get_result(self) -> Optional[MCPServer]:
        """Get the result after dialog closes"""
        return self.result