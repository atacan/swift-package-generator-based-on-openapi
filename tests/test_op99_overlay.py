"""Tests for Operation 99: Apply OpenAPI overlays using Speakeasy's OpenAPI CLI."""

import json
import shutil
import subprocess
from unittest.mock import MagicMock, patch

import pytest
import yaml

from bootstrapper.transformers.op99_overlay import apply_overlay, apply_overlay_file


class TestOp99Overlay:
    """Tests for Operation 99: Apply overlays using Speakeasy's OpenAPI CLI."""

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
    def test_speakeasy_openapi_not_installed(self, mock_run, tmp_path):
        """Test that a missing Speakeasy OpenAPI CLI is reported clearly."""
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
        assert "Speakeasy OpenAPI CLI not found" in result["reason"]
        assert "brew install openapi" in result["reason"]

    @patch("subprocess.run")
    def test_speakeasy_openapi_timeout(self, mock_run, tmp_path):
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
        mock_run.side_effect = subprocess.TimeoutExpired("openapi", 30)

        result = apply_overlay(tmp_path, "openapi.yaml")

        assert result["applied"] is False
        assert result["skipped"] is False
        assert "timed out" in result["reason"]

    @patch("subprocess.run")
    def test_speakeasy_openapi_error(self, mock_run, tmp_path):
        """Test that Speakeasy OpenAPI errors are captured."""
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
        mock_run.side_effect = subprocess.CalledProcessError(
            1, "openapi", stderr="Invalid overlay syntax"
        )

        result = apply_overlay(tmp_path, "openapi.yaml")

        assert result["applied"] is False
        assert result["skipped"] is False
        assert "Speakeasy OpenAPI failed" in result["reason"]
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
        assert call_args == [
            "openapi",
            "overlay",
            "apply",
            "--overlay",
            str(overlay_file),
            "--schema",
            str(openapi_file),
            "--out",
            str(openapi_file),
        ]

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

    @patch("subprocess.run")
    def test_apply_overlay_file_uses_explicit_overlay_path(self, mock_run, tmp_path):
        """Test path-based overlay application uses the exact overlay file provided."""
        openapi_file = tmp_path / "fixed.yaml"
        openapi_file.write_text("openapi: 3.1.0\ninfo:\n  title: Test\n  version: 1.0.0\n")

        overlay_file = tmp_path / "custom-overlay.yaml"
        overlay_file.write_text(
            "overlay: 1.0.0\ninfo:\n  title: Overlay\nactions:\n"
            "  - target: $.info\n    update:\n      description: Updated\n"
        )

        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = apply_overlay_file(openapi_file, overlay_file)

        assert result["applied"] is True
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert str(openapi_file) in call_args
        assert str(overlay_file) in call_args

    def test_apply_overlay_file_missing_overlay_is_error(self, tmp_path):
        """Test path-based overlay application fails for missing explicit overlays."""
        openapi_file = tmp_path / "fixed.yaml"
        openapi_file.write_text("openapi: 3.1.0\ninfo:\n  title: Test\n  version: 1.0.0\n")

        result = apply_overlay_file(openapi_file, tmp_path / "missing-overlay.yaml")

        assert result["applied"] is False
        assert result["skipped"] is False
        assert "Overlay file not found" in result["reason"]

    @pytest.mark.slow
    @pytest.mark.skipif(
        shutil.which("openapi") is None, reason="Speakeasy OpenAPI CLI not installed"
    )
    def test_speakeasy_preserves_schema_after_quoted_large_number_example(self, tmp_path):
        """Regression test for schema loss caused by openapi-format's YAML preprocessor."""
        openapi_file = tmp_path / "openapi.yaml"
        openapi_file.write_text(
            "openapi: 3.1.0\n"
            "info:\n"
            "  title: Test\n"
            "  version: 1.0.0\n"
            "paths: {}\n"
            "components:\n"
            "  schemas:\n"
            "    Before:\n"
            '      example: "{\\n  \\"score\\": 0.8189693396524255,\\n}"\n'
            "    CreateResponse:\n"
            "      type: object\n",
            encoding="utf-8",
        )
        overlay_file = tmp_path / "openapi-overlay.yaml"
        overlay_file.write_text(
            "overlay: 1.0.0\n"
            "info:\n"
            "  title: Test Overlay\n"
            "  version: 1.0.0\n"
            "actions:\n"
            "  - target: $.info\n"
            "    update:\n"
            "      description: Updated\n",
            encoding="utf-8",
        )

        result = apply_overlay(tmp_path)

        assert result["applied"] is True
        transformed = yaml.safe_load(openapi_file.read_text(encoding="utf-8"))
        assert transformed["components"]["schemas"]["CreateResponse"] == {"type": "object"}
        assert transformed["info"]["description"] == "Updated"
