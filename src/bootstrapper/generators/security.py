"""Module for extracting and classifying OpenAPI security schemes.

This module provides utilities to analyze OpenAPI specifications for security schemes
and generate appropriate Swift authentication middleware based on the detected schemes.
"""

from enum import Enum
from pathlib import Path

from bootstrapper.core.loader import load_spec
from bootstrapper.generators.templates import render_template, write_if_not_exists


class SecuritySchemeType(Enum):
    """Supported authentication scheme types."""

    HTTP_BEARER = "http_bearer"
    API_KEY_HEADER = "api_key_header"
    UNSUPPORTED = "unsupported"


class SecurityScheme:
    """Represents a security scheme from an OpenAPI specification."""

    def __init__(
        self,
        name: str,
        scheme_type: SecuritySchemeType,
        header_name: str | None = None,
    ):
        """Initialize a SecurityScheme.

        Args:
            name: The name of the security scheme (e.g., "BearerAuth")
            scheme_type: The classified type of the scheme
            header_name: The HTTP header name (only for API_KEY_HEADER type)
        """
        self.name = name
        self.scheme_type = scheme_type
        self.header_name = header_name


def extract_security_schemes(spec: dict) -> dict[str, dict]:
    """Extract security schemes from an OpenAPI specification.

    Args:
        spec: The OpenAPI specification as a dictionary

    Returns:
        Dictionary of security scheme definitions from components.securitySchemes,
        or empty dict if none are defined
    """
    return spec.get("components", {}).get("securitySchemes", {})


def classify_security_scheme(scheme_name: str, scheme_def: dict) -> SecurityScheme | None:
    """Classify a security scheme definition into a supported type.

    Args:
        scheme_name: The name of the security scheme
        scheme_def: The security scheme definition from the OpenAPI spec

    Returns:
        SecurityScheme object if the scheme is supported, None otherwise

    Supported schemes:
        - type="http" AND scheme="bearer" -> HTTP_BEARER
        - type="apiKey" AND in="header" -> API_KEY_HEADER
        - Everything else -> UNSUPPORTED (returns None)
    """
    scheme_type = scheme_def.get("type")

    # HTTP Bearer authentication
    if scheme_type == "http" and scheme_def.get("scheme") == "bearer":
        return SecurityScheme(scheme_name, SecuritySchemeType.HTTP_BEARER)

    # API Key in header
    if scheme_type == "apiKey" and scheme_def.get("in") == "header":
        header_name = scheme_def.get("name")
        if header_name:
            return SecurityScheme(
                scheme_name, SecuritySchemeType.API_KEY_HEADER, header_name=header_name
            )

    # Unsupported schemes: OAuth2, OpenID Connect, API key in query/cookie, HTTP Basic, etc.
    return None


def get_primary_security_scheme(openapi_path: Path) -> SecurityScheme | None:
    """Get the primary (first) supported security scheme from an OpenAPI spec.

    Args:
        openapi_path: Path to the OpenAPI specification file

    Returns:
        SecurityScheme object for the first supported scheme, or None if:
        - File doesn't exist
        - No security schemes are defined
        - All schemes are unsupported

    Note:
        Python 3.7+ preserves dict insertion order, so the first scheme
        in the YAML/JSON will be selected.
    """
    try:
        spec, _ = load_spec(openapi_path)
    except (FileNotFoundError, ValueError, Exception):
        return None

    schemes = extract_security_schemes(spec)
    if not schemes:
        return None

    # Get first scheme (dict order is preserved in Python 3.7+)
    for scheme_name, scheme_def in schemes.items():
        classified = classify_security_scheme(scheme_name, scheme_def)
        if classified:  # Return first supported scheme
            return classified

    return None


def generate_authentication_middleware(
    target_dir: Path,
    project_name: str,
    openapi_file: str = "openapi.yaml",
) -> dict[str, any]:
    """Generate AuthenticationMiddleware.swift based on OpenAPI security schemes.

    Args:
        target_dir: The target project directory
        project_name: Name of the Swift package
        openapi_file: Name of the OpenAPI spec file (default: "openapi.yaml")

    Returns:
        Dictionary with generation status:
        {
            "generated": bool,  # True if file was created, False otherwise
            "reason": str,      # Human-readable explanation
            "scheme_name": str | None,  # Name of the security scheme used
            "scheme_type": str | None,  # Type of authentication
        }
    """
    openapi_path = target_dir / openapi_file

    # Check if OpenAPI file exists
    if not openapi_path.exists():
        return {
            "generated": False,
            "reason": f"OpenAPI file not found: {openapi_file}",
            "scheme_name": None,
            "scheme_type": None,
        }

    # Extract primary security scheme
    raw_schemes = extract_security_schemes(load_spec(openapi_path)[0])
    security_scheme = get_primary_security_scheme(openapi_path)

    if not security_scheme:
        if raw_schemes:
            # Schemes exist but none are supported — caller should warn
            return {
                "generated": False,
                "reason": "No supported security schemes found",
                "scheme_name": None,
                "scheme_type": None,
                "unsupported_schemes": list(raw_schemes.keys()),
            }
        return {
            "generated": False,
            "reason": "No security schemes defined",
            "scheme_name": None,
            "scheme_type": None,
            "unsupported_schemes": [],
        }

    # Prepare template context
    context = {
        "project_name": project_name,
        "scheme_name": security_scheme.name,
        "scheme_type": security_scheme.scheme_type.value,
        "header_name": security_scheme.header_name,
    }

    # Render template
    content = render_template("AuthenticationMiddleware.swift.j2", context)

    # Write to Types directory
    types_dir = target_dir / "Sources" / f"{project_name}Types"
    auth_file = types_dir / "AuthenticationMiddleware.swift"

    # Use write_if_not_exists to preserve user edits
    was_created = write_if_not_exists(auth_file, content, "AuthenticationMiddleware.swift")

    if was_created:
        scheme_type_readable = security_scheme.scheme_type.value.replace("_", " ")
        return {
            "generated": True,
            "reason": f"Created with {scheme_type_readable} authentication",
            "scheme_name": security_scheme.name,
            "scheme_type": security_scheme.scheme_type.value,
            "unsupported_schemes": [],
        }
    else:
        return {
            "generated": False,
            "reason": "File already exists (preserved user edits)",
            "scheme_name": security_scheme.name,
            "scheme_type": security_scheme.scheme_type.value,
            "unsupported_schemes": [],
        }
