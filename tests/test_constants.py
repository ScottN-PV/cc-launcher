"""Unit tests for constants and templates."""

import pytest
from utils.constants import MCP_SERVER_TEMPLATES, ERROR_MESSAGES, CONFIG_DIR


class TestMCPTemplates:
    """Tests for pre-loaded MCP server templates."""

    def test_all_templates_present(self):
        """Verify all required templates exist."""
        expected_templates = [
            "filesystem",
            "ref",
            "supabase",
            "lucide-icons",
            "shadcn",
            "sequential-thinking",
            "motion"
        ]
        for template_id in expected_templates:
            assert template_id in MCP_SERVER_TEMPLATES, f"Missing template: {template_id}"

    def test_templates_have_required_fields(self):
        """Verify each template has all required fields."""
        for template_id, server in MCP_SERVER_TEMPLATES.items():
            assert server.id == template_id
            assert server.type == "stdio"  # All current templates are stdio
            assert server.is_template is True
            assert server.command is not None
            assert server.args is not None
            assert len(server.args) > 0
            assert server.description != ""
            assert server.category != ""
            assert server.validate_fields() is True, f"Template {template_id} has invalid fields"

    def test_no_duplicate_ids(self):
        """Verify no duplicate template IDs."""
        ids = [server.id for server in MCP_SERVER_TEMPLATES.values()]
        assert len(ids) == len(set(ids)), "Duplicate template IDs found"

    def test_no_duplicate_orders(self):
        """Verify no duplicate display orders."""
        orders = [server.order for server in MCP_SERVER_TEMPLATES.values()]
        assert len(orders) == len(set(orders)), "Duplicate template orders found"

    def test_templates_disabled_by_default(self):
        """Verify templates are disabled by default."""
        for server in MCP_SERVER_TEMPLATES.values():
            assert server.enabled is False, f"Template {server.id} should be disabled by default"

    def test_filesystem_template_config(self):
        """Verify filesystem template has correct configuration."""
        fs = MCP_SERVER_TEMPLATES["filesystem"]
        assert fs.id == "filesystem"
        assert fs.command == "cmd"
        assert "@modelcontextprotocol/server-filesystem" in " ".join(fs.args)
        assert "%CD%" in fs.args  # Should have %CD% for current directory
        assert fs.category == "core"


class TestErrorMessages:
    """Tests for error messages."""

    def test_all_error_messages_exist(self):
        """Verify all expected error messages are defined."""
        expected_errors = [
            "CONFIG_NOT_FOUND",
            "CONFIG_CORRUPTED",
            "TERMINAL_NOT_FOUND",
            "CLAUDE_CODE_RUNNING",
            "LAUNCH_FAILED",
            "MCP_CONFIG_FAILED",
            "NETWORK_OFFLINE"
        ]
        for error_key in expected_errors:
            assert error_key in ERROR_MESSAGES, f"Missing error message: {error_key}"
            assert ERROR_MESSAGES[error_key] != "", f"Empty error message for: {error_key}"

    def test_error_messages_have_placeholders(self):
        """Verify error messages with placeholders are properly formatted."""
        # CLAUDE_CODE_RUNNING should have {pid} placeholder
        assert "{pid}" in ERROR_MESSAGES["CLAUDE_CODE_RUNNING"]


class TestPaths:
    """Tests for configuration paths."""

    def test_config_dir_exists_or_can_be_created(self):
        """Verify config directory can be created."""
        # Just verify the path is valid, don't actually create it yet
        assert CONFIG_DIR is not None
        assert str(CONFIG_DIR).endswith(".claude")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])