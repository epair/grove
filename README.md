# Grove

A terminal UI for managing Git worktrees and tmux sessions.

> This project is almost entirely vibe-coded, so proceed with understanding/caution. I use this tool for managing my projects at work.

## What is it?

Grove helps you manage multiple Git worktrees in an interactive TUI. Think `lazygit` but for worktrees, with built-in tmux session tracking.

## Features

- Visual worktree browser with split-screen layout
- Create/delete worktrees interactively
- See which worktrees have active tmux sessions (● vs ○)
- Multi-repository support with quick switching (`Ctrl+R`)
- Smart detection - opens the right repo based on your current directory
- Track PR metadata per worktree

## Installation

**Option 1: Install globally with pipx (recommended)**
```bash
git clone https://github.com/yourusername/grove.git
cd grove
pipx install .
grove  # Run from anywhere
```

**Option 2: Run directly**
```bash
git clone https://github.com/yourusername/grove.git
cd grove
pip install -e .  # Install in editable mode
python -m src
```

**Requirements:** Python 3.13+, Git

## Usage

```bash
python -m src  # First run shows setup wizard
```

**Key bindings:**
- `↑/↓` or `j/k` - Navigate
- `Enter` - View worktree details
- `Ctrl+N` - Create worktree
- `Ctrl+D` - Delete worktree
- `Ctrl+R` - Switch repositories
- `q` - Quit

## Repository Structure

Grove expects a bare worktree setup:

```
your-project/
├── .bare/              # Bare git repo
├── main/               # Worktree
├── feature-x/          # Worktree
└── feature-y/          # Worktree
```

**Setup a new repo:**
```bash
git clone --bare https://github.com/user/repo.git repo/.bare
cd repo && git worktree add main
```

## Configuration

Config stored at `~/.config/grove/config`. Delete it to re-run setup wizard.

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
python -m pytest tests/ -v

# Type check
mypy src/

# Update global command after making changes
pipx install . --force
```

Built with [Textual](https://textual.textualize.io/).
