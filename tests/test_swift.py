"""Tests for Swift package scaffolding module."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from bootstrapper.generators.swift import (
    create_initial_swift_files,
    ensure_package_structure,
    run_openapi_generator,
    run_swift_build,
    setup_swift_package,
)


class TestEnsurePackageStructure:
    """Tests for ensure_package_structure function."""

    def test_creates_package_swift_on_first_run(self):
        """Test that Package.swift is created when it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir)
            project_name = "TestProject"

            results = ensure_package_structure(target_dir, project_name)

            assert results["package_swift"] is True
            assert (target_dir / "Package.swift").exists()

    def test_skips_package_swift_if_exists(self):
        """Test that existing Package.swift is not overwritten."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir)
            project_name = "TestProject"

            # Create initial Package.swift
            package_path = target_dir / "Package.swift"
            original_content = "// Original content"
            package_path.write_text(original_content, encoding="utf-8")

            results = ensure_package_structure(target_dir, project_name)

            assert results["package_swift"] is False
            assert package_path.read_text(encoding="utf-8") == original_content

    def test_creates_types_directory(self):
        """Test that Sources/{Name}Types directory is created."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir)
            project_name = "TestProject"

            results = ensure_package_structure(target_dir, project_name)

            types_dir = target_dir / "Sources" / f"{project_name}Types"
            assert results["types_dir"] is True
            assert types_dir.exists()
            assert types_dir.is_dir()

    def test_creates_client_directory(self):
        """Test that Sources/{Name}Client directory is created."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir)
            project_name = "TestProject"

            results = ensure_package_structure(target_dir, project_name)

            client_dir = target_dir / "Sources" / f"{project_name}Client"
            assert results["client_dir"] is True
            assert client_dir.exists()
            assert client_dir.is_dir()

    def test_creates_tests_directory(self):
        """Test that Tests/{Name}Tests directory is created."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir)
            project_name = "TestProject"

            results = ensure_package_structure(target_dir, project_name)

            tests_dir = target_dir / "Tests" / f"{project_name}Tests"
            assert results["tests_dir"] is True
            assert tests_dir.exists()
            assert tests_dir.is_dir()

    def test_creates_gitkeep_files(self):
        """Test that .gitkeep files are created to preserve directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir)
            project_name = "TestProject"

            ensure_package_structure(target_dir, project_name)

            types_gitkeep = target_dir / "Sources" / f"{project_name}Types" / ".gitkeep"
            client_gitkeep = target_dir / "Sources" / f"{project_name}Client" / ".gitkeep"
            tests_gitkeep = target_dir / "Tests" / f"{project_name}Tests" / ".gitkeep"

            assert types_gitkeep.exists()
            assert client_gitkeep.exists()
            assert tests_gitkeep.exists()

    def test_package_swift_contains_project_name(self):
        """Test that generated Package.swift contains the project name."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir)
            project_name = "MyAwesomeProject"

            ensure_package_structure(target_dir, project_name)

            package_content = (target_dir / "Package.swift").read_text(encoding="utf-8")
            assert project_name in package_content

    def test_package_swift_has_dependencies(self):
        """Test that Package.swift includes required dependencies."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir)
            project_name = "TestProject"

            ensure_package_structure(target_dir, project_name)

            package_content = (target_dir / "Package.swift").read_text(encoding="utf-8")
            # Check for key dependencies
            assert "swift-openapi-runtime" in package_content
            assert "async-http-client" in package_content

    def test_return_dict_has_all_keys(self):
        """Test that the return dictionary contains all expected keys."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir)
            project_name = "TestProject"

            results = ensure_package_structure(target_dir, project_name)

            expected_keys = {
                "package_swift",
                "types_dir",
                "client_dir",
                "tests_dir",
                "types_file",
                "client_file",
                "tests_file",
            }
            assert set(results.keys()) == expected_keys

    def test_idempotent_on_second_call(self):
        """Test that running twice produces the same structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir)
            project_name = "TestProject"

            # First call
            ensure_package_structure(target_dir, project_name)
            files_after_first = set(target_dir.rglob("*"))

            # Second call
            results2 = ensure_package_structure(target_dir, project_name)
            files_after_second = set(target_dir.rglob("*"))

            # Should be idempotent
            assert files_after_first == files_after_second
            assert results2["package_swift"] is False  # Already exists

    def test_with_special_project_name(self):
        """Test with project names containing hyphens and underscores."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir)
            project_name = "my-awesome_project"

            results = ensure_package_structure(target_dir, project_name)

            assert results["package_swift"] is True
            assert (target_dir / "Sources" / f"{project_name}Types").exists()


