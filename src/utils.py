"""Utility functions for Git worktree and tmux operations."""

import datetime
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any
from git import Repo
from git.exc import GitCommandError
import libtmux

from .config import get_repo_path, ConfigError

# Cache for tmux pane preview data to improve performance
# Structure: {worktree_name: (timestamp, pane_data)}
_tmux_pane_cache: dict[str, tuple[float, list[dict[str, str | bool]] | str]] = {}
TMUX_PANE_CACHE_TTL = 30.0  # seconds

# Default return value for git log when no data is available
_EMPTY_GIT_LOG: dict[str, Any] = {
    "sync_status": "no-upstream",
    "ahead_count": 0,
    "behind_count": 0,
    "comparison_branch": "",
    "commits": []
}


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


def get_tmux_server() -> libtmux.Server | None:
    """Get tmux server instance with error handling."""
    try:
        return libtmux.Server()
    except Exception:
        return None

def is_inside_tmux() -> bool:
    """Check if we're currently inside a tmux session."""
    return os.environ.get('TMUX') is not None

def session_exists(server: libtmux.Server, session_name: str) -> bool:
    """Check if a tmux session with the given name exists."""
    try:
        sessions = server.sessions.filter(session_name=session_name)
        return len(sessions) > 0
    except Exception:
        return False

def _run_hydration_script(session: Any, worktree_path: Path, session_name: str) -> None:
    """Find and run .tmux-sessionizer hydration script for a new session.

    Searches for the hydration script in the worktree directory, its parent,
    and the user's home directory (in that order).
    """
    hydration_script = None
    script_dir = None

    if (worktree_path / ".tmux-sessionizer").exists():
        hydration_script = worktree_path / ".tmux-sessionizer"
        script_dir = worktree_path
    elif (worktree_path.parent / ".tmux-sessionizer").exists():
        hydration_script = worktree_path.parent / ".tmux-sessionizer"
        script_dir = worktree_path.parent
    elif (Path.home() / ".tmux-sessionizer").exists():
        hydration_script = Path.home() / ".tmux-sessionizer"
        script_dir = Path.home()

    if hydration_script and script_dir:
        try:
            session.cmd(
                'run-shell',
                '-b',
                '-c', str(script_dir),
                f"bash '.tmux-sessionizer' && tmux display-message -t '{session_name}' 'Session hydrated successfully' || tmux display-message -t '{session_name}' 'Session hydration failed'"
            )
        except Exception:
            pass

def _setup_new_session(server: libtmux.Server, session_name: str, worktree_path: Path) -> Any:
    """Create a new tmux session, open pr.md in Neovim, and run hydration.

    Returns the created session object.
    """
    session = server.new_session(
        session_name=session_name,
        start_directory=str(worktree_path),
        attach=False
    )

    # Open pr.md in Neovim for new sessions
    bare_parent = get_repo_path()

    # Create metadata directory structure if it doesn't exist
    metadata_dir = bare_parent / ".grove" / "metadata" / session_name
    metadata_dir.mkdir(parents=True, exist_ok=True)

    # Create pr.md with template if it doesn't exist
    pr_file = metadata_dir / "pr.md"
    if not pr_file.exists():
        template = "# Pull Request\n\nWhat are you building?\n\n"
        pr_file.write_text(template)

    # Open the pr file in Neovim in the first pane
    try:
        first_pane = session.windows[0].panes[0]
        first_pane.send_keys(f"nvim {pr_file}")
    except Exception:
        pass

    _run_hydration_script(session, worktree_path, session_name)

    return session

def create_or_switch_to_session(worktree_path: Path) -> tuple[bool, str]:
    """Create or switch to a tmux session for a worktree (replaces tmux-sessionizer).

    Args:
        worktree_path: Path to the worktree directory

    Returns:
        Tuple of (success: bool, error_message: str)
    """
    try:
        # Get tmux server
        server = get_tmux_server()
        if server is None:
            return False, "Could not connect to tmux server"

        # Create session name from path basename (replace dots with dashes)
        session_name = worktree_path.name.replace('.', '-')

        # Check if session already exists
        if not session_exists(server, session_name):
            session = _setup_new_session(server, session_name, worktree_path)
        else:
            # Get existing session
            sessions = server.sessions.filter(session_name=session_name)
            if not sessions:
                return False, f"Session '{session_name}' not found"
            session = sessions[0]

        # Switch to the session (switch-client if inside tmux, attach if outside)
        if is_inside_tmux():
            session.switch_client()
        else:
            session.attach()

        return True, ""

    except Exception as e:
        return False, f"Tmux error: {str(e)}"

