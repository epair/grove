"""Tests for PR status functionality."""

import os
from pathlib import Path

from app import get_worktree_pr_status


class TestPRStatus:
    """Tests for PR status functionality."""

    def test_get_worktree_pr_status(self, change_to_example_repo: Path) -> None:
        """Test that get_worktree_pr_status correctly identifies worktrees with PRs."""
        pr_worktrees = get_worktree_pr_status()

        # feature-one has a .env file with WORKTREE_PR_PUBLISHED=true
        assert 'feature-one' in pr_worktrees
        # bugfix-01 doesn't have a .env file, so no PR
        assert 'bugfix-01' not in pr_worktrees

    def test_get_worktree_pr_status_outside_bare_repo(self, tmp_path: Path) -> None:
        """Test that get_worktree_pr_status returns empty set when not in a bare repo."""
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            pr_worktrees = get_worktree_pr_status()
            assert pr_worktrees == set()
        finally:
            os.chdir(original_cwd)