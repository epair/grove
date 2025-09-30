"""Tests for tmux session management integration."""

from pathlib import Path
from typing import Any
from unittest.mock import patch, MagicMock
from subprocess import CompletedProcess

import pytest
from textual.widgets import ListView, ListItem, Label

from src import GroveApp, get_active_tmux_sessions


class TestTmuxIntegration:
    """Tests for tmux session integration."""

    @patch('src.utils.subprocess.run')
    def test_get_active_tmux_sessions_success(self, mock_run: Any) -> None:
        """Test that get_active_tmux_sessions correctly parses tmux output."""
        # Mock successful tmux command with session output
        mock_run.return_value = CompletedProcess(
            args=['tmux', 'list-sessions', '-F', '#{session_name}'],
            returncode=0,
            stdout='session1\nsession2\nfeature-one\n',
            stderr=''
        )

        sessions = get_active_tmux_sessions()
        expected_sessions = {'session1', 'session2', 'feature-one'}
        assert sessions == expected_sessions

    @patch('src.utils.subprocess.run')
    def test_get_active_tmux_sessions_no_sessions(self, mock_run: Any) -> None:
        """Test that get_active_tmux_sessions handles no sessions gracefully."""
        # Mock tmux command with no sessions (returns empty output)
        mock_run.return_value = CompletedProcess(
            args=['tmux', 'list-sessions', '-F', '#{session_name}'],
            returncode=1,
            stdout='',
            stderr='no server running on /tmp/tmux-501/default'
        )

        sessions = get_active_tmux_sessions()
        assert sessions == set()

    @patch('src.utils.subprocess.run')
    def test_get_active_tmux_sessions_tmux_not_found(self, mock_run: Any) -> None:
        """Test that get_active_tmux_sessions handles tmux not being installed."""
        # Mock FileNotFoundError when tmux is not installed
        mock_run.side_effect = FileNotFoundError("tmux command not found")

        sessions = get_active_tmux_sessions()
        assert sessions == set()

    @patch('src.widgets.get_active_tmux_sessions')
    async def test_sidebar_with_active_tmux_sessions(self, mock_sessions: Any, change_to_example_repo: Path) -> None:
        """Test that sidebar shows filled circles for directories with active tmux sessions."""
        # Mock tmux sessions where one matches a worktree directory
        mock_sessions.return_value = {'feature-one', 'other-session'}
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
                directory_labels.append(str(label.content))

            # Verify feature-one has filled circle and PR indicator, bugfix-01 has empty circle
            expected_directories = ["○ bugfix-01", "● [bold]PR[/bold] feature-one"]
            assert directory_labels == expected_directories