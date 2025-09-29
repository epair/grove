"""Tests for PR creation functionality."""

from pathlib import Path
from typing import Any
from unittest.mock import patch, MagicMock

import pytest
from textual.widgets import Label, Input, Button, Checkbox

from app import GroveApp, PRFormScreen


class TestPRCreation:
    """Tests for PR creation feature."""

    @patch('app.get_active_tmux_sessions')
    async def test_p_keybinding_opens_pr_form(self, mock_sessions: Any, change_to_example_repo: Path) -> None:
        """Test that pressing 'p' opens the PRFormScreen."""
        mock_sessions.return_value = set()
        app = GroveApp()

        async with app.run_test() as pilot:
            # Set a selected worktree
            app.selected_worktree = "feature-one"

            # Initially, there should be no modal screen
            assert len(app.screen_stack) == 1

            # Press 'p' key to trigger create PR action
            await pilot.press("p")
            await pilot.pause()

            # Verify that a new screen (PRFormScreen) has been pushed
            assert len(app.screen_stack) == 2
            assert isinstance(app.screen, PRFormScreen)

            # Verify form elements are present
            form = app.screen
            assert form.query_one("#pr_title", Label) is not None
            assert form.query_one("#pr_title_input", Input) is not None
            assert form.query_one("#reviewers_label", Label) is not None
            assert form.query_one("#create_pr_button", Button) is not None
            assert form.query_one("#cancel_pr_button", Button) is not None

    @patch('app.get_active_tmux_sessions')
    async def test_p_keybinding_shows_warning_without_selection(self, mock_sessions: Any, change_to_example_repo: Path) -> None:
        """Test that pressing 'p' shows warning when no worktree is selected."""
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

            # Press 'p' key
            await pilot.press("p")
            await pilot.pause()

            # Verify warning notification was shown
            assert notify_called is True
            assert "No worktree selected" in notify_message
            assert notify_severity == "warning"

            # Verify no modal screen was opened
            assert len(app.screen_stack) == 1

    @patch('app.get_active_tmux_sessions')
    async def test_pr_form_checkboxes_present(self, mock_sessions: Any, change_to_example_repo: Path) -> None:
        """Test that PR form has all required checkboxes."""
        mock_sessions.return_value = set()
        app = GroveApp()

        async with app.run_test() as pilot:
            app.selected_worktree = "feature-one"
            await pilot.press("p")
            await pilot.pause()

            form = app.screen
            # Check all reviewer checkboxes are present
            reviewers = ["njm", "swlkr", "daviswahl", "BryceFrye", "neddenriep", "gorilla076"]
            for reviewer in reviewers:
                checkbox = form.query_one(f"#checkbox_{reviewer}", Checkbox)
                assert checkbox is not None
                assert reviewer in str(checkbox.label)

    @patch('app.get_active_tmux_sessions')
    async def test_pr_form_njm_selected_by_default(self, mock_sessions: Any, change_to_example_repo: Path) -> None:
        """Test that 'njm' checkbox is selected by default."""
        mock_sessions.return_value = set()
        app = GroveApp()

        async with app.run_test() as pilot:
            app.selected_worktree = "feature-one"
            await pilot.press("p")
            await pilot.pause()

            form = app.screen
            # Check that njm is selected by default
            njm_checkbox = form.query_one("#checkbox_njm", Checkbox)
            assert njm_checkbox.value is True

            # Check that others are not selected
            other_reviewers = ["swlkr", "daviswahl", "BryceFrye", "neddenriep", "gorilla076"]
            for reviewer in other_reviewers:
                checkbox = form.query_one(f"#checkbox_{reviewer}", Checkbox)
                assert checkbox.value is False

    @patch('app.get_active_tmux_sessions')
    async def test_pr_form_cancel_button_closes_form(self, mock_sessions: Any, change_to_example_repo: Path) -> None:
        """Test that clicking Cancel button closes the PR form."""
        mock_sessions.return_value = set()
        app = GroveApp()

        async with app.run_test() as pilot:
            app.selected_worktree = "feature-one"
            await pilot.press("p")
            await pilot.pause()

            # Verify we're on the PR form screen
            assert isinstance(app.screen, PRFormScreen)

            # Click cancel button
            await pilot.click("#cancel_pr_button")
            await pilot.pause()

            # Verify we're back to the main screen
            assert not isinstance(app.screen, PRFormScreen)

    @patch('app.get_active_tmux_sessions')
    async def test_pr_form_escape_key_closes_form(self, mock_sessions: Any, change_to_example_repo: Path) -> None:
        """Test that pressing Escape key closes the PR form."""
        mock_sessions.return_value = set()
        app = GroveApp()

        async with app.run_test() as pilot:
            app.selected_worktree = "feature-one"
            await pilot.press("p")
            await pilot.pause()

            # Verify we're on the PR form screen
            assert isinstance(app.screen, PRFormScreen)

            # Press Escape key
            await pilot.press("escape")
            await pilot.pause()

            # Verify we're back to the main screen
            assert not isinstance(app.screen, PRFormScreen)

    @patch('app.get_active_tmux_sessions')
    async def test_pr_form_validation_empty_title(self, mock_sessions: Any, change_to_example_repo: Path) -> None:
        """Test that PR form doesn't submit with empty title."""
        mock_sessions.return_value = set()
        app = GroveApp()

        async with app.run_test() as pilot:
            app.selected_worktree = "feature-one"
            await pilot.press("p")
            await pilot.pause()

            form = app.screen
            # Leave title empty
            title_input = form.query_one("#pr_title_input", Input)
            title_input.value = ""

            # Click create button with empty title
            await pilot.click("#create_pr_button")
            await pilot.pause()

            # Verify we're still on the form screen (validation prevented submission)
            assert isinstance(app.screen, PRFormScreen)

    @patch('app.subprocess.run')
    @patch('app.get_active_tmux_sessions')
    async def test_pr_form_submission_with_valid_data(self, mock_sessions: Any, mock_subprocess: Any, change_to_example_repo: Path) -> None:
        """Test that PR form submits correctly with valid data."""
        mock_sessions.return_value = set()

        # Mock successful git and gh commands
        def subprocess_side_effect(cmd, **kwargs):
            if 'git' in cmd[0] and 'branch' in cmd:
                return MagicMock(returncode=0, stdout="test-branch", stderr="")
            elif 'git' in cmd[0] and 'push' in cmd:
                return MagicMock(returncode=0, stdout="", stderr="")
            elif 'gh' in cmd[0]:
                return MagicMock(returncode=0, stdout="https://github.com/user/repo/pull/123", stderr="")
            return MagicMock(returncode=0, stdout="", stderr="")

        mock_subprocess.side_effect = subprocess_side_effect

        app = GroveApp()

        async with app.run_test() as pilot:
            # Mock app.exit to prevent actual exit
            exit_called = False
            def mock_exit() -> None:
                nonlocal exit_called
                exit_called = True
            app.exit = MagicMock(side_effect=mock_exit)

            app.selected_worktree = "feature-one"
            await pilot.press("p")
            await pilot.pause()

            form = app.screen
            # Set PR title
            title_input = form.query_one("#pr_title_input", Input)
            title_input.value = "Add awesome feature"

            # Select additional reviewers
            checkbox_swlkr = form.query_one("#checkbox_swlkr", Checkbox)
            checkbox_swlkr.toggle()

            # Click create button
            await pilot.click("#create_pr_button")
            await pilot.pause()

            # Verify subprocess was called
            assert mock_subprocess.called

            # Verify git commands were called
            git_calls = [call for call in mock_subprocess.call_args_list if 'git' in call[0][0][0]]
            assert len(git_calls) >= 2  # branch and push

            # Verify gh command was called
            gh_calls = [call for call in mock_subprocess.call_args_list if 'gh' in call[0][0][0]]
            assert len(gh_calls) == 1

    @patch('app.subprocess.run')
    @patch('app.get_active_tmux_sessions')
    async def test_pr_form_handles_git_push_failure(self, mock_sessions: Any, mock_subprocess: Any, change_to_example_repo: Path) -> None:
        """Test that PR form handles git push failure gracefully."""
        mock_sessions.return_value = set()

        # Mock git branch success but push failure
        def subprocess_side_effect(cmd, **kwargs):
            if 'git' in cmd[0] and 'branch' in cmd:
                return MagicMock(returncode=0, stdout="test-branch", stderr="")
            elif 'git' in cmd[0] and 'push' in cmd:
                return MagicMock(returncode=1, stdout="", stderr="Failed to push")
            return MagicMock(returncode=0, stdout="", stderr="")

        mock_subprocess.side_effect = subprocess_side_effect

        app = GroveApp()

        async with app.run_test() as pilot:
            # Mock notify to track error
            notifications = []
            def mock_notify(message: str, severity: str = "information", **kwargs: Any) -> None:
                notifications.append((message, severity))
            app.notify = MagicMock(side_effect=mock_notify)

            app.selected_worktree = "feature-one"

            # Call handler directly with form data
            form_data = {"title": "Test PR", "reviewers": ["njm"]}
            app.handle_pr_submission(form_data)

            # Verify error notification was shown
            assert len(notifications) == 1
            assert "Failed to push" in notifications[0][0]
            assert notifications[0][1] == "error"

    @patch('app.subprocess.run')
    @patch('app.get_active_tmux_sessions')
    async def test_pr_form_handles_gh_pr_create_failure(self, mock_sessions: Any, mock_subprocess: Any, change_to_example_repo: Path) -> None:
        """Test that PR form handles gh pr create failure gracefully."""
        mock_sessions.return_value = set()

        # Mock successful git commands but gh pr create failure
        def subprocess_side_effect(cmd, **kwargs):
            if 'git' in cmd[0] and 'branch' in cmd:
                return MagicMock(returncode=0, stdout="test-branch", stderr="")
            elif 'git' in cmd[0] and 'push' in cmd:
                return MagicMock(returncode=0, stdout="", stderr="")
            elif 'gh' in cmd[0]:
                return MagicMock(returncode=1, stdout="", stderr="Failed to create PR")
            return MagicMock(returncode=0, stdout="", stderr="")

        mock_subprocess.side_effect = subprocess_side_effect

        app = GroveApp()

        async with app.run_test() as pilot:
            # Mock notify to track error
            notifications = []
            def mock_notify(message: str, severity: str = "information", **kwargs: Any) -> None:
                notifications.append((message, severity))
            app.notify = MagicMock(side_effect=mock_notify)

            app.selected_worktree = "feature-one"

            # Call handler directly with form data
            form_data = {"title": "Test PR", "reviewers": ["njm", "swlkr"]}
            app.handle_pr_submission(form_data)

            # Verify error notification was shown
            assert len(notifications) == 1
            assert "Failed to create PR" in notifications[0][0]
            assert notifications[0][1] == "error"

    @patch('app.subprocess.run')
    @patch('app.get_active_tmux_sessions')
    @patch('app.Path.write_text')
    async def test_pr_form_writes_env_file(self, mock_write_text: Any, mock_sessions: Any, mock_subprocess: Any, change_to_example_repo: Path) -> None:
        """Test that PR form writes WORKTREE_PR_PUBLISHED to .env file."""
        mock_sessions.return_value = set()

        # Mock successful git and gh commands
        def subprocess_side_effect(cmd, **kwargs):
            if 'git' in cmd[0] and 'branch' in cmd:
                return MagicMock(returncode=0, stdout="test-branch", stderr="")
            elif 'git' in cmd[0] and 'push' in cmd:
                return MagicMock(returncode=0, stdout="", stderr="")
            elif 'gh' in cmd[0]:
                return MagicMock(returncode=0, stdout="https://github.com/user/repo/pull/123", stderr="")
            elif 'open' in cmd[0]:
                return MagicMock(returncode=0, stdout="", stderr="")
            return MagicMock(returncode=0, stdout="", stderr="")

        mock_subprocess.side_effect = subprocess_side_effect

        app = GroveApp()

        async with app.run_test() as pilot:
            # Mock app.exit to prevent actual exit
            app.exit = MagicMock()

            app.selected_worktree = "feature-one"

            # Call handler directly with form data
            form_data = {"title": "Test PR", "reviewers": []}
            app.handle_pr_submission(form_data)

            # Verify .env file write was attempted
            assert mock_write_text.called
            written_content = mock_write_text.call_args[0][0]
            assert "WORKTREE_PR_PUBLISHED=true" in written_content

    @patch('app.subprocess.run')
    @patch('app.get_active_tmux_sessions')
    async def test_pr_form_enter_key_submission(self, mock_sessions: Any, mock_subprocess: Any, change_to_example_repo: Path) -> None:
        """Test that pressing Enter in title field submits the PR form."""
        mock_sessions.return_value = set()

        # Mock successful git and gh commands
        def subprocess_side_effect(cmd, **kwargs):
            if 'git' in cmd[0] and 'branch' in cmd:
                return MagicMock(returncode=0, stdout="test-branch", stderr="")
            elif 'git' in cmd[0] and 'push' in cmd:
                return MagicMock(returncode=0, stdout="", stderr="")
            elif 'gh' in cmd[0]:
                return MagicMock(returncode=0, stdout="https://github.com/user/repo/pull/123", stderr="")
            return MagicMock(returncode=0, stdout="", stderr="")

        mock_subprocess.side_effect = subprocess_side_effect

        app = GroveApp()

        async with app.run_test() as pilot:
            # Mock app.exit to prevent actual exit
            app.exit = MagicMock()

            app.selected_worktree = "feature-one"
            await pilot.press("p")
            await pilot.pause()

            form = app.screen
            # Set PR title
            title_input = form.query_one("#pr_title_input", Input)
            title_input.value = "Quick PR via Enter"

            # Focus title input and press Enter
            title_input.focus()
            await pilot.press("enter")
            await pilot.pause()

            # Verify subprocess was called (form was submitted)
            assert mock_subprocess.called

    async def test_pr_form_handles_cancellation(self, change_to_example_repo: Path) -> None:
        """Test that PR form handles cancellation correctly."""
        app = GroveApp()

        async with app.run_test() as pilot:
            app.selected_worktree = "feature-one"

            # Call handler with None (cancelled form)
            app.handle_pr_submission(None)

            # Should return immediately without doing anything (no assertion needed for None return)