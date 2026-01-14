# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Grove is a Git Worktree and Tmux Session Manager - a modern terminal interface for managing Git worktrees and their associated tmux sessions in a unified, interactive environment.

#### Key functionality:

**Visual worktree browser:** Displays all Git worktrees in a repository with a split-screen layout (1/3 list view, 2/3 details view) ✅
**Tmux integration:** Shows active tmux session indicators (● for active, ○ for inactive) in the sidebar ✅
**Worktree management:** Create new worktrees from modal form, delete worktrees with confirmation dialog ✅
**Metadata system:** Maintains and displays worktree-specific PR information in a .grove/metadata/ directory structure as formatted markdown ✅
**Interactive navigation:** Keyboard-driven interface similar to lazygit/htop for efficient workflow management

The tool essentially bridges the gap between Git worktree management and tmux session organization, making it easier to switch between different branches/features while maintaining separate development environments. It pulls all data dynamically from Git and tmux CLI commands rather than using a database, keeping the system lightweight and in sync with the actual state of your repositories and sessions.

## Architecture

- **Main Application**: `src/` - Modular Python package using Python 3.13+
  - `src/app.py` - GroveApp main application class
  - `src/widgets.py` - Sidebar and MetadataDisplay widgets
  - `src/screens.py` - Modal screens (WorktreeFormScreen, ConfirmDeleteScreen, PRFormScreen, SetupWizardScreen)
  - `src/config.py` - TOML configuration management (repository location, setup wizard)
  - `src/utils.py` - Utility functions for git, tmux, and metadata operations
  - `src/__init__.py` - Package exports
  - `src/__main__.py` - Entry point with main() function and setup wizard integration
- **Styling**: `app.tcss` - Textual CSS for UI styling
- **Testing**: `tests/` - Comprehensive test suite covering all functionality
- **Test Data**: `tests/example_repo/` - Bare git repository structure for testing
- **Dependencies**: Requires `textual` library (currently v6.1.0), `gitpython` (v3.1+) for git operations, `pytest` for testing, and `pytest-textual-snapshot` for visual regression testing

### Key Components

**Application** (`src/app.py`):
- `GroveApp`: Main Textual app class using tokyo-night theme

**Widgets** (`src/widgets.py`):
- `Sidebar`: ListView widget that displays worktree directories with tmux session indicators
- `MetadataDisplay`: Markdown widget for displaying worktree metadata

**Screens** (`src/screens.py`):
- `WorktreeFormScreen`: Modal form for creating new worktrees (branch name and path)
- `ConfirmDeleteScreen`: Modal confirmation dialog for worktree deletion
- `PRFormScreen`: Modal form for creating pull requests
- `SetupWizardScreen`: First-time setup wizard for configuring repository location

**Configuration** (`src/config.py`):
- `get_config_path()`: Returns path to config file (~/.config/grove/config)
- `config_exists()`: Checks if config file exists
- `load_config()`: Loads and validates TOML configuration
- `save_config()`: Saves repository path to config file
- `get_repo_path()`: Gets repository path from config (replaces old .bare detection)
- `detect_potential_repositories()`: Auto-detects .bare repositories for setup wizard

**Utilities** (`src/utils.py`):
- `is_bare_git_repository()`: Validates the environment is a bare git repo
- `get_worktree_directories()`: Discovers directories at the same level as `.bare`
- `get_active_tmux_sessions()`: Retrieves active tmux session names
- `get_worktree_pr_status()`: Gets worktrees with published PRs
- `check_remote_branch_exists()`: Checks if remote branch exists
- `get_worktree_metadata()`: Reads metadata files for a worktree
- `get_worktree_git_info()`: Gets git information for a worktree
- `create_worktree_with_branch()`: Creates a git worktree with GitPython API
- `remove_worktree_with_branch()`: Removes a git worktree and its branch with GitPython API

## Development Commands

**Run the application:**
```bash
python -m src  # Can be run from any directory (uses config file)
```

**First-time setup:**
```bash
python -m src  # Automatically shows setup wizard if no config exists
```

**Re-run setup wizard:**
```bash
rm ~/.config/grove/config && python -m src
```

**Syntax check:**
```bash
python -m py_compile src/*.py
```

**Run tests:**
```bash
python -m pytest tests/ -v
```

**Run specific test file:**
```bash
python -m pytest tests/test_sidebar.py -v
```

**Type checking:**
```bash
mypy src/
```

**Note:** Always use `python -m pytest` instead of `pytest` directly to ensure proper Python path setup for module imports. The codebase uses comprehensive type hints throughout - all functions should include return type annotations and parameter types where applicable.

## Configuration

Grove uses a TOML configuration file to store the repository location. The config file is stored at `~/.config/grove/config`.

