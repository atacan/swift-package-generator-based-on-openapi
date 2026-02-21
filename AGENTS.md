## Introduction

Original plan to implement this project:

This project is a Python CLI utility managed by `uv` designed to bootstrap, sanitize, and maintain Swift Packages derived from OpenAPI specifications. Its core logic acts as a middleware pipeline that ingests a raw `original_openapi` file (JSON or YAML), recursively traverses the schema to apply specific structural fixes—such as resolving `anyOf` nullability issues, converting `const` to `enum`, and normalizing OpenAPI 3.0/3.1 differences—and outputs a clean specification compatible with Apple's strict `swift-openapi-generator`.

Beyond schema sanitization, the tool orchestrates the Swift Package Manager infrastructure. It scaffolds a modular directory structure (separating `Client` and `Types` targets), renders essential configuration files (`Package.swift`, `Makefile`, `openapi-generator-config.yaml`) using Jinja2 templates, and executes the necessary shell commands to generate the Swift code. The architecture is idempotent, allowing developers to re-run the tool to update API specifications without overwriting manual project configurations or overlay files.

### Transformers

The transformations are inside the "src/bootstrapper/transformers" directory and each of them have dedicated tests.
The overlay transformation should always be the last one to ensure that all other transformations are applied before the overlay is applied. 
When you add a new transformer, make sure to first add a test for it in the "tests/bootstrapper/transformers" directory, and move the overlay transformation to be the last one.

## Code Verification

**CRITICAL**: After making code changes, you MUST verify that the code works and "compiles" before marking tasks as complete.

### Verification Checklist

1. **Syntax Check**: Run the code to ensure no syntax errors
   ```bash
   uv run python -m bootstrapper.main --help
   ```

2. **Run Tests**: Execute the test suite
   ```bash
   uv run pytest
   ```

   To include slow tests (e.g., swift build verification):
   ```bash
   uv run pytest -m ""
   ```

3. **Lint & Format**: Check code quality
   ```bash
   uv run ruff check .
   uv run ruff format --check .
   ```

4. **Type Checking**: If mypy is configured, run type checks

5. **Integration Test**: For CLI changes, test the actual command
   ```bash
   uv run swift-bootstrapper --help
   ```

### When to Verify

- ✅ Before marking bd issues as complete
- ✅ After implementing any new feature
- ✅ After fixing bugs
- ✅ Before creating pull requests
- ❌ Do NOT skip verification "to save time"

### Handling Failures

If verification fails:
1. Keep the bd issue as `in_progress`
2. Fix the errors
3. Re-run verification
4. Only mark complete when ALL checks pass

## Project Overview

A Python CLI utility (managed by `uv`) that bootstraps Swift Packages from OpenAPI specifications. It sanitizes OpenAPI specs for compatibility with Apple's `swift-openapi-generator` and scaffolds a complete Swift Package Manager project.

**CLI Entry Point:** `swift-bootstrapper` (or `uv run swift-bootstrapper`)

## Architecture

```
src/bootstrapper/
├── main.py                    # CLI entry point (Typer-based)
├── config.py                  # Configuration constants
├── core/
│   ├── loader.py              # Load OpenAPI specs (JSON/YAML)
│   └── writer.py              # Write OpenAPI specs
├── generators/
│   ├── swift.py               # Package structure & swift-openapi-generator runner
│   ├── templates.py           # Jinja2 template rendering for config files
│   └── security.py            # AuthenticationMiddleware generation
├── transformers/
│   ├── manager.py             # Orchestrates transformation pipeline
│   ├── ops_base.py            # Base utilities for transformers
│   ├── op1_null_anyof.py      # Remove null from anyOf arrays
│   ├── op2_const_enum.py      # Convert const to enum
│   ├── op3_float_to_number.py # Convert float to number type
│   ├── op4_nullable.py        # Convert nullable (3.0 → 3.1)
│   ├── op5_format_fix.py      # Fix byte format issues
│   ├── op6_clean_required.py  # Clean required arrays
│   └── op7_overlay.py         # Apply OpenAPI overlay (always last)
└── resources/                 # Jinja2 templates (*.j2)
```

## Key Flows

### 1. Bootstrap Command Flow (`main.py:bootstrap()`)

