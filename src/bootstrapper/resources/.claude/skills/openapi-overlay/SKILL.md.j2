---
name: openapi-overlay
description: Create and apply OpenAPI Overlay Specification documents. Use when working with OpenAPI/Swagger files and needing to apply repeatable transformations such as adding metadata, filtering endpoints, translating descriptions, or modifying API specifications without editing the source.
---

# OpenAPI Overlay Specification

Overlay Specification 1.0.0 defines a document format for applying repeatable transformations to OpenAPI descriptions.

## Structure

```yaml
overlay: 1.0.0
info:
  title: Overlay description
  version: 1.0.0
extends: ./target-openapi.yaml  # optional - identifies target document
actions:
  - target: <JSONPath expression>
    update: <object to merge>  # OR
    remove: true
```

## Action Object

| Field | Description |
|-------|-------------|
| `target` | **Required.** JSONPath expression selecting nodes (must resolve to objects or arrays, not primitives) |
| `update` | Object to merge with target (for objects) or entry to append (for arrays) |
| `remove` | Boolean. When `true`, removes target from its container. Default: `false` |

Actions are applied sequentially—each action operates on the result of previous actions.

## Critical: Update Behavior

**Common mistake:** Assuming `update` replaces the target. It does NOT.

- For **objects**: `update` recursively **merges** properties. Existing properties not in `update` remain unchanged.
- For **arrays**: `update` **appends** the value as a new element.

### To Replace a Value

Delete first, then recreate:

```yaml
actions:
  # Step 1: Remove existing
  - target: $.paths['/users'].get.description
    remove: true
  # Step 2: Add new value (target the parent object)
  - target: $.paths['/users'].get
    update:
      description: Completely new description
```

### To Replace an Entire Object

```yaml
actions:
  # Remove the object
  - target: $.paths['/old-endpoint']
    remove: true
  # Recreate with new content
  - target: $.paths
    update:
      '/old-endpoint':
        get:
          summary: Rebuilt from scratch
          responses:
            '200':
              description: OK
```

## Targeting Primitives

Cannot select primitive values directly. To update a string/number/boolean, target the **containing object**:

```yaml
# Wrong - target is a primitive
- target: $.info.title
  update: New Title

# Correct - target the containing object
- target: $.info
  update:
    title: New Title
```

## Common Patterns

### Add metadata to all GET operations

```yaml
- target: $.paths.*.get
  update:
    x-safe: true
```

### Remove internal endpoints

```yaml
- target: $.paths['/internal/*']
  remove: true
```

### Remove endpoints by extension

```yaml
- target: "$.paths.*[?(@.x-internal == true)]"
  remove: true
```

### Add parameter to all operations

```yaml
- target: $.paths.*.*.parameters
  update:
    name: X-Request-ID
    in: header
    required: false
```

### Filter by JSONPath predicate

```yaml
- target: $.paths.*.get.parameters[?@.name=='filter']
  update:
    schema:
      $ref: '#/components/schemas/FilterSchema'
```

## JSONPath Notes

- Use `$` for document root
- `*` matches any property name
- `[?@.prop == 'value']` filters by predicate
- Results must be objects or arrays (not primitives or null)

## References

- Spec: https://spec.openapis.org/overlay/v1.0.0.html
- JSONPath: RFC 9535
