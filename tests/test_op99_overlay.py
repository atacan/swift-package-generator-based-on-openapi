"""Tests for Operation 6: Apply OpenAPI overlay using openapi-format CLI."""

import json
import subprocess
from unittest.mock import MagicMock, patch

from bootstrapper.transformers.op99_overlay import apply_overlay


class TestOp6Overlay:
    """Tests for Operation 6: Apply OpenAPI overlay using openapi-format CLI."""

    def test_no_overlay_file_skips(self, tmp_path):
        """Test that missing overlay file is skipped gracefully."""
        # Create only the openapi file
        openapi_file = tmp_path / "openapi.yaml"
        openapi_file.write_text("openapi: 3.1.0\ninfo:\n  title: Test\n  version: 1.0.0\n")

        result = apply_overlay(tmp_path, "openapi.yaml")

        assert result["applied"] is False
        assert result["skipped"] is True
        assert "No overlay file found" in result["reason"]

    def test_openapi_file_not_found(self, tmp_path):
        """Test that missing openapi file returns error."""
        result = apply_overlay(tmp_path, "openapi.yaml")

        assert result["applied"] is False
        assert result["skipped"] is False
        assert "OpenAPI file not found" in result["reason"]

    def test_empty_overlay_actions_skips(self, tmp_path):
        """Test that overlay with no actions is skipped."""
        # Create openapi file
        openapi_file = tmp_path / "openapi.yaml"
        openapi_file.write_text("openapi: 3.1.0\ninfo:\n  title: Test\n  version: 1.0.0\n")

        # Create empty overlay
        overlay_file = tmp_path / "openapi-overlay.yaml"
        overlay_file.write_text("overlay: 1.0.0\ninfo:\n  title: Test Overlay\nactions: []\n")

        result = apply_overlay(tmp_path, "openapi.yaml")

        assert result["applied"] is False
        assert result["skipped"] is True
        assert "Overlay has no actions defined" in result["reason"]

    def test_overlay_missing_actions_key_skips(self, tmp_path):
        """Test that overlay without actions key is skipped."""
        # Create openapi file
        openapi_file = tmp_path / "openapi.yaml"
        openapi_file.write_text("openapi: 3.1.0\ninfo:\n  title: Test\n  version: 1.0.0\n")

        # Create overlay without actions
        overlay_file = tmp_path / "openapi-overlay.yaml"
        overlay_file.write_text("overlay: 1.0.0\ninfo:\n  title: Test Overlay\n")

        result = apply_overlay(tmp_path, "openapi.yaml")

        assert result["applied"] is False
        assert result["skipped"] is True
        assert "Overlay has no actions defined" in result["reason"]

    def test_json_overlay_with_json_openapi(self, tmp_path):
        """Test that JSON overlay is used with JSON openapi file."""
        # Create openapi.json
        openapi_file = tmp_path / "openapi.json"
        openapi_file.write_text(
            json.dumps({"openapi": "3.1.0", "info": {"title": "Test", "version": "1.0.0"}})
        )

        # Create openapi-overlay.json (empty actions)
        overlay_file = tmp_path / "openapi-overlay.json"
        overlay_file.write_text(json.dumps({"overlay": "1.0.0", "info": {"title": "Overlay"}}))

        result = apply_overlay(tmp_path, "openapi.json")

        # Should skip because no actions
        assert result["skipped"] is True

    def test_unsupported_file_extension(self, tmp_path):
        """Test that unsupported file extensions are rejected."""
        result = apply_overlay(tmp_path, "openapi.txt")

        assert result["applied"] is False
        assert result["skipped"] is False
        assert "Unsupported file extension" in result["reason"]

    def test_malformed_overlay_file(self, tmp_path):
        """Test that malformed overlay file returns error."""
        # Create openapi file
        openapi_file = tmp_path / "openapi.yaml"
        openapi_file.write_text("openapi: 3.1.0\ninfo:\n  title: Test\n  version: 1.0.0\n")

        # Create malformed overlay
        overlay_file = tmp_path / "openapi-overlay.yaml"
        overlay_file.write_text("{ invalid yaml [")

        result = apply_overlay(tmp_path, "openapi.yaml")

        assert result["applied"] is False
        assert result["skipped"] is False
        assert "Failed to parse overlay file" in result["reason"]

    @patch("subprocess.run")
    def test_openapi_format_not_installed(self, mock_run, tmp_path):
        """Test that missing openapi-format CLI is reported clearly."""
        # Create files
        openapi_file = tmp_path / "openapi.yaml"
        openapi_file.write_text("openapi: 3.1.0\ninfo:\n  title: Test\n  version: 1.0.0\n")

        overlay_file = tmp_path / "openapi-overlay.yaml"
        overlay_content = (
            "overlay: 1.0.0\ninfo:\n  title: Overlay\nactions:\n"
            "  - target: $.info\n    update:\n      description: Updated\n"
        )
        overlay_file.write_text(overlay_content)

        # Mock subprocess to raise FileNotFoundError
        mock_run.side_effect = FileNotFoundError()

        result = apply_overlay(tmp_path, "openapi.yaml")

        assert result["applied"] is False
        assert result["skipped"] is False
        assert "openapi-format CLI not found" in result["reason"]
        assert "npm install -g openapi-format" in result["reason"]

    @patch("subprocess.run")
    def test_openapi_format_timeout(self, mock_run, tmp_path):
        """Test that timeout is handled gracefully."""
        # Create files
        openapi_file = tmp_path / "openapi.yaml"
        openapi_file.write_text("openapi: 3.1.0\ninfo:\n  title: Test\n  version: 1.0.0\n")

        overlay_file = tmp_path / "openapi-overlay.yaml"
        overlay_content = (
            "overlay: 1.0.0\ninfo:\n  title: Overlay\nactions:\n"
            "  - target: $.info\n    update:\n      description: Updated\n"
        )
        overlay_file.write_text(overlay_content)

        # Mock subprocess to raise TimeoutExpired
        mock_run.side_effect = subprocess.TimeoutExpired("openapi-format", 30)

        result = apply_overlay(tmp_path, "openapi.yaml")

        assert result["applied"] is False
        assert result["skipped"] is False
        assert "timed out" in result["reason"]

    @patch("subprocess.run")
    def test_openapi_format_error(self, mock_run, tmp_path):
        """Test that openapi-format errors are captured."""
        # Create files
        openapi_file = tmp_path / "openapi.yaml"
        openapi_file.write_text("openapi: 3.1.0\ninfo:\n  title: Test\n  version: 1.0.0\n")

        overlay_file = tmp_path / "openapi-overlay.yaml"
        overlay_content = (
            "overlay: 1.0.0\ninfo:\n  title: Overlay\nactions:\n"
            "  - target: $.info\n    update:\n      description: Updated\n"
        )
        overlay_file.write_text(overlay_content)

        # Mock subprocess to return error
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "Invalid overlay syntax"
        mock_run.side_effect = subprocess.CalledProcessError(
            1, "openapi-format", stderr="Invalid overlay syntax"
        )

        result = apply_overlay(tmp_path, "openapi.yaml")

        assert result["applied"] is False
        assert result["skipped"] is False
        assert "openapi-format failed" in result["reason"]
        assert "exit code 1" in result["reason"]

    @patch("subprocess.run")
    def test_successful_overlay_application(self, mock_run, tmp_path):
        """Test successful overlay application."""
        # Create files
        openapi_file = tmp_path / "openapi.yaml"
        openapi_file.write_text("openapi: 3.1.0\ninfo:\n  title: Test\n  version: 1.0.0\n")

        overlay_file = tmp_path / "openapi-overlay.yaml"
        overlay_content = (
            "overlay: 1.0.0\ninfo:\n  title: Overlay\nactions:\n"
            "  - target: $.info\n    update:\n      description: Updated\n"
        )
        overlay_file.write_text(overlay_content)

        # Mock successful subprocess call
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = apply_overlay(tmp_path, "openapi.yaml")

        assert result["applied"] is True
        assert result["skipped"] is False
        assert "successfully" in result["reason"]

        # Verify the command was called correctly
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert call_args[0] == "openapi-format"
        assert "--no-sort" in call_args
        assert "--overlayFile" in call_args
        assert str(openapi_file) in call_args
        assert str(overlay_file) in call_args

    @patch("subprocess.run")
    def test_yml_extension_supported(self, mock_run, tmp_path):
        """Test that .yml extension is supported alongside .yaml."""
        # Create files with .yml extension
        openapi_file = tmp_path / "openapi.yml"
        openapi_file.write_text("openapi: 3.1.0\ninfo:\n  title: Test\n  version: 1.0.0\n")

        overlay_file = tmp_path / "openapi-overlay.yaml"  # Still .yaml for overlay
        overlay_content = (
            "overlay: 1.0.0\ninfo:\n  title: Overlay\nactions:\n"
            "  - target: $.info\n    update:\n      description: Updated\n"
        )
        overlay_file.write_text(overlay_content)

        # Mock successful subprocess call
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = apply_overlay(tmp_path, "openapi.yml")

        assert result["applied"] is True
