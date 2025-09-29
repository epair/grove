"""Tests for worktree creation functionality."""

from pathlib import Path
from typing import Any
from unittest.mock import patch, MagicMock

import pytest
from textual.widgets import Label, Input, Button

from app import GroveApp, WorktreeFormScreen


class TestWorktreeCreation:
    """Tests for worktree creation feature."""

    @patch('app.get_active_tmux_sessions')
    async def test_n_keybinding_opens_worktree_form(self, mock_sessions: Any, change_to_example_repo: Path) -> None:
        """Test that pressing 'n' opens the WorktreeFormScreen."""
        mock_sessions.return_value = set()
        app = GroveApp()

        async with app.run_test() as pilot:
            # Initially, there should be no modal screen
            assert len(app.screen_stack) == 1

            # Press 'n' key to trigger new worktree action
            await pilot.press("n")

            # Verify that a new screen (WorktreeFormScreen) has been pushed
            assert len(app.screen_stack) == 2
            assert isinstance(app.screen, WorktreeFormScreen)

            # Verify form elements are present
            form = app.screen
            assert form.query_one("#title", Label) is not None
            assert form.query_one("#prefix_input", Input) is not None
            assert form.query_one("#name_input", Input) is not None
            assert form.query_one("#create_button", Button) is not None
            assert form.query_one("#cancel_button", Button) is not None

    @patch('app.get_active_tmux_sessions')
    async def test_worktree_form_initial_values(self, mock_sessions: Any, change_to_example_repo: Path) -> None:
        """Test that the WorktreeFormScreen has correct initial values."""
        mock_sessions.return_value = set()
        app = GroveApp()

        async with app.run_test() as pilot:
            # Press 'n' to open the form
            await pilot.press("n")

            form = app.screen
            # Check prefix input has default value
            prefix_input = form.query_one("#prefix_input", Input)
            assert prefix_input.value == "ep/"

            # Check name input is empty
            name_input = form.query_one("#name_input", Input)
            assert name_input.value == ""

    @patch('app.get_active_tmux_sessions')
    async def test_cancel_button_closes_form(self, mock_sessions: Any, change_to_example_repo: Path) -> None:
        """Test that clicking Cancel button closes the form."""
        mock_sessions.return_value = set()
        app = GroveApp()

        async with app.run_test() as pilot:
            # Press 'n' to open the form
            await pilot.press("n")

            # Verify we're on the form screen
            assert isinstance(app.screen, WorktreeFormScreen)

            # Click cancel button
            await pilot.click("#cancel_button")
            await pilot.pause()

            # Verify we're back to the main screen
            assert not isinstance(app.screen, WorktreeFormScreen)

    @patch('app.get_active_tmux_sessions')
    async def test_escape_key_closes_form(self, mock_sessions: Any, change_to_example_repo: Path) -> None:
        """Test that pressing Escape key closes the form."""
        mock_sessions.return_value = set()
        app = GroveApp()

        async with app.run_test() as pilot:
            # Press 'n' to open the form
            await pilot.press("n")

            # Verify we're on the form screen
            assert isinstance(app.screen, WorktreeFormScreen)

            # Press Escape key
            await pilot.press("escape")
            await pilot.pause()

            # Verify we're back to the main screen
            assert not isinstance(app.screen, WorktreeFormScreen)

    @patch('app.get_active_tmux_sessions')
    async def test_create_button_with_empty_name_validation(self, mock_sessions: Any, change_to_example_repo: Path) -> None:
        """Test that create button doesn't submit when name is empty."""
        mock_sessions.return_value = set()
        app = GroveApp()

        async with app.run_test() as pilot:
            # Press 'n' to open the form
            await pilot.press("n")

            form = app.screen
            # Set prefix but leave name empty
            prefix_input = form.query_one("#prefix_input", Input)
            prefix_input.value = "test/"

            # Click create button with empty name
            await pilot.click("#create_button")
            await pilot.pause()

            # Verify we're still on the form screen (validation prevented submission)
            assert isinstance(app.screen, WorktreeFormScreen)

    @patch('app.subprocess.run')
    @patch('app.get_active_tmux_sessions')
    async def test_create_button_with_valid_data(self, mock_sessions: Any, mock_subprocess: Any, change_to_example_repo: Path) -> None:
        """Test that create button submits form with valid data."""
        mock_sessions.return_value = set()
        # Mock successful subprocess calls
        mock_subprocess.return_value = MagicMock(returncode=0, stderr="")

        app = GroveApp()

        async with app.run_test() as pilot:
            # Mock app.exit to prevent actual exit
            exit_mock = MagicMock()
            app.exit = exit_mock  # type: ignore[method-assign]

            # Press 'n' to open the form
            await pilot.press("n")

            form = app.screen
            # Set both prefix and name
            prefix_input = form.query_one("#prefix_input", Input)
            name_input = form.query_one("#name_input", Input)

            prefix_input.value = "test/"
            name_input.value = "my-feature"

            # Click create button
            await pilot.click("#create_button")
            await pilot.pause()

            # Verify subprocess was called (form was submitted)
            assert mock_subprocess.called

    @patch('app.subprocess.run')
    @patch('app.get_active_tmux_sessions')
    async def test_enter_key_in_name_field_submits_form(self, mock_sessions: Any, mock_subprocess: Any, change_to_example_repo: Path) -> None:
        """Test that pressing Enter in name field submits the form."""
        mock_sessions.return_value = set()
        # Mock successful subprocess calls
        mock_subprocess.return_value = MagicMock(returncode=0, stderr="")

        app = GroveApp()

        async with app.run_test() as pilot:
            # Mock app.exit to prevent actual exit
            exit_mock = MagicMock()
            app.exit = exit_mock  # type: ignore[method-assign]

            # Press 'n' to open the form
            await pilot.press("n")

            form = app.screen
            # Set both prefix and name
            prefix_input = form.query_one("#prefix_input", Input)
            name_input = form.query_one("#name_input", Input)

            prefix_input.value = "feature/"
            name_input.value = "awesome-feature"

            # Focus name input and press Enter
            name_input.focus()
            await pilot.press("enter")
            await pilot.pause()

            # Verify subprocess was called (form was submitted)
            assert mock_subprocess.called

    @patch('app.subprocess.run')
    @patch('app.get_active_tmux_sessions')
    async def test_worktree_creation_subprocess_calls(self, mock_sessions: Any, mock_subprocess: Any, change_to_example_repo: Path) -> None:
        """Test that worktree creation makes correct subprocess calls."""
        mock_sessions.return_value = set()

        # Mock successful worktree-manager command
        mock_subprocess.return_value = MagicMock(returncode=0, stderr="")

        app = GroveApp()

        async with app.run_test() as pilot:
            # Mock app.exit to prevent actual exit
            exit_called = False
            def mock_exit() -> None:
                nonlocal exit_called
                exit_called = True
            exit_mock = MagicMock(side_effect=mock_exit)
            app.exit = exit_mock  # type: ignore[method-assign]

            # Simulate form data from user input
            form_data = {"prefix": "ep/", "name": "test-feature"}

            # Call the handler directly
            app.handle_worktree_creation(form_data)

            # Verify subprocess calls were made correctly (should have at least 2 calls)
            assert mock_subprocess.call_count >= 2

            # Find the worktree-manager and tmux-sessionizer calls
            worktree_call = None
            tmux_call = None

            for call in mock_subprocess.call_args_list:
                cmd = call[0][0]
                if cmd[0] == "worktree-manager":
                    worktree_call = call
                elif cmd[0] == "tmux-sessionizer":
                    tmux_call = call

            # Verify worktree-manager call
            assert worktree_call is not None
            assert worktree_call[0][0] == ["worktree-manager", "add", "test-feature"]
            assert worktree_call[1]["env"]["WORKTREE_PREFIX"] == "ep/"

            # Verify tmux-sessionizer call
            assert tmux_call is not None
            expected_path = str(Path.cwd() / "test-feature")
            assert tmux_call[0][0] == ["tmux-sessionizer", expected_path]

            # Verify app exit was called on success
            assert exit_called is True

    @patch('app.subprocess.run')
    @patch('app.get_active_tmux_sessions')
    async def test_worktree_creation_handles_command_failure(self, mock_sessions: Any, mock_subprocess: Any, change_to_example_repo: Path) -> None:
        """Test that worktree creation handles command failures gracefully."""
        mock_sessions.return_value = set()

        # Mock failed worktree-manager command
        mock_subprocess.return_value = MagicMock(returncode=1, stderr="Command failed")

        app = GroveApp()

        async with app.run_test() as pilot:
            # Mock app.notify to track error messages
            notify_called = False
            notify_message = ""
            notify_severity = ""

            def mock_notify(message: str, severity: str = "information", **kwargs: Any) -> None:
                nonlocal notify_called, notify_message, notify_severity
                notify_called = True
                notify_message = message
                notify_severity = severity

            notify_mock = MagicMock(side_effect=mock_notify)
            app.notify = notify_mock  # type: ignore[method-assign]

            # Simulate form data from user input
            form_data = {"prefix": "ep/", "name": "test-feature"}

            # Call the handler directly
            app.handle_worktree_creation(form_data)

            # Verify error notification was shown
            assert notify_called is True
            assert "Failed to create worktree" in notify_message
            assert notify_severity == "error"

            # Verify worktree-manager was called but tmux-sessionizer was not
            worktree_call = None
            tmux_call = None

            for call in mock_subprocess.call_args_list:
                cmd = call[0][0]
                if cmd[0] == "worktree-manager":
                    worktree_call = call
                elif cmd[0] == "tmux-sessionizer":
                    tmux_call = call

            assert worktree_call is not None  # worktree-manager was called
            assert tmux_call is None  # tmux-sessionizer was not called

    async def test_worktree_creation_handles_cancel(self, change_to_example_repo: Path) -> None:
        """Test that worktree creation handles cancellation correctly."""
        app = GroveApp()

        async with app.run_test() as pilot:
            # Call handler with None (cancelled form)
            app.handle_worktree_creation(None)

            # Should return immediately without doing anything (no assertion needed for None return)