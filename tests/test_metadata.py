"""Tests for worktree metadata functionality."""

import os
from pathlib import Path

from src import GroveApp, MetadataDisplay, get_worktree_metadata


class TestMetadata:
    """Tests for worktree metadata display."""

    def test_get_worktree_metadata_with_content(self, change_to_example_repo: Path) -> None:
        """Test that get_worktree_metadata reads pr.md correctly."""
        metadata = get_worktree_metadata("feature-one")

        # Verify it's a string
        assert isinstance(metadata, str)

        # Verify content from pr.md
        assert "PR #123" in metadata

    def test_get_worktree_metadata_missing_worktree(self, change_to_example_repo: Path) -> None:
        """Test that get_worktree_metadata handles missing worktree gracefully."""
        metadata = get_worktree_metadata("nonexistent-worktree")

        # Should return empty string for nonexistent worktree
        assert metadata == ""

    def test_get_worktree_metadata_outside_bare_repo(self, tmp_path: Path) -> None:
        """Test that get_worktree_metadata returns empty string when not in a bare repo."""
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            metadata = get_worktree_metadata("any-worktree")
            assert metadata == ""
        finally:
            os.chdir(original_cwd)

    async def test_metadata_display_widget_update(self, change_to_example_repo: Path) -> None:
        """Test that MetadataDisplay widget updates content correctly."""
        app = GroveApp()

        async with app.run_test() as pilot:
            metadata_display = app.query_one("#metadata", MetadataDisplay)

            # Test updating with a valid worktree
            metadata_display.update_content("feature-one")
            # Get the inner markdown widget
            from textual.widgets import Markdown
            markdown = metadata_display.query_one("#metadata_markdown", Markdown)
            content = str(markdown._markdown) if hasattr(markdown, '_markdown') else ""

            # Verify the content contains expected pr.md content
            assert "PR #123" in content

            # Test updating with empty worktree name
            metadata_display.update_content("")
            # Get the markdown content that was set via update()
            content = str(markdown._markdown) if hasattr(markdown, '_markdown') else ""
            assert "Select a worktree to view PR description" in content