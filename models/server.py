"""MCP Server data model for Claude Code Launcher."""

from dataclasses import dataclass, field
from typing import Dict, List, Literal, Optional
from datetime import datetime


@dataclass
class ValidationStatus:
    """Validation status for an MCP server."""

    npm_available: Optional[bool] = None
    npm_version: Optional[str] = None
    locally_installed: Optional[bool] = None
    local_version: Optional[str] = None
    last_checked: Optional[datetime] = None
    error_message: Optional[str] = None
    cached: bool = False  # Whether this is cached data

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "npm_available": self.npm_available,
            "npm_version": self.npm_version,
            "locally_installed": self.locally_installed,
            "local_version": self.local_version,
            "last_checked": self.last_checked.isoformat() if self.last_checked else None,
            "error_message": self.error_message,
            "cached": self.cached
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ValidationStatus":
        """Create from dictionary loaded from JSON."""
        last_checked = None
        if data.get("last_checked"):
            try:
                last_checked = datetime.fromisoformat(data["last_checked"])
            except (ValueError, TypeError):
                pass

        return cls(
            npm_available=data.get("npm_available"),
            npm_version=data.get("npm_version"),
            locally_installed=data.get("locally_installed"),
            local_version=data.get("local_version"),
            last_checked=last_checked,
            error_message=data.get("error_message"),
            cached=data.get("cached", False)
        )


@dataclass
class MCPServer:
    """MCP Server configuration."""

    # Identity
    id: str  # Unique identifier
    type: Literal["stdio", "http"]
    enabled: bool = True
    is_template: bool = False  # Pre-loaded template
    order: int = 0  # Display order

    # Metadata
    description: str = ""
    category: str = "general"

    # stdio specific
    command: Optional[str] = None
    args: Optional[List[str]] = None  # Supports %CD%, %USERPROFILE%, etc.
    env: Optional[Dict[str, str]] = None

    # http specific
    url: Optional[str] = None
    headers: Optional[Dict[str, str]] = None

    # Validation metadata
    validation: Optional[ValidationStatus] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "type": self.type,
            "enabled": self.enabled,
            "is_template": self.is_template,
            "order": self.order,
            "description": self.description,
            "category": self.category,
            "command": self.command,
            "args": self.args,
            "env": self.env,
            "url": self.url,
            "headers": self.headers,
            "validation": self.validation.to_dict() if self.validation else None
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MCPServer":
        """Create from dictionary loaded from JSON."""
        validation = None
        if data.get("validation"):
            validation = ValidationStatus.from_dict(data["validation"])

        return cls(
            id=data["id"],
            type=data["type"],
            enabled=data.get("enabled", True),
            is_template=data.get("is_template", False),
            order=data.get("order", 0),
            description=data.get("description", ""),
            category=data.get("category", "general"),
            command=data.get("command"),
            args=data.get("args"),
            env=data.get("env"),
            url=data.get("url"),
            headers=data.get("headers"),
            validation=validation
        )

    def validate_fields(self) -> bool:
        """Validate that required fields are present based on server type."""
        if self.type == "stdio":
            return self.command is not None and self.args is not None
        elif self.type == "http":
            return self.url is not None
        return False