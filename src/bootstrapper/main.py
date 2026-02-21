"""Main CLI entry point for the Swift OpenAPI Bootstrapper."""

from pathlib import Path

import typer
from rich.console import Console

from bootstrapper.config import (
    CONFIG_FILENAME,
    ProjectConfig,
    check_name_mismatch,
    load_config,
    save_config,
)
from bootstrapper.generators.security import generate_authentication_middleware
from bootstrapper.generators.swift import ensure_package_structure, run_openapi_generator
from bootstrapper.generators.templates import generate_config_files
from bootstrapper.transformers.manager import transform_spec
from bootstrapper.transformers.op99_overlay import apply_overlay

app = typer.Typer(
    name="swift-bootstrapper",
    help="Bootstrap and maintain Swift Packages based on OpenAPI specifications",
)
console = Console()


def find_original_openapi(target_dir: Path) -> Path | None:
    """
    Find the original OpenAPI specification file in the target directory.

    Looks for files in this order:
    1. original_openapi.yaml
    2. original_openapi.yml
    3. original_openapi.json

    Args:
        target_dir: Directory to search in

    Returns:
        Path to the found file, or None if not found
    """
    for name in ["original_openapi.yaml", "original_openapi.yml", "original_openapi.json"]:
        path = target_dir / name
        if path.exists():
            return path
    return None


def derive_project_name(target_dir: Path) -> str:
    """
    Derive the Swift package name from the target directory name.

    Args:
        target_dir: The directory path

    Returns:
        Sanitized project name (removes special characters, converts to PascalCase)
    """
    # Get the directory name
    dir_name = target_dir.resolve().name

    # Remove special characters and convert to PascalCase
    # Preserve existing uppercase letters while capitalizing first letter of each word
    words = dir_name.replace("-", " ").replace("_", " ").split()

    # Capitalize first letter of each word without lowercasing the rest
    # This preserves names like "AssemblyAI" correctly
    project_name = "".join(word[0].upper() + word[1:] if word else "" for word in words)

    return project_name or "SwiftAPIWrapper"


def resolve_project_name(
    target_dir: Path,
    cli_name: str | None,
    config: ProjectConfig,
) -> tuple[str, str]:
    """
    Resolve the project name based on priority order.

    Priority: CLI argument > config file > derived from folder

    Returns:
        Tuple of (resolved_name, source) where source describes origin
    """
    if cli_name:
        return cli_name, "CLI argument"

    if config.package_name:
        return config.package_name, "config file"

    derived = derive_project_name(target_dir)
    return derived, "auto-derived from directory"


