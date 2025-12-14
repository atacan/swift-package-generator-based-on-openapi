## Introduction

Original plan to implement this project:

This project is a Python CLI utility managed by `uv` designed to bootstrap, sanitize, and maintain Swift Packages derived from OpenAPI specifications. Its core logic acts as a middleware pipeline that ingests a raw `original_openapi` file (JSON or YAML), recursively traverses the schema to apply specific structural fixes—such as resolving `anyOf` nullability issues, converting `const` to `enum`, and normalizing OpenAPI 3.0/3.1 differences—and outputs a clean specification compatible with Apple's strict `swift-openapi-generator`.

Beyond schema sanitization, the tool orchestrates the Swift Package Manager infrastructure. It scaffolds a modular directory structure (separating `Client` and `Types` targets), renders essential configuration files (`Package.swift`, `Makefile`, `openapi-generator-config.yaml`) using Jinja2 templates, and executes the necessary shell commands to generate the Swift code. The architecture is idempotent, allowing developers to re-run the tool to update API specifications without overwriting manual project configurations or overlay files.

## Issue Tracking with bd (beads)

**IMPORTANT**: This project uses **bd (beads)** for ALL issue tracking. Do NOT use markdown TODOs, task lists, or other tracking methods.

### Why bd?

- Dependency-aware: Track blockers and relationships between issues
- Git-friendly: Auto-syncs to JSONL for version control
- Agent-optimized: JSON output, ready work detection, discovered-from links
- Prevents duplicate tracking systems and confusion

### Workflow for AI Agents

1. **Check ready work**: `bd ready` shows unblocked issues
2. **Claim your task**: `bd update <id> --status in_progress`
3. **Work on it**: Implement, test, document
4. **Discover new work?** Create linked issue:
   - `bd create "Found bug" -p 1 --deps discovered-from:<parent-id>`
5. **Complete**: `bd close <id> --reason "Done"`
6. **Commit together**: Always commit the `.beads/issues.jsonl` file together with the code changes so issue state stays in sync with code state

### Auto-Sync

bd automatically syncs with git:
- Exports to `.beads/issues.jsonl` after changes (5s debounce)
- Imports from JSONL when newer (e.g., after `git pull`)
- No manual export/import needed!

### Important Rules

- ✅ Use bd for ALL task tracking
- ✅ Always use `--json` flag for programmatic use
- ✅ Link discovered work with `discovered-from` dependencies
- ✅ Check `bd ready` before asking "what should I work on?"
- ✅ Store AI planning docs in `history/` directory
- ❌ Do NOT create markdown TODO lists
- ❌ Do NOT use external issue trackers
- ❌ Do NOT duplicate tracking systems
- ❌ Do NOT clutter repo root with planning documents

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
