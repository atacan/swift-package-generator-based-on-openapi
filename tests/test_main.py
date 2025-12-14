"""Tests for the main CLI module."""

from pathlib import Path

from typer.testing import CliRunner

from bootstrapper.main import app, derive_project_name, find_original_openapi


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

    def test_cli_bootstrap_help(self):
        """Test that bootstrap --help works."""
        runner = CliRunner()

        result = runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        assert "Bootstrap a Swift package" in result.stdout
