"""Profile data model for Claude Code Launcher."""

from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime


@dataclass
class Profile:
    """Profile containing a set of MCP servers for a specific project context."""

    id: str
    name: str
    servers: List[str]  # List of server IDs
    created: datetime
    modified: datetime
    last_used: Optional[datetime] = None
    description: str = ""
    scope: str = "global"  # "global" or "project"
    project_path: Optional[str] = None  # Path for project-specific profiles

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "servers": self.servers,
            "created": self.created.isoformat(),
            "modified": self.modified.isoformat(),
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "description": self.description,
            "scope": self.scope,
            "project_path": self.project_path
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Profile":
        """Create from dictionary loaded from JSON."""
        created = datetime.fromisoformat(data["created"])
        modified = datetime.fromisoformat(data["modified"])
        last_used = None
        if data.get("last_used"):
            try:
                last_used = datetime.fromisoformat(data["last_used"])
            except (ValueError, TypeError):
                pass

        return cls(
            id=data["id"],
            name=data["name"],
            servers=data.get("servers", []),
            created=created,
            modified=modified,
            last_used=last_used,
            description=data.get("description", ""),
            scope=data.get("scope", "global"),
            project_path=data.get("project_path")
        )