class TestRunSwiftBuild:
    """Tests for run_swift_build function."""

    @patch("bootstrapper.generators.swift.subprocess.run")
    def test_returns_true_on_successful_build(self, mock_run):
        """Test that successful swift build returns True."""
        mock_run.return_value = MagicMock(returncode=0)

        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_swift_build(Path(tmpdir))

            assert result is True
            mock_run.assert_called_once()

    @patch("bootstrapper.generators.swift.subprocess.run")
    def test_returns_false_on_failed_build(self, mock_run):
        """Test that failed swift build returns False."""
        mock_run.return_value = MagicMock(returncode=1)

        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_swift_build(Path(tmpdir))

            assert result is False

    @patch("bootstrapper.generators.swift.subprocess.run")
    def test_calls_swift_build(self, mock_run):
        """Test that the correct swift command is invoked."""
        mock_run.return_value = MagicMock(returncode=0)

        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir)
            run_swift_build(target_dir)

            mock_run.assert_called_once()
            args, kwargs = mock_run.call_args
            assert args[0] == ["swift", "build"]
            assert kwargs["cwd"] == target_dir

    @patch("bootstrapper.generators.swift.subprocess.run")
    def test_sets_capture_output(self, mock_run):
        """Test that output is captured."""
        mock_run.return_value = MagicMock(returncode=0)

        with tempfile.TemporaryDirectory() as tmpdir:
            run_swift_build(Path(tmpdir))

            _, kwargs = mock_run.call_args
            assert kwargs["capture_output"] is True
            assert kwargs["text"] is True

    @patch("bootstrapper.generators.swift.subprocess.run")
    def test_returns_false_on_timeout(self, mock_run):
        """Test that timeout returns False."""
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired("swift", 300)

        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_swift_build(Path(tmpdir))

            assert result is False

    @patch("bootstrapper.generators.swift.subprocess.run")
    def test_returns_false_on_missing_swift(self, mock_run):
        """Test that missing swift command returns False."""
        mock_run.side_effect = FileNotFoundError()

        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_swift_build(Path(tmpdir))

            assert result is False


