"""Swift package scaffolding and generation.

This module handles the creation and maintenance of Swift package structure,
including generating Package.swift from templates and running the OpenAPI generator.
"""

import subprocess
from datetime import datetime
from pathlib import Path

from bootstrapper.generators.templates import render_template, write_if_not_exists


def ensure_package_structure(target_dir: Path, project_name: str) -> dict[str, bool]:
    """Ensure the Swift package structure exists.

    Creates or updates the Package.swift file and the directory structure needed
    for the Types and Client targets.

    Args:
        target_dir: The directory where the package should be initialized
        project_name: The name of the Swift package

    Returns:
        Dictionary indicating what was created:
        - "package_swift": True if Package.swift was created, False if it already existed
        - "types_dir": True if Types directory was created
        - "client_dir": True if Client directory was created
        - "tests_dir": True if Tests directory was created
        - "types_file": True if Types Swift file was created, False if it already existed
        - "client_file": True if Client Swift file was created, False if it already existed
        - "tests_file": True if Tests Swift file was created, False if it already existed
    """
    results = {}

    # Check if Package.swift already exists
    package_swift_path = target_dir / "Package.swift"

    # Generate Package.swift from template only if it doesn't exist
    if not package_swift_path.exists():
        # Ensure target directory exists
        target_dir.mkdir(parents=True, exist_ok=True)
        context = {
            "project_name": project_name,
            "generation_timestamp": datetime.now().isoformat(),
        }
        content = render_template("Package.swift.j2", context)
        package_swift_path.write_text(content, encoding="utf-8")
        results["package_swift"] = True
    else:
        results["package_swift"] = False

    # Create directory structure for targets
    types_dir = target_dir / "Sources" / f"{project_name}Types"
    client_dir = target_dir / "Sources" / project_name
    tests_dir = target_dir / "Tests" / f"{project_name}Tests"

    # Create directories if they don't exist
    types_dir.mkdir(parents=True, exist_ok=True)
    results["types_dir"] = types_dir.exists()

    client_dir.mkdir(parents=True, exist_ok=True)
    results["client_dir"] = client_dir.exists()

    tests_dir.mkdir(parents=True, exist_ok=True)
    results["tests_dir"] = tests_dir.exists()

    # Create initial Swift files to satisfy Swift Package Manager
    swift_file_results = create_initial_swift_files(target_dir, project_name)
    results.update(swift_file_results)

    # Create .gitkeep files to ensure directories are tracked by git
    # (empty directories aren't tracked by git)
    for dir_path in [types_dir, client_dir, tests_dir]:
        gitkeep_path = dir_path / ".gitkeep"
        if not gitkeep_path.exists():
            gitkeep_path.touch()

    return results


def create_initial_swift_files(target_dir: Path, project_name: str) -> dict[str, bool]:
    """Create initial Swift files in each target to satisfy SPM.

    Creates minimal placeholder Swift files that allow swift build to succeed
    before code generation. Files contain only safe imports (no generated code
    references) and are created once then preserved on updates.

    Args:
        target_dir: The package root directory
        project_name: The name of the Swift package

    Returns:
        Dictionary indicating which files were created:
        - "types_file": True if created, False if existed
        - "client_file": True if created, False if existed
        - "tests_file": True if created, False if existed
    """
    # Create context for template rendering
    context = {"project_name": project_name}

    results = {}

    # Create Types file
    types_file_path = target_dir / "Sources" / f"{project_name}Types" / f"{project_name}Types.swift"
    types_content = render_template("TypesFile.swift.j2", context)
    results["types_file"] = write_if_not_exists(types_file_path, types_content, "Types Swift file")

    # Create Client file
    client_file_path = target_dir / "Sources" / project_name / f"{project_name}.swift"
    client_content = render_template("ClientFile.swift.j2", context)
    results["client_file"] = write_if_not_exists(
        client_file_path, client_content, "Client Swift file"
    )

    # Create Tests file
    tests_file_path = target_dir / "Tests" / f"{project_name}Tests" / f"{project_name}Tests.swift"
    tests_content = render_template("TestsFile.swift.j2", context)
    results["tests_file"] = write_if_not_exists(tests_file_path, tests_content, "Tests Swift file")

    return results


def run_swift_build(target_dir: Path) -> bool:
    """Run swift build to verify the package structure.

    Args:
        target_dir: The directory containing Package.swift

    Returns:
        True if build was successful, False otherwise
    """
    try:
        result = subprocess.run(
            ["swift", "build"],
            cwd=target_dir,
            capture_output=True,
            text=True,
            timeout=300,
        )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        return False
    except FileNotFoundError:
        # swift command not found
        return False


def run_openapi_generator(
    target_dir: Path,
    project_name: str,
    openapi_file: str = "openapi.yaml",
) -> dict[str, bool]:
    """Run the Swift OpenAPI Generator for Types and Client.

    Args:
        target_dir: The directory containing Package.swift and openapi files
        project_name: The name of the Swift package
        openapi_file: The name of the OpenAPI specification file (default: openapi.yaml)

    Returns:
        Dictionary indicating success:
        - "types_generated": True if Types generation succeeded
        - "client_generated": True if Client generation succeeded
    """
    results = {"types_generated": False, "client_generated": False}

    openapi_path = target_dir / openapi_file
    if not openapi_path.exists():
        return results

    # Generate Types
    types_config = "openapi-generator-config-types.yaml"
    types_output_dir = target_dir / "Sources" / f"{project_name}Types" / "GeneratedSources"

    try:
        result = subprocess.run(
            [
                "swift",
                "run",
                "swift-openapi-generator",
                "generate",
                "--config",
                types_config,
                openapi_file,
                "--output-directory",
                str(types_output_dir),
            ],
            cwd=target_dir,
            capture_output=True,
            text=True,
            timeout=300,
        )
        results["types_generated"] = result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        results["types_generated"] = False

    # Generate Client
    client_config = "openapi-generator-config-client.yaml"
    client_output_dir = target_dir / "Sources" / project_name / "GeneratedSources"

    try:
        result = subprocess.run(
            [
                "swift",
                "run",
                "swift-openapi-generator",
                "generate",
                "--config",
                client_config,
                openapi_file,
                "--output-directory",
                str(client_output_dir),
            ],
            cwd=target_dir,
            capture_output=True,
            text=True,
            timeout=300,
        )
        results["client_generated"] = result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        results["client_generated"] = False

    return results


def setup_swift_package(
    target_dir: Path,
    project_name: str,
    run_generator: bool = False,
) -> dict:
    """Complete setup of Swift package structure and optional code generation.

    This is the main orchestration function that:
    1. Creates the Package.swift and directory structure
    2. Optionally runs the OpenAPI generator

    Args:
        target_dir: The directory to set up as a Swift package
        project_name: The name of the Swift package
        run_generator: Whether to run swift-openapi-generator (default: False)

    Returns:
        Dictionary with setup results from all steps
    """
    results = {}

    # Ensure package structure
    structure_results = ensure_package_structure(target_dir, project_name)
    results["structure"] = structure_results

    # Verify package with swift build
    build_ok = run_swift_build(target_dir)
    results["build_verification"] = build_ok

    # Optionally run code generation
    if run_generator:
        generator_results = run_openapi_generator(target_dir, project_name)
        results["generation"] = generator_results

    return results
