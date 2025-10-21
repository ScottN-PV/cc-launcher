"""Preferences data model for Claude Code Launcher."""

from dataclasses import dataclass, field
from typing import Dict, List, Literal


@dataclass
class Preferences:
    """User preferences for the application."""

    # Theme
    theme: Literal["light", "dark"] = "dark"

    # Paths
    default_path: str = "C:\\Dev"
    last_path: str = ""
    recent_projects: List[str] = field(default_factory=list)
    project_last_profiles: Dict[str, str] = field(default_factory=dict)

    # Profile
    last_profile: str = "default"

    # Window behavior
    minimize_on_launch: bool = True
    close_to_tray: bool = True
    auto_start: bool = False

    # Server management
    auto_update_servers: bool = True
    skip_validation: bool = False  # Offline mode

    # Terminal preferences
    force_powershell: bool = False  # Skip Windows Terminal, use PowerShell directly

    # Window geometry
    window_geometry: Dict[str, int] = field(default_factory=lambda: {
        "width": 800,
        "height": 700,
        "x": None,
        "y": None
    })

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "theme": self.theme,
            "default_path": self.default_path,
            "last_path": self.last_path,
            "recent_projects": self.recent_projects,
            "project_last_profiles": self.project_last_profiles,
            "last_profile": self.last_profile,
            "minimize_on_launch": self.minimize_on_launch,
            "close_to_tray": self.close_to_tray,
            "auto_start": self.auto_start,
            "auto_update_servers": self.auto_update_servers,
            "skip_validation": self.skip_validation,
            "force_powershell": self.force_powershell,
            "window_geometry": self.window_geometry
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Preferences":
        """Create from dictionary loaded from JSON."""
        return cls(
            theme=data.get("theme", "dark"),
            default_path=data.get("default_path", "C:\\Dev"),
            last_path=data.get("last_path", ""),
            recent_projects=data.get("recent_projects", []),
            project_last_profiles=data.get("project_last_profiles", {}),
            last_profile=data.get("last_profile", "default"),
            minimize_on_launch=data.get("minimize_on_launch", True),
            close_to_tray=data.get("close_to_tray", True),
            auto_start=data.get("auto_start", False),
            auto_update_servers=data.get("auto_update_servers", True),
            skip_validation=data.get("skip_validation", False),
            force_powershell=data.get("force_powershell", False),
            window_geometry=data.get("window_geometry", {
                "width": 800,
                "height": 700,
                "x": None,
                "y": None
            })
        )