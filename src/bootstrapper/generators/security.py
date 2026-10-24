"""Module for extracting and classifying OpenAPI security schemes.

This module provides utilities to analyze OpenAPI specifications for security schemes
and generate appropriate Swift authentication middleware based on the detected schemes.
"""

from enum import Enum
from pathlib import Path
from urllib.parse import unquote

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
    if scheme_type == "http" and scheme_def.get("scheme", "").lower() == "bearer":
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


def swift_string(value: str) -> str:
    """Encode spec-provided text as a Swift literal, including interpolation escapes."""
    escaped = []
    for char in value:
        if char in ("\\", '"'):
            escaped.append("\\" + char)
        elif ord(char) < 32 or ord(char) == 127:
            escaped.append(f"\\u{{{ord(char):x}}}")
        else:
            escaped.append(char)
    return '"' + "".join(escaped) + '"'


def resolve_local_object(spec: dict, value: dict) -> dict:
    """Resolve local references without silently treating unresolved security as public."""
    seen = set()
    while "$ref" in value:
        reference = value["$ref"]
        if reference in seen or not reference.startswith("#/"):
            raise ValueError(f"Unsupported or cyclic security/path reference: {reference}")
        seen.add(reference)
        resolved = spec
        for token in unquote(reference[2:]).split("/"):
            resolved = resolved[token.replace("~1", "/").replace("~0", "~")]
        value = {**resolved, **{key: item for key, item in value.items() if key != "$ref"}}
    return value


def security_template_context(spec: dict) -> dict[str, str]:
    """Build transport-independent security metadata from the overlaid specification."""
    schemes = []
    for name, definition in sorted(extract_security_schemes(spec).items()):
        definition = resolve_local_object(spec, definition)
        scheme = classify_security_scheme(name, definition)
        expression = ".unsupported"
        if scheme:
            if scheme.scheme_type == SecuritySchemeType.HTTP_BEARER:
                expression = ".bearer"
            else:
                expression = f".apiKey(header: {swift_string(scheme.header_name.lower())})"
        schemes.append(f"{swift_string(name)}: {expression}")

    def requirements_literal(requirements: list[dict]) -> str:
        return (
            "["
            + ", ".join(
                "[" + ", ".join(swift_string(name) for name in sorted(requirement)) + "]"
                for requirement in requirements
            )
            + "]"
        )

    operations = []
    methods = {"get", "put", "post", "delete", "options", "head", "patch", "trace"}
    for path, path_item in spec.get("paths", {}).items():
        path_item = resolve_local_object(spec, path_item)
        for method, operation in path_item.items():
            if method not in methods or not isinstance(operation, dict):
                continue
            # Match swift-openapi-generator's operation identifier fallback.
            operation_id = operation.get("operationId", f"{method}{path}")
            requirements = operation.get("security", spec.get("security", []))
            operations.append(f"{swift_string(operation_id)}: {requirements_literal(requirements)}")
    return {
        "schemes_literal": "[" + ", ".join(schemes) + "]" if schemes else "[:]",
        "default_requirements_literal": requirements_literal(spec.get("security", [])),
        "operations_literal": "[" + ", ".join(operations) + "]" if operations else "[:]",
    }


def create_authentication_support(target_dir: Path, project_name: str) -> dict[str, bool]:
    """Create shared, editable authentication support and initial empty metadata."""
    client_dir = target_dir / "Sources" / project_name
    results = {}
    for filename in ("Authentication.swift", "AuthenticationMiddleware.swift"):
        results[filename] = write_if_not_exists(
            client_dir / "Authentication" / filename,
            render_template(f"{filename}.j2", {}),
        )
    metadata = client_dir / "Authentication" / "GeneratedSecurity" / "OperationSecurity.swift"
    write_if_not_exists(
        metadata, render_template("OperationSecurity.swift.j2", security_template_context({}))
    )
    return results


def generate_authentication_middleware(
    target_dir: Path,
    project_name: str,
    openapi_file: str = "openapi.yaml",
) -> dict:
    """Preserve shared authentication code and refresh security metadata after overlays."""
    openapi_path = target_dir / openapi_file
    if not openapi_path.exists():
        return {
            "generated": False,
            "reason": f"OpenAPI file not found: {openapi_file}",
            "scheme_name": None,
            "scheme_type": None,
            "unsupported_schemes": [],
        }

    spec, _ = load_spec(openapi_path)
    context = security_template_context(spec)
    support = create_authentication_support(target_dir, project_name)
    metadata = (
        target_dir
        / "Sources"
        / project_name
        / "Authentication"
        / "GeneratedSecurity"
        / "OperationSecurity.swift"
    )
    content = render_template("OperationSecurity.swift.j2", context)
    metadata_updated = metadata.read_text(encoding="utf-8") != content
    if metadata_updated:
        metadata.write_text(content, encoding="utf-8")

    schemes = extract_security_schemes(spec)
    unsupported = [
        name
        for name, definition in schemes.items()
        if classify_security_scheme(name, resolve_local_object(spec, definition)) is None
    ]
    primary = get_primary_security_scheme(openapi_path)
    if support["AuthenticationMiddleware.swift"]:
        reason = "Created shared authentication support"
    else:
        reason = "Authentication support already exists (preserved user edits)"
    return {
        "generated": support["AuthenticationMiddleware.swift"],
        "metadata_updated": metadata_updated,
        "reason": reason,
        "scheme_name": primary.name if primary else None,
        "scheme_type": primary.scheme_type.value if primary else None,
        "unsupported_schemes": unsupported,
    }
