"""Command panel UI component for Claude Code MCP Manager."""

import logging
import tkinter as tk
import ttkbootstrap as ttk

logger = logging.getLogger(__name__)


class LaunchCommandPanel(ttk.Frame):
    """Display a copyable launch command instead of executing it automatically."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)

        self._current_command: str = ""

        self._create_widgets()
        self._layout_widgets()
        self.show_placeholder("Select a project and enable servers to generate a command.")

    def _create_widgets(self) -> None:
        """Create UI widgets."""
        self.title_label = ttk.Label(
            self,
            text="Launch Command",
            font=("Segoe UI", 12, "bold")
        )

        import sys
        if sys.platform == "win32":
            desc_text = "Copy the command below and run it in PowerShell to start Claude Code with the selected MCP servers."
        else:
            desc_text = "Copy the command below and run it in your terminal (bash/zsh) to start Claude Code with the selected MCP servers."
        
        self.description_label = ttk.Label(
            self,
            text=desc_text,
            wraplength=460,
            bootstyle="secondary"
        )

        self.command_text = tk.Text(
            self,
            height=4,
            wrap="word",
            relief="solid",
            borderwidth=1,
            font=("Consolas", 10)
        )
        self.command_text.configure(state=tk.DISABLED)

        self.copy_button = ttk.Button(
            self,
            text="Copy Command",
            command=self._copy_command,
            bootstyle="secondary"
        )

        self.status_label = ttk.Label(
            self,
            text="",
            bootstyle="secondary",
            wraplength=460
        )

    def _layout_widgets(self) -> None:
        """Arrange widgets in the layout."""
        self.columnconfigure(0, weight=1)

        self.title_label.grid(row=0, column=0, sticky="w")
        self.description_label.grid(row=1, column=0, sticky="ew", pady=(4, 8))
        self.command_text.grid(row=2, column=0, sticky="ew")
        self.copy_button.grid(row=3, column=0, sticky="e", pady=8)
        self.status_label.grid(row=4, column=0, sticky="ew")

    def _set_command_text(self, value: str) -> None:
        self.command_text.configure(state=tk.NORMAL)
        self.command_text.delete("1.0", tk.END)
        if value:
            self.command_text.insert(tk.END, value)
        self.command_text.update_idletasks()

        display_lines = self.command_text.count("1.0", "end-1c", "displaylines")
        line_count = display_lines[0] if display_lines else 1

        if value:
            minimum_lines = 4
        else:
            minimum_lines = 3

        height = min(max(line_count, minimum_lines), 15)
        self.command_text.configure(height=height)

        self.command_text.configure(state=tk.DISABLED)
        self.event_generate("<<LaunchCommandPanelUpdated>>", when="tail")

    def show_placeholder(self, message: str) -> None:
        """Display an informational placeholder message."""
        self._current_command = ""
        self._set_command_text("")
        self._update_status(message, "secondary")

    def show_error(self, message: str) -> None:
        """Display an error message and clear the command."""
        self._current_command = ""
        self._set_command_text("")
        self._update_status(message, "danger")

    def show_command(self, command: str) -> None:
        """Display a launch command and enable copying."""
        import sys
        if sys.platform == "win32":
            status_text = "Command ready. Copy and run it in PowerShell."
        else:
            status_text = "Command ready. Copy and run it in your terminal."
        
        self._current_command = command
        self._set_command_text(command)
        self._update_status(status_text, "success")

    def _update_status(self, message: str, bootstyle: str) -> None:
        self.status_label.configure(text=message, bootstyle=bootstyle)

    def _copy_command(self) -> None:
        """Copy the current command to the clipboard."""
        if not self._current_command:
            logger.debug("No command available to copy")
            return

        try:
            self.clipboard_clear()
            self.clipboard_append(self._current_command)
            self._update_status("Command copied to clipboard.", "success")
            logger.info("Launch command copied to clipboard")
        except Exception as exc:
            logger.error("Failed to copy command: %s", exc)
            self._update_status("Unable to access clipboard. Try copying manually.", "danger")