def get_worktree_directories() -> list[str]:
    """Get directories at the same level as .bare directory, excluding hidden directories."""
    try:
        bare_parent = get_repo_path()
    except ConfigError:
        return []  # Return empty list if no active repo

    # Get all directories at the same level as .bare, excluding hidden ones
    directories: list[str] = []
    for item in bare_parent.iterdir():
        if item.is_dir() and not item.name.startswith('.'):
            directories.append(item.name)

    return sorted(directories)

def get_active_tmux_sessions() -> set[str]:
    """Get names of all active tmux sessions using libtmux."""
    try:
        server = get_tmux_server()
        if server is None:
            return set()
        return {session.name for session in server.sessions if session.name is not None}
    except Exception:
        return set()

def get_worktree_pr_status() -> set[str]:
    """Get names of worktrees that have a PR published."""
    try:
        bare_parent = get_repo_path()
    except ConfigError:
        return set()  # Return empty set if no active repo

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

def get_worktree_metadata(worktree_name: str) -> str:
    """Get pr.md metadata content for a worktree."""
    bare_parent = get_repo_path()

    if bare_parent is None:
        return ""

    metadata_dir = bare_parent / ".grove" / "metadata" / worktree_name
    pr_file = metadata_dir / "pr.md"

    if pr_file.exists():
        try:
            return pr_file.read_text().strip()
        except (IOError, OSError):
            return ""

    return ""

def get_worktree_git_info(worktree_name: str) -> dict[str, str]:
    """Get git information for a worktree (last commit message, date, committer)."""
    bare_parent = get_repo_path()

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

def get_worktree_git_status(worktree_name: str) -> dict[str, list[str]]:
    """Get git status for a worktree (staged, unstaged, untracked files).

    Returns:
        Dict with keys 'staged', 'unstaged', 'untracked' containing lists of file paths
    """
    bare_parent = get_repo_path()

    if bare_parent is None:
        return {"staged": [], "unstaged": [], "untracked": []}

    worktree_path = bare_parent / worktree_name
    if not worktree_path.exists():
        return {"staged": [], "unstaged": [], "untracked": []}

    try:
        # Get status using GitPython
        repo = Repo(str(worktree_path))
        status_output = repo.git.status('--short')

        staged = []
        unstaged = []
        untracked = []

        if status_output:
            # Don't strip the whole output - that removes leading spaces from first line!
            for line in status_output.split('\n'):
                # Strip only trailing whitespace from each line
                line = line.rstrip()
                if not line:
                    continue

                # Parse git status --short format
                # Format is: XY filename
                # X = staged status, Y = unstaged status
                status_codes = line[:2]
                filename = line[3:] if len(line) > 3 else ""  # Git status has space after XY codes

                x_code = status_codes[0]
                y_code = status_codes[1]

                # Check if file is untracked
                if x_code == '?' and y_code == '?':
                    untracked.append(filename)
                else:
                    # Check staged changes (first character)
                    if x_code != ' ' and x_code != '?':
                        staged.append(filename)

                    # Check unstaged changes (second character)
                    if y_code != ' ' and y_code != '?':
                        unstaged.append(filename)

        return {
            "staged": staged,
            "unstaged": unstaged,
            "untracked": untracked
        }
    except Exception:
        return {"staged": [], "unstaged": [], "untracked": []}

