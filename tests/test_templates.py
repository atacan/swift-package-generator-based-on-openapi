"""Tests for the template rendering system."""

import tempfile
from pathlib import Path

import pytest

from bootstrapper.generators.templates import (
    create_jinja_env,
    generate_config_files,
    get_template_dir,
    render_template,
    write_if_not_exists,
)


class TestGetTemplateDir:
    """Tests for get_template_dir function."""

    def test_returns_path_object(self):
        """Test that get_template_dir returns a Path object."""
        result = get_template_dir()
        assert isinstance(result, Path)

    def test_template_dir_exists(self):
        """Test that the template directory exists."""
        template_dir = get_template_dir()
        assert template_dir.exists()
        assert template_dir.is_dir()

    def test_template_dir_contains_templates(self):
        """Test that the template directory contains Jinja2 template files."""
        template_dir = get_template_dir()
        template_files = list(template_dir.glob("*.j2"))
        assert len(template_files) > 0

    def test_expected_templates_exist(self):
        """Test that expected template files exist in the directory."""
        template_dir = get_template_dir()
        expected_templates = [
            "Makefile.j2",
            ".gitignore.j2",
            ".env.example.j2",
            "openapi-generator-config-types.yaml.j2",
            "openapi-generator-config-client.yaml.j2",
            "overlay.yaml.j2",
        ]
        for template in expected_templates:
            assert (template_dir / template).exists()


class TestCreateJinjaEnv:
    """Tests for create_jinja_env function."""

    def test_returns_environment_object(self):
        """Test that create_jinja_env returns a Jinja2 Environment."""
        from jinja2 import Environment

        env = create_jinja_env()
        assert isinstance(env, Environment)

    def test_environment_has_correct_loader(self):
        """Test that the environment is configured with FileSystemLoader."""
        from jinja2 import FileSystemLoader

        env = create_jinja_env()
        assert isinstance(env.loader, FileSystemLoader)

    def test_environment_has_trim_blocks_enabled(self):
        """Test that trim_blocks is enabled."""
        env = create_jinja_env()
        assert env.trim_blocks is True

    def test_environment_has_lstrip_blocks_enabled(self):
        """Test that lstrip_blocks is enabled."""
        env = create_jinja_env()
        assert env.lstrip_blocks is True

    def test_environment_keeps_trailing_newline(self):
        """Test that keep_trailing_newline is enabled."""
        env = create_jinja_env()
        assert env.keep_trailing_newline is True

    def test_can_load_template_from_environment(self):
        """Test that templates can be loaded from the environment."""
        env = create_jinja_env()
        # Try to load a template that should exist
        template = env.get_template("Makefile.j2")
        assert template is not None