class TestRunOpenAPIGenerator:
    """Tests for run_openapi_generator function."""

    def test_returns_dict_with_result_keys(self):
        """Test that the return value is a dict with expected keys."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir)
            # Create minimal openapi.yaml so the function doesn't return early
            (target_dir / "openapi.yaml").write_text("openapi: 3.0.0")

            results = run_openapi_generator(target_dir, "TestProject")

            assert isinstance(results, dict)
            assert "types_generated" in results
            assert "client_generated" in results

    def test_returns_false_when_openapi_file_missing(self):
        """Test that function returns False for both when spec file is missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir)

            results = run_openapi_generator(target_dir, "TestProject")

            assert results["types_generated"] is False
            assert results["client_generated"] is False

    @patch("bootstrapper.generators.swift.subprocess.run")
    def test_types_generation_command(self, mock_run):
        """Test that correct command is used for types generation."""
        mock_run.return_value = MagicMock(returncode=0)

        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir)
            project_name = "TestProject"
            openapi_file = "openapi.yaml"

            # Create the openapi file
            (target_dir / openapi_file).write_text("openapi: 3.0.0")

            run_openapi_generator(target_dir, project_name, openapi_file)

            # Check that swift run command was called
            assert mock_run.called

    @patch("bootstrapper.generators.swift.subprocess.run")
    def test_client_generation_command(self, mock_run):
        """Test that correct command is used for client generation."""
        mock_run.return_value = MagicMock(returncode=0)

        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir)
            project_name = "TestProject"
            openapi_file = "openapi.yaml"

            (target_dir / openapi_file).write_text("openapi: 3.0.0")

            run_openapi_generator(target_dir, project_name, openapi_file)

            # Should be called at least twice (types and client)
            assert mock_run.call_count >= 2

    @patch("bootstrapper.generators.swift.subprocess.run")
    def test_successful_generation_returns_true(self, mock_run):
        """Test that successful generation returns True for both targets."""
        mock_run.return_value = MagicMock(returncode=0)

        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir)
            (target_dir / "openapi.yaml").write_text("openapi: 3.0.0")

            results = run_openapi_generator(target_dir, "TestProject")

            assert results["types_generated"] is True
            assert results["client_generated"] is True

    @patch("bootstrapper.generators.swift.subprocess.run")
    def test_failed_types_generation(self, mock_run):
        """Test handling when types generation fails."""
        # First call fails (types), second succeeds (client)
        mock_run.side_effect = [
            MagicMock(returncode=1),
            MagicMock(returncode=0),
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir)
            (target_dir / "openapi.yaml").write_text("openapi: 3.0.0")

            results = run_openapi_generator(target_dir, "TestProject")

            assert results["types_generated"] is False
            assert results["client_generated"] is True

    @patch("bootstrapper.generators.swift.subprocess.run")
    def test_handles_timeout(self, mock_run):
        """Test that timeout during generation is handled."""
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired("swift", 300)

        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir)
            (target_dir / "openapi.yaml").write_text("openapi: 3.0.0")

            results = run_openapi_generator(target_dir, "TestProject")

            assert results["types_generated"] is False

    @patch("bootstrapper.generators.swift.subprocess.run")
    def test_handles_missing_swift_command(self, mock_run):
        """Test that missing swift command is handled gracefully."""
        mock_run.side_effect = FileNotFoundError()

        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir)
            (target_dir / "openapi.yaml").write_text("openapi: 3.0.0")

            results = run_openapi_generator(target_dir, "TestProject")

            assert results["types_generated"] is False

    def test_with_json_openapi_file(self):
        """Test that JSON OpenAPI files are supported."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir)
            (target_dir / "openapi.json").write_text("{}")

            # Should not fail even without mocking (will fail gracefully)
            results = run_openapi_generator(target_dir, "TestProject", "openapi.json")

            assert isinstance(results, dict)
            assert "types_generated" in results

    def test_output_directories_in_command(self):
        """Test that output directories are correctly specified in command."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir)
            project_name = "TestProject"

            (target_dir / "openapi.yaml").write_text("openapi: 3.0.0")

            with patch("bootstrapper.generators.swift.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0)

                run_openapi_generator(target_dir, project_name)

                # Check that calls include output directories
                calls = mock_run.call_args_list
                types_output = target_dir / "Sources" / f"{project_name}Types" / "GeneratedSources"

                # At least one call should mention the types output directory
                assert any(str(types_output) in str(call) for call in calls)


class TestSetupSwiftPackage:
    """Tests for setup_swift_package function (main orchestration)."""

    def test_returns_dict_with_expected_keys(self):
        """Test that the return value contains expected keys."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir)

            results = setup_swift_package(target_dir, "TestProject", run_generator=False)

            assert isinstance(results, dict)
            assert "structure" in results
            assert "build_verification" in results

    def test_creates_package_structure(self):
        """Test that package structure is created."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir)

            setup_swift_package(target_dir, "TestProject", run_generator=False)

            assert (target_dir / "Package.swift").exists()
            assert (target_dir / "Sources" / "TestProjectTypes").exists()
            assert (target_dir / "Sources" / "TestProjectClient").exists()

    @patch("bootstrapper.generators.swift.run_swift_build")
    def test_runs_build_verification(self, mock_build):
        """Test that build verification is performed."""
        mock_build.return_value = True

        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir)

            results = setup_swift_package(target_dir, "TestProject", run_generator=False)

            mock_build.assert_called_once()
            assert "build_verification" in results

    @patch("bootstrapper.generators.swift.run_openapi_generator")
    def test_skips_generator_by_default(self, mock_generator):
        """Test that generator is not run by default."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir)

            setup_swift_package(target_dir, "TestProject", run_generator=False)

            mock_generator.assert_not_called()

    @patch("bootstrapper.generators.swift.run_openapi_generator")
    def test_runs_generator_when_requested(self, mock_generator):
        """Test that generator runs when requested."""
        mock_generator.return_value = {
            "types_generated": True,
            "client_generated": True,
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir)

            results = setup_swift_package(target_dir, "TestProject", run_generator=True)

            mock_generator.assert_called_once()
            assert "generation" in results

    @patch("bootstrapper.generators.swift.run_swift_build")
    @patch("bootstrapper.generators.swift.run_openapi_generator")
    def test_complete_setup_flow(self, mock_generator, mock_build):
        """Test complete setup with all steps."""
        mock_build.return_value = True
        mock_generator.return_value = {
            "types_generated": True,
            "client_generated": True,
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir)

            results = setup_swift_package(target_dir, "TestProject", run_generator=True)

            # All steps should be in results
            assert "structure" in results
            assert "build_verification" in results
            assert "generation" in results

            # Verify calls
            mock_build.assert_called_once()
            mock_generator.assert_called_once()

    def test_with_nested_target_directory(self):
        """Test that nested target directory is created as needed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a nested path that doesn't exist yet
            target_dir = Path(tmpdir) / "nested" / "deep" / "path"

            results = setup_swift_package(target_dir, "TestProject", run_generator=False)

            # Should have created the directory structure
            assert (target_dir / "Package.swift").exists()
            assert isinstance(results, dict)

    @patch("bootstrapper.generators.swift.run_swift_build")
    def test_propagates_build_failure(self, mock_build):
        """Test that build failure is reported in results."""
        mock_build.return_value = False

        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir)

            results = setup_swift_package(target_dir, "TestProject", run_generator=False)

            assert results["build_verification"] is False

    def test_with_different_project_names(self):
        """Test setup with various project name formats."""
        project_names = [
            "SimpleProject",
            "project-with-dashes",
            "project_with_underscores",
            "MixedCaseProject",
        ]

        for project_name in project_names:
            with tempfile.TemporaryDirectory() as tmpdir:
                target_dir = Path(tmpdir)

                setup_swift_package(target_dir, project_name, run_generator=False)

                assert (target_dir / "Package.swift").exists()
                assert (target_dir / "Sources" / f"{project_name}Types").exists()


