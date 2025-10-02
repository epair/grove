"""Tests for tmux session management integration."""

from pathlib import Path
from typing import Any
from unittest.mock import patch, MagicMock

import pytest
from textual.widgets import ListView, ListItem, Label

from src import GroveApp, get_active_tmux_sessions


class TestTmuxIntegration:
    """Tests for tmux session integration."""

    @patch('src.utils.get_tmux_server')
    def test_get_active_tmux_sessions_success(self, mock_get_server: Any) -> None:
        """Test that get_active_tmux_sessions correctly retrieves session names."""
        # Mock tmux server with sessions
        mock_server = MagicMock()
        mock_session1 = MagicMock()
        mock_session1.name = 'session1'
        mock_session2 = MagicMock()
        mock_session2.name = 'session2'
        mock_session3 = MagicMock()
        mock_session3.name = 'feature-one'

        mock_server.sessions = [mock_session1, mock_session2, mock_session3]
        mock_get_server.return_value = mock_server

        sessions = get_active_tmux_sessions()
        expected_sessions = {'session1', 'session2', 'feature-one'}
        assert sessions == expected_sessions

    @patch('src.utils.get_tmux_server')
    def test_get_active_tmux_sessions_no_sessions(self, mock_get_server: Any) -> None:
        """Test that get_active_tmux_sessions handles no sessions gracefully."""
        # Mock tmux server with no sessions
        mock_server = MagicMock()
        mock_server.sessions = []
        mock_get_server.return_value = mock_server

        sessions = get_active_tmux_sessions()
        assert sessions == set()

    @patch('src.utils.get_tmux_server')
    def test_get_active_tmux_sessions_tmux_not_found(self, mock_get_server: Any) -> None:
        """Test that get_active_tmux_sessions handles tmux not being available."""
        # Mock server not available
        mock_get_server.return_value = None

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