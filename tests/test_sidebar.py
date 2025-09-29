"""Tests for Grove sidebar UI functionality."""

from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from textual.widgets import ListView, ListItem, Label

from app import GroveApp, MetadataDisplay


class TestSidebar:
    """Tests for sidebar UI functionality."""

    @patch('app.get_active_tmux_sessions')
    async def test_grove_app_sidebar_content(self, mock_sessions: Any, change_to_example_repo: Path) -> None:
        """Test that the Grove app's sidebar displays the correct worktree directories with icons."""
        # Mock no tmux sessions for consistent testing
        mock_sessions.return_value = set()
        app = GroveApp()

        async with app.run_test() as pilot:
            # Get the sidebar widget
            sidebar = app.query_one("#sidebar", ListView)

            # Get all list items in the sidebar
            list_items = sidebar.query(ListItem)

            # Extract the text content from each list item
            directory_labels = []
            for item in list_items:
                label = item.query_one(Label)
                # Access the private content attribute since Label doesn't expose it publicly
                label_text = label._Static__content if hasattr(label, '_Static__content') else str(label)
                directory_labels.append(label_text)

            # Verify the expected directories are present with empty circle icons
            # Note: feature-one has a PR indicator because it has .env with WORKTREE_PR_PUBLISHED=true
            expected_directories = ["○ bugfix-01", "○ [bold]PR[/bold] feature-one"]
            assert directory_labels == expected_directories

    async def test_grove_app_starts_successfully(self, change_to_example_repo: Path) -> None:
        """Test that the Grove app starts successfully in a bare git repository."""
        app = GroveApp()

        async with app.run_test() as pilot:
            # Verify the app is running and main widgets are present
            assert app.query_one("#sidebar", ListView) is not None
            assert app.query_one("#body") is not None

            # Verify the sidebar is not empty
            sidebar = app.query_one("#sidebar", ListView)
            list_items = sidebar.query(ListItem)
            assert len(list_items) > 0

    @patch('app.get_active_tmux_sessions')
    async def test_sidebar_highlighting_updates_metadata(self, mock_sessions: Any, change_to_example_repo: Path) -> None:
        """Test that highlighting a worktree in sidebar updates the metadata display."""
        mock_sessions.return_value = set()
        app = GroveApp()

        async with app.run_test() as pilot:
            sidebar = app.query_one("#sidebar", ListView)
            metadata_display = app.query_one("#body", MetadataDisplay)

            # Simulate highlighting the first item (bugfix-01)
            sidebar.index = 0
            await pilot.pause()

            # Verify the selected worktree is updated
            assert app.selected_worktree == "bugfix-01"

            # Verify the metadata display shows bugfix-01 content
            # Get the markdown content that was set via update()
            content = str(metadata_display._markdown) if hasattr(metadata_display, '_markdown') else ""
            assert "# bugfix-01" in content

    @patch('app.get_active_tmux_sessions')
    async def test_reactive_selected_worktree_updates_display(self, mock_sessions: Any, change_to_example_repo: Path) -> None:
        """Test that changing selected_worktree reactive attribute updates the display."""
        mock_sessions.return_value = set()
        app = GroveApp()

        async with app.run_test() as pilot:
            metadata_display = app.query_one("#body", MetadataDisplay)

            # Change the reactive attribute directly
            app.selected_worktree = "feature-one"
            await pilot.pause()

            # Verify the metadata display is updated
            # Get the markdown content that was set via update()
            content = str(metadata_display._markdown) if hasattr(metadata_display, '_markdown') else ""
            assert "# feature-one" in content

    @patch('app.get_active_tmux_sessions')
    @patch('app.get_worktree_pr_status')
    async def test_sidebar_with_pr_indicators(self, mock_pr_status: Any, mock_sessions: Any, change_to_example_repo: Path) -> None:
        """Test that sidebar shows PR indicators for worktrees with published PRs."""
        # Mock no tmux sessions but feature-one has a PR
        mock_sessions.return_value = set()
        mock_pr_status.return_value = {'feature-one'}
        app = GroveApp()

        async with app.run_test() as pilot:
            # Get the sidebar widget
            sidebar = app.query_one("#sidebar", ListView)

            # Get all list items in the sidebar
            list_items = sidebar.query(ListItem)

            # Extract the text content from each list item
            directory_labels = []
            for item in list_items:
                label = item.query_one(Label)
                # Access the private content attribute since Label doesn't expose it publicly
                label_text = label._Static__content if hasattr(label, '_Static__content') else str(label)
                directory_labels.append(label_text)

            # Verify feature-one has PR indicator, bugfix-01 doesn't
            expected_directories = ["○ bugfix-01", "○ [bold]PR[/bold] feature-one"]
            assert directory_labels == expected_directories

    @patch('app.get_active_tmux_sessions')
    @patch('app.get_worktree_pr_status')
    async def test_sidebar_with_tmux_and_pr_indicators(self, mock_pr_status: Any, mock_sessions: Any, change_to_example_repo: Path) -> None:
        """Test that sidebar shows both tmux and PR indicators correctly."""
        # Mock tmux session for bugfix-01 and PR for feature-one
        mock_sessions.return_value = {'bugfix-01'}
        mock_pr_status.return_value = {'feature-one'}
        app = GroveApp()

        async with app.run_test() as pilot:
            # Get the sidebar widget
            sidebar = app.query_one("#sidebar", ListView)

            # Get all list items in the sidebar
            list_items = sidebar.query(ListItem)

            # Extract the text content from each list item
            directory_labels = []
            for item in list_items:
                label = item.query_one(Label)
                # Access the private content attribute since Label doesn't expose it publicly
                label_text = label._Static__content if hasattr(label, '_Static__content') else str(label)
                directory_labels.append(label_text)

            # Verify bugfix-01 has filled circle, feature-one has PR indicator
            expected_directories = ["● bugfix-01", "○ [bold]PR[/bold] feature-one"]
            assert directory_labels == expected_directories

    @patch('app.get_active_tmux_sessions')
    async def test_delete_action_integration_with_sidebar_selection(self, mock_sessions: Any, change_to_example_repo: Path) -> None:
        """Test full integration of selecting worktree from sidebar and deleting it."""
        mock_sessions.return_value = set()
        app = GroveApp()

        async with app.run_test() as pilot:
            sidebar = app.query_one("#sidebar", ListView)

            # Simulate highlighting the first item (bugfix-01)
            sidebar.index = 0
            await pilot.pause()

            # Verify the selected worktree is updated
            assert app.selected_worktree == "bugfix-01"

            # Import needed for this test
            from app import ConfirmDeleteScreen

            # Press 'd' to open delete confirmation
            await pilot.press("d")
            await pilot.pause()

            # Verify delete confirmation screen is shown
            assert len(app.screen_stack) == 2
            assert isinstance(app.screen, ConfirmDeleteScreen)
            assert app.screen.worktree_name == "bugfix-01"

            # Press 'n' to cancel
            await pilot.press("n")
            await pilot.pause()

            # Verify we're back to main screen
            assert len(app.screen_stack) == 1
            assert not isinstance(app.screen, ConfirmDeleteScreen)