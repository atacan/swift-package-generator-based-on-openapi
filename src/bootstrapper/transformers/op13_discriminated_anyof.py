"""Represent disjoint tagged anyOf schemas as oneOf for Swift enum generation.

Swift OpenAPI Generator only dispatches on a discriminator for oneOf. Converting
anyOf is equivalent only when every branch requires the discriminator property
and its allowed string values are disjoint. Branches must be explicit objects;
otherwise properties and required do not constrain non-object JSON values.
Unproven unions are left unchanged.
"""

from typing import Any

from bootstrapper.transformers.ops_base import recursive_walk


def normalize_discriminated_anyof(spec: dict) -> dict:
    schemas = spec.get("components", {}).get("schemas", {})

    def transform(data: Any, parent: Any, key: Any) -> Any:
        if not isinstance(data, dict) or "oneOf" in data:
            return data
        branches = data.get("anyOf")
        discriminator = data.get("discriminator")
        if not isinstance(branches, list) or len(branches) < 2:
            return data
        if not isinstance(discriminator, dict):
            return data
        property_name = discriminator.get("propertyName")
        if not isinstance(property_name, str):
            return data

        seen: set[str] = set()
        for branch in branches:
            ref = branch.get("$ref") if isinstance(branch, dict) else None
            prefix = "#/components/schemas/"
            if not isinstance(ref, str) or not ref.startswith(prefix):
                return data
            name = ref[len(prefix) :].replace("~1", "/").replace("~0", "~")
            target = schemas.get(name, {})
            if not isinstance(target, dict) or target.get("type") != "object":
                return data
            if property_name not in target.get("required", []):
                return data
            tag = target.get("properties", {}).get(property_name, {})
            values = tag.get("enum") if isinstance(tag, dict) else None
            if (
                not isinstance(values, list)
                or not values
                or not all(isinstance(v, str) for v in values)
            ):
                return data
            if seen.intersection(values):
                return data
            seen.update(values)

        data["oneOf"] = data.pop("anyOf")
        return data

    return recursive_walk(spec, transform)