```
1. Find original_openapi file (YAML/JSON)
2. Derive project name (from folder or --name flag)
3. Transform spec → openapi.yaml/json
4. Create Swift package structure (Sources/, Tests/)
5. Generate config files (Makefile, Package.swift, etc.)
6. Apply overlay (if exists with actions)
7. Generate AuthenticationMiddleware (if security schemes present)
8. Run swift-openapi-generator
```

### 2. Transformation Pipeline (`transformers/manager.py`)

Order matters - overlay is always last:
```python
spec = remove_null_anyof(spec)      # Op1
spec = convert_const_to_enum(spec)   # Op2
spec = convert_float_to_number(spec) # Op3
spec = convert_nullable_to_3_1(spec) # Op4
spec = fix_byte_format(spec)         # Op5
spec = clean_required_arrays(spec)   # Op6
# Op7 (overlay) applied separately in main.py after config generation
```

### 3. Package Naming (`main.py:derive_project_name()`)

```python
# Input: folder name → Output: PascalCase name
"my-api-wrapper" → "MyApiWrapper"
"AssemblyAI"     → "AssemblyAI"  # preserves existing uppercase
"my_api"         → "MyApi"
```

Priority: CLI `--name` flag > derived from folder name

## Generated Swift Package Structure

```
{target_dir}/
├── Package.swift
├── openapi.yaml              # Transformed (auto-generated, don't edit)
├── original_openapi.yaml     # Source (user-provided)
├── openapi-overlay.yaml      # Manual fixes (user-editable)
├── openapi-generator-config-types.yaml
├── openapi-generator-config-client.yaml
├── Makefile
├── .swift-format
├── .env.example
├── .gitignore
├── Sources/
│   ├── {ProjectName}Types/
│   │   ├── {ProjectName}Types.swift
│   │   ├── AuthenticationMiddleware.swift  # If security schemes exist
│   │   └── GeneratedSources/               # swift-openapi-generator output
│   └── {ProjectName}/
│       ├── {ProjectName}.swift
│       └── GeneratedSources/
└── Tests/
    └── {ProjectName}Tests/
        └── {ProjectName}Tests.swift
```

## Jinja2 Templates

Located in `src/bootstrapper/resources/`:
- `Package.swift.j2` - Swift Package manifest
- `Makefile.j2` - Build automation
- `openapi-generator-config-*.yaml.j2` - Generator configs
- `AuthenticationMiddleware.swift.j2` - Auth middleware
- `ClientFile.swift.j2`, `TypesFile.swift.j2`, `TestsFile.swift.j2` - Initial Swift files
- `overlay.yaml.j2`, `overlay.json.j2` - Overlay templates

**Template Context Variables:**
- `{{ project_name }}` - The Swift package name

## Key Design Patterns

### Idempotent "Write If Not Exists"

Files are only created if they don't exist. This allows:
- Re-running bootstrap to update generated code
- Preserving user edits to Package.swift, Makefile, etc.
- Safe updates when OpenAPI spec changes

### Overlay System

Users can add manual OpenAPI fixes via `openapi-overlay.yaml`:
```yaml
overlay: 1.0.0
actions:
  - target: "$.paths./api/v1/users.get.responses.200"
    update:
      description: "Fixed description"
```

Applied after all automated transformations.

## CLI Usage

```bash
# Basic usage (derives name from folder)
swift-bootstrapper /path/to/api-project

# With custom name
swift-bootstrapper /path/to/api-project --name MyCustomAPI

# Current directory
swift-bootstrapper .
```

## Development Commands

```bash
# Run CLI
uv run swift-bootstrapper --help

# Run tests
uv run pytest                    # Fast tests only
uv run pytest -m ""              # All tests including slow

# Lint & format
uv run ruff check .
uv run ruff format --check .

# Type checking (if configured)
uv run mypy src/
```

## Tests Structure

```
tests/
├── test_main.py                 # CLI and derive_project_name tests
├── test_integration.py          # Full bootstrap flow tests
└── bootstrapper/transformers/   # Individual transformer tests
    ├── test_op1_null_anyof.py
    ├── test_op2_const_enum.py
    └── ...
```

## Adding New Transformers

1. Create `src/bootstrapper/transformers/opN_name.py`
2. Add test in `tests/bootstrapper/transformers/test_opN_name.py`
3. Import and call in `transformers/manager.py`
4. **Important:** Overlay (op7) must remain last in the pipeline