def _format_relative_date(timestamp: int) -> str:
    """Format a commit timestamp as a human-readable relative date string."""
    commit_date = datetime.datetime.fromtimestamp(timestamp)
    now = datetime.datetime.now()
    delta = now - commit_date

    if delta.days > 365:
        return f"{delta.days // 365} year{'s' if delta.days // 365 > 1 else ''} ago"
    elif delta.days > 30:
        return f"{delta.days // 30} month{'s' if delta.days // 30 > 1 else ''} ago"
    elif delta.days > 0:
        return f"{delta.days} day{'s' if delta.days > 1 else ''} ago"
    elif delta.seconds > 3600:
        return f"{delta.seconds // 3600} hour{'s' if delta.seconds // 3600 > 1 else ''} ago"
    elif delta.seconds > 60:
        return f"{delta.seconds // 60} minute{'s' if delta.seconds // 60 > 1 else ''} ago"
    else:
        return "just now"

def _get_sync_status(repo: Repo, current_branch: Any) -> tuple[str, int, int, str, Any]:
    """Determine sync status between local branch and its upstream/comparison branch.

    Returns:
        Tuple of (sync_status, ahead_count, behind_count, comparison_branch_name, comparison_ref)
    """
    # Get upstream branch
    try:
        upstream = current_branch.tracking_branch()
    except Exception:
        upstream = None

    # If no upstream, try to use origin/main as comparison
    comparison_branch: Any = upstream

    if not upstream:
        try:
            repo.commit('origin/main')
            comparison_branch = 'origin/main'
        except Exception:
            comparison_branch = None

    sync_status = "no-upstream"
    ahead_count = 0
    behind_count = 0
    comparison_branch_name = ""

    if comparison_branch:
        try:
            branch_name = comparison_branch.name if hasattr(comparison_branch, 'name') else comparison_branch

            # Strip "origin/" prefix for display purposes
            display_name = branch_name
            if display_name.startswith('origin/'):
                display_name = display_name[7:]
            comparison_branch_name = display_name

            # Count commits ahead and behind
            ahead_commits = list(repo.iter_commits(f'{branch_name}..{current_branch.name}'))
            behind_commits = list(repo.iter_commits(f'{current_branch.name}..{branch_name}'))

            ahead_count = len(ahead_commits)
            behind_count = len(behind_commits)

            if ahead_count == 0 and behind_count == 0:
                sync_status = "up-to-date"
            elif ahead_count > 0 and behind_count == 0:
                sync_status = "ahead"
            elif ahead_count == 0 and behind_count > 0:
                sync_status = "behind"
            else:
                sync_status = "diverged"
        except Exception:
            pass

    return sync_status, ahead_count, behind_count, comparison_branch_name, comparison_branch

def _get_commit_list(repo: Repo, branch_name: str, comparison_branch: Any, max_count: int) -> list[dict[str, Any]]:
    """Get formatted commit list with pushed status.

    Args:
        repo: GitPython Repo instance
        branch_name: Name of the current branch
        comparison_branch: The upstream/comparison branch reference (or None)
        max_count: Maximum number of commits to retrieve

    Returns:
        List of commit dicts with 'hash', 'message', 'author', 'date', 'is_pushed'
    """
    commits: list[dict[str, Any]] = []
    try:
        commit_list = list(repo.iter_commits(branch_name, max_count=max_count))

        # Get the set of pushed/existing commit hashes
        pushed_commits: set[str] = set()
        if comparison_branch:
            try:
                comp_name = comparison_branch.name if hasattr(comparison_branch, 'name') else comparison_branch
                pushed_commit_list = list(repo.iter_commits(comp_name))
                pushed_commits = {commit.hexsha for commit in pushed_commit_list}
            except Exception:
                pass

        for commit in commit_list:
            relative_date = _format_relative_date(commit.committed_date)

            # Get commit message - ensure it's a string
            message_str = str(commit.message).strip()
            first_line = message_str.split('\n')[0] if '\n' in message_str else message_str

            commits.append({
                "hash": commit.hexsha[:7],
                "message": first_line,
                "author": commit.author.name,
                "date": relative_date,
                "is_pushed": commit.hexsha in pushed_commits
            })
    except Exception:
        pass

    return commits

