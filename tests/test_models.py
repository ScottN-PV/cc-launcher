"""Unit tests for data models."""

import pytest
from datetime import datetime
from models.preferences import Preferences
from models.server import MCPServer, ValidationStatus
from models.profile import Profile


class TestPreferences:
    """Tests for Preferences model."""

    def test_create_with_defaults(self):
        """Test creating preferences with default values."""
        prefs = Preferences()
        assert prefs.theme == "dark"
        assert prefs.default_path == "C:\\Dev"
        assert prefs.last_path == ""
        assert prefs.last_profile == "default"
        assert prefs.minimize_on_launch is True
        assert prefs.close_to_tray is True
        assert prefs.auto_start is False
        assert prefs.skip_validation is False
        assert prefs.window_geometry["width"] == 800
        assert prefs.window_geometry["height"] == 700

    def test_to_dict_from_dict(self):
        """Test serialization and deserialization."""
        prefs = Preferences(
            theme="light",
            default_path="C:\\Projects",
            last_path="C:\\Projects\\test",
            last_profile="frontend"
        )
        data = prefs.to_dict()

        # Verify dict contains all fields
        assert data["theme"] == "light"
        assert data["default_path"] == "C:\\Projects"
        assert data["last_path"] == "C:\\Projects\\test"
        assert data["last_profile"] == "frontend"

        # Deserialize and verify
        restored = Preferences.from_dict(data)
        assert restored.theme == prefs.theme
        assert restored.default_path == prefs.default_path
        assert restored.last_path == prefs.last_path
        assert restored.last_profile == prefs.last_profile


class TestValidationStatus:
    """Tests for ValidationStatus model."""

    def test_create_with_defaults(self):
        """Test creating validation status with defaults."""
        status = ValidationStatus()
        assert status.npm_available is None
        assert status.npm_version is None
        assert status.locally_installed is None
        assert status.local_version is None
        assert status.last_checked is None
        assert status.error_message is None
        assert status.cached is False

    def test_to_dict_from_dict(self):
        """Test serialization and deserialization."""
        now = datetime.now()
        status = ValidationStatus(
            npm_available=True,
            npm_version="1.2.0",
            locally_installed=True,
            local_version="1.2.0",
            last_checked=now,
            cached=False
        )
        data = status.to_dict()

        # Verify dict
        assert data["npm_available"] is True
        assert data["npm_version"] == "1.2.0"
        assert data["last_checked"] == now.isoformat()

        # Deserialize
        restored = ValidationStatus.from_dict(data)
        assert restored.npm_available is True
        assert restored.npm_version == "1.2.0"
        assert restored.last_checked.isoformat() == now.isoformat()


class TestMCPServer:
    """Tests for MCPServer model."""

    def test_create_stdio_server(self):
        """Test creating a stdio server."""
        server = MCPServer(
            id="filesystem",
            type="stdio",
            command="cmd",
            args=["/c", "npx", "-y", "@modelcontextprotocol/server-filesystem", "%CD%"],
            description="File system access",
            category="core"
        )
        assert server.id == "filesystem"
        assert server.type == "stdio"
        assert server.enabled is True
        assert server.is_template is False
        assert server.command == "cmd"
        assert len(server.args) == 5

    def test_create_http_server(self):
        """Test creating an HTTP server."""
        server = MCPServer(
            id="api-server",
            type="http",
            url="http://localhost:3000",
            headers={"Authorization": "Bearer token"},
            description="API server"
        )
        assert server.id == "api-server"
        assert server.type == "http"
        assert server.url == "http://localhost:3000"
        assert server.headers["Authorization"] == "Bearer token"

    def test_validate_fields_stdio(self):
        """Test field validation for stdio servers."""
        # Valid stdio server
        valid_server = MCPServer(
            id="test",
            type="stdio",
            command="cmd",
            args=["/c", "echo", "test"]
        )
        assert valid_server.validate_fields() is True

        # Invalid - missing command
        invalid_server = MCPServer(
            id="test",
            type="stdio",
            args=["/c", "echo", "test"]
        )
        assert invalid_server.validate_fields() is False

        # Invalid - missing args
        invalid_server2 = MCPServer(
            id="test",
            type="stdio",
            command="cmd"
        )
        assert invalid_server2.validate_fields() is False

    def test_validate_fields_http(self):
        """Test field validation for HTTP servers."""
        # Valid HTTP server
        valid_server = MCPServer(
            id="test",
            type="http",
            url="http://localhost:3000"
        )
        assert valid_server.validate_fields() is True

        # Invalid - missing URL
        invalid_server = MCPServer(
            id="test",
            type="http"
        )
        assert invalid_server.validate_fields() is False

    def test_to_dict_from_dict(self):
        """Test serialization and deserialization."""
        server = MCPServer(
            id="filesystem",
            type="stdio",
            enabled=True,
            is_template=True,
            order=1,
            command="cmd",
            args=["/c", "npx", "-y", "@modelcontextprotocol/server-filesystem"],
            env={"PATH": "C:\\Program Files\\nodejs"},
            description="File system access",
            category="core"
        )
        data = server.to_dict()

        # Verify dict
        assert data["id"] == "filesystem"
        assert data["type"] == "stdio"
        assert data["enabled"] is True
        assert data["is_template"] is True
        assert data["order"] == 1

        # Deserialize
        restored = MCPServer.from_dict(data)
        assert restored.id == server.id
        assert restored.type == server.type
        assert restored.enabled == server.enabled
        assert restored.is_template == server.is_template
        assert restored.command == server.command
        assert restored.args == server.args
        assert restored.env == server.env


class TestProfile:
    """Tests for Profile model."""

    def test_create_profile(self):
        """Test creating a profile."""
        now = datetime.now()
        profile = Profile(
            id="frontend-dev",
            name="Frontend Development",
            servers=["filesystem", "ref", "shadcn"],
            created=now,
            modified=now,
            description="React/Next.js development"
        )
        assert profile.id == "frontend-dev"
        assert profile.name == "Frontend Development"
        assert len(profile.servers) == 3
        assert "filesystem" in profile.servers
        assert profile.last_used is None

    def test_to_dict_from_dict(self):
        """Test serialization and deserialization."""
        now = datetime.now()
        profile = Profile(
            id="test-profile",
            name="Test Profile",
            servers=["server1", "server2"],
            created=now,
            modified=now,
            last_used=now,
            description="Test description"
        )
        data = profile.to_dict()

        # Verify dict
        assert data["id"] == "test-profile"
        assert data["name"] == "Test Profile"
        assert data["servers"] == ["server1", "server2"]
        assert data["description"] == "Test description"

        # Deserialize
        restored = Profile.from_dict(data)
        assert restored.id == profile.id
        assert restored.name == profile.name
        assert restored.servers == profile.servers
        assert restored.description == profile.description
        assert restored.created.isoformat() == profile.created.isoformat()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])