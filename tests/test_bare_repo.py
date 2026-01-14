"""Tests for bare git repository detection and worktree directory listing."""

import os
from pathlib import Path

from src import get_worktree_directories, is_bare_git_repository


class TestBareRepository:
    """Tests for bare git repository functionality."""

    def test_is_bare_git_repository_detection(self, change_to_example_repo: Path) -> None:
        """Test that the bare git repository is correctly detected."""
        assert is_bare_git_repository() is True

    def test_get_worktree_directories(self, change_to_example_repo: Path) -> None:
        """Test that worktree directories are correctly identified and sorted."""
        directories = get_worktree_directories()

        # Should contain the two worktree directories from example_repo
        expected_directories = ["bugfix-01", "feature-one"]
        assert directories == expected_directories

        # Verify hidden directories are excluded
        assert ".bare" not in directories
        assert ".git" not in directories
        assert ".grove" not in directories

    def test_get_worktree_directories_outside_bare_repo(self, tmp_path: Path) -> None:
        """Test that get_worktree_directories works based on config, not current directory."""
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            # With config-based system, worktrees are found via config regardless of cwd
            directories = get_worktree_directories()
            # Should still find the configured repo's worktrees
            expected_directories = ["bugfix-01", "feature-one"]
            assert directories == expected_directories
        finally:
            os.chdir(original_cwd)

    def test_is_bare_git_repository_outside_bare_repo(self, tmp_path: Path) -> None:
        """Test that is_bare_git_repository returns False when not in a bare repo."""
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            assert is_bare_git_repository() is False
        finally:
            os.chdir(original_cwd)