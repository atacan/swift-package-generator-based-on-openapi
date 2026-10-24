"""Swift package scaffolding and generation.

This module handles the creation and maintenance of Swift package structure,
including generating Package.swift from templates and running the OpenAPI generator.
"""

import subprocess
from datetime import datetime
from pathlib import Path
from typing import NotRequired, TypedDict

from bootstrapper.generators.security import (
    create_authentication_support,
    generate_authentication_middleware,
)
from bootstrapper.generators.templates import render_template, write_if_not_exists


def ensure_package_structure(target_dir: Path, project_name: str) -> dict[str, bool]:
    """Ensure the Swift package structure exists.

    Creates or updates the Package.swift file and the directory structure needed
    for Types, the shared Client, both transport convenience targets, and their tests.

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
        - "urlsession_dir" / "asynchttpclient_dir": Whether transport directories exist
        - "urlsession_file" / "asynchttpclient_file": Whether placeholders were created
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

    for suffix in ("URLSession", "AsyncHTTPClient"):
        transport_dir = target_dir / "Sources" / f"{project_name}{suffix}"
        transport_dir.mkdir(parents=True, exist_ok=True)
        results[f"{suffix.lower()}_dir"] = True

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

    Creates placeholders and shared authentication support that build before code
    generation. Client factory extensions are added after generation succeeds.
    All editable support files are created once and preserved on updates.

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
    context = {"project_name": project_name, "types_module": f"{project_name}Types"}

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

    # Only scaffold an empty test target. Existing suites may use custom names
    # or subdirectories instead of the original placeholder filename.
    tests_dir = target_dir / "Tests" / f"{project_name}Tests"
    if any(path.is_file() for path in tests_dir.rglob("*.swift")):
        results["tests_file"] = False
    else:
        tests_file_path = tests_dir / f"{project_name}Tests.swift"
        tests_content = render_template("TestsFile.swift.j2", context)
        results["tests_file"] = write_if_not_exists(
            tests_file_path, tests_content, "Tests Swift file"
        )

    for suffix, module in (
        ("URLSession", "OpenAPIURLSession"),
        ("AsyncHTTPClient", "OpenAPIAsyncHTTPClient"),
    ):
        context = {"project_name": project_name, "transport_module": module}
        results[f"{suffix.lower()}_file"] = write_if_not_exists(
            target_dir / "Sources" / f"{project_name}{suffix}" / f"{suffix}.swift",
            render_template("TransportFile.swift.j2", context),
        )
    for suffix in ("Types", "URLSession", "AsyncHTTPClient"):
        tests_dir = target_dir / "Tests" / f"{project_name}{suffix}Tests"
        if not any(path.is_file() for path in tests_dir.rglob("*.swift")):
            write_if_not_exists(
                tests_dir / f"{project_name}{suffix}Tests.swift",
                render_template("TestsFile.swift.j2", {"project_name": f"{project_name}{suffix}"}),
            )
    create_authentication_support(target_dir, project_name)
    return results


def create_client_helpers(target_dir: Path, project_name: str) -> None:
    """Add factories once the generated Client exists; preserve all helper edits."""
    context = {"project_name": project_name}
    for suffix in ("Authentication", "URLSession", "AsyncHTTPClient"):
        module = project_name if suffix == "Authentication" else f"{project_name}{suffix}"
        filename = f"Client+{suffix}.swift"
        write_if_not_exists(
            target_dir / "Sources" / module / filename,
            render_template(f"{filename}.j2", context),
        )


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


class GenerationResults(TypedDict):
    """Status for both generation steps, with diagnostics for any failed step."""

    types_generated: bool
    client_generated: bool
    types_error: NotRequired[str]
    client_error: NotRequired[str]


def _diagnostics(stdout: str | bytes | None, stderr: str | bytes | None) -> str:
    """Keep both output streams, including bytes captured before a timeout."""
    sections = []
    for output in (stdout, stderr):
        if isinstance(output, bytes):
            output = output.decode("utf-8", errors="replace")
        if output and output.strip():
            sections.append(output.rstrip())
    return "\n".join(sections)


def _run_generator_step(
    target_dir: Path,
    openapi_file: str,
    config_file: str,
    output_dir: Path,
) -> str | None:
    """Return diagnostics on failure, or None when generation succeeds."""
    try:
        result = subprocess.run(
            [
                "swift",
                "run",
                "swift-openapi-generator",
                "generate",
                "--config",
                config_file,
                openapi_file,
                "--output-directory",
                str(output_dir),
            ],
            cwd=target_dir,
            capture_output=True,
            text=True,
            timeout=300,
        )
    except subprocess.TimeoutExpired as error:
        output = _diagnostics(error.stdout, error.stderr)
        message = f"Swift OpenAPI Generator timed out after {error.timeout} seconds."
        return f"{message}\n{output}" if output else message
    except FileNotFoundError:
        return "Swift executable not found. Install Swift and ensure 'swift' is on PATH."

    if result.returncode == 0:
        return None
    output = _diagnostics(result.stdout, result.stderr)
    message = f"swift-openapi-generator exited with status {result.returncode}."
    return f"{message}\n{output}" if output else message


def run_openapi_generator(
    target_dir: Path,
    project_name: str,
    openapi_file: str = "openapi.yaml",
) -> GenerationResults:
    """Generate Types and Client, retaining diagnostics for each failed step.

    Both steps are attempted so callers can report partial success. Client helpers
    are created only when both steps succeed. Failures include the captured stdout
    and stderr, or an explanation for a missing input/toolchain or timeout.
    """
    results: GenerationResults = {"types_generated": False, "client_generated": False}
    openapi_path = target_dir / openapi_file
    if not openapi_path.exists():
        message = f"OpenAPI file not found: {openapi_path}"
        results["types_error"] = message
        results["client_error"] = message
        return results

    types_error = _run_generator_step(
        target_dir,
        openapi_file,
        "openapi-generator-config-types.yaml",
        target_dir / "Sources" / f"{project_name}Types" / "GeneratedSources",
    )
    results["types_generated"] = types_error is None
    if types_error is not None:
        results["types_error"] = types_error

    client_error = _run_generator_step(
        target_dir,
        openapi_file,
        "openapi-generator-config-client.yaml",
        target_dir / "Sources" / project_name / "GeneratedSources",
    )
    results["client_generated"] = client_error is None
    if client_error is not None:
        results["client_error"] = client_error

    if results["client_generated"] and results["types_generated"]:
        generate_authentication_middleware(target_dir, project_name, openapi_file)
        create_client_helpers(target_dir, project_name)

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
