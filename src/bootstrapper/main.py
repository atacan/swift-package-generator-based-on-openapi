"""Main CLI entry point for the Swift OpenAPI Bootstrapper."""

from pathlib import Path

import typer
from rich.console import Console

from bootstrapper.generators.swift import ensure_package_structure, run_openapi_generator
from bootstrapper.transformers.manager import transform_spec

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
    # For now, just remove hyphens and underscores, capitalize each word
    words = dir_name.replace("-", " ").replace("_", " ").split()
    project_name = "".join(word.capitalize() for word in words)

    return project_name or "SwiftAPIWrapper"


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

    # Derive project name if not provided
    if not project_name:
        project_name = derive_project_name(target_path)
        console.print(f"[dim]Auto-derived project name: {project_name}[/dim]")

    # Step 2: Process specification (apply transformations)
    output_file = target_path / f"openapi{original_openapi.suffix}"

    with console.status("[bold yellow]Applying transformations..."):
        try:
            transform_spec(original_openapi, output_file)
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

    console.print(
        f"[bold green]✓[/bold green] Created directory structure "
        f"(Types: {structure_results['types_dir']}, "
        f"Client: {structure_results['client_dir']}, "
        f"Tests: {structure_results['tests_dir']})"
    )

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
