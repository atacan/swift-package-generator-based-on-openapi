"""Tests for the main CLI module."""

import subprocess
from pathlib import Path
from unittest.mock import patch

import yaml
from typer.testing import CliRunner

from bootstrapper.config import ProjectConfig
from bootstrapper.main import app, derive_project_name, find_original_openapi, resolve_project_name


class TestFindOriginalOpenAPI:
    """Test the find_original_openapi function."""

    def test_finds_yaml_file(self, tmp_path):
        """Test finding original_openapi.yaml."""
        openapi_file = tmp_path / "original_openapi.yaml"
        openapi_file.write_text("openapi: 3.0.0")

        result = find_original_openapi(tmp_path)

        assert result == openapi_file

    def test_finds_yml_file(self, tmp_path):
        """Test finding original_openapi.yml."""
        openapi_file = tmp_path / "original_openapi.yml"
        openapi_file.write_text("openapi: 3.0.0")

        result = find_original_openapi(tmp_path)

        assert result == openapi_file

    def test_finds_json_file(self, tmp_path):
        """Test finding original_openapi.json."""
        openapi_file = tmp_path / "original_openapi.json"
        openapi_file.write_text('{"openapi": "3.0.0"}')

        result = find_original_openapi(tmp_path)

        assert result == openapi_file

    def test_prefers_yaml_over_yml(self, tmp_path):
        """Test that .yaml is preferred over .yml."""
        yaml_file = tmp_path / "original_openapi.yaml"
        yml_file = tmp_path / "original_openapi.yml"
        yaml_file.write_text("openapi: 3.0.0")
        yml_file.write_text("openapi: 3.0.0")

        result = find_original_openapi(tmp_path)

        assert result == yaml_file

    def test_prefers_yaml_over_json(self, tmp_path):
        """Test that .yaml is preferred over .json."""
        yaml_file = tmp_path / "original_openapi.yaml"
        json_file = tmp_path / "original_openapi.json"
        yaml_file.write_text("openapi: 3.0.0")
        json_file.write_text('{"openapi": "3.0.0"}')

        result = find_original_openapi(tmp_path)

        assert result == yaml_file

    def test_returns_none_when_not_found(self, tmp_path):
        """Test returns None when no OpenAPI file exists."""
        result = find_original_openapi(tmp_path)

        assert result is None

    def test_returns_none_for_empty_directory(self, tmp_path):
        """Test returns None for empty directory."""
        result = find_original_openapi(tmp_path)

        assert result is None


class TestDeriveProjectName:
    """Test the derive_project_name function."""

    def test_simple_directory_name(self, tmp_path):
        """Test with a simple directory name."""
        test_dir = tmp_path / "myproject"
        test_dir.mkdir()

        result = derive_project_name(test_dir)

        assert result == "Myproject"

    def test_hyphenated_directory_name(self, tmp_path):
        """Test converting hyphens to PascalCase."""
        test_dir = tmp_path / "my-api-wrapper"
        test_dir.mkdir()

        result = derive_project_name(test_dir)

        assert result == "MyApiWrapper"

    def test_underscored_directory_name(self, tmp_path):
        """Test converting underscores to PascalCase."""
        test_dir = tmp_path / "my_api_wrapper"
        test_dir.mkdir()

        result = derive_project_name(test_dir)

        assert result == "MyApiWrapper"

    def test_mixed_separators(self, tmp_path):
        """Test with mixed hyphens and underscores."""
        test_dir = tmp_path / "my-api_wrapper"
        test_dir.mkdir()

        result = derive_project_name(test_dir)

        assert result == "MyApiWrapper"

    def test_multiple_consecutive_separators(self, tmp_path):
        """Test with multiple consecutive separators."""
        test_dir = tmp_path / "my--api__wrapper"
        test_dir.mkdir()

        result = derive_project_name(test_dir)

        assert result == "MyApiWrapper"

    def test_uppercase_directory_name(self, tmp_path):
        """Test with uppercase directory name preserves case."""
        test_dir = tmp_path / "MYPROJECT"
        test_dir.mkdir()

        result = derive_project_name(test_dir)

        assert result == "MYPROJECT"

    def test_mixed_case_preserved(self, tmp_path):
        """Test that mixed case like 'AssemblyAI' is preserved."""
        test_dir = tmp_path / "AssemblyAI"
        test_dir.mkdir()

        result = derive_project_name(test_dir)

        assert result == "AssemblyAI"

    def test_mixed_case_with_hyphens(self, tmp_path):
        """Test that mixed case is preserved with hyphens."""
        test_dir = tmp_path / "AssemblyAI-wrapper"
        test_dir.mkdir()

        result = derive_project_name(test_dir)

        assert result == "AssemblyAIWrapper"

    def test_empty_string_returns_default(self):
        """Test that empty directory name returns default."""
        # Create a path that resolves to root or similar edge case
        # For practical purposes, we test the fallback logic
        result = derive_project_name(Path("/"))

        # Root directory "/" should be handled, but we expect fallback
        # The actual behavior depends on OS, but we ensure it doesn't crash
        assert isinstance(result, str)
        assert len(result) > 0

    def test_relative_path_resolved(self, tmp_path):
        """Test that relative paths are resolved correctly."""
        test_dir = tmp_path / "my-project"
        test_dir.mkdir()

        # Change to parent and use relative path
        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            result = derive_project_name(Path("my-project"))
            assert result == "MyProject"
        finally:
            os.chdir(original_cwd)


