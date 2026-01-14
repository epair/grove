"""Tests for PR status functionality."""

import os
from pathlib import Path

from src import get_worktree_pr_status


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
        """Test that get_worktree_pr_status works based on config, not current directory."""
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            # With config-based system, PR status is found via config regardless of cwd
            pr_worktrees = get_worktree_pr_status()
            # Should still find the configured repo's PR worktrees
            # feature-one has WORKTREE_PR_PUBLISHED=true in its .env
            assert pr_worktrees == {"feature-one"}
        finally:
            os.chdir(original_cwd)