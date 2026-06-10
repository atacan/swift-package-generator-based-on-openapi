"""Operation 11: Mark multipart request bodies as required.

OpenAPI request bodies are optional by default unless ``required: true`` is
set. The swift-openapi-generator skips optional multipart bodies, so multipart
request bodies need the top-level requestBody.required flag enabled.
"""

from typing import Any

HTTP_METHODS = {"get", "put", "post", "delete", "options", "head", "patch", "trace"}


def _resolve_ref(ref_string: str, spec: dict) -> dict | None:
    """Follow a local JSON $ref like '#/components/requestBodies/Foo' to its target."""
    if not ref_string.startswith("#/"):
        return None

    node: Any = spec
    for part in ref_string.lstrip("#/").split("/"):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]

    return node if isinstance(node, dict) else None


def _has_multipart_content(request_body: dict) -> bool:
    content = request_body.get("content")
    if not isinstance(content, dict):
        return False

    return any(
        isinstance(content_type, str) and "multipart" in content_type for content_type in content
    )


def _mark_if_multipart(request_body: dict | None) -> None:
    if isinstance(request_body, dict) and _has_multipart_content(request_body):
        request_body["required"] = True


def _request_body_for_operation(operation: dict, spec: dict) -> dict | None:
    request_body = operation.get("requestBody")
    if not isinstance(request_body, dict):
        return None

    if "$ref" in request_body:
        ref = request_body.get("$ref")
        return _resolve_ref(ref, spec) if isinstance(ref, str) else None

    return request_body


def require_multipart_request_bodies(spec: dict) -> dict:
    """Set ``required: true`` on multipart request bodies."""
    paths = spec.get("paths")
    if isinstance(paths, dict):
        for path_item in paths.values():
            if not isinstance(path_item, dict):
                continue
            for method, operation in path_item.items():
                if method.lower() not in HTTP_METHODS or not isinstance(operation, dict):
                    continue
                _mark_if_multipart(_request_body_for_operation(operation, spec))

    components = spec.get("components")
    if isinstance(components, dict):
        request_bodies = components.get("requestBodies")
        if isinstance(request_bodies, dict):
            for request_body in request_bodies.values():
                _mark_if_multipart(request_body if isinstance(request_body, dict) else None)

    return spec
