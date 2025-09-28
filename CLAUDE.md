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
- **Dependencies**: Requires `textual` library (currently v6.1.0)

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