**First-Time Setup:**
On first run, Grove will automatically launch a setup wizard that:
1. Auto-detects potential .bare repositories on your system (searches current directory, parent directories up to 5 levels, and common project directories like `~/code/projects`, `~/projects`, `~/dev`, `~/workspace`)
2. Presents detected repositories in a selectable list
3. Allows you to press 'c' to enter a custom repository path
4. Validates that the selected path contains a `.bare` directory
5. Saves the configuration to `~/.config/grove/config`

**Config File Structure:**
```toml
[grove]
config_version = "1.0"

[repository]
repo_path = "/path/to/your/repository"
```

**Troubleshooting:**
- If Grove shows a config error, check `~/.config/grove/config`
- You can delete the config file to re-run the setup wizard
- The repository path must be the parent directory of `.bare` (not the `.bare` directory itself)
- Grove validates that the configured path exists and contains a `.bare` directory on startup

**Important:** Unlike previous versions, Grove now works from any directory - the repository location comes from the config file, not your current working directory.

## Requirements

- Python 3.13+ with required dependencies:
  - `textual` (v6.0+) - TUI framework
  - `gitpython` (v3.1+) - Git operations
  - `libtmux` (v0.46+) - Tmux integration
  - `tomli-w` (v1.0+) - TOML config file writing
- A bare git repository with `.bare` directory structure
- First-time setup via the setup wizard (runs automatically)

## Key Behavior

- Application validates configuration file on startup (shows setup wizard if missing)
- Works from any directory (repository location comes from config, not current directory)
- Discovers and lists directories at the same level as `.bare` directory with tmux session indicators
- Excludes hidden directories (starting with `.`) from the sidebar
- Displays worktree PR information as formatted markdown in a single view
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
│       │   └── pr.md
│       └── bugfix-01/
│           └── pr.md
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

The test suite is organized into modular files, each testing a specific area of functionality:

- **Bare Repository Tests** (`tests/test_bare_repo.py`): Tests bare git repository detection and worktree directory discovery
- **Sidebar Tests** (`tests/test_sidebar.py`): Tests sidebar UI functionality, highlighting, and selection
- **Metadata Tests** (`tests/test_metadata.py`): Tests worktree metadata display and retrieval
- **Git Info Tests** (`tests/test_git_info.py`): Tests git information retrieval (commit messages, dates, etc.)
- **PR Status Tests** (`tests/test_pr_status.py`): Tests PR status detection and indicators
- **Tmux Integration Tests** (`tests/test_tmux_integration.py`): Tests tmux session integration
- **Worktree Creation Tests** (`tests/test_worktree_creation.py`): Tests worktree creation form and workflow
- **Worktree Deletion Tests** (`tests/test_worktree_deletion.py`): Tests worktree deletion with confirmation
- **PR Creation Tests** (`tests/test_pr_creation.py`): Tests PR creation form and GitHub integration
- **Snapshot Tests** (`tests/test_snapshots.py`): Visual regression tests that capture and compare screen renderings

- **Test Data**: `tests/example_repo/` - Complete bare git repository structure with:
  - `.bare/` directory (bare git repo)
  - `feature-one/` and `bugfix-01/` worktree directories
  - `.grove/metadata/` structure for testing metadata features
- **Snapshot Storage**: `tests/__snapshots__/test_snapshots/` - SVG snapshots of screen renderings

### Test Configuration

- **pytest.ini**: Configured for async test support and proper test discovery
- **Async Testing**: Uses Textual's built-in testing capabilities with `app.run_test()`
- **Fixtures** (`tests/conftest.py`): Provides directory switching and test isolation
- **Imports**: All tests import from `src` package (e.g., `from src import GroveApp, Sidebar`)

### Snapshot Testing

The project uses `pytest-textual-snapshot` for visual regression testing. Snapshot tests capture the visual rendering of the TUI and compare it against baseline snapshots to detect unintended UI changes.

**Available Snapshot Tests:**
- `test_main_app_screen` - Default state with sidebar and metadata display
- `test_main_app_screen_with_tmux_session` - Main screen with active tmux session indicator
- `test_main_app_with_selected_worktree` - Main screen with selected worktree showing metadata
- `test_worktree_form_screen` - Empty worktree creation form modal
- `test_worktree_form_screen_with_input` - Worktree form with user input filled in
- `test_confirm_delete_screen` - Delete confirmation dialog modal
- `test_pr_form_screen` - Empty PR creation form modal
- `test_pr_form_screen_with_input` - PR form with title and reviewer selections

**Run snapshot tests:**
```bash
python -m pytest tests/test_snapshots.py -v
```

**Update snapshots after intentional UI changes:**
```bash
python -m pytest tests/test_snapshots.py --snapshot-update
```

**IMPORTANT:** Always review the snapshot changes before updating. When a snapshot test fails, an HTML report is generated at `snapshot_report.html` showing the visual differences. Only update snapshots with `--snapshot-update` after verifying the changes are intentional and correct.

### Running Tests

All tests must be run with `python -m pytest` to ensure proper module import resolution. The test suite validates both the core utility functions and the full TUI interface integration.