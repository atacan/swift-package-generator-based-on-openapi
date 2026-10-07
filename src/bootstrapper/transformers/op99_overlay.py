"""Operation 99: Apply an OpenAPI overlay using Speakeasy's OpenAPI CLI.

This transformation applies overlay modifications to an OpenAPI specification
using ``openapi overlay apply``. Its YAML node model preserves large integers
exactly, including the signed Int64 bounds used by OpenAI's seed parameter.
"""

import json
import subprocess
from pathlib import Path
from typing import Any

import yaml


def apply_overlay(
    target_dir: Path,
    openapi_file: str = "openapi.yaml",
) -> dict[str, bool | str]:
    """Apply an OpenAPI overlay using Speakeasy's OpenAPI CLI.

    Args:
        target_dir: Directory containing the OpenAPI files
        openapi_file: Name of the OpenAPI spec file (e.g., "openapi.yaml" or "openapi.json")

    Returns:
        Dictionary with:
        - "applied": True if overlay was applied successfully
        - "skipped": True if skipped (no overlay or empty actions)
        - "reason": Description of what happened
    """
    # Derive overlay filename from openapi_file extension
    openapi_path = target_dir / openapi_file
    file_suffix = openapi_path.suffix  # e.g., ".yaml" or ".json"

    if file_suffix not in [".yaml", ".yml", ".json"]:
        return {
            "applied": False,
            "skipped": False,
            "reason": f"Unsupported file extension: {file_suffix}",
        }

    # Determine overlay filename based on extension
    if file_suffix == ".json":
        overlay_filename = "openapi-overlay.json"
    else:  # .yaml or .yml
        overlay_filename = "openapi-overlay.yaml"

    overlay_path = target_dir / overlay_filename

    # Check if openapi file exists
    if not openapi_path.exists():
        return {
            "applied": False,
            "skipped": False,
            "reason": f"OpenAPI file not found: {openapi_path}",
        }

    # Check if overlay file exists
    if not overlay_path.exists():
        return {
            "applied": False,
            "skipped": True,
            "reason": "No overlay file found",
        }

    return apply_overlay_file(openapi_path, overlay_path)


def apply_overlay_file(openapi_path: Path, overlay_path: Path) -> dict[str, bool | str]:
    """Apply a specific OpenAPI overlay file to a specific OpenAPI spec file.

    Args:
        openapi_path: Path to the OpenAPI spec file to update in place
        overlay_path: Path to the overlay file to apply

    Returns:
        Dictionary with:
        - "applied": True if overlay was applied successfully
        - "skipped": True if skipped (empty actions)
        - "reason": Description of what happened
    """
    file_suffix = openapi_path.suffix
    if file_suffix not in [".yaml", ".yml", ".json"]:
        return {
            "applied": False,
            "skipped": False,
            "reason": f"Unsupported file extension: {file_suffix}",
        }

    if not openapi_path.exists():
        return {
            "applied": False,
            "skipped": False,
            "reason": f"OpenAPI file not found: {openapi_path}",
        }

    if not overlay_path.exists():
        return {
            "applied": False,
            "skipped": False,
            "reason": f"Overlay file not found: {overlay_path}",
        }

    # Parse overlay file and check actions array
    try:
        overlay_data = _load_overlay_file(overlay_path)
    except Exception as e:
        return {
            "applied": False,
            "skipped": False,
            "reason": f"Failed to parse overlay file: {e}",
        }

    # Check if actions array exists and is non-empty
    actions = overlay_data.get("actions", []) if isinstance(overlay_data, dict) else []
    if not actions or (isinstance(actions, list) and len(actions) == 0):
        return {
            "applied": False,
            "skipped": True,
            "reason": "Overlay has no actions defined",
        }

    try:
        result = subprocess.run(
            [
                "openapi",
                "overlay",
                "apply",
                "--overlay",
                str(overlay_path),
                "--schema",
                str(openapi_path),
            ],
            capture_output=True,
            text=True,
            timeout=60,
            check=True,
        )

        # The CLI emits YAML for both input formats. Validate before writing and
        # retain JSON output when the input is JSON. Failed overlays leave input intact.
        transformed = yaml.safe_load(result.stdout)
        if not isinstance(transformed, dict):
            return {
                "applied": False,
                "skipped": False,
                "reason": "openapi overlay apply did not produce an object document",
            }
        output = (
            json.dumps(transformed, indent=2, ensure_ascii=False) + "\n"
            if file_suffix == ".json"
            else result.stdout
        )
        openapi_path.write_text(output, encoding="utf-8")

        return {
            "applied": True,
            "skipped": False,
            "reason": "Overlay applied successfully",
        }

    except FileNotFoundError:
        return {
            "applied": False,
            "skipped": False,
            "reason": (
                "openapi CLI not found. Install Speakeasy's OpenAPI CLI to apply overlays "
                "(brew install openapi)."
            ),
        }
    except subprocess.TimeoutExpired:
        return {
            "applied": False,
            "skipped": False,
            "reason": "openapi overlay apply timed out after 60 seconds",
        }
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.strip() if e.stderr else "No error details"
        return {
            "applied": False,
            "skipped": False,
            "reason": f"openapi overlay apply failed with exit code {e.returncode}: {stderr}",
        }


def _load_overlay_file(overlay_path: Path) -> dict[str, Any]:
    """Load and parse overlay file (JSON or YAML).

    Args:
        overlay_path: Path to the overlay file

    Returns:
        Parsed overlay data as dictionary

    Raises:
        json.JSONDecodeError: If JSON parsing fails
        yaml.YAMLError: If YAML parsing fails
    """
    with open(overlay_path, encoding="utf-8") as f:
        if overlay_path.suffix == ".json":
            return json.load(f)
        else:  # .yaml or .yml
            return yaml.safe_load(f)
