"""Tests for worktree deletion functionality."""

from pathlib import Path
from typing import Any
from unittest.mock import patch, MagicMock

import pytest
from textual.widgets import Label, Button, ListView

from app import GroveApp, ConfirmDeleteScreen


class TestWorktreeDeletion:
    """Tests for worktree deletion feature."""

    @patch('app.get_active_tmux_sessions')
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

    @patch('app.subprocess.run')
    @patch('app.get_active_tmux_sessions')
    async def test_confirm_delete_screen_yes_button(self, mock_sessions: Any, mock_subprocess: Any, change_to_example_repo: Path) -> None:
        """Test that clicking Yes button confirms deletion."""
        mock_sessions.return_value = set()
        mock_subprocess.return_value = MagicMock(returncode=0, stderr="")
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

    @patch('app.get_active_tmux_sessions')
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

    @patch('app.subprocess.run')
    @patch('app.get_active_tmux_sessions')
    async def test_confirm_delete_screen_y_key(self, mock_sessions: Any, mock_subprocess: Any, change_to_example_repo: Path) -> None:
        """Test that pressing 'y' key confirms deletion."""
        mock_sessions.return_value = set()
        mock_subprocess.return_value = MagicMock(returncode=0, stderr="")
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

    @patch('app.get_active_tmux_sessions')
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

    @patch('app.get_active_tmux_sessions')
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

    @patch('app.get_active_tmux_sessions')
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

    @patch('app.get_active_tmux_sessions')
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

    @patch('app.subprocess.run')
    @patch('app.get_active_tmux_sessions')
    async def test_worktree_deletion_successful_without_tmux_session(self, mock_sessions: Any, mock_subprocess: Any, change_to_example_repo: Path) -> None:
        """Test successful worktree deletion when no corresponding tmux session exists."""
        mock_sessions.return_value = set()  # No active sessions

        # Mock successful worktree-manager remove command
        worktree_remove_result = MagicMock(returncode=0, stderr="")

        # Mock tmux has-session command returning failure (session doesn't exist)
        tmux_has_session_result = MagicMock(returncode=1, stderr="session not found")

        # Configure subprocess.run to return different results based on command
        def subprocess_side_effect(cmd, **kwargs):
            if cmd[0] == "worktree-manager":
                return worktree_remove_result
            elif cmd[0] == "tmux" and cmd[1] == "has-session":
                return tmux_has_session_result
            return MagicMock(returncode=0)

        mock_subprocess.side_effect = subprocess_side_effect

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

            # Verify worktree-manager remove was called correctly
            worktree_calls = [call for call in mock_subprocess.call_args_list if call[0][0][0] == "worktree-manager"]
            assert len(worktree_calls) == 1
            assert worktree_calls[0][0][0] == ["worktree-manager", "remove", "ep/test-feature"]
            assert worktree_calls[0][1]["env"]["WORKTREE_PREFIX"] == "ep/"

            # Verify tmux has-session was called
            tmux_calls = [call for call in mock_subprocess.call_args_list if call[0][0][0] == "tmux"]
            assert len(tmux_calls) == 1
            assert tmux_calls[0][0][0] == ["tmux", "has-session", "-t", "ep/test-feature"]

            # Verify success notification
            assert len(notifications) == 1
            assert "deleted successfully" in notifications[0][0]
            assert notifications[0][1] == "information"

            # Verify sidebar was refreshed
            assert sidebar.clear.called
            assert sidebar.append.called

            # Verify selected worktree was cleared
            assert app.selected_worktree == ""

    @patch('app.subprocess.run')
    @patch('app.get_active_tmux_sessions')
    async def test_worktree_deletion_successful_with_tmux_session(self, mock_sessions: Any, mock_subprocess: Any, change_to_example_repo: Path) -> None:
        """Test successful worktree deletion when corresponding tmux session exists."""
        mock_sessions.return_value = set()

        # Mock successful worktree-manager remove command
        worktree_remove_result = MagicMock(returncode=0, stderr="")

        # Mock tmux has-session command returning success (session exists)
        tmux_has_session_result = MagicMock(returncode=0, stderr="")

        # Mock successful tmux kill-session command
        tmux_kill_session_result = MagicMock(returncode=0, stderr="")

        # Configure subprocess.run to return different results based on command
        def subprocess_side_effect(cmd, **kwargs):
            if cmd[0] == "worktree-manager":
                return worktree_remove_result
            elif cmd[0] == "tmux" and cmd[1] == "has-session":
                return tmux_has_session_result
            elif cmd[0] == "tmux" and cmd[1] == "kill-session":
                return tmux_kill_session_result
            return MagicMock(returncode=0)

        mock_subprocess.side_effect = subprocess_side_effect

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

            # Verify worktree-manager remove was called correctly
            worktree_calls = [call for call in mock_subprocess.call_args_list if call[0][0][0] == "worktree-manager"]
            assert len(worktree_calls) == 1
            assert worktree_calls[0][0][0] == ["worktree-manager", "remove", "feature/awesome-feature"]
            assert worktree_calls[0][1]["env"]["WORKTREE_PREFIX"] == "feature/"

            # Verify both tmux commands were called
            tmux_calls = [call for call in mock_subprocess.call_args_list if call[0][0][0] == "tmux"]
            assert len(tmux_calls) == 2

            # Check has-session call
            has_session_call = next(call for call in tmux_calls if call[0][0][1] == "has-session")
            assert has_session_call[0][0] == ["tmux", "has-session", "-t", "feature/awesome-feature"]

            # Check kill-session call
            kill_session_call = next(call for call in tmux_calls if call[0][0][1] == "kill-session")
            assert kill_session_call[0][0] == ["tmux", "kill-session", "-t", "feature/awesome-feature"]

            # Verify success notification mentions both worktree and tmux session
            assert len(notifications) == 1
            assert "and its tmux session deleted successfully" in notifications[0][0]
            assert notifications[0][1] == "information"

    @patch('app.subprocess.run')
    @patch('app.get_active_tmux_sessions')
    async def test_worktree_deletion_handles_worktree_manager_failure(self, mock_sessions: Any, mock_subprocess: Any, change_to_example_repo: Path) -> None:
        """Test that worktree deletion handles worktree-manager command failure."""
        mock_sessions.return_value = set()

        # Mock failed worktree-manager remove command
        mock_subprocess.return_value = MagicMock(returncode=1, stderr="Failed to remove worktree")

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

            # Verify only worktree-manager was called (no tmux commands)
            worktree_calls = [call for call in mock_subprocess.call_args_list if call[0][0][0] == "worktree-manager"]
            tmux_calls = [call for call in mock_subprocess.call_args_list if call[0][0][0] == "tmux"]

            assert len(worktree_calls) == 1
            assert len(tmux_calls) == 0

    @patch('app.subprocess.run')
    @patch('app.get_active_tmux_sessions')
    async def test_worktree_deletion_handles_tmux_kill_failure(self, mock_sessions: Any, mock_subprocess: Any, change_to_example_repo: Path) -> None:
        """Test that worktree deletion handles tmux kill-session failure gracefully."""
        mock_sessions.return_value = set()

        # Mock successful worktree-manager remove command
        worktree_remove_result = MagicMock(returncode=0, stderr="")

        # Mock tmux has-session command returning success (session exists)
        tmux_has_session_result = MagicMock(returncode=0, stderr="")

        # Mock failed tmux kill-session command
        tmux_kill_session_result = MagicMock(returncode=1, stderr="Failed to kill session")

        # Configure subprocess.run to return different results based on command
        def subprocess_side_effect(cmd, **kwargs):
            if cmd[0] == "worktree-manager":
                return worktree_remove_result
            elif cmd[0] == "tmux" and cmd[1] == "has-session":
                return tmux_has_session_result
            elif cmd[0] == "tmux" and cmd[1] == "kill-session":
                return tmux_kill_session_result
            return MagicMock(returncode=0)

        mock_subprocess.side_effect = subprocess_side_effect

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

    @patch('app.subprocess.run')
    @patch('app.get_active_tmux_sessions')
    async def test_worktree_deletion_handles_no_prefix(self, mock_sessions: Any, mock_subprocess: Any, change_to_example_repo: Path) -> None:
        """Test that worktree deletion works correctly for worktrees without prefix."""
        mock_sessions.return_value = set()

        # Mock successful worktree-manager remove command
        mock_subprocess.return_value = MagicMock(returncode=0, stderr="")

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

            # Verify worktree-manager remove was called with empty prefix
            worktree_calls = [call for call in mock_subprocess.call_args_list if call[0][0][0] == "worktree-manager"]
            assert len(worktree_calls) == 1
            assert worktree_calls[0][0][0] == ["worktree-manager", "remove", "simple-feature"]
            assert worktree_calls[0][1]["env"]["WORKTREE_PREFIX"] == ""