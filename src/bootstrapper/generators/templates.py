"""Template rendering system using Jinja2.

This module handles loading Jinja2 templates from the resources directory,
rendering them with project context, and writing config files to the target directory.
"""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader


def get_template_dir() -> Path:
    """Get the path to the templates directory."""
    return Path(__file__).parent.parent / "resources"


def create_jinja_env() -> Environment:
    """Create and configure a Jinja2 environment.

    Returns:
        Configured Jinja2 Environment with the templates directory as loader.
    """
    template_dir = get_template_dir()
    return Environment(
        loader=FileSystemLoader(template_dir),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )


def render_template(template_name: str, context: dict) -> str:
    """Render a template with the given context.

    Args:
        template_name: Name of the template file (e.g., "Makefile.j2")
        context: Dictionary of variables to pass to the template

    Returns:
        Rendered template as a string
    """
    env = create_jinja_env()
    template = env.get_template(template_name)
    return template.render(**context)


def write_if_not_exists(target_path: Path, content: str, description: str = "file") -> bool:
    """Write content to a file only if it doesn't already exist.

    This preserves user edits on updates.

    Args:
        target_path: Path where the file should be written
        content: Content to write to the file
        description: Human-readable description for logging

    Returns:
        True if file was created, False if it already existed (skipped)
    """
    if target_path.exists():
        return False

    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(content, encoding="utf-8")
    return True


def generate_config_files(
    target_dir: Path, project_name: str, file_format: str = ".yaml"
) -> dict[str, bool]:
    """Generate all config files from templates in the target directory.

    Only creates files that don't already exist to preserve user edits.

    Args:
        target_dir: Directory where config files should be written
        project_name: Name of the Swift package project
        file_format: File extension of the original OpenAPI spec (".yaml", ".yml", or ".json")

    Returns:
        Dictionary mapping filename to whether it was created (True) or skipped (False)
    """
    context = {"project_name": project_name}

    # Determine overlay file based on format
    if file_format == ".json":
        overlay_filename = "openapi-overlay.json"
        overlay_template = "overlay.json.j2"
    else:
        overlay_filename = "openapi-overlay.yaml"
        overlay_template = "overlay.yaml.j2"

    # Define all templates and their output paths
    templates = {
        "Makefile": "Makefile.j2",
        ".gitignore": ".gitignore.j2",
        ".env.example": ".env.example.j2",
        "openapi-generator-config-types.yaml": "openapi-generator-config-types.yaml.j2",
        "openapi-generator-config-client.yaml": "openapi-generator-config-client.yaml.j2",
        overlay_filename: overlay_template,
        ".swift-format": ".swift-format.j2",
        "AGENTS.md": "AGENTS.md.j2",
        "CLAUDE.md": "CLAUDE.md.j2",
        "README.md": "README.md.j2",
        ".claude/skills/openapi-overlay/SKILL.md": ".claude/skills/openapi-overlay/SKILL.md.j2",
    }

    results = {}

    for output_filename, template_name in templates.items():
        content = render_template(template_name, context)
        target_path = target_dir / output_filename
        created = write_if_not_exists(target_path, content, output_filename)
        results[output_filename] = created

    return results
