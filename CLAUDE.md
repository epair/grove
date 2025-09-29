# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Grove is a Git Worktree and Tmux Session Manager - a modern terminal interface for managing Git worktrees and their associated tmux sessions in a unified, interactive environment.

#### Key functionality:

**Visual worktree browser:** Displays all Git worktrees in a repository with a split-screen layout (1/3 list view, 2/3 details view) ✅
**Tmux integration:** Shows active tmux session indicators (● for active, ○ for inactive) in the sidebar ✅
**Worktree management:** Create new worktrees from modal form, delete worktrees with confirmation dialog ✅
**Metadata system:** Maintains and displays worktree-specific documentation (descriptions, PR info, notes) in a .grove/metadata/ directory structure as formatted markdown ✅
**Interactive navigation:** Keyboard-driven interface similar to lazygit/htop for efficient workflow management

The tool essentially bridges the gap between Git worktree management and tmux session organization, making it easier to switch between different branches/features while maintaining separate development environments. It pulls all data dynamically from Git and tmux CLI commands rather than using a database, keeping the system lightweight and in sync with the actual state of your repositories and sessions.

## Architecture

- **Main Application**: `app.py` - Single-file Textual application using Python 3.13+
- **Styling**: `app.tcss` - Textual CSS for UI styling
- **Testing**: `tests/test_integration.py` - Integration tests for TUI functionality
- **Test Data**: `tests/example_repo/` - Bare git repository structure for testing
- **Dependencies**: Requires `textual` library (currently v6.1.0) and `pytest` for testing

### Key Components

- `GroveApp`: Main Textual app class using tokyo-night theme
- `Sidebar`: ListView widget that displays worktree directories with tmux session indicators
- `WorktreeFormScreen`: Modal form for creating new worktrees (branch name and path)
- `ConfirmDeleteScreen`: Modal confirmation dialog for worktree deletion
- `is_bare_git_repository()`: Validates the environment is a bare git repo
- `get_worktree_directories()`: Discovers directories at the same level as `.bare`
- `get_active_tmux_sessions()`: Retrieves active tmux session names
- `get_worktree_metadata()`: Reads metadata files for a worktree
- `delete_worktree()`: Removes a worktree using git commands

## Development Commands

**Run the application:**
```bash
python app.py  # Must be run from a bare git repository directory
```

**Syntax check:**
```bash
python -m py_compile app.py
```

**Run tests:**
```bash
python -m pytest tests/ -v
```

**Run integration tests only:**
```bash
python -m pytest tests/test_integration.py -v
```

**Type checking:**
```bash
mypy app.py tests/
```

**Note:** Always use `python -m pytest` instead of `pytest` directly to ensure proper Python path setup for module imports. The codebase uses comprehensive type hints throughout - all functions should include return type annotations and parameter types where applicable.

## Requirements

- The application must be run from a directory containing a `.bare` subdirectory (bare git repository setup)
- Python 3.13+ with `textual` library installed

## Key Behavior

- Application exits with error if not run from a bare git repository
- Discovers and lists directories at the same level as `.bare` directory with tmux session indicators
- Excludes hidden directories (starting with `.`) from the sidebar
- Displays worktree metadata (description, PR info, notes) as formatted markdown in the main body
- Creates new worktrees via modal form (Ctrl+N)
- Deletes selected worktree with confirmation (Ctrl+D)
- Supports repositories with the following directory structure:

repository/
├── .git
├── .bare/
├── .grove/
│   ├── .setup
│   └── metadata/
│       ├── feature-one/
│       │   ├── description.md
│       │   ├── pr.md
│       │   └── notes.md
│       └── bugfix-01/
│           ├── description.md
│           ├── pr.md
│           └── notes.md
├── feature-one/
└── bugfix-01/

## Theme Colors

- Application uses tokyo-night theme (dark mode removed for consistency)
- The following Textual CSS variables are available to keep theme color usage consistent:
$primary	The primary color, can be considered the branding color. Typically used for titles, and backgrounds for strong emphasis.
$secondary	An alternative branding color, used for similar purposes as $primary, where an app needs to differentiate something from the primary color.
$foreground	The default text color, which should be legible on $background, $surface, and $panel.
$background	A color used for the background, where there is no content. Used as the default background color for screens.
$surface	The default background color of widgets, typically sitting on top of $background.
$panel	A color used to differentiate a part of the UI form the main content. Used sparingly in Textual itself.
$boost	A color with alpha that can be used to create layers on a background.
$warning	Indicates a warning. Typically used as a background color. $text-warning can be used for foreground.
$error	Indicates an error. Typically used as a background color. $text-error can be used for foreground.
$success	Used to indicate success. Typically used as a background color. $text-success can be used for foreground.
$accent	Used sparingly to draw attention. Typically contrasts with $primary and $secondary.

## Testing Infrastructure

The project includes comprehensive integration tests that validate the TUI functionality:

### Test Structure

- **Integration Tests**: `tests/test_integration.py` - Tests core TUI functionality including:
  - Bare git repository detection
  - Worktree directory discovery and listing
  - UI sidebar content validation
  - Hidden directory exclusion (`.bare`, `.git`, `.grove`)
  - App startup and error handling

- **Test Data**: `tests/example_repo/` - Complete bare git repository structure with:
  - `.bare/` directory (bare git repo)
  - `feature-one/` and `bugfix-01/` worktree directories
  - `.grove/metadata/` structure for testing metadata features

### Test Configuration

- **pytest.ini**: Configured for async test support and proper test discovery
- **Async Testing**: Uses Textual's built-in testing capabilities with `app.run_test()`
- **Fixtures**: Provides directory switching and test isolation

### Running Tests

All tests must be run with `python -m pytest` to ensure proper module import resolution. The test suite validates both the core functions (`is_bare_git_repository()`, `get_worktree_directories()`) and the full TUI interface integration.