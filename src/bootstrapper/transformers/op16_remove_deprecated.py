"""Remove deprecated schema properties and unused deprecated model definitions.

Visit schema positions rather than arbitrary dictionaries: payload examples,
defaults, extension values, and API properties named ``deprecated`` are data.
Deprecated models still referenced by the remaining API are retained.
"""

from collections.abc import Collection, Iterator
from typing import Any
from urllib.parse import unquote

_HTTP_METHODS = {"get", "put", "post", "delete", "options", "head", "patch", "trace", "query"}
_SCHEMA_MAPS = {"properties", "patternProperties", "$defs", "definitions", "dependentSchemas"}
_SCHEMA_LISTS = {"allOf", "anyOf", "oneOf", "prefixItems"}
_SCHEMA_SINGLE = {
    "additionalProperties",
    "unevaluatedProperties",
    "propertyNames",
    "contains",
    "additionalItems",
    "unevaluatedItems",
    "not",
    "if",
    "then",
    "else",
    "contentSchema",
}


def _values(value: Any):
    return value.values() if isinstance(value, dict) else ()


def _schema_nodes(schema: Any) -> Iterator[dict]:
    if not isinstance(schema, dict):
        return
    yield schema
    for key in _SCHEMA_MAPS:
        for child in _values(schema.get(key)):
            yield from _schema_nodes(child)
    for key in _SCHEMA_LISTS:
        children = schema.get(key, [])
        if isinstance(children, list):
            for child in children:
                yield from _schema_nodes(child)
    for key in _SCHEMA_SINGLE:
        yield from _schema_nodes(schema.get(key))
    items = schema.get("items")
    for child in items if isinstance(items, list) else [items]:
        yield from _schema_nodes(child)


def _document_schemas(spec: dict, include_models: bool = True) -> Iterator[Any]:
    def content(obj):
        if not isinstance(obj, dict):
            return
        for media in _values(obj.get("content")):
            if isinstance(media, dict):
                yield media.get("schema")
                for encoding in _values(media.get("encoding")):
                    if isinstance(encoding, dict):
                        for header in _values(encoding.get("headers")):
                            yield from parameter(header)

    def parameter(obj):
        if isinstance(obj, dict):
            yield obj.get("schema")
            yield from content(obj)

    def response(obj):
        if isinstance(obj, dict):
            yield from content(obj)
            for header in _values(obj.get("headers")):
                yield from parameter(header)

    def callback(obj):
        if isinstance(obj, dict):
            for key, item in obj.items():
                if key != "$ref" and not key.startswith("x-"):
                    yield from path_item(item)

    def operation(obj):
        if not isinstance(obj, dict):
            return
        for param in obj.get("parameters", []):
            yield from parameter(param)
        yield from content(obj.get("requestBody"))
        for value in _values(obj.get("responses")):
            yield from response(value)
        for value in _values(obj.get("callbacks")):
            yield from callback(value)

    def path_item(obj):
        if not isinstance(obj, dict):
            return
        for param in obj.get("parameters", []):
            yield from parameter(param)
        for key in _HTTP_METHODS:
            yield from operation(obj.get(key))
        for value in _values(obj.get("additionalOperations")):
            yield from operation(value)

    for path, item in spec.get("paths", {}).items():
        if path.startswith("/"):
            yield from path_item(item)
    for item in _values(spec.get("webhooks")):
        yield from path_item(item)
    components = spec.get("components", {})
    if include_models:
        yield from _values(components.get("schemas"))
    for key in ("parameters", "headers"):
        for value in _values(components.get(key)):
            yield from parameter(value)
    for value in _values(components.get("requestBodies")):
        yield from content(value)
    for value in _values(components.get("responses")):
        yield from response(value)
    for value in _values(components.get("callbacks")):
        yield from callback(value)
    for value in _values(components.get("pathItems")):
        yield from path_item(value)


def _model_references(schema: Any, model_names: Collection[str]) -> set[str]:
    names = set()
    prefix = "#/components/schemas/"
    for node in _schema_nodes(schema):
        refs = [node.get(key) for key in ("$ref", "$dynamicRef", "$recursiveRef")]
        discriminator = node.get("discriminator", {})
        if isinstance(discriminator, dict):
            for value in _values(discriminator.get("mapping")):
                if isinstance(value, str) and value in model_names:
                    names.add(value)
                refs.append(value)
        for ref in refs:
            if isinstance(ref, str):
                ref = unquote(ref)
            if isinstance(ref, str) and ref.startswith(prefix):
                names.add(ref[len(prefix) :].split("/")[0].replace("~1", "/").replace("~0", "~"))
    return names


def remove_deprecated_fields(spec: dict) -> dict:
    """Delete deprecated properties, clean required lists, and prune unused deprecated models."""
    for root in _document_schemas(spec):
        for node in _schema_nodes(root):
            properties = node.get("properties")
            if not isinstance(properties, dict):
                continue
            removed = {
                name
                for name, prop in properties.items()
                if isinstance(prop, dict) and prop.get("deprecated") is True
            }
            for name in removed:
                del properties[name]
            if removed and isinstance(node.get("required"), list):
                required = [name for name in node["required"] if name not in removed]
                if required:
                    node["required"] = required
                else:
                    del node["required"]

    models = spec.get("components", {}).get("schemas", {})
    deprecated = {
        name
        for name, schema in models.items()
        if isinstance(schema, dict) and schema.get("deprecated") is True
    }
    # All nondeprecated models are public generation roots. Also retain models
    # used by inline operation/component schemas, following transitive references.
    pending = list(models.keys() - deprecated)
    for root in _document_schemas(spec, include_models=False):
        pending.extend(_model_references(root, models))
    live = set()
    while pending:
        name = pending.pop()
        if name not in live and name in models:
            live.add(name)
            pending.extend(_model_references(models[name], models))
    for name in deprecated - live:
        del models[name]
    return spec