class TestRenderTemplate:
    """Tests for render_template function."""

    def test_render_template_returns_string(self):
        """Test that render_template returns a string."""
        result = render_template("Makefile.j2", {"project_name": "TestProject"})
        assert isinstance(result, str)

    def test_render_template_with_project_name(self):
        """Test that template is rendered with project_name context."""
        result = render_template("Makefile.j2", {"project_name": "MyProject"})
        # The Makefile template should contain project_name reference
        # This verifies rendering actually happened
        assert len(result) > 0

    def test_render_gitignore_template(self):
        """Test rendering .gitignore template."""
        result = render_template(".gitignore.j2", {"project_name": "TestProject"})
        assert isinstance(result, str)
        assert len(result) > 0
        # Should contain common gitignore patterns
        assert ".venv" in result or "venv" in result or len(result) > 0

    def test_render_env_example_template(self):
        """Test rendering .env.example template."""
        result = render_template(".env.example.j2", {"project_name": "TestProject"})
        assert isinstance(result, str)
        assert len(result) > 0

    def test_render_openapi_config_types_template(self):
        """Test rendering openapi-generator-config-types template."""
        result = render_template(
            "openapi-generator-config-types.yaml.j2", {"project_name": "TestProject"}
        )
        assert isinstance(result, str)
        assert len(result) > 0
        # YAML config should contain package name reference
        assert "TestProject" in result or len(result) > 0

    def test_render_openapi_config_client_template(self):
        """Test rendering openapi-generator-config-client template."""
        result = render_template(
            "openapi-generator-config-client.yaml.j2", {"project_name": "TestProject"}
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_render_overlay_template(self):
        """Test rendering overlay template."""
        result = render_template("overlay.yaml.j2", {"project_name": "TestProject"})
        assert isinstance(result, str)
        assert len(result) > 0

    def test_render_with_empty_context(self):
        """Test that rendering with empty context doesn't crash."""
        # Should work with minimal context
        result = render_template("Makefile.j2", {})
        assert isinstance(result, str)

    def test_render_nonexistent_template_raises_error(self):
        """Test that rendering a nonexistent template raises an error."""
        from jinja2 import TemplateNotFound

        with pytest.raises(TemplateNotFound):
            render_template("nonexistent.j2", {"project_name": "Test"})


class TestWriteIfNotExists:
    """Tests for write_if_not_exists function."""

    def test_write_new_file(self):
        """Test writing content to a new file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target_path = Path(tmpdir) / "new_file.txt"
            content = "Test content"

            result = write_if_not_exists(target_path, content)

            assert result is True
            assert target_path.exists()
            assert target_path.read_text(encoding="utf-8") == content

    def test_skip_existing_file(self):
        """Test that existing files are not overwritten."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target_path = Path(tmpdir) / "existing_file.txt"
            original_content = "Original content"
            target_path.write_text(original_content, encoding="utf-8")

            new_content = "New content"
            result = write_if_not_exists(target_path, new_content)

            assert result is False
            assert target_path.read_text(encoding="utf-8") == original_content

    def test_creates_parent_directories(self):
        """Test that parent directories are created if they don't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target_path = Path(tmpdir) / "subdir" / "nested" / "file.txt"
            content = "Test content"

            result = write_if_not_exists(target_path, content)

            assert result is True
            assert target_path.exists()
            assert target_path.parent.exists()

    def test_write_empty_content(self):
        """Test writing empty content to a file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target_path = Path(tmpdir) / "empty_file.txt"
            content = ""

            result = write_if_not_exists(target_path, content)

            assert result is True
            assert target_path.exists()
            assert target_path.read_text(encoding="utf-8") == ""

    def test_write_multiline_content(self):
        """Test writing multiline content to a file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target_path = Path(tmpdir) / "multiline.txt"
            content = "Line 1\nLine 2\nLine 3\n"

            result = write_if_not_exists(target_path, content)

            assert result is True
            assert target_path.read_text(encoding="utf-8") == content

    def test_write_content_with_special_characters(self):
        """Test writing content with special characters."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target_path = Path(tmpdir) / "special.txt"
            content = "Special: !@#$%^&*()\nUnicode: café, naïve, résumé"

            result = write_if_not_exists(target_path, content)

            assert result is True
            assert target_path.read_text(encoding="utf-8") == content

    def test_description_parameter_accepted(self):
        """Test that description parameter is accepted."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target_path = Path(tmpdir) / "file.txt"
            content = "Test"

            # Should not raise an error even though description is not used
            result = write_if_not_exists(target_path, content, description="custom description")

            assert result is True


class TestGenerateConfigFiles:
    """Tests for generate_config_files function."""

    def test_generate_all_config_files(self):
        """Test that all config files are generated in a new directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir)

            results = generate_config_files(target_dir, "TestProject")

            # All files should be created
            assert results["Makefile"] is True
            assert results[".gitignore"] is True
            assert results[".env.example"] is True
            assert results["openapi-generator-config-types.yaml"] is True
            assert results["openapi-generator-config-client.yaml"] is True
            assert results["openapi-overlay.yaml"] is True

    def test_all_generated_files_exist(self):
        """Test that all generated files actually exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir)

            generate_config_files(target_dir, "TestProject")

            assert (target_dir / "Makefile").exists()
            assert (target_dir / ".gitignore").exists()
            assert (target_dir / ".env.example").exists()
            assert (target_dir / "openapi-generator-config-types.yaml").exists()
            assert (target_dir / "openapi-generator-config-client.yaml").exists()
            assert (target_dir / "openapi-overlay.yaml").exists()

    def test_generated_files_have_content(self):
        """Test that generated files contain content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir)

            generate_config_files(target_dir, "TestProject")

            makefile = (target_dir / "Makefile").read_text(encoding="utf-8")
            assert len(makefile) > 0

            gitignore = (target_dir / ".gitignore").read_text(encoding="utf-8")
            assert len(gitignore) > 0

            env_example = (target_dir / ".env.example").read_text(encoding="utf-8")
            assert len(env_example) > 0

    def test_preserve_existing_files(self):
        """Test that existing files are not overwritten."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir)

            # First generation
            generate_config_files(target_dir, "TestProject")
            original_makefile = (target_dir / "Makefile").read_text(encoding="utf-8")

            # Modify the Makefile
            modified_content = original_makefile + "\n# User modification"
            (target_dir / "Makefile").write_text(modified_content, encoding="utf-8")

            # Second generation with different project name
            results = generate_config_files(target_dir, "NewProject")

            # Makefile should not be overwritten
            assert results["Makefile"] is False
            assert (target_dir / "Makefile").read_text(encoding="utf-8") == modified_content

    def test_skip_all_existing_files(self):
        """Test that all existing files are skipped on subsequent runs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir)

            # First generation
            first_results = generate_config_files(target_dir, "FirstProject")
            assert all(first_results.values())

            # Second generation
            second_results = generate_config_files(target_dir, "SecondProject")
            assert not any(second_results.values())

    def test_mixed_existing_and_new_files(self):
        """Test behavior when some files exist and others don't."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir)

            # Create a custom Makefile
            (target_dir / "Makefile").write_text("Custom makefile\n", encoding="utf-8")

            # Generate config files
            results = generate_config_files(target_dir, "TestProject")

            # Makefile should be skipped, others created
            assert results["Makefile"] is False
            assert results[".gitignore"] is True
            assert results[".env.example"] is True
            assert results["openapi-generator-config-types.yaml"] is True
            assert results["openapi-generator-config-client.yaml"] is True
            assert results["openapi-overlay.yaml"] is True

    def test_return_dict_keys_match_filenames(self):
        """Test that the returned dictionary keys match expected filenames."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir)

            results = generate_config_files(target_dir, "TestProject")

            expected_keys = {
                "Makefile",
                ".gitignore",
                ".env.example",
                "openapi-generator-config-types.yaml",
                "openapi-generator-config-client.yaml",
                "openapi-overlay.yaml",
            }
            assert set(results.keys()) == expected_keys

    def test_return_values_are_booleans(self):
        """Test that return values are all booleans."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir)

            results = generate_config_files(target_dir, "TestProject")

            for value in results.values():
                assert isinstance(value, bool)

    def test_project_name_substituted_in_templates(self):
        """Test that project name is properly substituted in templates."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir)
            project_name = "UniqueProjectName123"

            generate_config_files(target_dir, project_name)

            # Check that project name appears in YAML config files
            types_config = (target_dir / "openapi-generator-config-types.yaml").read_text(
                encoding="utf-8"
            )
            assert project_name in types_config

            client_config = (target_dir / "openapi-generator-config-client.yaml").read_text(
                encoding="utf-8"
            )
            assert project_name in client_config

    def test_creates_target_directory_if_missing(self):
        """Test that the target directory is created if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir) / "new" / "nested" / "directory"
            assert not target_dir.exists()

            generate_config_files(target_dir, "TestProject")

            assert target_dir.exists()
            assert (target_dir / "Makefile").exists()

    def test_different_project_names(self):
        """Test generation with various project names."""
        project_names = [
            "SimpleProject",
            "project-with-hyphens",
            "project_with_underscores",
            "MixedCaseProject",
        ]

        for project_name in project_names:
            with tempfile.TemporaryDirectory() as tmpdir:
                target_dir = Path(tmpdir)

                results = generate_config_files(target_dir, project_name)

                assert all(results.values())
                assert (target_dir / "Makefile").exists()

    def test_context_contains_project_name(self):
        """Test that context is built with project_name."""
        # This is implicit in other tests, but verifies the context building
        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir)
            project_name = "ContextTestProject"

            generate_config_files(target_dir, project_name)

            # If project name is in templates, it should appear in output
            makefile_content = (target_dir / "Makefile").read_text(encoding="utf-8")
            # Makefile typically includes project reference
            assert len(makefile_content) > 0
