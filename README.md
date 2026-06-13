# Swift OpenAPI Bootstrapper

Generate Swift Packages from OpenAPI specifications. Takes a raw OpenAPI file (YAML or JSON), applies fixes for compatibility with Apple's [swift-openapi-generator](https://github.com/apple/swift-openapi-generator), and scaffolds a complete Swift Package Manager project.

You can also use it as a transform-only OpenAPI fixer when you just want a sanitized spec written to an output path without creating a Swift package.

## Prerequisites

- [uv](https://docs.astral.sh/uv/) -- handles Python automatically, no manual Python install needed
- Swift 5.9+ toolchain (Xcode 15+ on macOS)

## Install

```bash
uv tool install git+https://github.com/atacan/swift-package-generator-based-on-openapi.git
```

This gives you the `swift-bootstrapper` command globally. Verify with:

```bash
swift-bootstrapper --help
```

To run without installing (one-off usage):

```bash
uvx --from git+https://github.com/atacan/swift-package-generator-based-on-openapi.git swift-bootstrapper --help
```

## Quick Start

### 1. Create a project folder and add your OpenAPI spec

```bash
mkdir MyAPIWrapper && cd MyAPIWrapper
```

Place your OpenAPI specification in this folder. It must be named one of:

- `original_openapi.yaml`
- `original_openapi.yml`
- `original_openapi.json`

### 2. Run the bootstrapper

```bash
swift-bootstrapper .
```

That's it. The tool will sanitize the spec, generate all config files, create the Swift package structure, and run `swift-openapi-generator`.

### 3. Install skills (interactive)

```bash
npx skills add atacan/agentic-coding-files
```

This command is interactive. Select the skills to install and choose the install location in the prompt.

### What gets created

```
MyAPIWrapper/
├── Package.swift                          # Swift package manifest
├── Makefile                               # Build shortcuts (make generate, make build, make test)
├── openapi.yaml                           # Sanitized spec (auto-generated, don't edit)
├── original_openapi.yaml                  # Your original spec (source of truth)
├── openapi-overlay.yaml                   # For manual schema fixes (edit this)
├── openapi-generator-config-types.yaml    # Generator config for Types target
├── openapi-generator-config-client.yaml   # Generator config for Client target
├── .swift-bootstrapper.yaml               # Package name configuration
├── .swift-format                          # Swift formatting rules
├── .env.example                           # Environment variable template
├── .gitignore
├── Sources/
│   ├── MyAPIWrapperTypes/
│   │   ├── MyAPIWrapperTypes.swift
│   │   ├── AuthenticationMiddleware.swift  # Only if spec has security schemes
│   │   └── GeneratedSources/              # swift-openapi-generator output
│   └── MyAPIWrapper/
│       ├── MyAPIWrapper.swift
│       └── GeneratedSources/
└── Tests/
    └── MyAPIWrapperTests/
        └── MyAPIWrapperTests.swift
```

## CLI Usage

The CLI has two modes:

- `bootstrap`: sanitize an OpenAPI spec and create/update a Swift package.
- `transform`: sanitize an OpenAPI spec file only.

For backwards compatibility, `swift-bootstrapper .` still runs `bootstrap`.

### Bootstrap a Swift package

```
swift-bootstrapper [TARGET_DIR] [--name NAME]
```

Equivalent explicit form:

```bash
swift-bootstrapper bootstrap [TARGET_DIR] [--name NAME]
```

| Argument / Option | Default | Description |
|---|---|---|
| `TARGET_DIR` | `.` (current directory) | Path to the folder containing `original_openapi.yaml` |
| `--name`, `-n` | auto-derived from folder name | Custom Swift package name |

### Examples

```bash
# Bootstrap from current directory, auto-derive package name
swift-bootstrapper .

# Bootstrap a specific folder
swift-bootstrapper /path/to/my-api-project

# Specify a custom package name
swift-bootstrapper . --name MyCustomAPI
swift-bootstrapper /path/to/project -n AssemblyAI
```

With `uvx`, run the same command without installing:

```bash
uvx --from git+https://github.com/atacan/swift-package-generator-based-on-openapi.git swift-bootstrapper bootstrap /path/to/my-api-project
uvx --from git+https://github.com/atacan/swift-package-generator-based-on-openapi.git swift-bootstrapper bootstrap /path/to/project --name AssemblyAI
```

### Transform an OpenAPI file only

Use `transform` when you only need the OpenAPI cleanup pipeline and do not want Swift package files, config files, generated sources, or Swift builds.

```bash
swift-bootstrapper transform INPUT_OPENAPI OUTPUT_OPENAPI
```

With an explicit overlay file:

```bash
swift-bootstrapper transform INPUT_OPENAPI OUTPUT_OPENAPI --overlay OVERLAY_FILE
```

| Argument / Option | Required | Description |
|---|---:|---|
| `INPUT_OPENAPI` | Yes | Source OpenAPI file (`.yaml`, `.yml`, or `.json`) |
| `OUTPUT_OPENAPI` | Yes | Destination for the transformed spec |
| `--overlay`, `-o` | No | Overlay file to apply after automated transformations |

Examples:

```bash
# Apply automated transformations only
swift-bootstrapper transform ./original_openapi.yaml ./openapi.yaml

# Apply automated transformations, then an overlay
swift-bootstrapper transform ./original_openapi.yaml ./openapi.yaml --overlay ./openapi-overlay.yaml

# JSON input is supported; output serialization follows the input file format
swift-bootstrapper transform ./original_openapi.json ./openapi.json
```

With `uvx`, run transform-only mode without installing:

```bash
# Apply automated transformations only
uvx --from git+https://github.com/atacan/swift-package-generator-based-on-openapi.git swift-bootstrapper transform ./original_openapi.yaml ./openapi.yaml

# Apply automated transformations, then an overlay
uvx --from git+https://github.com/atacan/swift-package-generator-based-on-openapi.git swift-bootstrapper transform ./original_openapi.yaml ./openapi.yaml --overlay ./openapi-overlay.yaml
```

The transform command applies the same automated spec fixes as bootstrap. Overlay application is optional, and when provided it always runs after automated transformations.

## Package Naming

The package name is resolved in this priority order:

1. **CLI `--name` flag** (highest priority)
2. **Existing `Package.swift`** (preserves current name if package already exists)
3. **`.swift-bootstrapper.yaml` config file**
4. **Auto-derived from folder name** (default)

Auto-derivation converts the folder name to PascalCase:

| Folder name | Package name |
|---|---|
| `my-api-client` | `MyApiClient` |
| `AssemblyAI` | `AssemblyAI` |
| `openai_wrapper` | `OpenaiWrapper` |

To set a persistent name without using the CLI flag every time, edit `.swift-bootstrapper.yaml`:

```yaml
package_name: MyCustomAPI
```

## Updating an OpenAPI Spec

When the API provider releases a new version, replace the original file and re-run:

```bash
cp ~/Downloads/updated_spec.yaml ./original_openapi.yaml
swift-bootstrapper .
```

The tool is idempotent:

- Re-applies all transformations to produce a fresh `openapi.yaml`
- Preserves existing files (`Package.swift`, `Makefile`, overlay, your Swift code)
- Regenerates only the `GeneratedSources/` directories

## Overlay Files

If the automated fixes aren't enough, add manual corrections in `openapi-overlay.yaml`. This file is applied **after** all automated transformations.

```yaml
overlay: "1.0.0"
actions:
  - target: "$.components.schemas.User"
    update:
      required: ["user_id"]
  - target: "$.paths./api/v1/users.get.responses.200"
    update:
      description: "Fixed response description"
```

Then re-run `swift-bootstrapper .` to apply.

## Automated Spec Fixes

These transformations are applied automatically to make specs compatible with `swift-openapi-generator`:

| Fix | What it does |
|---|---|
| Nullable handling | Converts OpenAPI 3.0 `nullable: true` to 3.1 style |
| anyOf simplification | Removes redundant `type: null` from `anyOf` arrays |
| const to enum | Converts `const` values to single-element `enum` arrays |
| Float to number | Normalizes `float` type to `number` |
| Format fixes | Converts `format: byte` to `contentEncoding: base64` |
| Required cleanup | Removes invalid entries from `required` arrays |
| Overlay | Applies manual fixes from `openapi-overlay.yaml` (always last) |

## Makefile Shortcuts

The generated `Makefile` provides these commands inside the Swift project:

```bash
make generate       # Regenerate Swift code from the OpenAPI spec
make build          # Build the Swift package
make test           # Run Swift tests
make format         # Run swift-format on Sources and Tests
make test-on-linux  # Run tests in a Docker container (swift:latest)
make merge-main     # Merge current branch into main and push
```

## File Reference

| File | Edit? | Purpose |
|---|---|---|
| `original_openapi.yaml` | Replace | Your source OpenAPI spec from the API provider |
| `openapi.yaml` | No | Auto-generated sanitized spec for Swift tools |
| `openapi-overlay.yaml` | Yes | Manual schema corrections applied on top |
| `.swift-bootstrapper.yaml` | Yes | Persists the package name across runs |
| `Package.swift` | Caution | Created once, then preserved on re-runs |
| `Makefile` | Caution | Created once, then preserved on re-runs |
| `Sources/*/GeneratedSources/` | No | Regenerated on every run |
| `Sources/*/*.swift` | Yes | Your custom Swift code, preserved on re-runs |

## Development

```bash
# Clone and install dependencies
git clone https://github.com/atacan/swift-package-generator-based-on-openapi.git
cd swift-package-generator-based-on-openapi
uv sync

# Run the CLI locally
uv run swift-bootstrapper --help

# Run tests
uv run pytest

# Run slow tests only, including real Swift package builds
uv run pytest -m slow

# Run all tests including slow integration tests and real Swift package builds
uv run pytest -m ""

# Lint and format
uv run ruff check .
uv run ruff format .
```
