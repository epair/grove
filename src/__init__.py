"""Grove - Git Worktree and Tmux Session Manager."""

from .app import GroveApp
from .clone import clone_repository
from .widgets import Sidebar, GitStatusDisplay, MetadataDisplay
from .screens import (
    WorktreeFormScreen,
    ConfirmDeleteScreen,
    PRFormScreen,
    RepositorySelectionScreen,
    AddRepositoryScreen,
    ConfirmDeleteRepositoryScreen,
)
from .utils import (
    is_bare_git_repository,
    get_worktree_directories,
    get_active_tmux_sessions,
    get_worktree_pr_status,
    check_remote_branch_exists,
    get_worktree_metadata,
    get_worktree_git_info,
)
from .config import (
    get_repositories,
    add_repository,
    remove_repository,
    update_last_used,
    set_active_repo,
    get_active_repo,
    get_repo_path,
    find_repo_for_directory,
    config_exists,
    detect_potential_repositories,
    ConfigError,
)

__all__ = [
    "GroveApp",
    "clone_repository",
    "Sidebar",
    "GitStatusDisplay",
    "MetadataDisplay",
    "WorktreeFormScreen",
    "ConfirmDeleteScreen",
    "PRFormScreen",
    "RepositorySelectionScreen",
    "AddRepositoryScreen",
    "ConfirmDeleteRepositoryScreen",
    "is_bare_git_repository",
    "get_worktree_directories",
    "get_active_tmux_sessions",
    "get_worktree_pr_status",
    "check_remote_branch_exists",
    "get_worktree_metadata",
    "get_worktree_git_info",
    "get_repositories",
    "add_repository",
    "remove_repository",
    "update_last_used",
    "set_active_repo",
    "get_active_repo",
    "get_repo_path",
    "find_repo_for_directory",
    "config_exists",
    "detect_potential_repositories",
    "ConfigError",
]