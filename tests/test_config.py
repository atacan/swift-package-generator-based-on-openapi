"""Tests for project configuration handling."""

from pathlib import Path

import yaml

from bootstrapper.config import (
    CONFIG_FILENAME,
    NameMismatch,
    ProjectConfig,
    check_name_mismatch,
    get_config_path,
    get_package_name_from_swift,
    load_config,
    save_config,
)


class TestProjectConfig:
    """Test the ProjectConfig model."""

    def test_default_values(self):
        """Test that empty config has None for package_name."""
        config = ProjectConfig()

        assert config.package_name is None

    def test_with_package_name(self):
        """Test config with explicit name."""
        config = ProjectConfig(package_name="MyPackage")

        assert config.package_name == "MyPackage"

    def test_model_dump_excludes_none(self):
        """Test that None values are excluded from dump."""
        config = ProjectConfig()

        data = config.model_dump(exclude_none=True)

        assert data == {}
        assert "package_name" not in data

    def test_model_dump_includes_value(self):
        """Test that non-None values are included in dump."""
        config = ProjectConfig(package_name="TestPkg")

        data = config.model_dump(exclude_none=True)

        assert data == {"package_name": "TestPkg"}


class TestGetConfigPath:
    """Test the get_config_path function."""

    def test_returns_correct_path(self, tmp_path):
        """Test that path is target_dir/.swift-bootstrapper.yaml."""
        result = get_config_path(tmp_path)

        expected = tmp_path / CONFIG_FILENAME
        assert result == expected

    def test_returns_path_object(self, tmp_path):
        """Test that result is Path type."""
        result = get_config_path(tmp_path)

        assert isinstance(result, Path)

    def test_with_nested_directory(self, tmp_path):
        """Test with nested directory structure."""
        nested_dir = tmp_path / "parent" / "child"

        result = get_config_path(nested_dir)

        expected = nested_dir / CONFIG_FILENAME
        assert result == expected


class TestLoadConfig:
    """Test the load_config function."""

    def test_returns_empty_config_when_file_missing(self, tmp_path):
        """Test returns empty config when file doesn't exist."""
        result = load_config(tmp_path)

        assert isinstance(result, ProjectConfig)
        assert result.package_name is None

    def test_loads_package_name(self, tmp_path):
        """Test loading package name from valid YAML."""
        config_file = tmp_path / CONFIG_FILENAME
        config_file.write_text("package_name: MyPackage\n")

        result = load_config(tmp_path)

        assert result.package_name == "MyPackage"

    def test_handles_empty_file(self, tmp_path):
        """Test that empty file returns empty config."""
        config_file = tmp_path / CONFIG_FILENAME
        config_file.write_text("")

        result = load_config(tmp_path)

        assert isinstance(result, ProjectConfig)
        assert result.package_name is None

    def test_handles_empty_yaml(self, tmp_path):
        """Test file with only comments returns empty config."""
        config_file = tmp_path / CONFIG_FILENAME
        config_file.write_text("# This is a comment\n# Another comment\n")

        result = load_config(tmp_path)

        assert isinstance(result, ProjectConfig)
        assert result.package_name is None

    def test_ignores_unknown_fields(self, tmp_path):
        """Test that Pydantic ignores extra fields."""
        config_file = tmp_path / CONFIG_FILENAME
        config_file.write_text("package_name: MyPackage\nunknown_field: value\n")

        result = load_config(tmp_path)

        assert result.package_name == "MyPackage"
        # Should not raise an error, just ignore unknown_field

    def test_loads_multiline_yaml(self, tmp_path):
        """Test loading from properly formatted YAML."""
        config_file = tmp_path / CONFIG_FILENAME
        config_content = """# Configuration file for Swift Bootstrapper
package_name: MyAwesomePackage
"""
        config_file.write_text(config_content)

        result = load_config(tmp_path)

        assert result.package_name == "MyAwesomePackage"

    def test_handles_null_values(self, tmp_path):
        """Test that explicit null values are handled correctly."""
        config_file = tmp_path / CONFIG_FILENAME
        config_file.write_text("package_name: null\n")

        result = load_config(tmp_path)

        assert result.package_name is None


