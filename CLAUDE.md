## Introduction

Original plan to implement this project:

@history/initial_plan.md

Ways of working:

@AGENTS.md

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
