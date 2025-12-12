---
name: beads
description: Beads is a lightweight memory system for coding agents, using a graph-based issue tracker. Four kinds of dependencies work to chain your issues together like beads, making them easy for agents to follow for long distances, and reliably perform complex task streams in the right order.
---

# Beads

For quick start, see [Quick Start](quickstart.md).

## Usage

### Health Check

Check installation health: `bd doctor` validates your `.beads/` setup, database version, ID format, and CLI version. Provides actionable fixes for any issues found.

### Creating Issues

```bash
bd create "Fix bug" -d "Description" -p 1 -t bug
bd create "Add feature" --description "Long description" --priority 2 --type feature
bd create "Task" -l "backend,urgent" --assignee alice

# Get JSON output for programmatic use
bd create "Fix bug" -d "Description" --json

# Create from templates (built-in: epic, bug, feature)
bd create --from-template epic "Q4 Platform Improvements"
bd create --from-template bug "Auth token validation fails"
bd create --from-template feature "Add OAuth support"

# Override template defaults
bd create --from-template bug "Critical issue" -p 0  # Override priority

# Create multiple issues from a markdown file
bd create -f feature-plan.md
```

Options:
- `-f, --file` - Create multiple issues from markdown file
- `--from-template` - Use template (epic, bug, feature, or custom)
- `-d, --description` - Issue description
- `-p, --priority` - Priority (0-4, 0=highest, default=2)
- `-t, --type` - Type (bug|feature|task|epic|chore, default=task)
- `-a, --assignee` - Assign to user
- `-l, --labels` - Comma-separated labels
- `--id` - Explicit issue ID (e.g., `worker1-100` for ID space partitioning)
- `--json` - Output in JSON format

See `bd template list` for available templates and `bd help template` for managing custom templates.

### Viewing Issues

```bash
bd info                                    # Show database path and daemon status
bd show bd-a1b2                            # Show full details
bd list                                    # List all issues
bd list --status open                      # Filter by status
bd list --priority 1                       # Filter by priority
bd list --assignee alice                   # Filter by assignee
bd list --label=backend,urgent             # Filter by labels (AND)
bd list --label-any=frontend,backend       # Filter by labels (OR)

# Advanced filters
bd list --title-contains "auth"            # Search title
bd list --desc-contains "implement"        # Search description
bd list --notes-contains "TODO"            # Search notes
bd list --id bd-123,bd-456                 # Specific IDs (comma-separated)

# Date range filters (YYYY-MM-DD or RFC3339)
bd list --created-after 2024-01-01         # Created after date
bd list --created-before 2024-12-31        # Created before date
bd list --updated-after 2024-06-01         # Updated after date
bd list --updated-before 2024-12-31        # Updated before date
bd list --closed-after 2024-01-01          # Closed after date
bd list --closed-before 2024-12-31         # Closed before date

# Empty/null checks
bd list --empty-description                # Issues with no description
bd list --no-assignee                      # Unassigned issues
bd list --no-labels                        # Issues with no labels

# Priority ranges
bd list --priority-min 0 --priority-max 1  # P0 and P1 only
bd list --priority-min 2                   # P2 and below

# Combine multiple filters
bd list --status open --priority 1 --label-any urgent,critical --no-assignee

# JSON output for agents
bd info --json
bd list --json
bd show bd-a1b2 --json
```

### Updating Issues

```bash
bd update bd-a1b2 --status in_progress
bd update bd-a1b2 --priority 2
bd update bd-a1b2 --assignee bob
bd close bd-a1b2 --reason "Completed"
bd close bd-a1b2 bd-f14c bd-3e7a   # Close multiple

# JSON output
bd update bd-a1b2 --status in_progress --json
```

### Dependencies

```bash
# Add dependency (bd-f14c depends on bd-a1b2)
bd dep add bd-f14c bd-a1b2
bd dep add bd-3e7a bd-a1b2 --type blocks

# Remove dependency
bd dep remove bd-f14c bd-a1b2

# Show dependency tree
bd dep tree bd-f14c

# Detect cycles
bd dep cycles
```

#### Dependency Types

- **blocks**: Hard blocker (default) - issue cannot start until blocker is resolved
- **related**: Soft relationship - issues are connected but not blocking
- **parent-child**: Hierarchical relationship (child depends on parent)
- **discovered-from**: Issue discovered during work on another issue (automatically inherits parent's `source_repo`)

Only `blocks` dependencies affect ready work detection.

> **Note:** Issues created with `discovered-from` dependencies automatically inherit the parent's `source_repo` field, ensuring discovered work stays in the same repository as the parent task.

### Finding Work

```bash
# Show ready work (no blockers)
bd ready
bd ready --limit 20
bd ready --priority 1
bd ready --assignee alice

# Sort policies (hybrid is default)
bd ready --sort priority    # Strict priority order (P0, P1, P2, P3)
bd ready --sort oldest      # Oldest issues first (backlog clearing)
bd ready --sort hybrid      # Recent by priority, old by age (default)

# Show blocked issues
bd blocked

# Statistics
bd stats

# JSON output for agents
bd ready --json
```

### Labels

Add flexible metadata to issues for filtering and organization:

```bash
# Add labels during creation
bd create "Fix auth bug" -t bug -p 1 -l auth,backend,urgent

# Add/remove labels
bd label add bd-a1b2 security
bd label remove bd-a1b2 urgent

# List labels
bd label list bd-a1b2            # Labels on one issue
bd label list-all                # All labels with counts

# Filter by labels
bd list --label backend,auth     # AND: must have ALL labels
bd list --label-any frontend,ui  # OR: must have AT LEAST ONE
```

**See [docs/LABELS.md](docs/LABELS.md) for complete label documentation and best practices.**

### Deleting Issues

```bash
# Single issue deletion (preview mode)
bd delete bd-a1b2

# Force single deletion
bd delete bd-a1b2 --force

# Batch deletion
bd delete bd-a1b2 bd-f14c bd-3e7a --force

# Delete from file (one ID per line)
bd delete --from-file deletions.txt --force

# Cascade deletion (recursively delete dependents)
bd delete bd-a1b2 --cascade --force
```

The delete operation removes all dependency links, updates text references to `[deleted:ID]`, and removes the issue from database and JSONL.