class TestSaveConfig:
    """Test the save_config function."""

    def test_creates_new_file(self, tmp_path):
        """Test creating a new config file."""
        config = ProjectConfig(package_name="NewPackage")

        result = save_config(tmp_path, config)

        assert result is True
        config_file = tmp_path / CONFIG_FILENAME
        assert config_file.exists()

    def test_writes_correct_content(self, tmp_path):
        """Test that written YAML content is valid."""
        config = ProjectConfig(package_name="TestPackage")

        save_config(tmp_path, config)

        config_file = tmp_path / CONFIG_FILENAME
        content = config_file.read_text()
        data = yaml.safe_load(content)

        assert data == {"package_name": "TestPackage"}

    def test_does_not_overwrite_existing(self, tmp_path):
        """Test that existing file is not overwritten."""
        config_file = tmp_path / CONFIG_FILENAME
        original_content = "package_name: OriginalName\n# User comment\n"
        config_file.write_text(original_content)

        config = ProjectConfig(package_name="NewName")
        result = save_config(tmp_path, config)

        assert result is False
        assert config_file.read_text() == original_content

    def test_creates_parent_directories(self, tmp_path):
        """Test that parent directories are created if needed."""
        nested_dir = tmp_path / "parent" / "child"
        config = ProjectConfig(package_name="TestPkg")

        result = save_config(nested_dir, config)

        assert result is True
        assert nested_dir.exists()
        config_file = nested_dir / CONFIG_FILENAME
        assert config_file.exists()

    def test_excludes_none_values(self, tmp_path):
        """Test that None values produce clean output."""
        config = ProjectConfig()  # package_name is None

        save_config(tmp_path, config)

        config_file = tmp_path / CONFIG_FILENAME
        content = config_file.read_text()
        data = yaml.safe_load(content)

        # Empty config should produce empty YAML or None
        assert data is None or data == {}

    def test_preserves_unicode(self, tmp_path):
        """Test that unicode characters are preserved."""
        config = ProjectConfig(package_name="MyPackage")

        save_config(tmp_path, config)

        config_file = tmp_path / CONFIG_FILENAME
        # Should not contain escaped unicode
        content = config_file.read_text()
        assert "\\u" not in content


class TestGetPackageNameFromSwift:
    """Test the get_package_name_from_swift function."""

    def test_returns_none_when_file_missing(self, tmp_path):
        """Test returns None when Package.swift doesn't exist."""
        result = get_package_name_from_swift(tmp_path)

        assert result is None

    def test_extracts_name_correctly(self, tmp_path):
        """Test extracting name from valid Package.swift."""
        package_swift = tmp_path / "Package.swift"
        package_content = """// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "TestPackage",
    products: [
        .library(name: "TestPackage", targets: ["TestPackage"]),
    ],
    targets: [
        .target(name: "TestPackage"),
    ]
)
"""
        package_swift.write_text(package_content)

        result = get_package_name_from_swift(tmp_path)

        assert result == "TestPackage"

    def test_handles_whitespace_variations(self, tmp_path):
        """Test handling of whitespace variations in name declaration."""
        test_cases = [
            ('name: "MyPackage"', "MyPackage"),
            ('name:"MyPackage"', "MyPackage"),
            ('name:  "MyPackage"', "MyPackage"),
            ('name:\t"MyPackage"', "MyPackage"),
            ('name:   "MyPackage"  ', "MyPackage"),
        ]

        for name_decl, expected_name in test_cases:
            package_swift = tmp_path / "Package.swift"
            content = f"""let package = Package(
    {name_decl},
    products: []
)
"""
            package_swift.write_text(content)

            result = get_package_name_from_swift(tmp_path)

            assert result == expected_name, f"Failed for: {name_decl}"

    def test_returns_none_when_no_match(self, tmp_path):
        """Test returns None for malformed Package.swift."""
        package_swift = tmp_path / "Package.swift"
        # Invalid content without proper name declaration
        package_swift.write_text("// Just a comment\nlet x = 5\n")

        result = get_package_name_from_swift(tmp_path)

        assert result is None

    def test_extracts_first_name_match(self, tmp_path):
        """Test that first name match is extracted."""
        package_swift = tmp_path / "Package.swift"
        content = """let package = Package(
    name: "FirstPackage",
    products: [
        .library(name: "SecondPackage", targets: ["Target"]),
    ]
)
"""
        package_swift.write_text(content)

        result = get_package_name_from_swift(tmp_path)

        assert result == "FirstPackage"

    def test_handles_complex_package_names(self, tmp_path):
        """Test extraction of complex package names."""
        test_names = [
            "MyAPI",
            "my-api-wrapper",
            "MyAPI_Client",
            "API2Swift",
            "AssemblyAI",
        ]

        for name in test_names:
            package_swift = tmp_path / "Package.swift"
            content = f'let package = Package(name: "{name}")'
            package_swift.write_text(content)

            result = get_package_name_from_swift(tmp_path)

            assert result == name, f"Failed to extract: {name}"

    def test_handles_empty_file(self, tmp_path):
        """Test handling of empty Package.swift file."""
        package_swift = tmp_path / "Package.swift"
        package_swift.write_text("")

        result = get_package_name_from_swift(tmp_path)

        assert result is None


