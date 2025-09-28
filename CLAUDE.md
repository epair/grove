# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Grove is a Git Worktree and Tmux Session Manager - a modern terminal interface for managing Git worktrees and their associated tmux sessions in a unified, interactive environment.

#### Key functionality (not implemented yet):

**Visual worktree browser:** Displays all Git worktrees in a repository with a split-screen layout (1/3 list view, 2/3 details view)
**Tmux integration:** Shows active tmux session indicators and allows quick navigation to worktree-specific sessions
**Worktree management:** Create new worktrees (from new or existing branches), delete worktrees, and view worktree status
**Metadata system:** Maintains worktree-specific documentation (descriptions, PR info, notes) in a .grove/metadata/ directory structure
**Interactive navigation:** Keyboard-driven interface similar to lazygit/htop for efficient workflow management

The tool essentially bridges the gap between Git worktree management and tmux session organization, making it easier to switch between different branches/features while maintaining separate development environments. It pulls all data dynamically from Git and tmux CLI commands rather than using a database, keeping the system lightweight and in sync with the actual state of your repositories and sessions.

## Architecture

- **Main Application**: `app.py` - Single-file Textual application using Python 3.13+
- **Styling**: `app.tcss` - Textual CSS for UI styling
- **Testing**: `tests/test_integration.py` - Integration tests for TUI functionality
- **Test Data**: `tests/example_repo/` - Bare git repository structure for testing
- **Dependencies**: Requires `textual` library (currently v6.1.0) and `pytest` for testing

### Key Components

- `GroveApp`: Main Textual app class with dark mode toggle
- `Sidebar`: ListView widget that displays worktree directories
- `is_bare_git_repository()`: Validates the environment is a bare git repo
- `get_worktree_directories()`: Discovers directories at the same level as `.bare`

## Development Commands

**Run the application:**
```bash
python app.py # should display an error message about not running in a bare repository
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
- Discovers and lists directories at the same level as `.bare` directory
- Excludes hidden directories (starting with `.`) from the sidebar
- Supports dark/light theme toggle with 'd' key
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