def get_worktree_git_log(worktree_name: str) -> dict[str, Any]:
    """Get git log information for a worktree with push/unpush status.

    Returns:
        Dict with:
        - 'sync_status': str - 'up-to-date', 'ahead', 'behind', 'diverged', 'no-upstream'
        - 'ahead_count': int - number of commits ahead of remote
        - 'behind_count': int - number of commits behind remote
        - 'comparison_branch': str - name of branch being compared against
        - 'commits': list of dicts with 'hash', 'message', 'author', 'date', 'is_pushed'
    """
    bare_parent = get_repo_path()

    if bare_parent is None:
        return _EMPTY_GIT_LOG.copy()

    worktree_path = bare_parent / worktree_name
    if not worktree_path.exists():
        return _EMPTY_GIT_LOG.copy()

    try:
        repo = Repo(str(worktree_path))

        if repo.head.is_detached:
            return _EMPTY_GIT_LOG.copy()

        current_branch = repo.active_branch

        sync_status, ahead_count, behind_count, comparison_branch_name, comparison_ref = _get_sync_status(repo, current_branch)
        commits = _get_commit_list(repo, current_branch.name, comparison_ref, 20)

        return {
            "sync_status": sync_status,
            "ahead_count": ahead_count,
            "behind_count": behind_count,
            "comparison_branch": comparison_branch_name,
            "commits": commits
        }

    except Exception:
        return _EMPTY_GIT_LOG.copy()

def _capture_window_data(window: Any) -> dict[str, str | bool]:
    """Capture pane content data for a single tmux window.

    Returns a dict with 'window_name', 'window_index', 'content', and 'is_active' keys.
    """
    window_name: str = str(window.window_name or f"window-{window.window_index}")
    window_index: str = str(window.window_index or "0")
    is_active: bool = window.window_active == '1'

    if not window.panes:
        return {
            "window_name": window_name,
            "window_index": window_index,
            "content": "No panes in window",
            "is_active": is_active
        }

    # Find the active pane
    active_pane = None
    for pane in window.panes:
        if pane.pane_active == '1':
            active_pane = pane
            break

    # If no active pane found, use the first pane
    if active_pane is None:
        active_pane = window.panes[0]

    # Capture the pane content (visible portion only for performance)
    try:
        captured = active_pane.capture_pane()

        if isinstance(captured, list):
            content = '\n'.join(captured)
        else:
            content = str(captured) if captured else "Empty pane"
    except Exception:
        content = "Error capturing pane"

    return {
        "window_name": window_name,
        "window_index": window_index,
        "content": content,
        "is_active": is_active
    }

def get_tmux_pane_preview(worktree_name: str) -> list[dict[str, str | bool]] | str:
    """Get tmux pane preview content for all windows in a worktree's active session.

    Args:
        worktree_name: The name of the worktree

    Returns:
        List of dictionaries with 'window_name', 'window_index', and 'content' keys,
        or an error message string if something went wrong
    """
    if not worktree_name:
        return ""

    # Check cache first
    current_time = time.time()
    if worktree_name in _tmux_pane_cache:
        cached_timestamp, cached_data = _tmux_pane_cache[worktree_name]
        if current_time - cached_timestamp < TMUX_PANE_CACHE_TTL:
            return cached_data

    try:
        # Get tmux server
        server = get_tmux_server()
        if server is None:
            result: list[dict[str, str | bool]] | str = "Tmux not available"
            _tmux_pane_cache[worktree_name] = (time.time(), result)
            return result

        # Create session name from worktree name (replace dots with dashes)
        session_name = worktree_name.replace('.', '-')

        # Check if session exists
        if not session_exists(server, session_name):
            result = "No active tmux session"
            _tmux_pane_cache[worktree_name] = (time.time(), result)
            return result

        # Get the session
        sessions = server.sessions.filter(session_name=session_name)
        if not sessions:
            result = "No active tmux session"
            _tmux_pane_cache[worktree_name] = (time.time(), result)
            return result

        session = sessions[0]

        # Get all windows in the session
        if not session.windows:
            result = "No windows in session"
            _tmux_pane_cache[worktree_name] = (time.time(), result)
            return result

        windows_data = [_capture_window_data(window) for window in session.windows]

        result = windows_data if windows_data else "No windows in session"

        # Cache the result
        _tmux_pane_cache[worktree_name] = (time.time(), result)

        return result

    except Exception as e:
        error_msg = f"Error capturing pane: {str(e)}"
        # Cache error messages too (to avoid repeated failures)
        _tmux_pane_cache[worktree_name] = (time.time(), error_msg)
        return error_msg

