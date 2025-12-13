# Swift OpenAPI Bootstrapper

Python CLI tool that generates and maintains Swift packages from OpenAPI specifications. Sanitizes imperfect OpenAPI files and scaffolds Swift Package Manager infrastructure.

## Installation

```bash
# Install globally with uv
uv tool install git+https://github.com/atacan/swift-package-generator-based-on-openapi.git

# Verify installation
swift-bootstrapper --help
```

## First-Time Setup

**1. Prepare your project folder**
```bash
mkdir MyAPIWrapper
cd MyAPIWrapper
```

**2. Add your OpenAPI file**
- Name it `original_openapi.yaml` or `original_openapi.json`
- Place it in the project root

**3. Run the bootstrapper**
```bash
swift-bootstrapper .
```

**What gets created:**
- `openapi.yaml` - Sanitized version (auto-generated, don't edit)
- `openapi-overlay.yaml` - For manual schema fixes (edit this)
- `Package.swift` - Swift package definition with dependencies
- `Makefile` - Shortcuts for common tasks
- `.env` - Configuration file for API keys
- `Sources/` - Generated Swift code structure

## Updating OpenAPI Spec

When the API provider releases a new version:

**1. Replace the original file**
```bash
cp ~/Downloads/new_api_spec.yaml ./original_openapi.yaml
```

**2. Re-run the bootstrapper**
```bash
swift-bootstrapper .
```

The tool will:
- Re-apply all transformations
- Preserve your overlay fixes
- Regenerate Swift code
- Keep your manual code intact

## Using Overlay Files

When you need to fix schema issues manually:

**1. Edit `openapi-overlay.yaml`**
```yaml
overlay: "1.0.0"
actions:
  - target: "$.components.schemas.User"
    update:
      required: ["user_id"]
```

**2. Re-run the bootstrapper**
```bash
swift-bootstrapper .
```

The overlay is applied **after** automated transformations.

## Common Workflows

### Update everything after changing files
```bash
swift-bootstrapper .
```

### Use Makefile shortcuts (if generated)
```bash
make generate  # Regenerate Swift code
```

### Check what the tool fixed
Compare `original_openapi.yaml` with `openapi.yaml` to see applied transformations.

## What Gets Fixed Automatically

1. **Nullable handling**: Converts `nullable: true` to OpenAPI 3.1 style
2. **anyOf simplification**: Removes redundant `type: null` entries
3. **const to enum**: Converts `const` to `enum` arrays
4. **Format fixes**: Updates `format: byte` to `contentEncoding: base64`
5. **Required cleanup**: Removes invalid entries from `required` arrays

## File Roles

| File | Purpose | Edit? |
|------|---------|-------|
| `original_openapi.yaml` | Source of truth from API provider | ✓ Replace when updated |
| `openapi.yaml` | Sanitized version for Swift tools | ✗ Auto-generated |
| `openapi-overlay.yaml` | Manual schema corrections | ✓ Add your fixes here |
| `Package.swift` | Swift package configuration | ⚠️ Managed by tool |
| `Sources/` | Swift code (generated + manual) | Mixed |

## Development

```bash
# Install dependencies
uv sync

# Run tests
uv run pytest

# Lint
uv run ruff check .

# Format
uv run ruff format .
```

## Requirements

- Python 3.12+
- uv package manager
- Swift 5.9+ (for generated packages)