class TestCLIBootstrapCommand:
    """Test the bootstrap CLI command."""

    def test_cli_requires_openapi_file(self, tmp_path):
        """Test that CLI exits with error if no OpenAPI file found."""
        runner = CliRunner()

        result = runner.invoke(app, [str(tmp_path)])

        assert result.exit_code == 1
        assert "Could not find original_openapi" in result.stdout

    def test_cli_help_command(self):
        """Test that help command works."""
        runner = CliRunner()

        result = runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        assert "Bootstrap a Swift package" in result.stdout
        assert "transform" in result.stdout

    def test_cli_bootstrap_help(self):
        """Test that bootstrap --help works."""
        runner = CliRunner()

        result = runner.invoke(app, ["bootstrap", "--help"])

        assert result.exit_code == 0
        assert "Bootstrap a Swift package" in result.stdout

    def test_legacy_bootstrap_invocation_still_works(self, tmp_path):
        """Test that swift-bootstrapper TARGET_DIR still routes to bootstrap."""
        runner = CliRunner()

        result = runner.invoke(app, [str(tmp_path)])

        assert result.exit_code == 1
        assert "Could not find original_openapi" in result.stdout


class TestCLITransformCommand:
    """Test the transform-only CLI command."""

    def test_cli_transform_help(self):
        """Test that transform --help works."""
        runner = CliRunner()

        result = runner.invoke(app, ["transform", "--help"])

        assert result.exit_code == 0
        assert "Transform an OpenAPI specification" in result.stdout
        assert "--overlay" in result.stdout
        assert "requires Node.js/npx" in result.stdout
        assert "openapi-format" in result.stdout

    def test_transform_writes_output_without_package_scaffolding(self, tmp_path):
        """Test transform-only mode writes a spec and does not create Swift package files."""
        input_file = tmp_path / "input.yaml"
        output_file = tmp_path / "fixed.yaml"
        input_file.write_text(
            """
openapi: 3.1.0
info:
  title: Test
  version: 1.0.0
paths: {}
components:
  schemas:
    Sample:
      type: object
      properties:
        status:
          const: active
        score:
          type: float
""",
            encoding="utf-8",
        )

        result = CliRunner().invoke(app, ["transform", str(input_file), str(output_file)])

        assert result.exit_code == 0
        assert output_file.exists()
        output = yaml.safe_load(output_file.read_text(encoding="utf-8"))
        sample_properties = output["components"]["schemas"]["Sample"]["properties"]
        assert sample_properties["status"]["enum"] == ["active"]
        assert "const" not in sample_properties["status"]
        assert sample_properties["score"]["type"] == "number"
        assert not (tmp_path / "Package.swift").exists()
        assert not (tmp_path / "Sources").exists()
        assert not (tmp_path / "Tests").exists()
        assert not (tmp_path / ".swift-bootstrapper.yaml").exists()

    @patch("bootstrapper.main.apply_overlay_file")
    def test_transform_applies_overlay_after_transformations(self, mock_apply_overlay, tmp_path):
        """Test transform-only mode applies the explicit overlay to the output file."""
        input_file = tmp_path / "input.yaml"
        output_file = tmp_path / "fixed.yaml"
        overlay_file = tmp_path / "custom-overlay.yaml"
        input_file.write_text(
            "openapi: 3.1.0\ninfo:\n  title: Test\n  version: 1.0.0\npaths: {}\n",
            encoding="utf-8",
        )
        overlay_file.write_text("overlay: 1.0.0\nactions: []\n", encoding="utf-8")
        mock_apply_overlay.return_value = {
            "applied": True,
            "skipped": False,
            "reason": "Overlay applied successfully",
        }

        result = CliRunner().invoke(
            app,
            ["transform", str(input_file), str(output_file), "--overlay", str(overlay_file)],
        )

        assert result.exit_code == 0
        assert output_file.exists()
        mock_apply_overlay.assert_called_once_with(output_file.resolve(), overlay_file.resolve())

    def test_transform_missing_input_fails(self, tmp_path):
        """Test missing input file returns a clear failure."""
        output_file = tmp_path / "fixed.yaml"

        result = CliRunner().invoke(
            app,
            ["transform", str(tmp_path / "missing.yaml"), str(output_file)],
        )

        assert result.exit_code == 1
        assert "OpenAPI file not found" in result.stdout

    def test_transform_unsupported_input_suffix_fails(self, tmp_path):
        """Test unsupported input suffix returns a clear failure."""
        input_file = tmp_path / "input.txt"
        output_file = tmp_path / "fixed.yaml"
        input_file.write_text("openapi: 3.1.0\n", encoding="utf-8")

        result = CliRunner().invoke(app, ["transform", str(input_file), str(output_file)])

        assert result.exit_code == 1
        assert "Unsupported file format" in result.stdout

    def test_transform_missing_explicit_overlay_fails(self, tmp_path):
        """Test an explicitly provided missing overlay is an error."""
        input_file = tmp_path / "input.yaml"
        output_file = tmp_path / "fixed.yaml"
        overlay_file = tmp_path / "missing-overlay.yaml"
        input_file.write_text(
            "openapi: 3.1.0\ninfo:\n  title: Test\n  version: 1.0.0\npaths: {}\n",
            encoding="utf-8",
        )

        result = CliRunner().invoke(
            app,
            ["transform", str(input_file), str(output_file), "--overlay", str(overlay_file)],
        )

        assert result.exit_code == 1
        assert "Overlay file not found" in result.stdout

    def test_transform_malformed_overlay_fails(self, tmp_path):
        """Test malformed explicit overlay returns a clear failure."""
        input_file = tmp_path / "input.yaml"
        output_file = tmp_path / "fixed.yaml"
        overlay_file = tmp_path / "overlay.yaml"
        input_file.write_text(
            "openapi: 3.1.0\ninfo:\n  title: Test\n  version: 1.0.0\npaths: {}\n",
            encoding="utf-8",
        )
        overlay_file.write_text("{ invalid yaml [", encoding="utf-8")

        result = CliRunner().invoke(
            app,
            ["transform", str(input_file), str(output_file), "--overlay", str(overlay_file)],
        )

        assert result.exit_code == 1
        assert "Failed to parse overlay file" in result.stdout

    @patch("bootstrapper.transformers.op99_overlay.subprocess.run")
    def test_transform_openapi_format_failure_fails(self, mock_run, tmp_path):
        """Test openapi-format failures are surfaced by transform-only mode."""
        input_file = tmp_path / "input.yaml"
        output_file = tmp_path / "fixed.yaml"
        overlay_file = tmp_path / "overlay.yaml"
        input_file.write_text(
            "openapi: 3.1.0\ninfo:\n  title: Test\n  version: 1.0.0\npaths: {}\n",
            encoding="utf-8",
        )
        overlay_file.write_text(
            "overlay: 1.0.0\nactions:\n"
            "  - target: $.info\n    update:\n      description: Updated\n",
            encoding="utf-8",
        )
        mock_run.side_effect = subprocess.CalledProcessError(
            1, "npx", stderr="Invalid overlay syntax"
        )

        result = CliRunner().invoke(
            app,
            ["transform", str(input_file), str(output_file), "--overlay", str(overlay_file)],
        )

        assert result.exit_code == 1
        assert "openapi-format failed" in result.stdout


