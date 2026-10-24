"""Infer wire-value mappings for provably disjoint referenced object variants.

Mappings use each union branch's original reference. Only required discriminator
properties constrained to finite, disjoint string values are eligible. Local
references, their siblings, and allOf are conjunctions, so their constraints must
be intersected. Unresolved, cyclic, inline, ambiguous, or conflicting variants
leave the union unchanged; explicit mappings are never overwritten.
"""

from typing import Any
from urllib.parse import unquote

from bootstrapper.transformers.ops_base import recursive_walk

_JSON_TYPES = frozenset({"null", "boolean", "object", "array", "number", "integer", "string"})
_UNSUPPORTED_COMPOSITIONS = {"anyOf", "oneOf", "not", "if", "then", "else"}


def _resolve_local_ref(spec: dict, ref: Any) -> Any:
    if not isinstance(ref, str) or not ref.startswith("#/"):
        return None
    target: Any = spec
    for token in unquote(ref[2:]).split("/"):
        # Only ~0 and ~1 are valid JSON Pointer escapes.
        if "~" in token.replace("~1", "").replace("~0", ""):
            return None
        token = token.replace("~1", "/").replace("~0", "~")
        if isinstance(target, dict):
            target = target.get(token)
        elif isinstance(target, list):
            if (
                not token.isascii()
                or not token.isdecimal()
                or (token != "0" and token.startswith("0"))
                or len(token) > len(str(len(target)))
            ):
                return None
            index = int(token)
            target = target[index] if index < len(target) else None
        else:
            return None
    return target


def _conjuncts(spec: dict, schema: Any, refs: frozenset[str] = frozenset()) -> list[dict] | None:
    """Flatten AND constraints without discarding $ref siblings or following cycles."""
    if not isinstance(schema, dict) or _UNSUPPORTED_COMPOSITIONS.intersection(schema):
        return None
    result = [schema]
    if "$ref" in schema:
        ref = schema["$ref"]
        if not isinstance(ref, str) or ref in refs:
            return None
        target = _conjuncts(spec, _resolve_local_ref(spec, ref), refs | {ref})
        if target is None:
            return None
        result.extend(target)
    if "allOf" in schema:
        all_of = schema["allOf"]
        if not isinstance(all_of, list) or not all_of:
            return None
        for branch in all_of:
            constraints = _conjuncts(spec, branch, refs)
            if constraints is None:
                return None
            result.extend(constraints)
    return result


def _allowed_types(schema: dict) -> frozenset[str] | None:
    value = schema.get("type")
    if value is None:
        return _JSON_TYPES
    types = [value] if isinstance(value, str) else value
    if (
        not isinstance(types, list)
        or not types
        or not all(isinstance(item, str) and item in _JSON_TYPES for item in types)
    ):
        return None
    return frozenset(types)


def _tag_values(spec: dict, schema: Any) -> tuple[frozenset[str] | None, bool]:
    """Return intersected finite values, or an unconstrained tag; flag invalid proofs."""
    constraints = _conjuncts(spec, schema)
    if constraints is None:
        return None, False
    values: frozenset[str] | None = None
    types = _JSON_TYPES
    for constraint in constraints:
        allowed = _allowed_types(constraint)
        if allowed is None:
            return None, False
        types &= allowed
        for keyword in ("enum", "const"):
            if keyword not in constraint:
                continue
            candidates = constraint[keyword] if keyword == "enum" else [constraint[keyword]]
            if (
                not isinstance(candidates, list)
                or not candidates
                or not all(isinstance(value, str) for value in candidates)
            ):
                return None, False
            finite = frozenset(candidates)
            values = finite if values is None else values & finite
    if not types or (values is not None and (not values or "string" not in types)):
        return None, False
    return values, True


def _branch_values(spec: dict, branch: dict, property_name: str) -> frozenset[str] | None:
    constraints = _conjuncts(spec, branch)
    if constraints is None:
        return None
    types = _JSON_TYPES
    required = False
    tag_constraints: list[dict] = []
    for constraint in constraints:
        allowed = _allowed_types(constraint)
        if allowed is None:
            return None
        types &= allowed
        required_names = constraint.get("required", [])
        if not isinstance(required_names, list) or not all(
            isinstance(name, str) for name in required_names
        ):
            return None
        required |= property_name in required_names
        properties = constraint.get("properties", {})
        if not isinstance(properties, dict):
            return None
        if property_name in properties:
            tag_constraints.append(properties[property_name])
    if types != {"object"} or not required or not tag_constraints:
        return None
    # Intersect the property's type and values across every object conjunct too.
    values, valid = _tag_values(spec, {"allOf": tag_constraints})
    return values if valid else None


def infer_discriminator_mappings(spec: dict) -> dict:
    """Complete missing mappings when every branch proves an unambiguous wire tag."""

    def transform(data: Any, parent: Any, key: Any) -> Any:
        if not isinstance(data, dict) or ("oneOf" in data and "anyOf" in data):
            return data
        branches = data.get("oneOf", data.get("anyOf"))
        discriminator = data.get("discriminator")
        if not isinstance(branches, list) or len(branches) < 2:
            return data
        if not isinstance(discriminator, dict):
            return data
        property_name = discriminator.get("propertyName")
        if not isinstance(property_name, str):
            return data
        existing = discriminator.get("mapping", {})
        if not isinstance(existing, dict) or not all(
            isinstance(tag, str) and isinstance(ref, str) for tag, ref in existing.items()
        ):
            return data

        inferred: dict[str, str] = {}
        for branch in branches:
            if not isinstance(branch, dict) or not isinstance(branch.get("$ref"), str):
                return data
            values = _branch_values(spec, branch, property_name)
            if not values or inferred.keys() & values:
                return data
            ref = branch["$ref"]
            for value in sorted(values):
                if value in existing and existing[value] != ref:
                    return data
                inferred[value] = ref
        discriminator["mapping"] = {**existing, **inferred}
        return data

    return recursive_walk(spec, transform)
