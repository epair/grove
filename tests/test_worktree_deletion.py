"""Tests for worktree deletion functionality."""

from pathlib import Path
from typing import Any
from unittest.mock import patch, MagicMock

import pytest
from textual.widgets import Label, Button, ListView

from src import GroveApp, ConfirmDeleteScreen


class TestWorktreeDeletion:
    """Tests for worktree deletion feature."""

    @patch('src.utils.get_active_tmux_sessions')
    async def test_confirm_delete_screen_initial_state(self, mock_sessions: Any, change_to_example_repo: Path) -> None:
        """Test that ConfirmDeleteScreen displays correct initial content."""
        mock_sessions.return_value = set()
        app = GroveApp()
        worktree_name = "test-worktree"

        async with app.run_test() as pilot:
            # Set selected worktree and open delete confirmation
            app.selected_worktree = worktree_name
            await pilot.press("d")
            await pilot.pause()

            # Verify we're on the delete confirmation screen
            assert isinstance(app.screen, ConfirmDeleteScreen)
            screen = app.screen

            # Verify title
            title = screen.query_one("#delete_title", Label)
            assert str(title.content) == "Delete Worktree"

            # Verify message contains worktree name
            message = screen.query_one("#delete_message", Label)
            assert worktree_name in str(message.content)

            # Verify warning message
            warning = screen.query_one("#delete_warning", Label)
            assert "cannot be undone" in str(warning.content)

            # Verify buttons are present
            yes_button = screen.query_one("#yes_button", Button)
            no_button = screen.query_one("#no_button", Button)
            assert "Yes" in str(yes_button.label)
            assert "No" in str(no_button.label)

    @patch('src.app.get_tmux_server')
    @patch('src.utils.get_active_tmux_sessions')
    async def test_confirm_delete_screen_yes_button(self, mock_sessions: Any, mock_get_server: Any, change_to_example_repo: Path) -> None:
        """Test that clicking Yes button confirms deletion."""
        mock_sessions.return_value = set()
        # Mock tmux server to return None (no session exists)
        mock_get_server.return_value = None
        app = GroveApp()

        async with app.run_test() as pilot:
            # Set selected worktree and open delete confirmation
            app.selected_worktree = "test-worktree"
            await pilot.press("d")
            await pilot.pause()

            # Verify we're on the delete confirmation screen
            assert isinstance(app.screen, ConfirmDeleteScreen)

            # Mock sidebar operations
            sidebar = app.query_one("#sidebar", ListView)
            sidebar.clear = MagicMock()
            sidebar.append = MagicMock()

            # Click Yes button
            await pilot.click("#yes_button")
            await pilot.pause()

            # Verify we're back to main screen (deletion was confirmed)
            assert not isinstance(app.screen, ConfirmDeleteScreen)

    @patch('src.utils.get_active_tmux_sessions')
    async def test_confirm_delete_screen_no_button(self, mock_sessions: Any, change_to_example_repo: Path) -> None:
        """Test that clicking No button cancels deletion."""
        mock_sessions.return_value = set()
        app = GroveApp()

        async with app.run_test() as pilot:
            # Set selected worktree and open delete confirmation
            app.selected_worktree = "test-worktree"
            await pilot.press("d")
            await pilot.pause()

            # Verify we're on the delete confirmation screen
            assert isinstance(app.screen, ConfirmDeleteScreen)

            # Click No button
            await pilot.click("#no_button")
            await pilot.pause()

            # Verify we're back to main screen (deletion was cancelled)
            assert not isinstance(app.screen, ConfirmDeleteScreen)

    @patch('src.app.get_tmux_server')
    @patch('src.utils.get_active_tmux_sessions')
    async def test_confirm_delete_screen_y_key(self, mock_sessions: Any, mock_get_server: Any, change_to_example_repo: Path) -> None:
        """Test that pressing 'y' key confirms deletion."""
        mock_sessions.return_value = set()
        # Mock tmux server to return None (no session exists)
        mock_get_server.return_value = None
        app = GroveApp()

        async with app.run_test() as pilot:
            # Set selected worktree and open delete confirmation
            app.selected_worktree = "test-worktree"
            await pilot.press("d")
            await pilot.pause()

            # Verify we're on the delete confirmation screen
            assert isinstance(app.screen, ConfirmDeleteScreen)

            # Mock sidebar operations
            sidebar = app.query_one("#sidebar", ListView)
            sidebar.clear = MagicMock()
            sidebar.append = MagicMock()

            # Press 'y' key
            await pilot.press("y")
            await pilot.pause()

            # Verify we're back to main screen (deletion was confirmed)
            assert not isinstance(app.screen, ConfirmDeleteScreen)

    @patch('src.utils.get_active_tmux_sessions')
    async def test_confirm_delete_screen_n_key(self, mock_sessions: Any, change_to_example_repo: Path) -> None:
        """Test that pressing 'n' key cancels deletion."""
        mock_sessions.return_value = set()
        app = GroveApp()

        async with app.run_test() as pilot:
            # Set selected worktree and open delete confirmation
            app.selected_worktree = "test-worktree"
            await pilot.press("d")
            await pilot.pause()

            # Verify we're on the delete confirmation screen
            assert isinstance(app.screen, ConfirmDeleteScreen)

            # Press 'n' key
            await pilot.press("n")
            await pilot.pause()

            # Verify we're back to main screen (deletion was cancelled)
            assert not isinstance(app.screen, ConfirmDeleteScreen)

    @patch('src.utils.get_active_tmux_sessions')
    async def test_confirm_delete_screen_escape_key(self, mock_sessions: Any, change_to_example_repo: Path) -> None:
        """Test that pressing Escape key cancels deletion."""
        mock_sessions.return_value = set()
        app = GroveApp()

        async with app.run_test() as pilot:
            # Set selected worktree and open delete confirmation
            app.selected_worktree = "test-worktree"
            await pilot.press("d")
            await pilot.pause()

            # Verify we're on the delete confirmation screen
            assert isinstance(app.screen, ConfirmDeleteScreen)

            # Press Escape key
            await pilot.press("escape")
            await pilot.pause()

            # Verify we're back to main screen (deletion was cancelled)
            assert not isinstance(app.screen, ConfirmDeleteScreen)

    @patch('src.utils.get_active_tmux_sessions')
    async def test_d_keybinding_opens_delete_confirmation_with_selection(self, mock_sessions: Any, change_to_example_repo: Path) -> None:
        """Test that pressing 'd' opens delete confirmation when worktree is selected."""
        mock_sessions.return_value = set()
        app = GroveApp()

        async with app.run_test() as pilot:
            # Set a selected worktree
            app.selected_worktree = "feature-one"

            # Initially, there should be no modal screen
            assert len(app.screen_stack) == 1

            # Press 'd' key to trigger delete action
            await pilot.press("d")
            await pilot.pause()

            # Verify that a new screen (ConfirmDeleteScreen) has been pushed
            assert len(app.screen_stack) == 2
            assert isinstance(app.screen, ConfirmDeleteScreen)

            # Verify the screen was initialized with correct worktree name
            assert app.screen.worktree_name == "feature-one"

    @patch('src.utils.get_active_tmux_sessions')
    async def test_d_keybinding_shows_warning_without_selection(self, mock_sessions: Any, change_to_example_repo: Path) -> None:
        """Test that pressing 'd' shows warning when no worktree is selected."""
        mock_sessions.return_value = set()
        app = GroveApp()

        async with app.run_test() as pilot:
            # Ensure no worktree is selected
            app.selected_worktree = ""

            # Mock the notify method to capture notifications
            notify_called = False
            notify_message = ""
            notify_severity = ""

            def mock_notify(message: str, severity: str = "information", **kwargs: Any) -> None:
                nonlocal notify_called, notify_message, notify_severity
                notify_called = True
                notify_message = message
                notify_severity = severity

            app.notify = MagicMock(side_effect=mock_notify)

            # Press 'd' key
            await pilot.press("d")
            await pilot.pause()

            # Verify warning notification was shown
            assert notify_called is True
            assert "No worktree selected" in notify_message
            assert notify_severity == "warning"

            # Verify no modal screen was opened
            assert len(app.screen_stack) == 1

    @patch('src.widgets.get_worktree_pr_status')
    @patch('src.widgets.get_active_tmux_sessions')
    @patch('src.app.get_worktree_directories')
    @patch('src.app.get_worktree_pr_status')
    @patch('src.app.get_active_tmux_sessions')
    @patch('src.app.get_tmux_server')
    @patch('src.app.session_exists')
    @patch('src.app.remove_worktree_with_branch')
    @patch('src.utils.get_active_tmux_sessions')
    async def test_worktree_deletion_successful_without_tmux_session(self, mock_sessions: Any, mock_remove_worktree: Any, mock_session_exists: Any, mock_get_server: Any, mock_app_sessions: Any, mock_app_pr: Any, mock_app_dirs: Any, mock_widgets_sessions: Any, mock_widgets_pr: Any, change_to_example_repo: Path) -> None:
        """Test successful worktree deletion when no corresponding tmux session exists."""
        mock_sessions.return_value = set()  # No active sessions
        mock_app_sessions.return_value = set()  # Mock for sidebar refresh
        mock_app_pr.return_value = set()  # Mock for sidebar refresh
        mock_app_dirs.return_value = []  # Mock for sidebar refresh
        mock_widgets_sessions.return_value = set()  # Mock for Sidebar compose
        mock_widgets_pr.return_value = set()  # Mock for Sidebar compose

        # Mock successful worktree removal
        mock_remove_worktree.return_value = (True, "")

        # Mock tmux server and session_exists returning False (session doesn't exist)
        mock_server = MagicMock()
        mock_get_server.return_value = mock_server
        mock_session_exists.return_value = False

        app = GroveApp()

        async with app.run_test() as pilot:
            # Set up selected worktree with prefix
            app.selected_worktree = "ep/test-feature"

            # Mock notifications to track messages
            notifications = []
            def mock_notify(message: str, severity: str = "information", **kwargs: Any) -> None:
                notifications.append((message, severity))

            app.notify = MagicMock(side_effect=mock_notify)

            # Mock sidebar operations
            sidebar = app.query_one("#sidebar", ListView)
            sidebar.clear = MagicMock()
            sidebar.append = MagicMock()

            # Call deletion handler with confirmation
            app.handle_worktree_deletion(True)

            # Verify remove_worktree_with_branch was called correctly
            mock_remove_worktree.assert_called_once_with("ep/test-feature")

            # Verify session_exists was called to check for tmux session
            mock_session_exists.assert_called()

            # Verify success notification
            assert len(notifications) == 1
            assert "deleted successfully" in notifications[0][0]
            assert notifications[0][1] == "information"

            # Verify sidebar was refreshed
            assert sidebar.clear.called
            assert sidebar.append.called

            # Verify selected worktree was cleared
            assert app.selected_worktree == ""

    @patch('src.widgets.get_worktree_pr_status')
    @patch('src.widgets.get_active_tmux_sessions')
    @patch('src.app.get_worktree_directories')
    @patch('src.app.get_worktree_pr_status')
    @patch('src.app.get_active_tmux_sessions')
    @patch('src.app.get_tmux_server')
    @patch('src.app.session_exists')
    @patch('src.app.remove_worktree_with_branch')
    @patch('src.utils.get_active_tmux_sessions')
    async def test_worktree_deletion_successful_with_tmux_session(self, mock_sessions: Any, mock_remove_worktree: Any, mock_session_exists: Any, mock_get_server: Any, mock_app_sessions: Any, mock_app_pr: Any, mock_app_dirs: Any, mock_widgets_sessions: Any, mock_widgets_pr: Any, change_to_example_repo: Path) -> None:
        """Test successful worktree deletion when corresponding tmux session exists."""
        mock_sessions.return_value = set()
        mock_app_sessions.return_value = set()  # Mock for sidebar refresh
        mock_app_pr.return_value = set()  # Mock for sidebar refresh
        mock_app_dirs.return_value = []  # Mock for sidebar refresh
        mock_widgets_sessions.return_value = set()  # Mock for Sidebar compose
        mock_widgets_pr.return_value = set()  # Mock for Sidebar compose

        # Mock successful worktree removal
        mock_remove_worktree.return_value = (True, "")

        # Mock tmux server with session that exists
        mock_session = MagicMock()
        mock_session.kill_session = MagicMock()
        mock_server = MagicMock()
        mock_server.sessions.filter.return_value = [mock_session]
        mock_get_server.return_value = mock_server
        mock_session_exists.return_value = True

        app = GroveApp()

        async with app.run_test() as pilot:
            # Set up selected worktree with prefix
            app.selected_worktree = "feature/awesome-feature"

            # Mock notifications to track messages
            notifications = []
            def mock_notify(message: str, severity: str = "information", **kwargs: Any) -> None:
                notifications.append((message, severity))

            app.notify = MagicMock(side_effect=mock_notify)

            # Mock sidebar operations
            sidebar = app.query_one("#sidebar", ListView)
            sidebar.clear = MagicMock()
            sidebar.append = MagicMock()

            # Call deletion handler with confirmation
            app.handle_worktree_deletion(True)

            # Verify remove_worktree_with_branch was called correctly
            mock_remove_worktree.assert_called_once_with("feature/awesome-feature")

            # Verify session_exists and kill_session were called
            mock_session_exists.assert_called()
            mock_server.sessions.filter.assert_called()
            mock_session.kill_session.assert_called_once()

            # Verify success notification mentions both worktree and tmux session
            assert len(notifications) == 1
            assert "and its tmux session deleted successfully" in notifications[0][0]
            assert notifications[0][1] == "information"

    @patch('src.widgets.get_worktree_pr_status')
    @patch('src.widgets.get_active_tmux_sessions')
    @patch('src.app.get_worktree_directories')
    @patch('src.app.get_worktree_pr_status')
    @patch('src.app.get_active_tmux_sessions')
    @patch('src.app.remove_worktree_with_branch')
    @patch('src.utils.get_active_tmux_sessions')
    async def test_worktree_deletion_handles_worktree_manager_failure(self, mock_sessions: Any, mock_remove_worktree: Any, mock_app_sessions: Any, mock_app_pr: Any, mock_app_dirs: Any, mock_widgets_sessions: Any, mock_widgets_pr: Any, change_to_example_repo: Path) -> None:
        """Test that worktree deletion handles worktree removal failure."""
        mock_sessions.return_value = set()
        mock_app_sessions.return_value = set()  # Mock for sidebar refresh (shouldn't be called)
        mock_app_pr.return_value = set()  # Mock for sidebar refresh (shouldn't be called)
        mock_app_dirs.return_value = []  # Mock for sidebar refresh (shouldn't be called)
        mock_widgets_sessions.return_value = set()  # Mock for Sidebar compose
        mock_widgets_pr.return_value = set()  # Mock for Sidebar compose

        # Mock failed worktree removal
        mock_remove_worktree.return_value = (False, "Git error: Failed to remove worktree")

        app = GroveApp()

        async with app.run_test() as pilot:
            # Set up selected worktree
            app.selected_worktree = "test-feature"

            # Mock notifications to track messages
            notifications = []
            def mock_notify(message: str, severity: str = "information", **kwargs: Any) -> None:
                notifications.append((message, severity))

            app.notify = MagicMock(side_effect=mock_notify)

            # Call deletion handler with confirmation
            app.handle_worktree_deletion(True)

            # Verify error notification was shown
            assert len(notifications) == 1
            assert "Failed to delete worktree" in notifications[0][0]
            assert notifications[0][1] == "error"

            # Verify remove_worktree_with_branch was called
            mock_remove_worktree.assert_called_once_with("test-feature")

    @patch('src.app.get_tmux_server')
    @patch('src.app.session_exists')
    @patch('src.app.remove_worktree_with_branch')
    @patch('src.utils.get_active_tmux_sessions')
    async def test_worktree_deletion_handles_tmux_kill_failure(self, mock_sessions: Any, mock_remove_worktree: Any, mock_session_exists: Any, mock_get_server: Any, change_to_example_repo: Path) -> None:
        """Test that worktree deletion handles tmux kill-session failure gracefully."""
        mock_sessions.return_value = set()

        # Mock successful worktree removal
        mock_remove_worktree.return_value = (True, "")

        # Mock tmux server with session that exists but kill_session raises exception
        mock_session = MagicMock()
        mock_session.kill_session.side_effect = Exception("Failed to kill session")
        mock_server = MagicMock()
        mock_server.sessions.filter.return_value = [mock_session]
        mock_get_server.return_value = mock_server
        mock_session_exists.return_value = True

        app = GroveApp()

        async with app.run_test() as pilot:
            # Set up selected worktree
            app.selected_worktree = "test-feature"

            # Mock notifications to track messages
            notifications = []
            def mock_notify(message: str, severity: str = "information", **kwargs: Any) -> None:
                notifications.append((message, severity))

            app.notify = MagicMock(side_effect=mock_notify)

            # Mock sidebar operations
            sidebar = app.query_one("#sidebar", ListView)
            sidebar.clear = MagicMock()
            sidebar.append = MagicMock()

            # Call deletion handler with confirmation
            app.handle_worktree_deletion(True)

            # Verify warning notification was shown
            assert len(notifications) == 1
            assert "Worktree deleted but failed to kill tmux session" in notifications[0][0]
            assert notifications[0][1] == "warning"

    async def test_worktree_deletion_handles_cancellation(self, change_to_example_repo: Path) -> None:
        """Test that worktree deletion handles cancellation correctly."""
        app = GroveApp()

        async with app.run_test() as pilot:
            # Set up selected worktree
            app.selected_worktree = "test-feature"

            # Call handler with cancellation (False or None)
            app.handle_worktree_deletion(False)
            app.handle_worktree_deletion(None)

            # Should return immediately without doing anything (no assertion needed for early return)

    @patch('src.app.get_tmux_server')
    @patch('src.app.session_exists')
    @patch('src.app.remove_worktree_with_branch')
    @patch('src.utils.get_active_tmux_sessions')
    async def test_worktree_deletion_handles_no_prefix(self, mock_sessions: Any, mock_remove_worktree: Any, mock_session_exists: Any, mock_get_server: Any, change_to_example_repo: Path) -> None:
        """Test that worktree deletion works correctly for worktrees without prefix."""
        mock_sessions.return_value = set()

        # Mock successful worktree removal
        mock_remove_worktree.return_value = (True, "")

        # Mock tmux server where session doesn't exist
        mock_server = MagicMock()
        mock_get_server.return_value = mock_server
        mock_session_exists.return_value = False

        app = GroveApp()

        async with app.run_test() as pilot:
            # Set up selected worktree without prefix (no slash)
            app.selected_worktree = "simple-feature"

            # Mock notifications to track messages
            notifications = []
            def mock_notify(message: str, severity: str = "information", **kwargs: Any) -> None:
                notifications.append((message, severity))

            app.notify = MagicMock(side_effect=mock_notify)

            # Mock sidebar operations
            sidebar = app.query_one("#sidebar", ListView)
            sidebar.clear = MagicMock()
            sidebar.append = MagicMock()

            # Call deletion handler with confirmation
            app.handle_worktree_deletion(True)

            # Verify remove_worktree_with_branch was called
            mock_remove_worktree.assert_called_once_with("simple-feature")