"""Utility functions for Git worktree and tmux operations."""

import subprocess
from pathlib import Path


def is_bare_git_repository() -> bool:
    """Check if current directory or parent contains a bare git repository."""
    current_path = Path.cwd()

    # Check current directory for .bare subdirectory
    if (current_path / ".bare").is_dir():
        return True

    # Check parent directory for .bare subdirectory
    if (current_path.parent / ".bare").is_dir():
        return True

    return False

def get_worktree_directories() -> list[str]:
    """Get directories at the same level as .bare directory, excluding hidden directories."""
    current_path = Path.cwd()
    bare_parent: Path | None = None

    # Find where the .bare directory is located
    if (current_path / ".bare").is_dir():
        bare_parent = current_path
    elif (current_path.parent / ".bare").is_dir():
        bare_parent = current_path.parent

    if bare_parent is None:
        return []

    # Get all directories at the same level as .bare, excluding hidden ones
    directories: list[str] = []
    for item in bare_parent.iterdir():
        if item.is_dir() and not item.name.startswith('.'):
            directories.append(item.name)

    return sorted(directories)

def get_active_tmux_sessions() -> set[str]:
    """Get names of all active tmux sessions using tmux format strings."""
    try:
        result = subprocess.run(
            ['tmux', 'list-sessions', '-F', '#{session_name}'],
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode == 0 and result.stdout.strip():
            return set(result.stdout.strip().split('\n'))
    except (FileNotFoundError, subprocess.SubprocessError):
        pass
    return set()

def get_worktree_pr_status() -> set[str]:
    """Get names of worktrees that have a PR published."""
    current_path = Path.cwd()
    bare_parent: Path | None = None

    # Find where the .bare directory is located
    if (current_path / ".bare").is_dir():
        bare_parent = current_path
    elif (current_path.parent / ".bare").is_dir():
        bare_parent = current_path.parent

    if bare_parent is None:
        return set()

    # Check each worktree for .env file with WORKTREE_PR_PUBLISHED=true
    pr_worktrees: set[str] = set()
    directories = get_worktree_directories()

    for directory in directories:
        env_file = bare_parent / directory / ".env"
        if env_file.exists():
            try:
                content = env_file.read_text()
                # Check if WORKTREE_PR_PUBLISHED=true is in the file
                for line in content.strip().split('\n'):
                    if line.strip() == 'WORKTREE_PR_PUBLISHED=true':
                        pr_worktrees.add(directory)
                        break
            except (IOError, OSError):
                pass

    return pr_worktrees

def check_remote_branch_exists(worktree_path: Path) -> bool:
    """Check if the remote upstream branch exists for a worktree.

    Returns True if remote branch exists, False if it's gone or there's no upstream.
    """
    try:
        # Use git status to check if upstream branch is gone
        result = subprocess.run(
            ['git', '-C', str(worktree_path), 'status', '-b', '--porcelain'],
            capture_output=True,
            text=True,
            check=False
        )

        if result.returncode == 0 and result.stdout:
            # Check if the first line contains [gone]
            first_line = result.stdout.strip().split('\n')[0]
            if '[gone]' in first_line:
                return False
            # If there's tracking info without [gone], the branch exists
            if '...' in first_line:
                return True
    except (FileNotFoundError, subprocess.SubprocessError):
        pass

    # If we can't determine, assume it exists to be safe
    return True

def get_worktree_metadata(worktree_name: str) -> dict[str, str]:
    """Get metadata for a worktree from .grove/metadata/{worktree}/ directory."""
    current_path = Path.cwd()
    bare_parent: Path | None = None

    # Find where the .bare directory is located
    if (current_path / ".bare").is_dir():
        bare_parent = current_path
    elif (current_path.parent / ".bare").is_dir():
        bare_parent = current_path.parent

    if bare_parent is None:
        return {}

    metadata_dir = bare_parent / ".grove" / "metadata" / worktree_name
    if not metadata_dir.exists():
        return {}

    metadata = {}
    for filename in ["description.md", "pr.md", "notes.md"]:
        file_path = metadata_dir / filename
        if file_path.exists():
            try:
                metadata[filename[:-3]] = file_path.read_text().strip()
            except (IOError, OSError):
                metadata[filename[:-3]] = ""
        else:
            metadata[filename[:-3]] = ""

    return metadata

def get_worktree_git_info(worktree_name: str) -> dict[str, str]:
    """Get git information for a worktree (last commit message, date, committer)."""
    current_path = Path.cwd()
    bare_parent: Path | None = None

    # Find where the .bare directory is located
    if (current_path / ".bare").is_dir():
        bare_parent = current_path
    elif (current_path.parent / ".bare").is_dir():
        bare_parent = current_path.parent

    if bare_parent is None:
        return {"commit_message": "N/A", "commit_date": "N/A", "committer": "N/A"}

    worktree_path = bare_parent / worktree_name
    if not worktree_path.exists():
        return {"commit_message": "N/A", "commit_date": "N/A", "committer": "N/A"}

    try:
        # Get last commit info using git log with format
        result = subprocess.run(
            ['git', '-C', str(worktree_path), 'log', '-1', '--format=%s%n%ci%n%an <%ae>'],
            capture_output=True,
            text=True,
            check=False
        )

        if result.returncode == 0 and result.stdout.strip():
            lines = result.stdout.strip().split('\n')
            return {
                "commit_message": lines[0] if len(lines) > 0 else "N/A",
                "commit_date": lines[1] if len(lines) > 1 else "N/A",
                "committer": lines[2] if len(lines) > 2 else "N/A"
            }
    except (FileNotFoundError, subprocess.SubprocessError):
        pass

    return {"commit_message": "N/A", "commit_date": "N/A", "committer": "N/A"}