class TestCreateInitialSwiftFiles:
    """Tests for create_initial_swift_files function and Swift file creation."""

    def test_initial_swift_files_created(self):
        """Verify Swift files are created with correct names in correct locations.

        Tests that all three initial Swift files are created:
        - Sources/{ProjectName}Types/{ProjectName}Types.swift
        - Sources/{ProjectName}Client/{ProjectName}Client.swift
        - Tests/{ProjectName}Tests/{ProjectName}Tests.swift
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir)
            project_name = "TestProject"

            # ensure_package_structure calls create_initial_swift_files internally
            ensure_package_structure(target_dir, project_name)

            # Verify all three files exist
            types_dir = target_dir / "Sources" / f"{project_name}Types"
            types_file = types_dir / f"{project_name}Types.swift"
            client_dir = target_dir / "Sources" / f"{project_name}Client"
            client_file = client_dir / f"{project_name}Client.swift"
            tests_dir = target_dir / "Tests" / f"{project_name}Tests"
            tests_file = tests_dir / f"{project_name}Tests.swift"

            assert types_file.exists(), f"Types file should exist at {types_file}"
            assert client_file.exists(), f"Client file should exist at {client_file}"
            assert tests_file.exists(), f"Tests file should exist at {tests_file}"

    def test_swift_file_content(self):
        """Verify files contain expected content from Jinja2 templates.

        Tests that:
        - TypesFile contains 'import OpenAPIRuntime' and project_name in header
        - ClientFile contains 'import OpenAPIRuntime', 'import OpenAPIAsyncHTTPClient'
        - TestsFile contains 'import Testing', 'import {ProjectName}Client', 'import UsefulThings'
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir)
            project_name = "MyAPIClient"

            ensure_package_structure(target_dir, project_name)

            # Read types file and verify content
            types_dir = target_dir / "Sources" / f"{project_name}Types"
            types_file = types_dir / f"{project_name}Types.swift"
            types_content = types_file.read_text(encoding="utf-8")
            assert "import OpenAPIRuntime" in types_content
            assert project_name in types_content
            assert "Auto-generated by swift-openapi-bootstrapper" in types_content

            # Read client file and verify content
            client_dir = target_dir / "Sources" / f"{project_name}Client"
            client_file = client_dir / f"{project_name}Client.swift"
            client_content = client_file.read_text(encoding="utf-8")
            assert "import OpenAPIRuntime" in client_content
            assert "import OpenAPIAsyncHTTPClient" in client_content
            assert project_name in client_content

            # Read tests file and verify content
            tests_dir = target_dir / "Tests" / f"{project_name}Tests"
            tests_file = tests_dir / f"{project_name}Tests.swift"
            tests_content = tests_file.read_text(encoding="utf-8")
            assert "import Testing" in tests_content
            assert f"import {project_name}Client" in tests_content
            assert "import UsefulThings" in tests_content

    def test_swift_files_preserved(self):
        """Verify preservation behavior - user edits are not overwritten.

        Tests that:
        1. Files are created on first run
        2. User modifications are preserved on subsequent runs
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir)
            project_name = "TestProject"

            # First run - files created
            results1 = ensure_package_structure(target_dir, project_name)
            assert results1["types_file"] is True
            assert results1["client_file"] is True
            assert results1["tests_file"] is True

            # Simulate user edits by modifying file contents
            types_dir = target_dir / "Sources" / f"{project_name}Types"
            types_file = types_dir / f"{project_name}Types.swift"
            user_content = (
                "// USER MODIFIED CONTENT\nimport OpenAPIRuntime\n\nstruct MyCustomType {}\n"
            )
            types_file.write_text(user_content, encoding="utf-8")

            # Second run - files should be preserved
            results2 = ensure_package_structure(target_dir, project_name)
            assert results2["types_file"] is False  # Not created (preserved)
            assert results2["client_file"] is False  # Not created (preserved)
            assert results2["tests_file"] is False  # Not created (preserved)

            # Verify user modifications were preserved
            preserved_content = types_file.read_text(encoding="utf-8")
            assert preserved_content == user_content
            assert "USER MODIFIED CONTENT" in preserved_content

    @pytest.mark.slow
    @pytest.mark.skipif(
        not Path("/usr/bin/swift").exists() and not Path("/usr/local/bin/swift").exists(),
        reason="Swift toolchain not available",
    )
    def test_swift_files_allow_build(self):
        """Verify swift build succeeds with just initial files (before code generation).

        This test verifies that the initial Swift files created by the bootstrapper
        allow the Swift package to build successfully, even before any OpenAPI code
        generation has occurred.

        Note: Skipped if Swift toolchain is not installed.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir)
            project_name = "BuildTestProject"

            # Set up the package structure with initial Swift files
            ensure_package_structure(target_dir, project_name)

            # Run swift build
            build_success = run_swift_build(target_dir)

            assert build_success, "Swift build should succeed with initial Swift files"

    def test_create_initial_swift_files_return_values(self):
        """Test create_initial_swift_files() function directly.

        Verifies return values:
        - First call: Returns {"types_file": True, "client_file": True, "tests_file": True}
        - Second call: Returns {"types_file": False, "client_file": False, "tests_file": False}
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir)
            project_name = "TestProject"

            # Create directories first (function expects them to exist)
            (target_dir / "Sources" / f"{project_name}Types").mkdir(parents=True)
            (target_dir / "Sources" / f"{project_name}Client").mkdir(parents=True)
            (target_dir / "Tests" / f"{project_name}Tests").mkdir(parents=True)

            # First call - files should be created
            results1 = create_initial_swift_files(target_dir, project_name)
            assert results1["types_file"] is True
            assert results1["client_file"] is True
            assert results1["tests_file"] is True

            # Second call - files should not be recreated
            results2 = create_initial_swift_files(target_dir, project_name)
            assert results2["types_file"] is False
            assert results2["client_file"] is False
            assert results2["tests_file"] is False

    def test_ensure_package_structure_return_includes_files(self):
        """Verify ensure_package_structure() return dict includes Swift file keys.

        Tests that the return dictionary includes:
        - "types_file": bool
        - "client_file": bool
        - "tests_file": bool
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir)
            project_name = "TestProject"

            results = ensure_package_structure(target_dir, project_name)

            # Verify all expected keys are present
            assert "types_file" in results
            assert "client_file" in results
            assert "tests_file" in results

            # Verify values are booleans
            assert isinstance(results["types_file"], bool)
            assert isinstance(results["client_file"], bool)
            assert isinstance(results["tests_file"], bool)

            # On first run, all should be True (files created)
            assert results["types_file"] is True
            assert results["client_file"] is True
            assert results["tests_file"] is True