@app.command()
def bootstrap(
    target_dir: str = typer.Argument(
        ".",
        help="Path to the directory containing original_openapi.yaml/json",
    ),
    project_name: str = typer.Option(
        None,
        "--name",
        "-n",
        help="Name for the Swift package (auto-derived from directory if not specified)",
    ),
) -> None:
    """Bootstrap a Swift package from an OpenAPI specification.

    This command will:
    1. Find the original_openapi file in the target directory
    2. Apply transformations to create a clean openapi file
    3. Set up the Swift package structure
    4. Run the OpenAPI generator to create Swift code
    """
    # Convert to Path and resolve
    target_path = Path(target_dir).resolve()

    # Display header
    console.print()
    console.print("[bold blue]Swift OpenAPI Bootstrapper[/bold blue]")
    console.print(f"[dim]Target directory: {target_path}[/dim]")
    console.print()

    # Step 1: Find original_openapi file
    with console.status("[bold yellow]Searching for original_openapi file..."):
        original_openapi = find_original_openapi(target_path)

    if not original_openapi:
        console.print(
            "[bold red]✗[/bold red] Error: Could not find original_openapi.yaml, "
            "original_openapi.yml, or original_openapi.json"
        )
        raise typer.Exit(1)

    console.print(f"[bold green]✓[/bold green] Found: {original_openapi.name}")

    # Load existing config (if any)
    config = load_config(target_path)

    # Resolve project name with priority: CLI > config > derived
    project_name, name_source = resolve_project_name(target_path, project_name, config)

    # Check for mismatch with existing Package.swift
    mismatch = check_name_mismatch(target_path, project_name)
    if mismatch:
        console.print()
        console.print("[bold yellow]⚠ Warning: Package name mismatch detected[/bold yellow]")
        console.print(f"  Config file says: {mismatch.config_name}")
        console.print(f"  Package.swift uses: {mismatch.package_swift_name}")
        console.print("  Existing files will NOT be renamed. Using Package.swift name.")
        console.print("  To rename, manually update Package.swift and directory names.")
        console.print()
        # Use the existing Package.swift name
        project_name = mismatch.package_swift_name
        name_source = "existing Package.swift"

    console.print(f"[dim]Project name: {project_name} ({name_source})[/dim]")

    # Update config with resolved name for saving
    config.package_name = project_name

    # Step 2: Process specification (apply transformations)
    output_file = target_path / f"openapi{original_openapi.suffix}"

    console.print("[bold yellow]Applying transformations...[/bold yellow]")
    try:
        transform_spec(original_openapi, output_file, console=console)
    except Exception as e:
        console.print(f"[bold red]✗[/bold red] Failed to transform spec: {e}")
        raise typer.Exit(1)

    console.print(
        f"[bold green]✓[/bold green] Transformed specification written to: {output_file.name}"
    )

    # Step 3: Ensure package structure
    with console.status("[bold yellow]Setting up Swift package structure..."):
        try:
            structure_results = ensure_package_structure(target_path, project_name)
        except Exception as e:
            console.print(f"[bold red]✗[/bold red] Failed to create package structure: {e}")
            raise typer.Exit(1)

    # Report what was created
    if structure_results["package_swift"]:
        console.print("[bold green]✓[/bold green] Created Package.swift")
    else:
        console.print("[bold blue]✓[/bold blue] Package.swift already exists (preserved)")

    # Report Swift file creation
    if any(
        [
            structure_results.get("types_file"),
            structure_results.get("client_file"),
            structure_results.get("tests_file"),
        ]
    ):
        console.print("[bold green]✓[/bold green] Created initial Swift files")

    # Step 3.5: Generate config files (Makefile, .gitignore, .env, generator configs)
    with console.status("[bold yellow]Generating config files..."):
        try:
            config_results = generate_config_files(
                target_path, project_name, file_format=original_openapi.suffix
            )
        except Exception as e:
            console.print(f"[bold red]✗[/bold red] Failed to generate config files: {e}")
            raise typer.Exit(1)

    # Report which config files were created
    created_configs = [name for name, created in config_results.items() if created]
    if created_configs:
        config_names = ", ".join(created_configs)
        console.print(f"[bold green]✓[/bold green] Generated config files: {config_names}")
    else:
        console.print("[bold blue]✓[/bold blue] Config files already exist (preserved)")

    # Save the project config file (if it doesn't exist)
    config_created = save_config(target_path, config)
    if config_created:
        console.print(f"[bold green]✓[/bold green] Created {CONFIG_FILENAME}")
    else:
        console.print(f"[bold blue]✓[/bold blue] {CONFIG_FILENAME} already exists (preserved)")

    console.print(
        f"[bold green]✓[/bold green] Created directory structure "
        f"(Types: {structure_results['types_dir']}, "
        f"Client: {structure_results['client_dir']}, "
        f"Tests: {structure_results['tests_dir']})"
    )

    # Step 3.6: Apply overlay if it exists and has actions
    with console.status("[bold yellow]Applying overlay..."):
        try:
            overlay_results = apply_overlay(target_path, openapi_file=output_file.name)
        except Exception as e:
            console.print(f"[bold red]✗[/bold red] Failed to apply overlay: {e}")
            raise typer.Exit(1)

    # Report results (only show if applied or failed, silent skip for empty overlay)
    if overlay_results["applied"]:
        console.print(f"[bold green]✓[/bold green] {overlay_results['reason']}")
    elif not overlay_results["skipped"]:
        # Only show warning if it was attempted but failed
        console.print(f"[bold yellow]![/bold yellow] Overlay: {overlay_results['reason']}")
    # Silent skip when overlay has no actions (normal/expected case)

    # Step 3.7: Generate AuthenticationMiddleware if security schemes defined
    with console.status("[bold yellow]Analyzing security schemes..."):
        try:
            auth_results = generate_authentication_middleware(
                target_path, project_name, openapi_file=output_file.name
            )
        except Exception as e:
            console.print(f"[bold red]✗[/bold red] Failed to analyze security: {e}")
            raise typer.Exit(1)

    # Report results
    if auth_results["generated"]:
        console.print(
            f"[bold green]✓[/bold green] Generated AuthenticationMiddleware.swift "
            f"({auth_results['reason']})"
        )
    elif "already exists" in auth_results["reason"]:
        console.print(
            "[bold blue]✓[/bold blue] AuthenticationMiddleware.swift already exists (preserved)"
        )
    # Silent skip if no security schemes (normal/expected)

    # Step 4: Run OpenAPI generator
    with console.status("[bold yellow]Running Swift OpenAPI Generator..."):
        try:
            generator_results = run_openapi_generator(
                target_path, project_name, openapi_file=output_file.name
            )
        except Exception as e:
            console.print(f"[bold red]✗[/bold red] Failed to run generator: {e}")
            raise typer.Exit(1)

    # Report generation results
    if generator_results["types_generated"]:
        console.print("[bold green]✓[/bold green] Generated Types")
    else:
        console.print(
            "[bold yellow]![/bold yellow] Types generation failed "
            "(config file may be missing or swift toolchain not available)"
        )

    if generator_results["client_generated"]:
        console.print("[bold green]✓[/bold green] Generated Client")
    else:
        console.print(
            "[bold yellow]![/bold yellow] Client generation failed "
            "(config file may be missing or swift toolchain not available)"
        )

    # Final success message
    console.print()
    console.print(f"[bold green]✓ Success![/bold green] {project_name} is ready.")
    console.print(f"[dim]Open {target_path}/Package.swift to begin.[/dim]")
    console.print()


if __name__ == "__main__":
    app()