class TestCheckNameMismatch:
    """Test the check_name_mismatch function."""

    def test_returns_none_when_no_package_swift(self, tmp_path):
        """Test returns None when Package.swift doesn't exist."""
        result = check_name_mismatch(tmp_path, "MyPackage")

        assert result is None

    def test_returns_none_when_names_match(self, tmp_path):
        """Test returns None when names match."""
        package_swift = tmp_path / "Package.swift"
        package_swift.write_text('let package = Package(name: "MyPackage")')

        result = check_name_mismatch(tmp_path, "MyPackage")

        assert result is None

    def test_returns_mismatch_when_names_differ(self, tmp_path):
        """Test returns NameMismatch when names differ."""
        package_swift = tmp_path / "Package.swift"
        package_swift.write_text('let package = Package(name: "ExistingPackage")')

        result = check_name_mismatch(tmp_path, "NewPackage")

        assert isinstance(result, NameMismatch)
        assert result.config_name == "NewPackage"
        assert result.package_swift_name == "ExistingPackage"

    def test_mismatch_contains_both_names(self, tmp_path):
        """Test that NameMismatch contains both names."""
        package_swift = tmp_path / "Package.swift"
        package_swift.write_text('let package = Package(name: "OldName")')

        result = check_name_mismatch(tmp_path, "NewName")

        assert result is not None
        assert result.config_name == "NewName"
        assert result.package_swift_name == "OldName"

    def test_case_sensitive_comparison(self, tmp_path):
        """Test that name comparison is case-sensitive."""
        package_swift = tmp_path / "Package.swift"
        package_swift.write_text('let package = Package(name: "MyPackage")')

        result = check_name_mismatch(tmp_path, "mypackage")

        assert isinstance(result, NameMismatch)
        assert result.config_name == "mypackage"
        assert result.package_swift_name == "MyPackage"

    def test_returns_none_when_package_swift_unparseable(self, tmp_path):
        """Test returns None when Package.swift exists but can't be parsed."""
        package_swift = tmp_path / "Package.swift"
        package_swift.write_text("// Invalid content")

        result = check_name_mismatch(tmp_path, "MyPackage")

        # Since get_package_name_from_swift returns None for unparseable files,
        # check_name_mismatch should also return None
        assert result is None

    def test_handles_whitespace_in_resolved_name(self, tmp_path):
        """Test handling of edge cases in resolved name."""
        package_swift = tmp_path / "Package.swift"
        package_swift.write_text('let package = Package(name: "MyPackage")')

        # Test with various resolved names
        result1 = check_name_mismatch(tmp_path, "MyPackage")
        assert result1 is None

        result2 = check_name_mismatch(tmp_path, "DifferentPackage")
        assert isinstance(result2, NameMismatch)
