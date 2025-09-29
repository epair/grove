"""Tests for git information retrieval functionality."""

import os
from pathlib import Path
from subprocess import CompletedProcess
from typing import Any
from unittest.mock import patch

from app import get_worktree_git_info


class TestGitInfo:
    """Tests for git information functionality."""

    @patch('app.subprocess.run')
    def test_get_worktree_git_info_success(self, mock_run: Any, change_to_example_repo: Path) -> None:
        """Test that get_worktree_git_info correctly parses git log output."""
        # Mock successful git log command
        mock_run.return_value = CompletedProcess(
            args=['git', '-C', 'feature-one', 'log', '-1', '--format=%s%n%ci%n%an <%ae>'],
            returncode=0,
            stdout='Add authentication system\n2024-09-28 10:30:45 -0700\nJohn Doe <john@example.com>\n',
            stderr=''
        )

        git_info = get_worktree_git_info("feature-one")

        assert git_info["commit_message"] == "Add authentication system"
        assert git_info["commit_date"] == "2024-09-28 10:30:45 -0700"
        assert git_info["committer"] == "John Doe <john@example.com>"

    @patch('app.subprocess.run')
    def test_get_worktree_git_info_failure(self, mock_run: Any, change_to_example_repo: Path) -> None:
        """Test that get_worktree_git_info handles git command failure gracefully."""
        # Mock failed git log command
        mock_run.return_value = CompletedProcess(
            args=['git', '-C', 'feature-one', 'log', '-1', '--format=%s%n%ci%n%an <%ae>'],
            returncode=1,
            stdout='',
            stderr='fatal: not a git repository'
        )

        git_info = get_worktree_git_info("feature-one")

        assert git_info["commit_message"] == "N/A"
        assert git_info["commit_date"] == "N/A"
        assert git_info["committer"] == "N/A"

    def test_get_worktree_git_info_outside_bare_repo(self, tmp_path: Path) -> None:
        """Test that get_worktree_git_info returns N/A values when not in a bare repo."""
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            git_info = get_worktree_git_info("any-worktree")
            assert git_info["commit_message"] == "N/A"
            assert git_info["commit_date"] == "N/A"
            assert git_info["committer"] == "N/A"
        finally:
            os.chdir(original_cwd)