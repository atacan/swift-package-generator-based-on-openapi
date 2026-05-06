"""Operation 10: Ensure path operationId values are unique.

Some upstream specs reuse the same ``operationId`` for multiple path operations.
The swift-openapi-generator requires unique operation identifiers. This
transformer replaces duplicate operation IDs with deterministic IDs derived from
their paths.
"""

import re
from collections import Counter
from collections.abc import Iterator

HTTP_METHODS = {"get", "put", "post", "delete", "options", "head", "patch", "trace"}
_VERSION_SEGMENT_RE = re.compile(r"^v\d+$", re.IGNORECASE)
_WORD_RE = re.compile(r"[A-Za-z0-9]+")


def _iter_operations(spec: dict) -> Iterator[tuple[str, str, dict]]:
    paths = spec.get("paths")
    if not isinstance(paths, dict):
        return

    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        for method, operation in path_item.items():
            if method.lower() not in HTTP_METHODS or not isinstance(operation, dict):
                continue
            yield path, method.lower(), operation


def _pascal_case(value: str) -> str:
    words = _WORD_RE.findall(value)
    return "".join(word[:1].upper() + word[1:] for word in words)


def _path_to_operation_id(path: str) -> str:
    segments = [segment for segment in path.strip("/").split("/") if segment]
    if segments and _VERSION_SEGMENT_RE.fullmatch(segments[0]):
        segments = segments[1:]

    operation_id = ""

    for segment in segments:
        if segment.startswith("{") and segment.endswith("}"):
            parameter_name = segment[1:-1]
            normalized = "_".join(_WORD_RE.findall(parameter_name))
            if normalized:
                if operation_id and not operation_id.endswith("_"):
                    operation_id += "_"
                operation_id += f"{normalized}_"
            continue

        normalized_literal = _pascal_case(segment)
        if not normalized_literal:
            continue

        if not operation_id:
            operation_id += normalized_literal[:1].lower() + normalized_literal[1:]
        else:
            operation_id += normalized_literal

    return operation_id.rstrip("_") or "operation"


def _unique_operation_id(base_operation_id: str, used_operation_ids: set[str]) -> str:
    if base_operation_id not in used_operation_ids:
        return base_operation_id

    suffix = 2
    while f"{base_operation_id}_{suffix}" in used_operation_ids:
        suffix += 1
    return f"{base_operation_id}_{suffix}"


def ensure_unique_operation_ids(spec: dict) -> dict:
    """Replace duplicate operationId values with unique path-derived values."""
    operations = list(_iter_operations(spec))
    operation_id_counts = Counter(
        operation.get("operationId")
        for _, _, operation in operations
        if isinstance(operation.get("operationId"), str)
    )

    if all(count == 1 for count in operation_id_counts.values()):
        return spec

    duplicate_operation_ids = {
        operation_id for operation_id, count in operation_id_counts.items() if count > 1
    }
    used_operation_ids = {
        operation_id
        for operation_id, count in operation_id_counts.items()
        if count == 1 and isinstance(operation_id, str)
    }

    for path, _, operation in operations:
        operation_id = operation.get("operationId")
        if operation_id not in duplicate_operation_ids:
            continue

        path_based_operation_id = _path_to_operation_id(path)
        unique_operation_id = _unique_operation_id(path_based_operation_id, used_operation_ids)
        operation["operationId"] = unique_operation_id
        used_operation_ids.add(unique_operation_id)

    return spec
