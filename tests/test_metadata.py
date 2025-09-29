"""Tests for worktree metadata functionality."""

import os
from pathlib import Path

from app import GroveApp, MetadataDisplay, get_worktree_metadata


class TestMetadata:
    """Tests for worktree metadata display."""

    def test_get_worktree_metadata_with_content(self, change_to_example_repo: Path) -> None:
        """Test that get_worktree_metadata reads metadata files correctly."""
        metadata = get_worktree_metadata("feature-one")

        # Verify all expected metadata keys are present
        assert "description" in metadata
        assert "pr" in metadata
        assert "notes" in metadata

        # Verify content matches what we expect from the test files
        assert "user authentication" in metadata["description"].lower()
        assert "PR #123" in metadata["pr"]
        assert "password reset" in metadata["notes"]

    def test_get_worktree_metadata_missing_worktree(self, change_to_example_repo: Path) -> None:
        """Test that get_worktree_metadata handles missing worktree gracefully."""
        metadata = get_worktree_metadata("nonexistent-worktree")

        # Should return empty dict for nonexistent worktree
        assert metadata == {}

    def test_get_worktree_metadata_outside_bare_repo(self, tmp_path: Path) -> None:
        """Test that get_worktree_metadata returns empty dict when not in a bare repo."""
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            metadata = get_worktree_metadata("any-worktree")
            assert metadata == {}
        finally:
            os.chdir(original_cwd)

    async def test_metadata_display_widget_update(self, change_to_example_repo: Path) -> None:
        """Test that MetadataDisplay widget updates content correctly."""
        app = GroveApp()

        async with app.run_test() as pilot:
            metadata_display = app.query_one("#body", MetadataDisplay)

            # Test updating with a valid worktree
            metadata_display.update_content("feature-one")
            # Get the markdown content that was set via update()
            # Since Markdown doesn't expose the content directly, we check if the widget has been updated
            # by looking for the expected text in its render output
            content = str(metadata_display._markdown) if hasattr(metadata_display, '_markdown') else ""

            # Verify the content contains expected sections
            assert "# feature-one" in content
            assert "## Description" in content
            assert "## Pull Request Info" in content
            assert "## Notes" in content
            assert "## Git Information" in content

            # Test updating with empty worktree name
            metadata_display.update_content("")
            # Get the markdown content that was set via update()
            # Since Markdown doesn't expose the content directly, we check if the widget has been updated
            # by looking for the expected text in its render output
            content = str(metadata_display._markdown) if hasattr(metadata_display, '_markdown') else ""
            assert "Select a worktree to view its metadata." in content