class TestResolveProjectName:
    """Test the resolve_project_name function."""

    def test_cli_takes_priority(self, tmp_path):
        """Test that CLI argument takes highest priority."""
        config = ProjectConfig(package_name="ConfigName")

        name, source = resolve_project_name(tmp_path, "CLIName", config)

        assert name == "CLIName"
        assert source == "CLI argument"

    def test_config_takes_priority_over_derived(self, tmp_path):
        """Test that config takes priority over derived name."""
        test_dir = tmp_path / "my-project"
        test_dir.mkdir()
        config = ProjectConfig(package_name="ConfigName")

        name, source = resolve_project_name(test_dir, None, config)

        assert name == "ConfigName"
        assert source == "config file"

    def test_falls_back_to_derived(self, tmp_path):
        """Test that derived name is used when CLI and config are empty."""
        test_dir = tmp_path / "my-project"
        test_dir.mkdir()
        config = ProjectConfig()  # No package_name

        name, source = resolve_project_name(test_dir, None, config)

        assert name == "MyProject"
        assert source == "auto-derived from directory"

    def test_cli_empty_string_uses_config(self, tmp_path):
        """Test that empty CLI string falls back to config."""
        config = ProjectConfig(package_name="ConfigName")

        name, source = resolve_project_name(tmp_path, "", config)

        # Empty string is falsy, so config should be used
        assert name == "ConfigName"
        assert source == "config file"

    def test_cli_none_uses_config(self, tmp_path):
        """Test that None CLI value falls back to config."""
        config = ProjectConfig(package_name="ConfigName")

        name, source = resolve_project_name(tmp_path, None, config)

        assert name == "ConfigName"
        assert source == "config file"

    def test_both_empty_uses_derived(self, tmp_path):
        """Test derivation when both CLI and config are empty."""
        test_dir = tmp_path / "test-api-client"
        test_dir.mkdir()
        config = ProjectConfig()

        name, source = resolve_project_name(test_dir, None, config)

        assert name == "TestApiClient"
        assert source == "auto-derived from directory"
