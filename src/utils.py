"""Utility functions for Git worktree and tmux operations."""

import subprocess
from pathlib import Path
from git import Repo
from git.exc import GitCommandError


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

def get_bare_parent() -> Path | None:
    """Get bare parent directory containing .bare subdirectory."""
    current_path = Path.cwd()
    bare_parent: Path | None = None

    # Find where the .bare directory is located
    if (current_path / ".bare").is_dir():
        bare_parent = current_path
    elif (current_path.parent / ".bare").is_dir():
        bare_parent = current_path.parent

    return bare_parent

def get_worktree_directories() -> list[str]:
    """Get directories at the same level as .bare directory, excluding hidden directories."""
    bare_parent = get_bare_parent()

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
    bare_parent = get_bare_parent()

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
        # Open repo and use git status to check if upstream branch is gone
        repo = Repo(str(worktree_path))
        status_output = repo.git.status('-b', '--porcelain')

        if status_output:
            # Check if the first line contains [gone]
            first_line = status_output.strip().split('\n')[0]
            if '[gone]' in first_line:
                return False
            # If there's tracking info without [gone], the branch exists
            if '...' in first_line:
                return True
    except Exception:
        pass

    # If we can't determine, assume it exists to be safe
    return True

def get_worktree_metadata(worktree_name: str) -> dict[str, str]:
    """Get metadata for a worktree from .grove/metadata/{worktree}/ directory."""
    bare_parent = get_bare_parent()

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
    bare_parent = get_bare_parent()

    if bare_parent is None:
        return {"commit_message": "N/A", "commit_date": "N/A", "committer": "N/A"}

    worktree_path = bare_parent / worktree_name
    if not worktree_path.exists():
        return {"commit_message": "N/A", "commit_date": "N/A", "committer": "N/A"}

    try:
        # Get last commit info using GitPython
        repo = Repo(str(worktree_path))
        log_output = repo.git.log('-1', '--format=%s%n%ci%n%an <%ae>')

        if log_output.strip():
            lines = log_output.strip().split('\n')
            return {
                "commit_message": lines[0] if len(lines) > 0 else "N/A",
                "commit_date": lines[1] if len(lines) > 1 else "N/A",
                "committer": lines[2] if len(lines) > 2 else "N/A"
            }
    except Exception:
        pass

    return {"commit_message": "N/A", "commit_date": "N/A", "committer": "N/A"}

def create_worktree_with_branch(name: str, prefix: str) -> tuple[bool, str]:
    """Create a git worktree with the specified name and branch prefix.

    Args:
        name: The worktree directory name
        prefix: The branch prefix (e.g., "ep/", "" for no prefix)

    Returns:
        Tuple of (success: bool, error_message: str)
    """
    bare_parent = get_bare_parent()

    if bare_parent is None:
        return False, "Could not find .bare directory"

    # Paths
    bare_repo_path = bare_parent / ".bare"
    worktree_dir = bare_parent / name
    branch_name = f"{prefix}{name}"

    try:
        # Open the bare repository
        repo = Repo(str(bare_repo_path))

        # Check if remote branch exists
        remote_branch_exists = False
        try:
            repo.git.show_ref('--verify', '--quiet', f'refs/remotes/origin/{branch_name}')
            remote_branch_exists = True
        except GitCommandError:
            remote_branch_exists = False

        if remote_branch_exists:
            # Fetch the remote branch
            repo.git.fetch('origin', f'{branch_name}:{branch_name}')
        else:
            # Fetch main and create a new branch from it
            repo.git.fetch('origin', 'main:main')
            try:
                repo.git.branch(branch_name, 'main')
            except GitCommandError:
                # Branch might already exist locally
                pass

        # Create the worktree
        repo.git.worktree('add', str(worktree_dir), branch_name)

        # Run .grove/.setup script if it exists
        setup_script = bare_parent / ".grove" / ".setup"
        if setup_script.exists() and setup_script.is_file():
            try:
                subprocess.run(
                    [str(setup_script), str(worktree_dir)],
                    cwd=str(bare_parent),
                    capture_output=True,
                    text=True,
                    timeout=30
                )
            except (subprocess.SubprocessError, subprocess.TimeoutExpired):
                # Setup script failed, but worktree was created
                pass

        return True, ""

    except GitCommandError as e:
        return False, f"Git error: {str(e)}"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"

def remove_worktree_with_branch(worktree_dir_name: str) -> tuple[bool, str]:
    """Remove a git worktree and its associated branch.

    Args:
        worktree_dir_name: The worktree directory name

    Returns:
        Tuple of (success: bool, error_message: str)
    """
    bare_parent = get_bare_parent()

    if bare_parent is None:
        return False, "Could not find .bare directory"

    # Paths
    bare_repo_path = bare_parent / ".bare"
    worktree_dir = bare_parent / worktree_dir_name

    try:
        # Open the bare repository
        repo = Repo(str(bare_repo_path))

        # Get the branch name from the worktree itself (instead of reconstructing it)
        branch_name = None
        if worktree_dir.exists():
            try:
                # Open a repo object for the worktree to get its active branch
                worktree_repo = Repo(str(worktree_dir))
                if not worktree_repo.head.is_detached:
                    branch_name = worktree_repo.active_branch.name
            except Exception:
                # If we can't determine the branch, that's okay - we'll skip branch deletion
                pass

        # Check if worktree is registered
        try:
            worktrees = repo.git.worktree('list').strip().split('\n')
            worktree_registered = any(worktree_dir_name in wt for wt in worktrees)
        except GitCommandError:
            worktree_registered = False

        # Remove the worktree if registered
        if worktree_registered:
            try:
                repo.git.worktree('remove', '--force', str(worktree_dir))
            except GitCommandError as e:
                # Continue even if removal fails - we'll try directory removal
                pass

        # Remove the directory if it still exists
        if worktree_dir.exists():
            import shutil
            try:
                shutil.rmtree(worktree_dir)
            except (OSError, PermissionError) as e:
                return False, f"Failed to remove directory: {str(e)}"

        # Prune stale worktree entries
        try:
            repo.git.worktree('prune')
        except GitCommandError:
            pass

        # Remove the branch if we found one
        branch_error = None
        if branch_name:
            try:
                repo.git.branch('-D', branch_name)
            except GitCommandError as e:
                # Capture error but don't fail the whole operation
                branch_error = str(e)

        # Return success for worktree removal, but include branch deletion warning if any
        if branch_error:
            return True, f"Worktree removed but branch deletion failed: {branch_error}"

        return True, ""

    except GitCommandError as e:
        return False, f"Git error: {str(e)}"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"