def create_worktree_with_branch(name: str, prefix: str) -> tuple[bool, str]:
    """Create a git worktree with the specified name and branch prefix.

    Args:
        name: The worktree directory name
        prefix: The branch prefix (e.g., "ep/", "" for no prefix)

    Returns:
        Tuple of (success: bool, error_message: str)
    """
    bare_parent = get_repo_path()

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

def _stop_docker_containers(worktree_dir: Path) -> str | None:
    """Run docker stop script if present in the worktree directory.

    Args:
        worktree_dir: Path to the worktree directory

    Returns:
        Warning message string if there was an issue, None if successful or no script found
    """
    docker_stop_script = worktree_dir / "bin" / "docker" / "stop"

    if not (docker_stop_script.exists() and docker_stop_script.is_file()):
        return None

    try:
        stop_result = subprocess.run(
            [str(docker_stop_script)],
            cwd=str(worktree_dir),
            capture_output=True,
            text=True,
            timeout=60
        )

        if stop_result.returncode != 0 and stop_result.stderr:
            return f"Docker cleanup had warnings: {stop_result.stderr.strip()}"

    except subprocess.TimeoutExpired:
        return "Docker cleanup timed out after 60 seconds"
    except Exception as e:
        return f"Docker cleanup failed: {str(e)}"

    return None

def _remove_worktree_directory(repo: Repo, worktree_dir: Path, worktree_dir_name: str) -> tuple[bool, str]:
    """Remove a worktree's git registration and directory.

    Args:
        repo: GitPython Repo instance for the bare repository
        worktree_dir: Path to the worktree directory
        worktree_dir_name: Name of the worktree directory

    Returns:
        Tuple of (success: bool, error_message: str)
    """
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
        except GitCommandError:
            # Continue even if removal fails - we'll try directory removal
            pass

    # Remove the directory if it still exists
    if worktree_dir.exists():
        try:
            shutil.rmtree(worktree_dir)
        except (OSError, PermissionError) as e:
            return False, f"Failed to remove directory: {str(e)}"

    # Prune stale worktree entries
    try:
        repo.git.worktree('prune')
    except GitCommandError:
        pass

    return True, ""

def remove_worktree_with_branch(worktree_dir_name: str) -> tuple[bool, str]:
    """Remove a git worktree and its associated branch.

    Args:
        worktree_dir_name: The worktree directory name

    Returns:
        Tuple of (success: bool, error_message: str)
    """
    bare_parent = get_repo_path()

    if bare_parent is None:
        return False, "Could not find .bare directory"

    # Paths
    bare_repo_path = bare_parent / ".bare"
    worktree_dir = bare_parent / worktree_dir_name

    try:
        # Stop Docker containers if stop script exists
        docker_stop_warning = _stop_docker_containers(worktree_dir)

        # Open the bare repository
        repo = Repo(str(bare_repo_path))

        # Get the branch name from the worktree itself (instead of reconstructing it)
        branch_name = None
        if worktree_dir.exists():
            try:
                worktree_repo = Repo(str(worktree_dir))
                if not worktree_repo.head.is_detached:
                    branch_name = worktree_repo.active_branch.name
            except Exception:
                pass

        # Remove worktree registration and directory
        success, error_msg = _remove_worktree_directory(repo, worktree_dir, worktree_dir_name)
        if not success:
            return False, error_msg

        # Remove the branch if we found one
        branch_error = None
        if branch_name:
            try:
                repo.git.branch('-D', branch_name)
            except GitCommandError as e:
                branch_error = str(e)

        # Build the final message with all warnings
        warnings = []
        if docker_stop_warning:
            warnings.append(docker_stop_warning)
        if branch_error:
            warnings.append(f"Branch deletion failed: {branch_error}")

        # Return success for worktree removal, but include warnings if any
        if warnings:
            return True, "Worktree removed. " + " ".join(warnings)

        return True, ""

    except GitCommandError as e:
        return False, f"Git error: {str(e)}"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"
